"""
DevOps Toolkit - Plugin Architecture Module

This module provides support for extending DevOps Toolkit with custom plugins
for various functions like deployment, infrastructure, monitoring, and more.
"""
import os
import sys
import importlib
import inspect
import pkgutil
from typing import Dict, Any, Optional, List, Set, Type, Callable, TypeVar, Generic, Union
from abc import ABC, abstractmethod
import logging

# Local imports
from devops_toolkit.config import get_config
from devops_toolkit.logging import get_logger

# Initialize logger
logger = get_logger(__name__)


class PluginError(Exception):
    """Raised when plugin operations encounter an error."""
    pass


T = TypeVar('T')


class Plugin(Generic[T], ABC):
    """
    Base class for all plugins.
    
    Type parameter T represents the plugin interface type.
    """
    
    @classmethod
    @abstractmethod
    def get_plugin_type(cls) -> str:
        """
        Get the type of plugin.
        
        Returns:
            String identifier for the plugin type (e.g., "deployment", "infrastructure")
        """
        pass
    
    @classmethod
    @abstractmethod
    def get_plugin_name(cls) -> str:
        """
        Get the name of the plugin.
        
        Returns:
            String identifier for the plugin (e.g., "aws", "kubernetes")
        """
        pass
    
    @classmethod
    def get_plugin_version(cls) -> str:
        """
        Get the version of the plugin.
        
        Returns:
            Version string for the plugin
        """
        return "1.0.0"
    
    @classmethod
    def get_plugin_description(cls) -> str:
        """
        Get the description of the plugin.
        
        Returns:
            Description string for the plugin
        """
        return cls.__doc__ or "No description available"


