import logging
import json
import requests
import os
from celery.task import task
from datetime import datetime, timedelta
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.template import Context, Template
from cabot.metricsapp.api import get_dashboard_info, get_updated_datetime, get_panel_info, \
    get_es_status_check_fields, get_series_ids, adjust_time_range
from cabot.metricsapp.defs import GRAFANA_SYNC_TIMEDELTA_MINUTES
from cabot.metricsapp.models import MetricsStatusCheckBase, ElasticsearchStatusCheck, GrafanaDataSource, \
    GrafanaInstance, GrafanaPanel
from cabot.metricsapp.templates import SOURCE_CHANGED_EXISTING, SOURCE_CHANGED_NONEXISTING, \
    SERIES_CHANGED, ES_QUERIES_CHANGED
import jsondiff

logger = logging.getLogger(__name__)


def _dashboard_deleted_handler(check, panel):
    """
    When the dashboard is deleted in Grafana, deactivate the check and send an email
    :param check: the status check
    :param panel: the GrafanaPanel object
    :return None
    """
    check.active = False
    check.save()
    send_grafana_sync_email.apply_async(args=([str(check.created_by.email)],
                                              '{}\n\n'
                                              'Dashboard "{}" has been deleted, so check "{}" has been deactivated. '
                                              'If you would like to keep the check, re-enable it with '
                                              'auto_sync: False.'
                                              .format(check.get_url_for_check(),
                                                      panel.dashboard_uri.split('/')[1],
                                                      check.name),
                                              check.name))


def _panel_deleted_handler(check, panel, dashboard_meta):
    """
    When a check's panel is deleted in Grafana, deactivate the check and send an email
    :param check: the status check
    :param panel: the GrafanaPanel object
    :param dashboard_meta: "meta" section of Grafana dashboard api response
    :return None
    """
    check.active = False
    check.save()
    send_grafana_sync_email.apply_async(args=([str(check.created_by.email), str(dashboard_meta['createdBy']),
                                               str(dashboard_meta['updatedBy'])],
                                              '{}\n\n'
                                              'Panel {} in dashboard "{}" has been deleted, so check "{}" has been '
                                              'deactivated. If you would like to keep the check, re-enable it with '
                                              'auto_sync: False.'.format(check.get_url_for_check(),
                                                                         panel.panel_id,
                                                                         panel.dashboard_uri.split('/')[1],
                                                                         check.name),
                                              check.name))


@task(ignore_result=True)
def sync_all_grafana_checks(validate_sites=True):
    """Task to sync all status checks with auto_sync set to their Grafana dashbaords"""
    sync_time = datetime.now()

    # Check if any Grafana sites are down and if so, exclude checks for that instance
    inaccessible_panels = []
    if validate_sites:
        for site in GrafanaInstance.objects.all():
            response = site.get_request()
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as e:
                logger.exception('Request to Grafana site {} failed with {}'.format(site.url, e))
                inaccessible_panels.extend(GrafanaPanel.objects.filter(grafana_instance=site))

    for check in MetricsStatusCheckBase.objects.filter(auto_sync=True).filter(active=True)\
            .exclude(grafana_panel__isnull=True).exclude(grafana_panel__in=inaccessible_panels):
        sync_grafana_check.apply_async(args=(check.id, str(sync_time)))


def grafana_query_diff(old_queries, new_queries):
    # type: (dict, dict) -> str
    """returns human-readable diff between two Grafana query strings"""

    # dump=True converts the result to a string and replaces the special keys
    # jsondiff.delete and jsondiff.insert with the strings "$delete" and "$insert"
    # if we don't do dump=True, json.dumps will sometimes barf because it doesn't know what to do with these symbols
    diff = jsondiff.diff(old_queries, new_queries, dump=True)

    # since we had to dump to string to fix the symbols, we have to re-parse the string in order to pretty-print it
    diff = json.loads(diff)
    diff = json.dumps(diff, indent=2, sort_keys=True)  # pretty-print it
    return diff


