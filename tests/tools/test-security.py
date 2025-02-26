"""
Tests for the security module.
"""
import os
import tempfile
from typing import Dict, Any, List
from unittest import mock

import pytest
import json

from devops_toolkit.tools.security import (
    SecurityScanError,
    SecurityScanner,
    DependencyScanner,
    CodeScanner,
    ContainerScanner,
    scan,
    check_compliance,
    generate_security_report,
)


class TestSecurityScanner:
    """Tests for SecurityScanner base class."""

    def test_init(self):
        """Test initialization of SecurityScanner."""
        scanner = SecurityScanner("test-scanner")
        assert scanner.name == "test-scanner"

    def test_scan_not_implemented(self):
        """Test scan method raises NotImplementedError."""
        scanner = SecurityScanner("test-scanner")
        with pytest.raises(NotImplementedError):
            scanner.scan("target")


class TestDependencyScanner:
    """Tests for DependencyScanner."""

    def test_init(self):
        """Test initialization of DependencyScanner."""
        scanner = DependencyScanner("dep-scanner")
        assert scanner.name == "dep-scanner"

    def test_scan(self):
        """Test scan method returns expected structure."""
        scanner = DependencyScanner()
        result = scanner.scan("app")
        
        assert result["scanner"] == scanner.name
        assert result["target"] == "app"
        assert "scan_time" in result
        assert "dependencies_checked" in result
        assert "vulnerabilities_found" in result
        assert "issues" in result
        
        # Check issues structure
        issues = result["issues"]
        assert isinstance(issues, list)
        for issue in issues:
            assert "package" in issue
            assert "installed_version" in issue
            assert "vulnerable_versions" in issue
            assert "severity" in issue
            assert "description" in issue
            assert "recommendation" in issue


class TestCodeScanner:
    """Tests for CodeScanner."""

    def test_init(self):
        """Test initialization of CodeScanner."""
        scanner = CodeScanner("code-scanner")
        assert scanner.name == "code-scanner"

    def test_scan(self):
        """Test scan method returns expected structure."""
        scanner = CodeScanner()
        result = scanner.scan("app")
        
        assert result["scanner"] == scanner.name
        assert result["target"] == "app"
        assert "scan_time" in result
        assert "files_scanned" in result
        assert "issues_found" in result
        assert "issues" in result
        
        # Check issues structure
        issues = result["issues"]
        assert isinstance(issues, list)
        for issue in issues:
            assert "file" in issue
            assert "line" in issue
            assert "severity" in issue
            assert "category" in issue
            assert "description" in issue
            assert "recommendation" in issue


class TestContainerScanner:
    """Tests for ContainerScanner."""

    def test_init(self):
        """Test initialization of ContainerScanner."""
        scanner = ContainerScanner("container-scanner")
        assert scanner.name == "container-scanner"

    def test_scan(self):
        """Test scan method returns expected structure."""
        scanner = ContainerScanner()
        result = scanner.scan("app:latest")
        
        assert result["scanner"] == scanner.name
        assert result["target"] == "app:latest"
        assert "scan_time" in result
        assert "layers_scanned" in result
        assert "vulnerabilities_found" in result
        assert "issues" in result
        
        # Check issues structure
        issues = result["issues"]
        assert isinstance(issues, list)
        for issue in issues:
            assert "package" in issue
            assert "installed_version" in issue
            assert "fixed_version" in issue
            assert "severity" in issue
            assert "vulnerability_id" in issue
            assert "description" in issue
            assert "recommendation" in issue


class TestScanFunction:
    """Tests for scan function."""

    def test_scan_all(self):
        """Test scan function with all scan types."""
        result = scan("test-app")
        
        assert result["app_name"] == "test-app"
        assert result["scan_type"] == "all"
        assert "target" in result
        assert "scan_time" in result
        assert "scans" in result
        assert "summary" in result
        
        # Check scans structure
        scans = result["scans"]
        assert isinstance(scans, list)
        assert len(scans) == 3  # dependencies, code, container
        
        # Check summary structure
        summary = result["summary"]
        assert "total_issues" in summary
        assert "severity_counts" in summary
        assert all(severity in summary["severity_counts"] for severity in ["critical", "high", "medium", "low"])

    def test_scan_specific_type(self):
        """Test scan function with specific scan type."""
        result = scan("test-app", scan_type="dependencies")
        
        assert result["app_name"] == "test-app"
        assert result["scan_type"] == "dependencies"
        assert "scans" in result
        assert len(result["scans"]) == 1
        assert result["scans"][0]["scanner"] == "dependency-scanner"

    @mock.patch('devops_toolkit.tools.security._generate_report')
    def test_scan_with_output(self, mock_generate_report):
        """Test scan function with output file."""
        result = scan("test-app", output_file="report.txt", report_format="text")
        
        assert result["app_name"] == "test-app"
        mock_generate_report.assert_called_once_with(result, "text", "report.txt")


