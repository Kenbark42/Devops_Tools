"""
Tests for the DevOps Toolkit CLI.
"""
import pytest
from click.testing import CliRunner

from devops_toolkit.cli import main, deploy, monitor, provision, security_scan


@pytest.fixture
def runner():
    """Fixture for CLI test runner."""
    return CliRunner()


def test_main_command(runner):
    """Test main command executes without error."""
    result = runner.invoke(main)
    assert result.exit_code == 0
    assert "DevOps Toolkit" in result.output


def test_deploy_command(runner):
    """Test deploy command with required arguments."""
    result = runner.invoke(
        deploy,
        [
            "--app-name", "test-app",
            "--version", "1.0.0",
            "--env", "dev",
        ],
    )
    assert result.exit_code == 0
    assert "Deploying test-app" in result.output
    assert "version 1.0.0" in result.output
    assert "to dev" in result.output
    assert "Deployment completed successfully" in result.output


def test_deploy_command_missing_args(runner):
    """Test deploy command with missing required arguments."""
    result = runner.invoke(deploy, ["--app-name", "test-app"])
    assert result.exit_code != 0
    assert "Missing option" in result.output


def test_deploy_command_invalid_env(runner):
    """Test deploy command with invalid environment."""
    result = runner.invoke(
        deploy,
        [
            "--app-name", "test-app",
            "--version", "1.0.0",
            "--env", "invalid-env",
        ],
    )
    assert result.exit_code != 0
    assert "invalid choice" in result.output.lower()


def test_monitor_command(runner):
    """Test monitor command with required arguments."""
    result = runner.invoke(
        monitor,
        [
            "--app-name", "test-app",
            "--env", "production",
        ],
    )
    assert result.exit_code == 0
    assert "Monitoring test-app" in result.output
    assert "in production environment" in result.output
    assert "one-time" in result.output


def test_monitor_command_watch_mode(runner):
    """Test monitor command in watch mode."""
    result = runner.invoke(
        monitor,
        [
            "--app-name", "test-app",
            "--env", "staging",
            "--watch",
        ],
    )
    assert result.exit_code == 0
    assert "continuous" in result.output


def test_provision_command(runner):
    """Test provision command with required arguments."""
    result = runner.invoke(
        provision,
        [
            "--provider", "aws",
            "--template", "infra/template.yaml",
        ],
    )
    assert result.exit_code == 0
    assert "Provisioning infrastructure" in result.output
    assert "aws" in result.output.lower()
    assert "template.yaml" in result.output


def test_provision_command_dry_run(runner):
    """Test provision command in dry-run mode."""
    result = runner.invoke(
        provision,
        [
            "--provider", "aws",
            "--template", "infra/template.yaml",
            "--dry-run",
        ],
    )
    assert result.exit_code == 0
    assert "Validating" in result.output
    assert "validation successful" in result.output.lower()


def test_security_scan_command(runner):
    """Test security scan command with required arguments."""
    result = runner.invoke(
        security_scan,
        [
            "--app-name", "test-app",
        ],
    )
    assert result.exit_code == 0
    assert "Running all security scan" in result.output
    assert "Security scan completed" in result.output


def test_security_scan_command_with_scan_type(runner):
    """Test security scan command with specific scan type."""
    result = runner.invoke(
        security_scan,
        [
            "--app-name", "test-app",
            "--scan-type", "dependencies",
        ],
    )
    assert result.exit_code == 0
    assert "Running dependencies security scan" in result.output


def test_security_scan_command_with_output(runner):
    """Test security scan command with output file."""
    with runner.isolated_filesystem():
        result = runner.invoke(
            security_scan,
            [
                "--app-name", "test-app",
                "--output", "report.txt",
            ],
        )
        assert result.exit_code == 0
        assert "Report saved to" in result.output
