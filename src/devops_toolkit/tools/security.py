"""
DevOps Toolkit - Security Module

This module provides functions for security scanning of applications,
dependencies, containers, and infrastructure.
"""
import json
import os
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Set


class SecurityScanError(Exception):
    """Raised when a security scan encounters an error."""
    pass


class SecurityScanner:
    """Base class for security scanners."""

    def __init__(self, name: str):
        """
        Initialize a security scanner.

        Args:
            name: Name of the scanner
        """
        self.name = name

    def scan(self, target: str) -> Dict[str, Any]:
        """
        Scan a target for security issues.

        Args:
            target: The target to scan

        Returns:
            Dict containing scan results
        """
        raise NotImplementedError("Subclasses must implement scan()")


class DependencyScanner(SecurityScanner):
    """Scanner for application dependencies."""

    def __init__(self, name: str = "dependency-scanner"):
        """Initialize a dependency scanner."""
        super().__init__(name)

    def scan(self, target: str) -> Dict[str, Any]:
        """
        Scan application dependencies for vulnerabilities.

        Args:
            target: Path to the application or dependency file

        Returns:
            Dict containing scan results
        """
        # In a real implementation, this would use tools like safety or npm audit
        # For demonstration, we'll return mock results
        return {
            "scanner": self.name,
            "target": target,
            "scan_time": datetime.now().isoformat(),
            "dependencies_checked": 42,
            "vulnerabilities_found": 3,
            "issues": [
                {
                    "package": "requests",
                    "installed_version": "2.22.0",
                    "vulnerable_versions": "<2.23.0",
                    "severity": "high",
                    "description": "Vulnerability in urllib3 dependency",
                    "recommendation": "Upgrade to requests>=2.23.0"
                },
                {
                    "package": "django",
                    "installed_version": "2.2.10",
                    "vulnerable_versions": "<2.2.13",
                    "severity": "medium",
                    "description": "Potential SQL injection vulnerability",
                    "recommendation": "Upgrade to django>=2.2.13"
                },
                {
                    "package": "pillow",
                    "installed_version": "6.2.0",
                    "vulnerable_versions": "<6.2.2",
                    "severity": "low",
                    "description": "Potential DoS vulnerability",
                    "recommendation": "Upgrade to pillow>=6.2.2"
                }
            ]
        }


class CodeScanner(SecurityScanner):
    """Scanner for application code."""

    def __init__(self, name: str = "code-scanner"):
        """Initialize a code scanner."""
        super().__init__(name)

    def scan(self, target: str) -> Dict[str, Any]:
        """
        Scan application code for security issues.

        Args:
            target: Path to the application code

        Returns:
            Dict containing scan results
        """
        # In a real implementation, this would use tools like bandit or SonarQube
        # For demonstration, we'll return mock results
        return {
            "scanner": self.name,
            "target": target,
            "scan_time": datetime.now().isoformat(),
            "files_scanned": 15,
            "issues_found": 2,
            "issues": [
                {
                    "file": "app/views.py",
                    "line": 42,
                    "severity": "high",
                    "category": "sql-injection",
                    "description": "Potential SQL injection vulnerability",
                    "recommendation": "Use parameterized queries or ORM"
                },
                {
                    "file": "app/utils.py",
                    "line": 23,
                    "severity": "medium",
                    "category": "hardcoded-password",
                    "description": "Hard-coded credentials in source code",
                    "recommendation": "Use environment variables or secure credential storage"
                }
            ]
        }


class ContainerScanner(SecurityScanner):
    """Scanner for container images."""

    def __init__(self, name: str = "container-scanner"):
        """Initialize a container scanner."""
        super().__init__(name)

    def scan(self, target: str) -> Dict[str, Any]:
        """
        Scan a container image for vulnerabilities.

        Args:
            target: Name or path of the container image

        Returns:
            Dict containing scan results
        """
        # In a real implementation, this would use tools like Clair, Trivy, or Anchore
        # For demonstration, we'll return mock results
        return {
            "scanner": self.name,
            "target": target,
            "scan_time": datetime.now().isoformat(),
            "layers_scanned": 8,
            "vulnerabilities_found": 4,
            "issues": [
                {
                    "package": "openssl",
                    "installed_version": "1.1.1d-0+deb10u3",
                    "fixed_version": "1.1.1d-0+deb10u5",
                    "severity": "critical",
                    "vulnerability_id": "CVE-2021-3449",
                    "description": "Null pointer dereference in OpenSSL",
                    "recommendation": "Update base image or package"
                },
                {
                    "package": "libsqlite3-0",
                    "installed_version": "3.27.2-3",
                    "fixed_version": "3.27.2-3+deb10u1",
                    "severity": "high",
                    "vulnerability_id": "CVE-2020-11655",
                    "description": "SQLite vulnerability",
                    "recommendation": "Update base image or package"
                }
            ]
        }


