import itertools
import json
import re
import subprocess
import time
import os
from datetime import timedelta

import requests
from django.conf import settings
from django.db import models
from django.utils import timezone
from cabot.cabotapp.modelcategories.common import StatusCheck
from cabot.cabotapp.modelcategories.common import StatusCheckResult
from cabot.cabotapp.modelcategories.common import Service
from cabot.cabotapp.modelcategories.common import Instance
from cabot.cabotapp.modelcategories.common import Snapshot
from cabot.cabotapp.modelcategories.user import UserProfile


from .alert import (
    send_alert,
    send_alert_update
)
from .calendar import get_events
from .graphite import parse_metric
from .jenkins import get_job_status
from .tasks import update_service, update_instance

def add_custom_check_plugins():
    custom_check_types = []
    plugins_name = None
    if os.environ.get('CABOT_CUSTOM_CHECK_PLUGINS'):
        plugins_name = os.environ.get('CABOT_CUSTOM_CHECK_PLUGINS').split(',')
        for plugin_name in plugins_name:
            check_name = plugin_name.replace('cabot_check_', '')
            custom_check = {}
            custom_check['creation_url'] = "create-" + check_name + "-check"
            custom_check['check_name'] = check_name
            custom_check_types.append(custom_check)

    return custom_check_types

class CustomStatusCheck(StatusCheck):
    class Meta(StatusCheck.Meta):
        proxy = True

    custom_check_types = add_custom_check_plugins()

class ICMPStatusCheck(StatusCheck):
    class Meta(StatusCheck.Meta):
        proxy = True

    @property
    def check_category(self):
        return "ICMP/Ping Check"

    def _run(self):
        result = StatusCheckResult(status_check=self)
        instances = self.instance_set.all()
        target = self.instance_set.get().address

        # We need to read both STDOUT and STDERR because ping can write to both, depending on the kind of error.
        # Thanks a lot, ping.
        ping_process = subprocess.Popen("ping -c 1 " + target, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                        shell=True)
        response = ping_process.wait()

        if response == 0:
            result.succeeded = True
        else:
            output = ping_process.stdout.read()
            result.succeeded = False
            result.error = output

        return result


def minimize_targets(targets):
    split = [target.split(".") for target in targets]

    prefix_nodes_in_common = 0
    for i, nodes in enumerate(itertools.izip(*split)):
        if any(node != nodes[0] for node in nodes):
            prefix_nodes_in_common = i
            break
    split = [nodes[prefix_nodes_in_common:] for nodes in split]

    suffix_nodes_in_common = 0
    for i, nodes in enumerate(reversed(zip(*split))):
        if any(node != nodes[0] for node in nodes):
            suffix_nodes_in_common = i
            break
    if suffix_nodes_in_common:
        split = [nodes[:-suffix_nodes_in_common] for nodes in split]

    return [".".join(nodes) for nodes in split]

class GraphiteStatusCheck(StatusCheck):

    class Meta(StatusCheck.Meta):
        proxy = True

    @property
    def check_category(self):
        return "Metric check"

    def format_error_message(self, failures, actual_hosts, hosts_by_target):
        if actual_hosts < self.expected_num_hosts:
            return "Hosts missing | %d/%d hosts" % (
                actual_hosts, self.expected_num_hosts)
        elif actual_hosts > 1:
            threshold = float(self.value)
            failures_by_host = ["%s: %s %s %0.1f" % (
                hosts_by_target[target], value, self.check_type, threshold)
                                for target, value in failures]
            return ", ".join(failures_by_host)
        else:
            target, value = failures[0]
            return "%s %s %0.1f" % (value, self.check_type, float(self.value))

    def _run(self):
        if not hasattr(self, 'utcnow'):
            self.utcnow = None
        result = StatusCheckResult(status_check=self)

        failures = []

        last_result = self.last_result()
        if last_result:
            last_result_started = last_result.time
            time_to_check = max(self.frequency, ((timezone.now() - last_result_started).total_seconds() / 60) + 1)
        else:
            time_to_check = self.frequency

        graphite_output = parse_metric(self.metric, mins_to_check=time_to_check, utcnow=self.utcnow)

        try:
            result.raw_data = json.dumps(graphite_output['raw'])
        except:
            result.raw_data = graphite_output['raw']

        if graphite_output["error"]:
            result.succeeded = False
            result.error = graphite_output["error"]
            return result

        if graphite_output['num_series_with_data'] > 0:
            result.average_value = graphite_output['average_value']
            for s in graphite_output['series']:
                if not s["values"]:
                    continue
                failure_value = None
                if self.check_type == '<':
                    if float(s['min']) < float(self.value):
                        failure_value = s['min']
                elif self.check_type == '<=':
                    if float(s['min']) <= float(self.value):
                        failure_value = s['min']
                elif self.check_type == '>':
                    if float(s['max']) > float(self.value):
                        failure_value = s['max']
                elif self.check_type == '>=':
                    if float(s['max']) >= float(self.value):
                        failure_value = s['max']
                elif self.check_type == '==':
                    if float(self.value) in s['values']:
                        failure_value = float(self.value)
                else:
                    raise Exception(u'Check type %s not supported' %
                                    self.check_type)

                if not failure_value is None:
                    failures.append((s["target"], failure_value))

        if len(failures) > self.allowed_num_failures:
            result.succeeded = False
        elif graphite_output['num_series_with_data'] < self.expected_num_hosts:
            result.succeeded = False
        else:
            result.succeeded = True

        if not result.succeeded:
            targets = [s["target"] for s in graphite_output["series"]]
            hosts = minimize_targets(targets)
            hosts_by_target = dict(zip(targets, hosts))

            result.error = self.format_error_message(
                failures,
                graphite_output['num_series_with_data'],
                hosts_by_target,
            )

        return result


