"""
Tests for the deployment module.
"""
import os
import tempfile
from typing import Dict, Any

import pytest
import yaml

from devops_toolkit.tools.deployment import (
    load_config,
    deploy,
    rollback,
    get_deployment_history,
    DeploymentConfig,
)


@pytest.fixture
def sample_config() -> Dict[str, Any]:
    """Sample configuration for testing."""
    return {
        "deployment": {
            "replicas": 3,
            "resources": {
                "limits": {
                    "cpu": "500m",
                    "memory": "512Mi"
                },
                "requests": {
                    "cpu": "250m",
                    "memory": "256Mi"
                }
            },
            "env_vars": {
                "DEBUG": "false",
                "LOG_LEVEL": "info"
            },
            "healthcheck": {
                "path": "/health",
                "port": 8080,
                "initialDelaySeconds": 10,
                "periodSeconds": 30
            },
            "volumes": [
                {
                    "name": "config-volume",
                    "mountPath": "/etc/config"
                }
            ]
        }
    }


@pytest.fixture
def config_file(sample_config: Dict[str, Any]) -> str:
    """Create a temporary config file for testing."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".yaml") as f:
        yaml.dump(sample_config, f)
        config_path = f.name

    yield config_path

    # Clean up the temporary file
    if os.path.exists(config_path):
        os.unlink(config_path)


def test_load_config(config_file: str, sample_config: Dict[str, Any]) -> None:
    """Test loading configuration from a file."""
    loaded_config = load_config(config_file)
    assert loaded_config == sample_config


def test_load_config_file_not_found() -> None:
    """Test handling of missing configuration file."""
    with pytest.raises(FileNotFoundError):
        load_config("nonexistent_config.yaml")


def test_deployment_config_model() -> None:
    """Test the DeploymentConfig model."""
    # Minimal config
    config = DeploymentConfig(
        app_name="test-app",
        version="1.0.0",
        environment="dev"
    )
    assert config.app_name == "test-app"
    assert config.version == "1.0.0"
    assert config.environment == "dev"
    assert config.replicas == 1  # Default value

    # Full config
    full_config = DeploymentConfig(
        app_name="test-app",
        version="1.0.0",
        environment="production",
        replicas=3,
        resources={
            "limits": {
                "cpu": "500m",
                "memory": "512Mi"
            }
        },
        env_vars={
            "DEBUG": "false"
        },
        healthcheck={
            "path": "/health"
        },
        volumes=[
            {
                "name": "config-volume",
                "mountPath": "/etc/config"
            }
        ]
    )
    assert full_config.replicas == 3
    assert full_config.resources["limits"]["cpu"] == "500m"
    assert full_config.env_vars["DEBUG"] == "false"


def test_deploy_function(config_file: str) -> None:
    """Test the deploy function."""
    result = deploy(
        app_name="test-app",
        version="1.0.0",
        environment="dev",
        config_path=config_file,
        wait=False
    )

    assert result["status"] == "success"
    assert result["app_name"] == "test-app"
    assert result["version"] == "1.0.0"
    assert result["environment"] == "dev"
    assert "deployment_time" in result
    assert "details" in result


def test_rollback_function() -> None:
    """Test the rollback function."""
    result = rollback(
        app_name="test-app",
        environment="dev"
    )

    assert result["status"] == "success"
    assert result["app_name"] == "test-app"
    assert result["environment"] == "dev"
    assert "rollback_time" in result

    # Test with specific version
    result_with_version = rollback(
        app_name="test-app",
        environment="dev",
        version="1.0.0"
    )
    assert result_with_version["rollback_to"] == "1.0.0"


def test_get_deployment_history() -> None:
    """Test retrieving deployment history."""
    history = get_deployment_history(
        app_name="test-app",
        environment="dev",
        limit=2
    )

    assert isinstance(history, list)
    assert len(history) <= 2

    if history:
        entry = history[0]
        assert "version" in entry
        assert "deployed_at" in entry
        assert "status" in entry
