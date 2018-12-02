# -*- coding: utf-8 -*-
import json
import requests
from urlparse import urlparse

from django.db import models
from django.utils import timezone

from cabot.cabotapp.models import StatusCheck, StatusCheckResult

def process_matrix(data):
    metrics = []
    values = []
    for result in data['result']:
        metrics.append(result['metric'])
        metricValues = []
        for value in result['value']:
            metricValues.append(value)
        values.append(metricValues)
    if len(data) > 0:
        raise Exception("Metrics failed: {}\nWith values: {}".format(str(metrics), str(values)))


def process_vector(data, ret):

    all_values = []
    for target in data['result']:
        series = {'values': [ float(target['value'][1]) ]}
        series['target'] = target['metric']['__name__']
        all_values.extend(series['values'])
        if series['values']:
            ret['num_series_with_data'] += 1
            series['max'] = max(series['values'])
            series['min'] = min(series['values'])
            series['average_value'] = sum(series['values']) / len(series['values'])
            ret['series'].append(series)
        else:
            ret['num_series_no_data'] += 1
    if all_values:
        ret['average_value'] = sum(all_values) / len(all_values)
    ret['all_values'] = all_values
    ret['raw'] = data

    return ret


def process_scalar(data):
    value = [data]
    if len(data) > 0:
        raise Exception("Metrics failed with values: " + str(value))


def process_string(data):
    value = [data]
    if len(data) > 0:
        raise Exception("Metrics failed with values: {}".format(str(value)))


def process_unknown(data):
    print('processing unknown')

class PrometheusStatusCheck(StatusCheck):
    check_name = 'prometheus'
    edit_url_name = 'update-prometheus-check'
    duplicate_url_name = 'duplicate-prometheus-check'
    icon_class = 'glyphicon-fire'
    host = models.TextField(
        help_text='Host to check.',
    )
    query = models.TextField(
        help_text='Query to execute.',
    )

    # class Meta(StatusCheck.Meta):
    #     proxy = True

    @property
    def check_category(self):
        return "Metric check"

    def parse_metric(self, metric=None, mins_to_check=None, timenow=None):
        ret = {
            'num_series_with_data': 0,
            'num_series_no_data': 0,
            'error': None,
            'raw': '',
            'series': [],
        }
        try:
            url = urlparse(self.host)
            # NOTE: Scheme is http only
            # TODO: Add auth if provided
            url = url._replace(scheme='http',
                               path='/api/v1/query',
                               params='',
                               query='',
                               fragment='')

            payload = {
                'query': self.query
            }

            r = requests.get(url.geturl(), params=payload)
            data = r.json()['data']

            type = data['resultType']

            if type == 'matrix':
                ret_val = process_matrix(data)
            elif type == 'vector':
                process_vector(data, ret)
            elif type == 'scalar':
                ret_val = process_scalar(data)
            elif type == 'string':
                ret_val = process_string(data)
            else:
                ret_val = process_unknown(data)

        except Exception as e:
            ret["error"] = u"{} {}".format(e.message, self.host)

        return ret

    def format_error_message(self, failures, actual_hosts=None,
                             hosts_by_target=None):
        # if actual_hosts < self.expected_num_hosts:
        #     return "Hosts missing | %d/%d hosts" % (
        #         actual_hosts, self.expected_num_hosts)
        # elif actual_hosts > 1:
        #     threshold = float(self.value)
        #     failures_by_host = ["%s: %s %s %0.1f" % (
        #         hosts_by_target[target], value, self.check_type, threshold)
        #                         for target, value in failures]
        #     return ", ".join(failures_by_host)
        # else:
        value = failures[0]
        return "%s %s %0.1f" % (value, self.check_type, float(self.value))

    def _run(self):
        if not hasattr(self, 'utcnow'):
            self.utcnow = None

        result = StatusCheckResult(status_check=self)
        # NOTE: Can be added later
        # last_result = self.last_result()
        #
        # if last_result:
        #     last_result_started = last_result.time
        #     time_to_check = max(self.frequency, ((timezone.now() - last_result_started).total_seconds() / 60) + 1)
        # else:
        #     time_to_check = self.frequency

        output = self.parse_metric()
        result.raw_data = output["raw"]

        # Check if the metric condition
        if output["error"]:
            result.succeeded = False
            result.error = output["error"]
            return result

        failures = []
        failure_value = None
        if output['num_series_with_data'] > 0:
            result.average_value = output['average_value']
            for s in output['series']:
                if not s["values"]:
                    continue
                failure_value = None
                if self.check_type == '<':
                    if float(s["min"]) < float(self.value):
                        failure_value = s["min"]
                elif self.check_type == '<=':
                    if float(s["min"]) <= float(self.value):
                        failure_value = s["min"]
                elif self.check_type == '>':
                    if float(s["max"]) > float(self.value):
                        failure_value = s["max"]
                elif self.check_type == '>=':
                    if float(s["max"]) >= float(self.value):
                        failure_value = s["max"]
                elif self.check_type == '==':
                    if float(self.value) in s['values']:
                        failure_value = float(self.value)
                else:
                    raise Exception(u'Check type %s not supported' %
                                    self.check_type)

                if failure_value:
                    failures.append(failure_value)

        if len(failures) > self.allowed_num_failures:
            result.succeeded = False

        elif output['num_series_with_data'] < self.expected_num_hosts:
            result.succeeded = False
        else:
            result.succeeded = True

        if not result.succeeded:
            # targets = [s["target"] for s in output["series"]]
            # hosts = minimize_targets(targets)
            # hosts_by_target = dict(zip(targets, hosts))

            result.error = self.format_error_message(
                failures,
                output['num_series_with_data']
            )

        return result