class PluginManager:
    """
    Manager for discovering, loading, and using plugins.
    """
    
    def __init__(self):
        """Initialize plugin manager."""
        self._plugins: Dict[str, Dict[str, Type[Plugin]]] = {}
        self._plugin_instances: Dict[str, Dict[str, Plugin]] = {}
        self._plugin_directories: List[str] = []
        self._loaded = False
    
    def register_plugin_directory(self, directory: str) -> None:
        """
        Register a directory for plugin discovery.
        
        Args:
            directory: Directory path to search for plugins
        """
        if os.path.exists(directory) and os.path.isdir(directory):
            if directory not in self._plugin_directories:
                self._plugin_directories.append(directory)
                logger.debug(f"Registered plugin directory: {directory}")
        else:
            logger.warning(f"Plugin directory not found: {directory}")
    
    def register_plugin(self, plugin_class: Type[Plugin]) -> None:
        """
        Register a plugin class.
        
        Args:
            plugin_class: Plugin class to register
        
        Raises:
            PluginError: If plugin registration fails
        """
        try:
            plugin_type = plugin_class.get_plugin_type()
            plugin_name = plugin_class.get_plugin_name()
            
            # Initialize plugin type dict if needed
            if plugin_type not in self._plugins:
                self._plugins[plugin_type] = {}
            
            # Register plugin
            self._plugins[plugin_type][plugin_name] = plugin_class
            logger.debug(f"Registered plugin: {plugin_type}/{plugin_name}")
        
        except Exception as e:
            raise PluginError(f"Failed to register plugin {plugin_class.__name__}: {str(e)}")
    
    def discover_plugins(self) -> None:
        """
        Discover plugins in registered directories.
        
        This method searches for Python modules in the registered directories
        and attempts to find and register plugin classes.
        """
        # Add built-in plugin directories
        config = get_config()
        
        # Add user plugin directory from config if it exists
        user_plugin_dir = os.path.expanduser("~/.devops-toolkit/plugins")
        if os.path.exists(user_plugin_dir):
            self.register_plugin_directory(user_plugin_dir)
        
        # Search for plugins in registered directories
        for directory in self._plugin_directories:
            self._discover_plugins_in_directory(directory)
        
        self._loaded = True
        logger.info(f"Discovered plugins: {self.get_plugin_counts()}")
    
    def _discover_plugins_in_directory(self, directory: str) -> None:
        """
        Discover plugins in a specific directory.
        
        Args:
            directory: Directory path to search for plugins
        """
        # Make sure directory is in the Python path
        if directory not in sys.path:
            sys.path.insert(0, directory)
        
        # Discover Python modules in directory
        for _, name, is_pkg in pkgutil.iter_modules([directory]):
            try:
                # Import the module
                module = importlib.import_module(name)
                
                # Search for plugin classes in module
                for item_name, item in inspect.getmembers(module, inspect.isclass):
                    # Check if it's a plugin class
                    if issubclass(item, Plugin) and item is not Plugin:
                        self.register_plugin(item)
            
            except Exception as e:
                logger.warning(f"Error loading module {name}: {str(e)}")
    
    def get_plugin(self, plugin_type: str, plugin_name: str) -> Optional[Type[Plugin]]:
        """
        Get a plugin class by type and name.
        
        Args:
            plugin_type: Type of plugin
            plugin_name: Name of plugin
        
        Returns:
            Plugin class or None if not found
        """
        if not self._loaded:
            self.discover_plugins()
        
        return self._plugins.get(plugin_type, {}).get(plugin_name)
    
    def get_plugin_instance(self, plugin_type: str, plugin_name: str, **kwargs) -> Optional[Plugin]:
        """
        Get a plugin instance by type and name.
        
        Args:
            plugin_type: Type of plugin
            plugin_name: Name of plugin
            **kwargs: Additional arguments to pass to plugin constructor
        
        Returns:
            Plugin instance or None if not found
        
        Raises:
            PluginError: If plugin instantiation fails
        """
        # Initialize cache for this plugin type if needed
        if plugin_type not in self._plugin_instances:
            self._plugin_instances[plugin_type] = {}
        
        # Return existing instance if already created
        if plugin_name in self._plugin_instances[plugin_type]:
            return self._plugin_instances[plugin_type][plugin_name]
        
        # Get plugin class
        plugin_class = self.get_plugin(plugin_type, plugin_name)
        if not plugin_class:
            return None
        
        try:
            # Create and cache instance
            instance = plugin_class(**kwargs)
            self._plugin_instances[plugin_type][plugin_name] = instance
            return instance
        
        except Exception as e:
            raise PluginError(f"Failed to instantiate plugin {plugin_type}/{plugin_name}: {str(e)}")
    
    def get_plugins_by_type(self, plugin_type: str) -> Dict[str, Type[Plugin]]:
        """
        Get all plugins of a specific type.
        
        Args:
            plugin_type: Type of plugins to get
        
        Returns:
            Dict mapping plugin names to plugin classes
        """
        if not self._loaded:
            self.discover_plugins()
        
        return self._plugins.get(plugin_type, {})
    
    def get_plugin_types(self) -> List[str]:
        """
        Get all available plugin types.
        
        Returns:
            List of plugin types
        """
        if not self._loaded:
            self.discover_plugins()
        
        return list(self._plugins.keys())
    
    def get_plugin_counts(self) -> Dict[str, int]:
        """
        Get counts of plugins by type.
        
        Returns:
            Dict mapping plugin types to counts
        """
        if not self._loaded:
            self.discover_plugins()
        
        return {plugin_type: len(plugins) for plugin_type, plugins in self._plugins.items()}