def scan(
    app_name: str,
    scan_type: str = "all",
    target_path: Optional[str] = None,
    report_format: str = "text",
    output_file: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Perform security scans on applications.

    Args:
        app_name: Name of the application to scan
        scan_type: Type of security scan to perform (dependencies, code, container, all)
        target_path: Path to the application (defaults to current directory if None)
        report_format: Format for the security report (text, json, html)
        output_file: Output file for the report (optional)

    Returns:
        Dict containing scan results

    Raises:
        SecurityScanError: If any scan fails
    """
    print(f"Starting {scan_type} security scan for {app_name}")

    target = target_path or os.getcwd()
    results = {
        "app_name": app_name,
        "scan_type": scan_type,
        "target": target,
        "scan_time": datetime.now().isoformat(),
        "scans": []
    }

    # Determine which scans to run
    scan_types = ["dependencies", "code", "container"] if scan_type == "all" else [scan_type]

    try:
        # Run dependency scan if requested
        if "dependencies" in scan_types:
            print("Scanning dependencies...")
            dependency_scanner = DependencyScanner()
            dependency_results = dependency_scanner.scan(target)
            results["scans"].append(dependency_results)

        # Run code scan if requested
        if "code" in scan_types:
            print("Scanning application code...")
            code_scanner = CodeScanner()
            code_results = code_scanner.scan(target)
            results["scans"].append(code_results)

        # Run container scan if requested
        if "container" in scan_types:
            print("Scanning container image...")
            container_scanner = ContainerScanner()
            container_results = container_scanner.scan(f"{app_name}:latest")
            results["scans"].append(container_results)

        # Generate summary
        total_issues = sum(len(scan.get("issues", [])) for scan in results["scans"])
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}

        for scan in results["scans"]:
            for issue in scan.get("issues", []):
                severity = issue.get("severity", "low").lower()
                if severity in severity_counts:
                    severity_counts[severity] += 1

        results["summary"] = {
            "total_issues": total_issues,
            "severity_counts": severity_counts
        }

        # Output report if requested
        if output_file:
            _generate_report(results, report_format, output_file)

        return results

    except Exception as e:
        raise SecurityScanError(f"Security scan failed: {str(e)}")


def _generate_report(
    results: Dict[str, Any],
    format: str,
    output_file: str
) -> None:
    """
    Generate a security report in the specified format.

    Args:
        results: Scan results
        format: Report format (text, json, html)
        output_file: Output file path
    """
    if format == "json":
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
    elif format == "html":
        # In a real implementation, this would generate a proper HTML report
        # For demonstration, we'll create a simple HTML file
        with open(output_file, 'w') as f:
            f.write("<!DOCTYPE html>\n<html>\n<head>\n")
            f.write("<title>Security Scan Report</title>\n")
            f.write("<style>body{font-family:sans-serif;margin:20px}")
            f.write("table{border-collapse:collapse;width:100%}")
            f.write("th,td{border:1px solid #ddd;padding:8px}")
            f.write(".critical{background-color:#ff5252}")
            f.write(".high{background-color:#ff9e80}")
            f.write(".medium{background-color:#ffecb3}")
            f.write(".low{background-color:#e8f5e9}")
            f.write("</style>\n</head>\n<body>\n")

            f.write(f"<h1>Security Scan Report: {results['app_name']}</h1>\n")
            f.write(f"<p>Scan Time: {results['scan_time']}</p>\n")
            f.write(f"<p>Scan Type: {results['scan_type']}</p>\n")

            # Summary section
            summary = results.get("summary", {})
            f.write("<h2>Summary</h2>\n")
            f.write("<p>Total Issues: " + str(summary.get("total_issues", 0)) + "</p>\n")
            f.write("<ul>\n")
            for severity, count in summary.get("severity_counts", {}).items():
                f.write(f"<li>{severity.capitalize()}: {count}</li>\n")
            f.write("</ul>\n")

            # Detailed results
            f.write("<h2>Detailed Results</h2>\n")
            for scan in results.get("scans", []):
                f.write(f"<h3>{scan.get('scanner', 'Unknown Scanner')}</h3>\n")
                issues = scan.get("issues", [])
                if issues:
                    f.write("<table>\n")
                    f.write("<tr><th>Severity</th><th>Issue</th><th>Recommendation</th></tr>\n")
                    for issue in issues:
                        severity = issue.get("severity", "low").lower()
                        f.write(f"<tr class='{severity}'>\n")
                        f.write(f"<td>{severity.capitalize()}</td>\n")
                        if "package" in issue:
                            description = f"{issue.get('package')} {issue.get('installed_version')} - {issue.get('description', '')}"
                        else:
                            description = f"{issue.get('file', '')}:{issue.get('line', '')} - {issue.get('description', '')}"
                        f.write(f"<td>{description}</td>\n")
                        f.write(f"<td>{issue.get('recommendation', '')}</td>\n")
                        f.write("</tr>\n")
                    f.write("</table>\n")
                else:
                    f.write("<p>No issues found</p>\n")

            f.write("</body>\n</html>")
    else:  # Default to text format
        with open(output_file, 'w') as f:
            f.write(f"Security Scan Report: {results['app_name']}\n")
            f.write(f"Scan Time: {results['scan_time']}\n")
            f.write(f"Scan Type: {results['scan_type']}\n\n")

            # Summary section
            summary = results.get("summary", {})
            f.write("Summary:\n")
            f.write(f"- Total Issues: {summary.get('total_issues', 0)}\n")
            for severity, count in summary.get("severity_counts", {}).items():
                f.write(f"- {severity.capitalize()}: {count}\n")
            f.write("\n")

            # Detailed results
            f.write("Detailed Results:\n")
            for scan in results.get("scans", []):
                f.write(f"\n{scan.get('scanner', 'Unknown Scanner')}:\n")
                for issue in scan.get("issues", []):
                    severity = issue.get("severity", "low").upper()
                    f.write(f"[{severity}] ")
                    if "package" in issue:
                        f.write(f"{issue.get('package')} {issue.get('installed_version')}: {issue.get('description', '')}\n")
                        f.write(f"  Recommendation: {issue.get('recommendation', '')}\n")
                    else:
                        f.write(f"{issue.get('file', '')}:{issue.get('line', '')}: {issue.get('description', '')}\n")
                        f.write(f"  Recommendation: {issue.get('recommendation', '')}\n")

    print(f"Report generated and saved to: {output_file}")


def check_compliance(
    app_name: str,
    framework: str,
    scan_results: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Check compliance against a security framework.

    Args:
        app_name: Name of the application
        framework: Compliance framework to check against
        scan_results: Optional scan results to use (will run scan if None)

    Returns:
        Dict containing compliance results
    """
    print(f"Checking {app_name} compliance against {framework} framework")

    # Run scan if results not provided
    if scan_results is None:
        scan_results = scan(app_name, scan_type="all")

    # Map of frameworks to their requirements
    frameworks = {
        "owasp-top10": [
            "injection",
            "broken-authentication",
            "sensitive-data-exposure",
            "xml-external-entities",
            "broken-access-control",
            "security-misconfiguration",
            "cross-site-scripting",
            "insecure-deserialization",
            "vulnerable-components",
            "insufficient-logging-monitoring"
        ],
        "pci-dss": [
            "secure-network",
            "protect-cardholder-data",
            "vulnerability-management",
            "access-control",
            "monitoring-networks",
            "security-policy",
        ],
        "hipaa": [
            "access-controls",
            "audit-controls",
            "integrity-controls",
            "transmission-security",
        ]
    }

    # Check if framework is supported
    if framework not in frameworks:
        return {
            "app_name": app_name,
            "framework": framework,
            "status": "error",
            "message": f"Unsupported compliance framework: {framework}",
            "supported_frameworks": list(frameworks.keys())
        }

    # In a real implementation, this would analyze scan results against framework requirements
    # For demonstration, we'll return mock compliance results
    requirements = frameworks[framework]
    compliance_results = []
    
    for req in requirements:
        # Simulate compliance check for each requirement
        compliant = bool(hash(f"{app_name}{req}") % 3 != 0)  # Random compliance result
        compliance_results.append({
            "requirement": req,
            "compliant": compliant,
            "details": f"Details for {req} compliance check" if compliant else f"Failed {req} compliance check",
            "recommendation": "" if compliant else f"Implement proper {req} controls"
        })

    compliant_count = sum(1 for r in compliance_results if r["compliant"])
    
    return {
        "app_name": app_name,
        "framework": framework,
        "check_time": datetime.now().isoformat(),
        "requirements_count": len(requirements),
        "compliant_count": compliant_count,
        "compliance_percentage": round(compliant_count / len(requirements) * 100, 1),
        "overall_status": "compliant" if compliant_count == len(requirements) else "non-compliant",
        "results": compliance_results
    }


def generate_security_report(
    app_name: str,
    include_compliance: bool = False,
    compliance_framework: Optional[str] = None,
    output_file: Optional[str] = None,
    report_format: str = "text"
) -> Dict[str, Any]:
    """
    Generate a comprehensive security report.

    Args:
        app_name: Name of the application
        include_compliance: Whether to include compliance checks
        compliance_framework: Framework to check compliance against
        output_file: Output file for the report
        report_format: Format for the report (text, json, html)

    Returns:
        Dict containing the complete report data
    """
    # Run security scan
    scan_results = scan(app_name, scan_type="all")
    
    # Prepare report data
    report = {
        "app_name": app_name,
        "report_type": "security",
        "timestamp": datetime.now().isoformat(),
        "scan_results": scan_results
    }
    
    # Add compliance data if requested
    if include_compliance:
        framework = compliance_framework or "owasp-top10"
        compliance_results = check_compliance(app_name, framework, scan_results)
        report["compliance"] = compliance_results
    
    # Generate report file if requested
    if output_file:
        if report_format == "json":
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2)
        else:
            # In a real implementation, this would generate text/HTML report
            # For demonstration, we'll simulate it
            with open(output_file, 'w') as f:
                f.write(f"Security Report for {app_name}\n")
                f.write(f"Generated: {report['timestamp']}\n\n")
                f.write("--- See detailed content in the JSON structure ---\n")
    
    return report