@task(ignore_result=True)
def sync_grafana_check(check_id, sync_time):
    """
    Sync a check to a dashboard (sync fields: name, data source, series, ES queries)
    :param check_id: id of the status check
    :param sync_time: time the sync started (will check if there were changes before this time)
    :return None
    """
    check = MetricsStatusCheckBase.objects.get(id=check_id)
    panel = check.grafana_panel
    grafana_instance = panel.grafana_instance

    try:
        dashboard_info = get_dashboard_info(grafana_instance, panel.dashboard_uri)
    except ValidationError:
        # Dashboard does not exist--deactive check
        _dashboard_deleted_handler(check, panel)
        return

    last_updated = get_updated_datetime(dashboard_info)
    sync_time = datetime.strptime(sync_time, '%Y-%m-%d %H:%M:%S.%f')

    # Check if the dashboard has been updated since the last sync_grafana_check ran
    if sync_time - last_updated < timedelta(minutes=GRAFANA_SYNC_TIMEDELTA_MINUTES):
        # Check if anything relevant to the check is changed
        try:
            panel_info = get_panel_info(dashboard_info, panel.panel_id)
        except ValidationError:
            # Panel does not exist--deactivate check
            _panel_deleted_handler(check, panel, dashboard_info['meta'])
            return

        context_dict = dict()
        changed_message = []

        # Check datasource parity
        source_name = panel_info.get('datasource') or 'default'
        old_source_possibilities = [source.grafana_source_name for source in GrafanaDataSource.objects.filter(
                                        metrics_source_base=check.source,
                                        grafana_instance_id=grafana_instance.id
                                    )]
        if source_name not in old_source_possibilities:
            context_dict['old_source'] = ' or '.join(old_source_possibilities)
            context_dict['new_source'] = source_name

            if GrafanaDataSource.objects.filter(grafana_source_name=source_name).exists():
                changed_message.append(SOURCE_CHANGED_EXISTING)
                source = GrafanaDataSource.objects.get(grafana_source_name=source_name)
                check.source = source
                check.save()
            else:
                changed_message.append(SOURCE_CHANGED_NONEXISTING)

        # Check series parity
        series_ids = get_series_ids(panel_info)
        if series_ids != panel.series_ids:
            context_dict['old_series'] = panel.series_ids
            context_dict['new_series'] = series_ids
            changed_message.append(SERIES_CHANGED)
            panel.series_ids = series_ids
            panel.save()

        # Check Elasticsearch query parity (if it's an Elasticsearch status check)
        if ElasticsearchStatusCheck.objects.filter(id=check_id).exists():
            queries = get_es_status_check_fields(dashboard_info, panel_info, panel.selected_series)['queries']
            # Don't change the time range specified in the check
            queries = adjust_time_range(queries, check.time_range)

            old_queries = check.queries
            check.queries = json.dumps(queries)
            # Saving the check adjust the time range, so might change the queries
            check.save()
            if check.queries != old_queries:
                context_dict['old_queries'] = str(old_queries)
                context_dict['new_queries'] = str(check.queries)
                context_dict['queries_diff'] = grafana_query_diff(json.loads(old_queries), queries)
                changed_message.append(ES_QUERIES_CHANGED)

        # If anything has changed, send an email!
        if changed_message != []:
            context = Context(context_dict)
            template = Template('{}\n\n{}'.format(check.get_url_for_check(), '\n\n'.join(changed_message)))

            email_list = []
            if check.created_by is not None:
                email_list.append(str(check.created_by.email))

            # Only email grafana dashboard creator and updater if they're Cabot users
            dashboard_meta = dashboard_info['meta']
            for email in [str(dashboard_meta['createdBy']), str(dashboard_meta['updatedBy'])]:
                if User.objects.filter(email=email).exists():
                    email_list.append(email)

            send_grafana_sync_email.apply_async(args=(email_list, template.render(context), check.name))


@task(ignore_result=True)
def send_grafana_sync_email(emails, message, check_name):
    """
    Send an email about a dashboard being updated from Grafana
    :param emails: list of emails to send to
    :param message: message listing the changes
    :param check_name: name of the status check
    :return None
    """
    send_mail(subject='Cabot check {} changed due to Grafana dashboard update'.format(check_name),
              message=message,
              from_email='Cabot Updates<{}>'.format(os.environ.get('CABOT_FROM_EMAIL')),
              recipient_list=emails)
