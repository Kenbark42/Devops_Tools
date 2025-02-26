"""
Tests for the infrastructure module.
"""
import os
import tempfile
from typing import Dict, Any, List
from unittest import mock

import pytest
import yaml
import json

from devops_toolkit.tools.infrastructure import (
    ProviderNotSupportedError,
    load_template,
    load_parameters,
    provision,
    destroy,
    get_infrastructure_status,
    scale,
    generate_terraform,
)


@pytest.fixture
def sample_yaml_template() -> str:
    """Create a temporary YAML template file for testing."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".yaml") as f:
        template = {
            "resources": {
                "compute": [
                    {
                        "name": "app-server",
                        "type": "ec2-instance",
                        "size": "t3.medium",
                        "count": 2
                    }
                ],
                "database": [
                    {
                        "name": "app-db",
                        "type": "rds-instance",
                        "engine": "postgres",
                        "size": "db.t3.small"
                    }
                ],
                "networking": [
                    {
                        "name": "app-vpc",
                        "type": "vpc",
                        "cidr": "10.0.0.0/16"
                    }
                ]
            }
        }
        yaml.dump(template, f)
        template_path = f.name

    yield template_path

    # Clean up the temporary file
    if os.path.exists(template_path):
        os.unlink(template_path)


@pytest.fixture
def sample_json_template() -> str:
    """Create a temporary JSON template file for testing."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
        template = {
            "resources": {
                "compute": [
                    {
                        "name": "app-server",
                        "type": "ec2-instance",
                        "size": "t3.medium",
                        "count": 2
                    }
                ]
            }
        }
        json.dump(template, f)
        template_path = f.name

    yield template_path

    # Clean up the temporary file
    if os.path.exists(template_path):
        os.unlink(template_path)


@pytest.fixture
def sample_yaml_params() -> str:
    """Create a temporary YAML parameters file for testing."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".yaml") as f:
        params = {
            "environment": "dev",
            "region": "us-west-2",
            "tags": {
                "project": "test-project",
                "owner": "test-team"
            }
        }
        yaml.dump(params, f)
        params_path = f.name

    yield params_path

    # Clean up the temporary file
    if os.path.exists(params_path):
        os.unlink(params_path)


class TestTemplateLoading:
    """Tests for template loading functions."""

    def test_load_yaml_template(self, sample_yaml_template):
        """Test loading YAML template."""
        template = load_template(sample_yaml_template)
        assert isinstance(template, dict)
        assert "resources" in template
        assert "compute" in template["resources"]
        assert len(template["resources"]["compute"]) == 1
        assert template["resources"]["compute"][0]["name"] == "app-server"

    def test_load_json_template(self, sample_json_template):
        """Test loading JSON template."""
        template = load_template(sample_json_template)
        assert isinstance(template, dict)
        assert "resources" in template
        assert "compute" in template["resources"]
        assert len(template["resources"]["compute"]) == 1
        assert template["resources"]["compute"][0]["name"] == "app-server"

    def test_load_template_not_found(self):
        """Test handling of missing template file."""
        with pytest.raises(FileNotFoundError):
            load_template("nonexistent_template.yaml")

    def test_load_template_invalid_format(self):
        """Test handling of unsupported template format."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            f.write(b"This is not a valid template")
            template_path = f.name

        try:
            with pytest.raises(ValueError, match="Unsupported template format"):
                load_template(template_path)
        finally:
            if os.path.exists(template_path):
                os.unlink(template_path)

    def test_load_yaml_params(self, sample_yaml_params):
        """Test loading YAML parameters."""
        params = load_parameters(sample_yaml_params)
        assert isinstance(params, dict)
        assert "environment" in params
        assert params["environment"] == "dev"
        assert "region" in params
        assert "tags" in params

    def test_load_params_not_found(self):
        """Test handling of missing parameters file."""
        with pytest.raises(FileNotFoundError):
            load_parameters("nonexistent_params.yaml")


class TestProvisioning:
    """Tests for infrastructure provisioning functions."""

    def test_provision_unsupported_provider(self, sample_yaml_template):
        """Test provision with unsupported provider."""
        with pytest.raises(ProviderNotSupportedError):
            provision("unsupported", sample_yaml_template)

    def test_provision_dry_run(self, sample_yaml_template, sample_yaml_params):
        """Test provision in dry-run mode."""
        result = provision("aws", sample_yaml_template, sample_yaml_params, dry_run=True)
        assert result["status"] == "validated"
        assert result["provider"] == "aws"
        assert result["template"] == sample_yaml_template
        assert result["parameters"] == sample_yaml_params
        assert "validation_time" in result
        assert "issues" in result

    def test_provision_actual(self, sample_yaml_template, sample_yaml_params):
        """Test actual provisioning."""
        result = provision("aws", sample_yaml_template, sample_yaml_params)
        assert result["status"] == "success"
        assert result["provider"] == "aws"
        assert result["template"] == sample_yaml_template
        assert result["parameters"] == sample_yaml_params
        assert "provision_id" in result
        assert "provision_time" in result
        assert "resources" in result
        assert len(result["resources"]) > 0
        assert "outputs" in result


class TestInfrastructureManagement:
    """Tests for infrastructure management functions."""

    def test_destroy(self):
        """Test destroying infrastructure."""
        result = destroy("aws", "infra-1234567890")
        assert result["status"] == "success"
        assert result["provider"] == "aws"
        assert result["provision_id"] == "infra-1234567890"
        assert "destroy_time" in result

    def test_get_infrastructure_status_specific(self):
        """Test getting status of specific infrastructure."""
        result = get_infrastructure_status("aws", "infra-1234567890")
        assert isinstance(result, dict)
        assert result["provider"] == "aws"
        assert result["provision_id"] == "infra-1234567890"
        assert "status" in result
        assert "resources" in result

    def test_get_infrastructure_status_all(self):
        """Test getting status of all infrastructure."""
        result = get_infrastructure_status("aws")
        assert isinstance(result, list)
        assert len(result) > 0
        for item in result:
            assert "provider" in item
            assert "provision_id" in item
            assert "status" in item

    def test_scale(self):
        """Test scaling infrastructure resources."""
        result = scale("aws", "infra-1234567890", "compute", 5)
        assert result["status"] == "success"
        assert result["provider"] == "aws"
        assert result["provision_id"] == "infra-1234567890"
        assert result["resource_type"] == "compute"
        assert result["new_count"] == 5
        assert "previous_count" in result
        assert "scale_time" in result


class TestTerraformGeneration:
    """Tests for Terraform generation functions."""

    def test_generate_terraform(self, sample_yaml_template):
        """Test generating Terraform code."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = generate_terraform(sample_yaml_template, tmpdir)
            assert result["status"] == "success"
            assert result["template"] == sample_yaml_template
            assert result["output_dir"] == tmpdir
            assert "files" in result
            
            # Check if files were created
            for file in result["files"]:
                file_path = os.path.join(tmpdir, file)
                assert os.path.exists(file_path)
                
                # Check file content
                with open(file_path, 'r') as f:
                    content = f.read()
                    assert f"Generated from {sample_yaml_template}" in content