# Plugin interface types
class DeploymentPlugin(Plugin["DeploymentPlugin"]):
    """Base class for deployment plugins."""
    
    @classmethod
    def get_plugin_type(cls) -> str:
        return "deployment"
    
    @abstractmethod
    def deploy(self, app_name: str, version: str, environment: str, **kwargs) -> Dict[str, Any]:
        """
        Deploy an application to the target environment.
        
        Args:
            app_name: Name of the application
            version: Version to deploy
            environment: Target environment
            **kwargs: Additional deployment options
        
        Returns:
            Dict with deployment status and details
        """
        pass
    
    @abstractmethod
    def rollback(self, app_name: str, environment: str, version: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Rollback a deployment to a previous version.
        
        Args:
            app_name: Name of the application
            environment: Environment to rollback
            version: Specific version to rollback to (optional)
            **kwargs: Additional rollback options
        
        Returns:
            Dict with rollback status and details
        """
        pass


class InfrastructurePlugin(Plugin["InfrastructurePlugin"]):
    """Base class for infrastructure plugins."""
    
    @classmethod
    def get_plugin_type(cls) -> str:
        return "infrastructure"
    
    @abstractmethod
    def provision(self, template_path: str, params_path: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Provision infrastructure based on a template.
        
        Args:
            template_path: Path to the infrastructure template
            params_path: Path to the parameters file (optional)
            **kwargs: Additional provisioning options
        
        Returns:
            Dict with provisioning status and details
        """
        pass
    
    @abstractmethod
    def destroy(self, provision_id: str, **kwargs) -> Dict[str, Any]:
        """
        Destroy provisioned infrastructure.
        
        Args:
            provision_id: ID of the provisioned infrastructure
            **kwargs: Additional destruction options
        
        Returns:
            Dict with destruction status and details
        """
        pass


class MonitoringPlugin(Plugin["MonitoringPlugin"]):
    """Base class for monitoring plugins."""
    
    @classmethod
    def get_plugin_type(cls) -> str:
        return "monitoring"
    
    @abstractmethod
    def check_status(self, app_name: str, environment: str, **kwargs) -> Dict[str, Any]:
        """
        Check the status of an application.
        
        Args:
            app_name: Name of the application
            environment: Environment to check
            **kwargs: Additional status check options
        
        Returns:
            Dict containing status information
        """
        pass
    
    @abstractmethod
    def create_alert_rule(self, name: str, app_name: str, metric: str, threshold: float, **kwargs) -> Dict[str, Any]:
        """
        Create an alerting rule for a specific metric.
        
        Args:
            name: Name of the alert rule
            app_name: Name of the application
            metric: Metric to monitor
            threshold: Threshold value
            **kwargs: Additional alert rule options
        
        Returns:
            Dict containing the created alert rule
        """
        pass


class SecurityPlugin(Plugin["SecurityPlugin"]):
    """Base class for security plugins."""
    
    @classmethod
    def get_plugin_type(cls) -> str:
        return "security"
    
    @abstractmethod
    def scan(self, app_name: str, scan_type: str, **kwargs) -> Dict[str, Any]:
        """
        Perform security scans on applications.
        
        Args:
            app_name: Name of the application to scan
            scan_type: Type of security scan to perform
            **kwargs: Additional scan options
        
        Returns:
            Dict containing scan results
        """
        pass


# Global plugin manager instance
_plugin_manager_instance = None


def get_plugin_manager() -> PluginManager:
    """
    Get the global plugin manager instance.
    
    Returns:
        PluginManager object
    """
    global _plugin_manager_instance
    if _plugin_manager_instance is None:
        _plugin_manager_instance = PluginManager()
    return _plugin_manager_instance


# Example plugin implementation (for documentation)
class ExampleAWSDeploymentPlugin(DeploymentPlugin):
    """AWS deployment plugin for DevOps Toolkit."""
    
    @classmethod
    def get_plugin_name(cls) -> str:
        return "aws"
    
    @classmethod
    def get_plugin_version(cls) -> str:
        return "1.0.0"
    
    def __init__(self, region: str = "us-east-1", **kwargs):
        """
        Initialize AWS deployment plugin.
        
        Args:
            region: AWS region
            **kwargs: Additional options
        """
        self.region = region
    
    def deploy(self, app_name: str, version: str, environment: str, **kwargs) -> Dict[str, Any]:
        """
        Deploy an application to AWS.
        
        Args:
            app_name: Name of the application
            version: Version to deploy
            environment: Target environment
            **kwargs: Additional deployment options
        
        Returns:
            Dict with deployment status and details
        """
        # Implementation would use boto3 to deploy to AWS
        return {
            "status": "success",
            "app_name": app_name,
            "version": version,
            "environment": environment,
            "provider": "aws",
            "region": self.region
        }
    
    def rollback(self, app_name: str, environment: str, version: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Rollback a deployment on AWS.
        
        Args:
            app_name: Name of the application
            environment: Environment to rollback
            version: Specific version to rollback to (optional)
            **kwargs: Additional rollback options
        
        Returns:
            Dict with rollback status and details
        """
        # Implementation would use boto3 to rollback deployment
        return {
            "status": "success",
            "app_name": app_name,
            "environment": environment,
            "provider": "aws",
            "region": self.region,
            "rollback_to": version or "previous version"
        }
