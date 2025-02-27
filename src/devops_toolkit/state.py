"""
DevOps Toolkit - State Management Module

This module provides functionality for tracking and managing state of
deployments, infrastructure, and other resources.
"""
import os
import json
import time
import shutil
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple, Union
from pathlib import Path

# Local imports
from devops_toolkit.config import get_config
from devops_toolkit.logging import get_logger

# Initialize logger
logger = get_logger(__name__)


class StateError(Exception):
    """Raised when state operations encounter an error."""
    pass


class State:
    """
    Base class for managing state information.
    """

    def __init__(self,
                 resource_type: str,
                 resource_id: str,
                 state_dir: Optional[str] = None):
        """
        Initialize state manager.

        Args:
            resource_type: Type of resource (e.g., "deployment", "infrastructure")
            resource_id: Unique identifier for the resource
            state_dir: Directory to store state files (optional)
                Defaults to config value or ~/.devops-toolkit/state
        """
        self.resource_type = resource_type
        self.resource_id = resource_id

        # Get state directory from config if not provided
        if state_dir is None:
            config = get_config()
            state_dir = config.get_global().state_dir

        self.state_dir = os.path.expanduser(state_dir)
        self.resource_dir = os.path.join(
            self.state_dir, self.resource_type, self.resource_id
        )

        # Ensure state directory exists
        os.makedirs(self.resource_dir, exist_ok=True)

        # Current state data
        self._state_data: Dict[str, Any] = {}
        self._loaded = False

    def _get_state_file_path(self) -> str:
        """
        Get path to the state file.

        Returns:
            Path to state file
        """
        return os.path.join(self.resource_dir, "state.json")

    def _get_history_dir(self) -> str:
        """
        Get path to the history directory.

        Returns:
            Path to history directory
        """
        history_dir = os.path.join(self.resource_dir, "history")
        os.makedirs(history_dir, exist_ok=True)
        return history_dir

    def load(self) -> Dict[str, Any]:
        """
        Load state data from file.

        Returns:
            Dict containing state data

        Raises:
            StateError: If state file cannot be loaded
        """
        state_file = self._get_state_file_path()

        if not os.path.exists(state_file):
            # Initialize empty state if file doesn't exist
            self._state_data = {
                "resource_type": self.resource_type,
                "resource_id": self.resource_id,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "version": 1,
                "history": [],
                "data": {}
            }
            self._loaded = True
            return self._state_data

        try:
            with open(state_file, 'r') as f:
                self._state_data = json.load(f)

                # Ensure all required keys exist
                if "version" not in self._state_data:
                    self._state_data["version"] = 1
                if "history" not in self._state_data:
                    self._state_data["history"] = []
                if "data" not in self._state_data:
                    self._state_data["data"] = {}

                self._loaded = True
                return self._state_data
        except json.JSONDecodeError as e:
            raise StateError(f"Invalid state file format: {str(e)}")
        except Exception as e:
            raise StateError(f"Error loading state file: {str(e)}")

    def save(self, data: Optional[Dict[str, Any]] = None) -> str:
        """
        Save state data to file.

        Args:
            data: State data to save (optional)
                If not provided, will save current state data

        Returns:
            Path to saved state file

        Raises:
            StateError: If state file cannot be saved
        """
        if data is not None:
            self._state_data.update({"data": data})

        # Update metadata
        self._state_data["updated_at"] = datetime.now().isoformat()
        if "version" not in self._state_data:
            self._state_data["version"] = 1
        else:
            self._state_data["version"] += 1

        # Save history
        history_entry = {
            "version": self._state_data["version"],
            "timestamp": self._state_data["updated_at"],
            "data": self._state_data["data"]
        }

        if "history" not in self._state_data:
            self._state_data["history"] = []

        self._state_data["history"].append(
            {"version": history_entry["version"],
             "timestamp": history_entry["timestamp"]}
        )

        # Limit history entries in main state file (keep only the last 5)
        if len(self._state_data["history"]) > 5:
            self._state_data["history"] = self._state_data["history"][-5:]

        # Save current state
        state_file = self._get_state_file_path()
        try:
            with open(state_file, 'w') as f:
                json.dump(self._state_data, f, indent=2)
        except Exception as e:
            raise StateError(f"Error saving state file: {str(e)}")

        # Save history entry
        history_dir = self._get_history_dir()
        history_file = os.path.join(
            history_dir, f"v{history_entry['version']}-{int(time.time())}.json"
        )
        try:
            with open(history_file, 'w') as f:
                json.dump(history_entry, f, indent=2)
        except Exception as e:
            logger.warning(f"Error saving history file: {str(e)}")

        return state_file

    def get(self) -> Dict[str, Any]:
        """
        Get current state data.

        Returns:
            Dict containing state data
        """
        if not self._loaded:
            self.load()
        return self._state_data["data"]

    def get_metadata(self) -> Dict[str, Any]:
        """
        Get state metadata.

        Returns:
            Dict containing state metadata
        """
        if not self._loaded:
            self.load()

        metadata = {k: v for k, v in self._state_data.items() if k != "data"}
        return metadata

    def get_version(self, version: Optional[int] = None) -> Dict[str, Any]:
        """
        Get specific version of state data.

        Args:
            version: Version number to retrieve
                If None, returns latest version

        Returns:
            Dict containing state data for the specified version

        Raises:
            StateError: If version cannot be found
        """
        if not self._loaded:
            self.load()

        if version is None:
            return self._state_data["data"]

        # Look for version in history directory
        history_dir = self._get_history_dir()
        version_files = [f for f in os.listdir(
            history_dir) if f.startswith(f"v{version}-")]

        if not version_files:
            raise StateError(f"Version {version} not found in history")

        try:
            with open(os.path.join(history_dir, version_files[0]), 'r') as f:
                history_entry = json.load(f)
                return history_entry["data"]
        except Exception as e:
            raise StateError(f"Error loading version {version}: {str(e)}")

    def list_versions(self) -> List[Dict[str, Any]]:
        """
        List all available versions of state data.

        Returns:
            List of dicts containing version information
        """
        if not self._loaded:
            self.load()

        # Get versions from history directory
        history_dir = self._get_history_dir()
        versions = []

        if os.path.exists(history_dir):
            for filename in os.listdir(history_dir):
                if filename.startswith("v") and filename.endswith(".json"):
                    try:
                        with open(os.path.join(history_dir, filename), 'r') as f:
                            history_entry = json.load(f)
                            versions.append({
                                "version": history_entry["version"],
                                "timestamp": history_entry["timestamp"]
                            })
                    except Exception as e:
                        logger.warning(
                            f"Error reading history file {filename}: {str(e)}")

        # Sort by version
        return sorted(versions, key=lambda x: x["version"])

    def rollback(self, version: Optional[int] = None) -> Dict[str, Any]:
        """
        Rollback to a previous version of state data.

        Args:
            version: Version to rollback to
                If None, rolls back to the previous version

        Returns:
            Dict containing state data after rollback

        Raises:
            StateError: If rollback fails
        """
        if not self._loaded:
            self.load()

        # Get list of versions
        versions = self.list_versions()
        if not versions:
            raise StateError("No versions available for rollback")

        # Determine target version
        current_version = self._state_data["version"]

        if version is None:
            # Rollback to previous version
            if len(versions) < 2:
                raise StateError("No previous version available for rollback")

            # Find previous version
            prev_versions = [
                v for v in versions if v["version"] < current_version]
            if not prev_versions:
                raise StateError("No previous version available for rollback")

            target_version = max(prev_versions, key=lambda x: x["version"])[
                "version"]
        else:
            # Check if target version exists
            if version >= current_version:
                raise StateError(
                    f"Cannot rollback to version {version}: not a previous version")

            target_versions = [v for v in versions if v["version"] == version]
            if not target_versions:
                raise StateError(f"Version {version} not found in history")

            target_version = version

        # Get target version data
        target_data = self.get_version(target_version)

        # Update state with target version data
        self._state_data["data"] = target_data
        # Increment version for the rollback action
        self._state_data["version"] += 1
        self._state_data["updated_at"] = datetime.now().isoformat()

        # Save new state
        self.save()

        logger.info(
            f"Rolled back to version {target_version} (created new version {self._state_data['version']})")
        return self._state_data["data"]

    def delete(self) -> None:
        """
        Delete state data and history.

        Raises:
            StateError: If deletion fails
        """
        try:
            if os.path.exists(self.resource_dir):
                shutil.rmtree(self.resource_dir)

            self._state_data = {}
            self._loaded = False
            logger.info(
                f"Deleted state for {self.resource_type}/{self.resource_id}")
        except Exception as e:
            raise StateError(f"Error deleting state: {str(e)}")


