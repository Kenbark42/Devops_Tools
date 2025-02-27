"""
DevOps Toolkit - Configuration Management Module

This module provides a unified way to load, validate, and access configuration
across the entire toolkit.
"""
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, Union, List, Set

import yaml
from pydantic import BaseModel, Field, ValidationError, create_model


class ConfigError(Exception):
    """Raised when configuration errors occur."""
    pass


class ConfigBase(BaseModel):
    """Base class for all configuration models."""
    pass


class GlobalConfig(ConfigBase):
    """Global configuration settings that apply to all modules."""
    log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    log_file: Optional[str] = None
    state_dir: str = Field(default="~/.devops-toolkit/state")
    secrets_dir: str = Field(default="~/.devops-toolkit/secrets")
    default_environment: str = Field(default="dev")
    environments: List[str] = Field(default=["dev", "staging", "production"])


class Config:
    """Main configuration handler for DevOps Toolkit."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration handler.

        Args:
            config_path: Path to the configuration file (optional)
                If not provided, will look in standard locations.
        """
        self._config_path = config_path
        self._config_data: Dict[str, Any] = {}
        self._loaded = False
        self._global_config: Optional[GlobalConfig] = None
        self._module_configs: Dict[str, BaseModel] = {}

    def _find_config_file(self) -> str:
        """
        Find configuration file in standard locations.

        Returns:
            Path to the configuration file

        Raises:
            ConfigError: If configuration file cannot be found
        """
        # If config path is provided, use it
        if self._config_path:
            if os.path.exists(self._config_path):
                return self._config_path
            else:
                raise ConfigError(f"Specified configuration file not found: {self._config_path}")

        # List of locations to check, in order of preference
        search_paths = [
            # Current directory
            "./devops.yaml",
            "./devops.yml",
            "./devops.json",
            "./config.yaml",
            "./config.yml",
            "./config.json",
            # User config directory
            os.path.expanduser("~/.devops-toolkit/config.yaml"),
            os.path.expanduser("~/.devops-toolkit/config.yml"),
            os.path.expanduser("~/.config/devops-toolkit/config.yaml"),
            # System config directory
            "/etc/devops-toolkit/config.yaml",
        ]

        for path in search_paths:
            if os.path.exists(path):
                return path

        # No configuration file found, use default
        return ""

    def _load_config_file(self, config_path: str) -> Dict[str, Any]:
        """
        Load configuration from file.

        Args:
            config_path: Path to the configuration file

        Returns:
            Dict containing configuration data

        Raises:
            ConfigError: If configuration file cannot be loaded or has invalid format
        """
        if not config_path:
            return {}

        try:
            _, ext = os.path.splitext(config_path)
            with open(config_path, 'r') as f:
                if ext.lower() in ('.yaml', '.yml'):
                    return yaml.safe_load(f) or {}
                elif ext.lower() == '.json':
                    return json.load(f)
                else:
                    raise ConfigError(f"Unsupported configuration format: {ext}")
        except (yaml.YAMLError, json.JSONDecodeError) as e:
            raise ConfigError(f"Invalid configuration format in {config_path}: {str(e)}")
        except Exception as e:
            raise ConfigError(f"Error loading configuration from {config_path}: {str(e)}")

    def load(self) -> 'Config':
        """
        Load configuration from file.

        Returns:
            Self, for method chaining

        Raises:
            ConfigError: If configuration cannot be loaded
        """
        try:
            # Find and load configuration file
            config_path = self._find_config_file()
            if config_path:
                self._config_path = config_path
                self._config_data = self._load_config_file(config_path)
            else:
                self._config_data = {}

            # Load global configuration
            global_data = self._config_data.get('global', {})
            self._global_config = GlobalConfig(**global_data)

            # Create necessary directories
            self._ensure_directories()

            self._loaded = True
            return self
        except ValidationError as e:
            raise ConfigError(f"Configuration validation error: {str(e)}")
        except Exception as e:
            raise ConfigError(f"Error loading configuration: {str(e)}")

    def _ensure_directories(self) -> None:
        """Ensure that required directories exist."""
        if self._global_config:
            for dir_path in [self._global_config.state_dir, self._global_config.secrets_dir]:
                full_path = os.path.expanduser(dir_path)
                os.makedirs(full_path, exist_ok=True, mode=0o700)  # Secure permissions for secrets

    def get_global(self) -> GlobalConfig:
        """
        Get global configuration.

        Returns:
            GlobalConfig object

        Raises:
            ConfigError: If configuration is not loaded
        """
        if not self._loaded:
            self.load()
        return self._global_config

    def get_module_config(self, module_name: str, model_class: type) -> BaseModel:
        """
        Get configuration for a specific module.

        Args:
            module_name: Name of the module
            model_class: Pydantic model class for module configuration

        Returns:
            Configuration object for the module

        Raises:
            ConfigError: If configuration is invalid
        """
        if not self._loaded:
            self.load()

        # Return cached config if available
        if module_name in self._module_configs:
            return self._module_configs[module_name]

        try:
            # Get module configuration from overall config
            module_data = self._config_data.get(module_name, {})
            config_obj = model_class(**module_data)
            self._module_configs[module_name] = config_obj
            return config_obj
        except ValidationError as e:
            raise ConfigError(f"Invalid configuration for module {module_name}: {str(e)}")

    def save(self, config_path: Optional[str] = None) -> str:
        """
        Save current configuration to file.

        Args:
            config_path: Path to save configuration (optional)
                If not provided, will use the current config path or a default.

        Returns:
            Path to the saved configuration file

        Raises:
            ConfigError: If configuration cannot be saved
        """
        save_path = config_path or self._config_path or os.path.expanduser("~/.devops-toolkit/config.yaml")

        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)

        # Build complete config data
        config_data = {
            'global': self._global_config.dict()
        }

        # Add module configs
        for module_name, module_config in self._module_configs.items():
            config_data[module_name] = module_config.dict()

        try:
            _, ext = os.path.splitext(save_path)
            with open(save_path, 'w') as f:
                if ext.lower() in ('.yaml', '.yml'):
                    yaml.dump(config_data, f, default_flow_style=False)
                elif ext.lower() == '.json':
                    json.dump(config_data, f, indent=2)
                else:
                    raise ConfigError(f"Unsupported configuration format: {ext}")
            return save_path
        except Exception as e:
            raise ConfigError(f"Error saving configuration to {save_path}: {str(e)}")


# Global configuration instance
_config_instance = None


def get_config() -> Config:
    """
    Get the global configuration instance.

    Returns:
        Config object
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = Config().load()
    return _config_instance
