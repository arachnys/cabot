import json
import logging
import requests
from django.core.exceptions import ValidationError
from pytimeparse import parse


logger = logging.getLogger(__name__)


def get_dashboards(grafana_instance):
    """
    Get information about all Grafana dashboards from the API
    :param grafana_instance: GrafanaInstance object corresponding to the Grafana site
    :return: api response containing dashboard id, title, uri, etc.
    """
    response = grafana_instance.get_request('api/search')

    try:
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        logger.exception('Request to {} failed with error {}'.format(grafana_instance.url, e))
        raise ValidationError('Request to Grafana API failed.')


def get_dashboard_choices(api_response):
    """
    Given a response from the Grafana API, find a list of dashboard name choices
    :param api_response: response data from the Grafana API
    :return: list of dashboard URIs and names
    """
    return [(dash['uri'], dash['title']) for dash in api_response]


def get_dashboard_info(grafana_instance, dashboard_uri):
    """
    Get information about a Grafana dashboard
    :param grafana_instance: GrafanaInstance object corresponding to the Grafana site
    :param dashboard_uri: dashboard part of the url
    :return: api response containing creator information and panel information
    """
    response = grafana_instance.get_request('api/dashboards/{}'.format(dashboard_uri))

    try:
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        logger.exception('Request to {} for dashboard {} failed with error {}'.format(grafana_instance.url,
                                                                                      dashboard_uri, e))
        raise ValidationError('Request to Grafana API failed.')


def get_panel_choices(dashboard_info, templating_dict):
    """
    Get a list of graph panel choices (names and data)
    :param dashboard_info: Dashboard data from the Grafana API
    :param templating_dict: dictionary of {template_name, template_value}
    :return list of ({panel_id, datasource, panel_info}, name) tuples for panels
    """
    panels = []
    for row in dashboard_info['dashboard']['rows']:
        for panel in filter(lambda panel: panel['type'] == 'graph', row['panels']):
            datasource = panel.get('datasource')
            # default datasource is not listed in the API response
            if datasource is None:
                datasource = 'default'

            title = template_response(panel['title'], templating_dict)
            panels.append((dict(panel_id=panel['id'], datasource=datasource, panel_info=panel), title))

    return panels


def get_series_choices(panel_info, templating_dict):
    """
    Get a list of the series for the panel with the input id
    :param panel_id: the id of the selected panel
    :param templating_dict: dictionary of {template_name, template_value}
    :return list of (id, series_info) tuples from the series in the panel
    """
    templated_panel = template_response(panel_info, templating_dict)
    out = []
    # Will display all fields in a json blob (not pretty but it works)
    for series in filter(lambda s: s.get('hide') is not True, templated_panel['targets']):
        # ref_id, datasource type, and timefield aren't useful info to display
        ref_id = series.pop('refId')
        series.pop('dsType')
        series.pop('timeField')
        out.append((ref_id, json.dumps(series)))
    return out


def template_response(data, templating_dict):
    """
    Change data from the Grafana dashboard API response
    based on the dashboard templates
    :param data: Data from the Grafana dashboard API
    :param templating_dict: dictionary of {template_name, template _value}
    :return: panel_info with all templating values filled in
    """
    data = json.dumps(data)
    # Loop through all the templates and replace them if they're used in this panel
    for template in templating_dict:
        data = data.replace('${}'.format(template), templating_dict[template])
    return json.loads(data)


def create_generic_templating_dict(dashboard_info):
    """
    Generic templating dictionary: name just maps to value
    :param dashboard_info: Grafana dashboard API response
    :return: dict of {"name": "value"}
    """
    templates = {}

    templating_info = dashboard_info['dashboard']['templating']
    for template in filter(lambda template: template.get('current'), templating_info['list']):
        value = template['current']['value']
        name = template['name']

        if isinstance(value, list):
            value = ', '.join(value)
        elif value == '$__auto_interval':
            value = 'auto'

        templates[name] = value

    return templates


def get_status_check_fields(dashboard_info, panel_info, grafana_instance_id, datasource, templating_dict):
    """
    Given dashboard, panel, instance, and datasource info, find the fields for a generic status check
    :param dashboard_info: Grafana API dashboard info
    :param panel_info: Grafana API panel info
    :param grafana_instance_id: ID of the Grafana instance used
    :param templating_dict: dictionary of {template_name, template _value}
    :return: dictionary containing StatusCheck field names and values
    """
    fields = {}

    fields['name'] = template_response(panel_info['title'], templating_dict)
    fields['source_info'] = dict(grafana_source_name=datasource,
                                 grafana_instance_id=grafana_instance_id)

    # Earliest time should be formatted "now-3h", all other formats will be ignored
    time_from = dashboard_info['dashboard']['time']['from'].split('-')
    if len(time_from) == 2:
        timestring = str(time_from[1])
        # pytimeparse.parse returns seconds, we want minutes
        fields['time_range'] = parse(timestring) / 60

    thresholds = panel_info['thresholds']
    for threshold in thresholds:
        if threshold['op'] == 'gt':
            fields['check_type'] = '>'
        else:
            fields['check_type'] = '<'

        color = threshold['colorMode']
        if color == 'warning':
            fields['warning_value'] = float(threshold['value'])
        elif color == 'critical':
            fields['high_alert_value'] = float(threshold['value'])

    return fields
