from ..models import StatusCheck

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

    def __str__(self):
        return self.name


class GraphiteStatusCheckForm(StatusCheckForm):
    class Meta:
        model = GraphiteStatusCheck
        fields = (
            'name',
            'metric',
            'check_type',
            'value',
            'frequency',
            'active',
            'importance',
            'expected_num_hosts',
            'allowed_num_failures',
            'debounce',
        )
        widgets = dict(**base_widgets)
        widgets.update({
            'value': forms.TextInput(attrs={
                'style': 'width: 100px',
                'placeholder': 'threshold value',
            }),
            'metric': forms.TextInput(attrs={
                'style': 'width: 100%',
                'placeholder': 'graphite metric key'
            }),
            'check_type': forms.Select(attrs={
                'data-rel': 'chosen',
            })
        })



#views

class GraphiteCheckUpdateView(CheckUpdateView):
    model = GraphiteStatusCheck
    form_class = GraphiteStatusCheckForm


class GraphiteCheckCreateView(CheckCreateView):
    model = GraphiteStatusCheck
    form_class = GraphiteStatusCheckForm