class StateManager:
    """
    Manager for all state objects in the system.
    """

    def __init__(self, state_dir: Optional[str] = None):
        """
        Initialize state manager.

        Args:
            state_dir: Directory to store state files (optional)
                Defaults to config value or ~/.devops-toolkit/state
        """
        # Get state directory from config if not provided
        if state_dir is None:
            config = get_config()
            state_dir = config.get_global().state_dir

        self.state_dir = os.path.expanduser(state_dir)

        # Ensure state directory exists
        os.makedirs(self.state_dir, exist_ok=True)

    def get_state(self, resource_type: str, resource_id: str) -> State:
        """
        Get state object for a specific resource.

        Args:
            resource_type: Type of resource
            resource_id: Unique identifier for the resource

        Returns:
            State object
        """
        return State(resource_type, resource_id, self.state_dir)

    def list_resources(self, resource_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all resources with state data.

        Args:
            resource_type: Filter by resource type (optional)

        Returns:
            List of dicts containing resource information
        """
        resources = []

        # If resource type is specified, only list that type
        if resource_type:
            resource_type_dir = os.path.join(self.state_dir, resource_type)
            if os.path.exists(resource_type_dir):
                for resource_id in os.listdir(resource_type_dir):
                    resource_dir = os.path.join(resource_type_dir, resource_id)
                    if os.path.isdir(resource_dir):
                        try:
                            state = State(
                                resource_type, resource_id, self.state_dir)
                            metadata = state.get_metadata()
                            resources.append({
                                "resource_type": resource_type,
                                "resource_id": resource_id,
                                "metadata": metadata
                            })
                        except Exception as e:
                            logger.warning(
                                f"Error loading state for {resource_type}/{resource_id}: {str(e)}")
        else:
            # List all resource types
            if os.path.exists(self.state_dir):
                for resource_type in os.listdir(self.state_dir):
                    resource_type_dir = os.path.join(
                        self.state_dir, resource_type)
                    if os.path.isdir(resource_type_dir):
                        for resource_id in os.listdir(resource_type_dir):
                            resource_dir = os.path.join(
                                resource_type_dir, resource_id)
                            if os.path.isdir(resource_dir):
                                try:
                                    state = State(
                                        resource_type, resource_id, self.state_dir)
                                    metadata = state.get_metadata()
                                    resources.append({
                                        "resource_type": resource_type,
                                        "resource_id": resource_id,
                                        "metadata": metadata
                                    })
                                except Exception as e:
                                    logger.warning(
                                        f"Error loading state for {resource_type}/{resource_id}: {str(e)}")

        return resources

    def delete_resource(self, resource_type: str, resource_id: str) -> None:
        """
        Delete state data for a specific resource.

        Args:
            resource_type: Type of resource
            resource_id: Unique identifier for the resource

        Raises:
            StateError: If deletion fails
        """
        state = State(resource_type, resource_id, self.state_dir)
        state.delete()

    def export_state(self, output_dir: str,
                     resource_type: Optional[str] = None,
                     resource_id: Optional[str] = None) -> str:
        """
        Export state data to a directory.

        Args:
            output_dir: Directory to export state data to
            resource_type: Type of resource to export (optional)
            resource_id: Specific resource ID to export (optional)

        Returns:
            Path to exported state data

        Raises:
            StateError: If export fails
        """
        # Create output directory
        output_path = os.path.expanduser(output_dir)
        os.makedirs(output_path, exist_ok=True)

        # Determine what to export
        if resource_type and resource_id:
            # Export specific resource
            state = State(resource_type, resource_id, self.state_dir)
            data = {
                "resource_type": resource_type,
                "resource_id": resource_id,
                "state": state.get(),
                "metadata": state.get_metadata(),
                "exported_at": datetime.now().isoformat()
            }

            export_file = os.path.join(
                output_path, f"{resource_type}-{resource_id}.json")
            try:
                with open(export_file, 'w') as f:
                    json.dump(data, f, indent=2)
                return export_file
            except Exception as e:
                raise StateError(f"Error exporting state: {str(e)}")

        else:
            # Export all resources or resources of a specific type
            resources = self.list_resources(resource_type)

            if not resources:
                raise StateError("No resources found to export")

            # Export each resource to a separate file
            exported_files = []
            for resource in resources:
                try:
                    state = State(
                        resource["resource_type"],
                        resource["resource_id"],
                        self.state_dir
                    )
                    data = {
                        "resource_type": resource["resource_type"],
                        "resource_id": resource["resource_id"],
                        "state": state.get(),
                        "metadata": state.get_metadata(),
                        "exported_at": datetime.now().isoformat()
                    }

                    export_file = os.path.join(
                        output_path,
                        f"{resource['resource_type']}-{resource['resource_id']}.json"
                    )
                    with open(export_file, 'w') as f:
                        json.dump(data, f, indent=2)
                    exported_files.append(export_file)
                except Exception as e:
                    logger.warning(
                        f"Error exporting state for {resource['resource_type']}/{resource['resource_id']}: {str(e)}")

            # Create index file
            index_file = os.path.join(output_path, "index.json")
            try:
                with open(index_file, 'w') as f:
                    json.dump({
                        "resources": resources,
                        "exported_at": datetime.now().isoformat()
                    }, f, indent=2)
            except Exception as e:
                logger.warning(f"Error creating index file: {str(e)}")

            return output_path


# Global state manager instance
_state_manager_instance = None


def get_state_manager() -> StateManager:
    """
    Get the global state manager instance.

    Returns:
        StateManager object
    """
    global _state_manager_instance
    if _state_manager_instance is None:
        _state_manager_instance = StateManager()
    return _state_manager_instance