class HttpStatusCheck(StatusCheck):
    class Meta(StatusCheck.Meta):
        proxy = True

    @property
    def check_category(self):
        return "HTTP check"

    def _run(self):
        result = StatusCheckResult(status_check=self)

        auth = None
        if self.username or self.password:
            auth = (self.username, self.password)

        try:
            resp = requests.get(
                self.endpoint,
                timeout=self.timeout,
                verify=self.verify_ssl_certificate,
                auth=auth,
                headers={
                    "User-Agent": settings.HTTP_USER_AGENT,
                },
            )
        except requests.RequestException as e:
            result.error = u'Request error occurred: %s' % (e.message,)
            result.succeeded = False
        else:
            if self.status_code and resp.status_code != int(self.status_code):
                result.error = u'Wrong code: got %s (expected %s)' % (
                    resp.status_code, int(self.status_code))
                result.succeeded = False
                result.raw_data = resp.content
            elif self.text_match:
                if not re.search(self.text_match, resp.content):
                    result.error = u'Failed to find match regex /%s/ in response body' % self.text_match
                    result.raw_data = resp.content
                    result.succeeded = False
                else:
                    result.succeeded = True
            else:
                result.succeeded = True
        return result


class JenkinsStatusCheck(StatusCheck):
    class Meta(StatusCheck.Meta):
        proxy = True

    @property
    def check_category(self):
        return "Jenkins check"

    @property
    def failing_short_status(self):
        return 'Job failing on Jenkins'

    def _run(self):
        result = StatusCheckResult(status_check=self)
        try:
            status = get_job_status(self.name)
            active = status['active']
            result.job_number = status['job_number']
            if status['status_code'] == 404:
                result.error = u'Job %s not found on Jenkins' % self.name
                result.succeeded = False
                return result
            elif status['status_code'] > 400:
                # Will fall through to next block
                raise Exception(u'returned %s' % status['status_code'])
        except Exception as e:
            # If something else goes wrong, we will *not* fail - otherwise
            # a lot of services seem to fail all at once.
            # Ugly to do it here but...
            result.error = u'Error fetching from Jenkins - %s' % e.message
            result.succeeded = True
            return result

        if not active:
            # We will fail if the job has been disabled
            result.error = u'Job "%s" disabled on Jenkins' % self.name
            result.succeeded = False
        else:
            if self.max_queued_build_time and status['blocked_build_time']:
                if status['blocked_build_time'] > self.max_queued_build_time * 60:
                    result.succeeded = False
                    result.error = u'Job "%s" has blocked build waiting for %ss (> %sm)' % (
                        self.name,
                        int(status['blocked_build_time']),
                        self.max_queued_build_time,
                    )
                else:
                    result.succeeded = status['succeeded']
            else:
                result.succeeded = status['succeeded']
            if not status['succeeded']:
                if result.error:
                    result.error += u'; Job "%s" failing on Jenkins' % self.name
                else:
                    result.error = u'Job "%s" failing on Jenkins' % self.name
                result.raw_data = status
        return result
