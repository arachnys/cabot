from ..models import StatusCheck, StatusCheckResult

import subprocess

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

        args = ['ping', '-c', '1', target]
        try:
            # We redirect stderr to STDOUT because ping can write to both, depending on the kind of error.
            subprocess.check_output(args, stderr=subprocess.STDOUT, shell=False)
            result.succeeded = True
        except subprocess.CalledProcessError as e:
            result.succeeded = False
            result.error = e.output

        return result

    def __str__(self):
        return self.name


class ICMPStatusCheckForm(StatusCheckForm):
    class Meta:
        model = ICMPStatusCheck
        fields = (
            'name',
            'frequency',
            'importance',
            'active',
            'debounce',
        )
        widgets = dict(**base_widgets)


#views
class ICMPCheckCreateView(CheckCreateView):
    model = ICMPStatusCheck
    form_class = ICMPStatusCheckForm


class ICMPCheckUpdateView(CheckUpdateView):
    model = ICMPStatusCheck
    form_class = ICMPStatusCheckForm
