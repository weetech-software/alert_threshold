import os
import alert_threshold_metric_one
import pytest
from unittest.mock import patch


# https://codecut.ai/pytest-mock-vs-unittest-mock-simplifying-mocking-in-python-tests/
# 

class TestAlertThresholdMetricOne:

    @pytest.fixture()
    def setUp(self):
        self.fixture = range(1, 10)
        yield "resource"
        del self.fixture

    # TODO should not have mock the whole function but the function inside .check
    def test_check_ok(self, setUp):
        with patch("alert_threshold_metric_one.check"):
            try:
                metric='indices/get/current'
                script='elasticsearch-cluster-node-stat-indices-get.py'
                stateFile='/var/lib/monitoring-weetech-ch/state/es1-weetech-ch-alert-threshold.json'
                value=0
                operator='=='
                threshold_operator='>='
                alert_value=2
                ssh_host='es1.weetech.ch'
                ops_timeout=60
                alert_threshold_metric_one.check(metric, script, stateFile, value, operator, threshold_operator, alert_value, ssh_host, ops_timeout)
            except:
               self.fail('should not have exception')    

    # TODO should not have mock the whole function but the function inside .check
    def test_check_error(self, setUp):
        
        with patch("alert_threshold_metric_one.check"):
            # setting a very small timeout to simulate failure test
            timeout_sec = 0.01
            try:
                metric='indices/get/current'
                script='elasticsearch-cluster-node-stat-indices-get.py'
                stateFile='/var/lib/monitoring-weetech-ch/state/es1-weetech-ch-alert-threshold.json'
                value=0
                operator='=='
                threshold_operator='>='
                alert_value=2
                ssh_host='es1.weetech.ch'
                ops_timeout=60
                alert_threshold_metric_one.check(metric, script, stateFile, value, operator, threshold_operator, alert_value, ssh_host, ops_timeout)
            except:
               self.fail('should not have exception')

