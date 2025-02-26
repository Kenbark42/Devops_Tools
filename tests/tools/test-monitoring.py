"""
Tests for the monitoring module.
"""
import time
from typing import Dict, Any, List
from unittest import mock

import pytest

from devops_toolkit.tools.monitoring import (
    MetricCollector,
    PrometheusCollector,
    CloudWatchCollector,
    check_status,
    create_alert_rule,
    get_metrics_dashboard,
)


class TestMetricCollector:
    """Tests for MetricCollector base class."""

    def test_init(self):
        """Test initialization of MetricCollector."""
        collector = MetricCollector("test-collector", 120)
        assert collector.name == "test-collector"
        assert collector.interval == 120

    def test_collect_not_implemented(self):
        """Test collect method raises NotImplementedError."""
        collector = MetricCollector("test-collector")
        with pytest.raises(NotImplementedError):
            collector.collect()


class TestPrometheusCollector:
    """Tests for PrometheusCollector."""

    def test_init(self):
        """Test initialization of PrometheusCollector."""
        collector = PrometheusCollector(
            "prom-collector",
            "http://prometheus:9090",
            'sum(rate(http_requests_total[5m]))',
            30
        )
        assert collector.name == "prom-collector"
        assert collector.endpoint == "http://prometheus:9090"
        assert collector.query == 'sum(rate(http_requests_total[5m]))'
        assert collector.interval == 30

    def test_collect(self):
        """Test collect method returns expected structure."""
        collector = PrometheusCollector(
            "prom-collector",
            "http://prometheus:9090",
            'sum(rate(http_requests_total[5m]))'
        )
        result = collector.collect()
        
        assert result["name"] == "prom-collector"
        assert result["source"] == "prometheus"
        assert result["endpoint"] == "http://prometheus:9090"
        assert result["query"] == 'sum(rate(http_requests_total[5m]))'
        assert "timestamp" in result
        assert "value" in result
        assert "unit" in result


class TestCloudWatchCollector:
    """Tests for CloudWatchCollector."""

    def test_init(self):
        """Test initialization of CloudWatchCollector."""
        collector = CloudWatchCollector(
            "cw-collector",
            "AWS/EC2",
            "CPUUtilization",
            {"InstanceId": "i-12345678"},
            300
        )
        assert collector.name == "cw-collector"
        assert collector.namespace == "AWS/EC2"
        assert collector.metric_name == "CPUUtilization"
        assert collector.dimensions == {"InstanceId": "i-12345678"}
        assert collector.interval == 300

    def test_collect(self):
        """Test collect method returns expected structure."""
        collector = CloudWatchCollector(
            "cw-collector",
            "AWS/EC2",
            "CPUUtilization",
            {"InstanceId": "i-12345678"}
        )
        result = collector.collect()
        
        assert result["name"] == "cw-collector"
        assert result["source"] == "cloudwatch"
        assert result["namespace"] == "AWS/EC2"
        assert result["metric_name"] == "CPUUtilization"
        assert result["dimensions"] == {"InstanceId": "i-12345678"}
        assert "timestamp" in result
        assert "value" in result
        assert "unit" in result


class TestMonitoringFunctions:
    """Tests for monitoring module functions."""

    def test_check_status_single(self):
        """Test check_status returns single status check."""
        result = check_status("test-app", "dev")
        
        assert isinstance(result, dict)
        assert result["app_name"] == "test-app"
        assert result["environment"] == "dev"
        assert "timestamp" in result
        assert "status" in result
        assert "metrics" in result
        
        # Check metrics structure
        metrics = result["metrics"]
        assert "cpu_usage" in metrics
        assert "memory_usage" in metrics
        assert "request_rate" in metrics
        assert "error_rate" in metrics
        assert "response_time" in metrics

    @mock.patch('time.sleep', return_value=None)  # Mock sleep to speed up test
    def test_check_status_continuous(self, mock_sleep):
        """Test check_status in continuous mode."""
        result = check_status("test-app", "dev", continuous=True, max_checks=3)
        
        assert isinstance(result, list)
        assert len(result) == 3
        
        for check in result:
            assert check["app_name"] == "test-app"
            assert check["environment"] == "dev"
            assert "timestamp" in check
            assert "status" in check
            assert "metrics" in check

    def test_create_alert_rule(self):
        """Test create_alert_rule function."""
        result = create_alert_rule(
            "high-cpu-alert",
            "web-server",
            "cpu_usage",
            90.0,
            ">",
            "5m",
            "critical",
            ["email", "slack"]
        )
        
        assert result["name"] == "high-cpu-alert"
        assert result["app_name"] == "web-server"
        assert result["condition"]["metric"] == "cpu_usage"
        assert result["condition"]["operator"] == ">"
        assert result["condition"]["threshold"] == 90.0
        assert result["condition"]["duration"] == "5m"
        assert result["severity"] == "critical"
        assert result["notification_channels"] == ["email", "slack"]
        assert "created_at" in result
        assert result["status"] == "active"

    def test_get_metrics_dashboard(self):
        """Test get_metrics_dashboard function."""
        result = get_metrics_dashboard("web-server", "production", "3h")
        
        assert result["app_name"] == "web-server"
        assert result["environment"] == "production"
        assert result["time_range"] == "3h"
        assert "refresh_interval" in result
        assert "panels" in result
        
        # Check panels structure
        panels = result["panels"]
        assert isinstance(panels, list)
        assert len(panels) > 0
        
        for panel in panels:
            assert "title" in panel
            assert "type" in panel
            assert "metrics" in panel
            assert "position" in panel