class TestComplianceFunction:
    """Tests for compliance function."""

    def test_check_compliance_unsupported_framework(self):
        """Test checking compliance with unsupported framework."""
        result = check_compliance("test-app", "unsupported-framework")
        
        assert result["app_name"] == "test-app"
        assert result["framework"] == "unsupported-framework"
        assert result["status"] == "error"
        assert "message" in result
        assert "supported_frameworks" in result

    def test_check_compliance_supported_framework(self):
        """Test checking compliance with supported framework."""
        result = check_compliance("test-app", "owasp-top10")
        
        assert result["app_name"] == "test-app"
        assert result["framework"] == "owasp-top10"
        assert "check_time" in result
        assert "requirements_count" in result
        assert "compliant_count" in result
        assert "compliance_percentage" in result
        assert "overall_status" in result
        assert "results" in result
        
        # Check results structure
        compliance_results = result["results"]
        assert isinstance(compliance_results, list)
        for req in compliance_results:
            assert "requirement" in req
            assert "compliant" in req
            assert "details" in req
            assert "recommendation" in req


class TestReportGeneration:
    """Tests for report generation functions."""

    @mock.patch('devops_toolkit.tools.security.scan')
    def test_generate_security_report(self, mock_scan):
        """Test generating security report."""
        # Setup mock return value
        mock_scan.return_value = {
            "app_name": "test-app",
            "scan_type": "all",
            "scans": [],
            "summary": {"total_issues": 0, "severity_counts": {}}
        }
        
        result = generate_security_report("test-app")
        
        assert result["app_name"] == "test-app"
        assert result["report_type"] == "security"
        assert "timestamp" in result
        assert "scan_results" in result
        assert "compliance" not in result
        
        # Verify mock was called correctly
        mock_scan.assert_called_once_with("test-app", scan_type="all")

    @mock.patch('devops_toolkit.tools.security.scan')
    @mock.patch('devops_toolkit.tools.security.check_compliance')
    def test_generate_security_report_with_compliance(self, mock_compliance, mock_scan):
        """Test generating security report with compliance."""
        # Setup mock return values
        mock_scan.return_value = {
            "app_name": "test-app",
            "scan_type": "all",
            "scans": [],
            "summary": {"total_issues": 0, "severity_counts": {}}
        }
        mock_compliance.return_value = {
            "app_name": "test-app",
            "framework": "owasp-top10",
            "overall_status": "compliant",
            "results": []
        }
        
        result = generate_security_report(
            "test-app",
            include_compliance=True,
            compliance_framework="owasp-top10"
        )
        
        assert result["app_name"] == "test-app"
        assert "scan_results" in result
        assert "compliance" in result
        assert result["compliance"]["framework"] == "owasp-top10"
        
        # Verify mocks were called correctly
        mock_scan.assert_called_once_with("test-app", scan_type="all")
        mock_compliance.assert_called_once_with("test-app", "owasp-top10", mock_scan.return_value)

    @mock.patch('devops_toolkit.tools.security.scan')
    def test_generate_security_report_with_output(self, mock_scan):
        """Test generating security report with output file."""
        # Setup mock return value
        mock_scan.return_value = {
            "app_name": "test-app",
            "scan_type": "all",
            "scans": [],
            "summary": {"total_issues": 0, "severity_counts": {}}
        }
        
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            output_file = f.name
        
        try:
            result = generate_security_report(
                "test-app",
                output_file=output_file,
                report_format="json"
            )
            
            # Check if file was created
            assert os.path.exists(output_file)
            
            # Check file content
            with open(output_file, 'r') as f:
                report_json = json.load(f)
                assert report_json["app_name"] == "test-app"
                assert report_json["report_type"] == "security"
        
        finally:
            # Clean up temporary file
            if os.path.exists(output_file):
                os.unlink(output_file)
