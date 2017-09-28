import subprocess

from mock import patch

from cabot.cabotapp.models import (
    ICMPStatusCheck,
    Instance,
    Service,
)

from .tests_basic import LocalTestCase

class TestICMPCheckRun(LocalTestCase):

    def setUp(self):
        super(TestICMPCheckRun, self).setUp()
        self.instance = Instance.objects.create(
            name='Instance',
            address='1.2.3.4'
        )
        self.icmp_check = ICMPStatusCheck.objects.create(
            name='ICMP Check',
            created_by=self.user,
            importance=Service.CRITICAL_STATUS,
        )
        self.instance.status_checks.add(
            self.icmp_check)

        self.patch = patch('cabot.cabotapp.models.subprocess.check_output', autospec=True)
        self.mock_check_output = self.patch.start()

    def tearDown(self):
        self.patch.stop()
        super(TestICMPCheckRun, self).tearDown()

    def test_icmp_run_use_instance_address(self):
        self.icmp_check.run()
        args = ['ping', '-c', '1', u'1.2.3.4']
        self.mock_check_output.assert_called_once_with(args, shell=False, stderr=-2)

    def test_icmp_run_success(self):
        checkresults = self.icmp_check.statuscheckresult_set.all()
        self.assertEqual(len(checkresults), 0)
        self.icmp_check.run()
        checkresults = self.icmp_check.statuscheckresult_set.all()
        self.assertEqual(len(checkresults), 1)
        self.assertTrue(self.icmp_check.last_result().succeeded)

    def test_icmp_run_bad_address(self):
        self.mock_check_output.side_effect = subprocess.CalledProcessError(2, None, "ping: bad address")
        checkresults = self.icmp_check.statuscheckresult_set.all()
        self.assertEqual(len(checkresults), 0)
        self.icmp_check.run()
        checkresults = self.icmp_check.statuscheckresult_set.all()
        self.assertEqual(len(checkresults), 1)
        self.assertFalse(self.icmp_check.last_result().succeeded)

    def test_icmp_run_inacessible(self):
        self.mock_check_output.side_effect = subprocess.CalledProcessError(1, None, "packet loss")
        checkresults = self.icmp_check.statuscheckresult_set.all()
        self.assertEqual(len(checkresults), 0)
        self.icmp_check.run()
        checkresults = self.icmp_check.statuscheckresult_set.all()
        self.assertEqual(len(checkresults), 1)
        self.assertFalse(self.icmp_check.last_result().succeeded)
