"""
DevOps Toolkit - Template Library Module

This module provides functionality for managing infrastructure templates
including template storage, retrieval, validation, and parametrization.
"""
import os
import json
import yaml
import shutil
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional, List, Union, Set
from pathlib import Path
import re

# Local imports
from devops_toolkit.config import get_config
from devops_toolkit.logging import get_logger
from devops_toolkit.state import get_state_manager

# Initialize logger
logger = get_logger(__name__)


class TemplateError(Exception):
    """Raised when template operations encounter an error."""
    pass


class Template:
    """
    Class representing an infrastructure template.
    """

    def __init__(self, 
                 template_id: str, 
                 template_type: str,
                 provider: str,
                 template_path: Optional[str] = None,
                 content: Optional[Dict[str, Any]] = None):
        """
        Initialize template.

        Args:
            template_id: Unique identifier for the template
            template_type: Type of template (e.g., "compute", "network", "database")
            provider: Infrastructure provider (e.g., "aws", "azure", "gcp")
            template_path: Path to template file (optional)
            content: Template content as dictionary (optional)
                Either template_path or content must be provided

        Raises:
            TemplateError: If neither template_path nor content is provided
        """
        self.template_id = template_id
        self.template_type = template_type
        self.provider = provider
        self.template_path = template_path
        self._content = content

        # Validate that either path or content is provided
        if not template_path and not content:
            raise TemplateError("Either template_path or content must be provided")

        # Load content if not provided
        if not self._content and template_path:
            self._load_content()

    def _load_content(self) -> None:
        """
        Load template content from file.

        Raises:
            TemplateError: If template file cannot be loaded
        """
        if not self.template_path:
            raise TemplateError("Template path not provided")

        if not os.path.exists(self.template_path):
            raise TemplateError(f"Template file not found: {self.template_path}")

        try:
            _, ext = os.path.splitext(self.template_path)
            with open(self.template_path, 'r') as f:
                if ext.lower() in ('.yaml', '.yml'):
                    self._content = yaml.safe_load(f)
                elif ext.lower() == '.json':
                    self._content = json.load(f)
                else:
                    raise TemplateError(f"Unsupported template format: {ext}")
        except (yaml.YAMLError, json.JSONDecodeError) as e:
            raise TemplateError(f"Invalid template format: {str(e)}")
        except Exception as e:
            raise TemplateError(f"Error loading template file: {str(e)}")

    def get_content(self) -> Dict[str, Any]:
        """
        Get template content.

        Returns:
            Dict containing template content

        Raises:
            TemplateError: If template content cannot be loaded
        """
        if not self._content:
            self._load_content()
        return self._content

    def save(self, output_path: Optional[str] = None, format: str = 'yaml') -> str:
        """
        Save template to file.

        Args:
            output_path: Path to save template (optional)
                If not provided, will use the original template path or a default
            format: Output format ('yaml' or 'json')

        Returns:
            Path to saved template

        Raises:
            TemplateError: If template cannot be saved
        """
        if not self._content:
            raise TemplateError("No template content to save")

        # Determine output path
        save_path = output_path or self.template_path
        if not save_path:
            config = get_config()
            base_dir = os.path.expanduser(config.get_global().state_dir)
            templates_dir = os.path.join(base_dir, "templates", self.provider)
            os.makedirs(templates_dir, exist_ok=True)
            save_path = os.path.join(templates_dir, f"{self.template_id}.{format.lower()}")

        try:
            with open(save_path, 'w') as f:
                if format.lower() == 'yaml':
                    yaml.dump(self._content, f, default_flow_style=False)
                elif format.lower() == 'json':
                    json.dump(self._content, f, indent=2)
                else:
                    raise TemplateError(f"Unsupported output format: {format}")
            
            # Update template path
            self.template_path = save_path
            return save_path
        except Exception as e:
            raise TemplateError(f"Error saving template: {str(e)}")

    def validate(self) -> List[Dict[str, Any]]:
        """
        Validate template structure and content.

        Returns:
            List of validation issues, empty if valid

        Raises:
            TemplateError: If validation fails
        """
        issues = []
        content = self.get_content()

        # Basic validation - would be more comprehensive in a real implementation
        if not content:
            issues.append({
                "severity": "error",
                "message": "Template is empty"
            })
            return issues

        # Check for required sections based on provider
        if self.provider == "aws":
            # CloudFormation template validation
            if "Resources" not in content:
                issues.append({
                    "severity": "error",
                    "message": "CloudFormation template must have a Resources section"
                })
        elif self.provider == "azure":
            # ARM template validation
            if "$schema" not in content:
                issues.append({
                    "severity": "warning",
                    "message": "ARM template should have a $schema property"
                })
            if "resources" not in content:
                issues.append({
                    "severity": "error",
                    "message": "ARM template must have a resources section"
                })
        elif self.provider == "gcp":
            # GCP Deployment Manager template validation
            if "resources" not in content:
                issues.append({
                    "severity": "error",
                    "message": "GCP template must have a resources section"
                })
        elif self.provider == "kubernetes":
            # Kubernetes manifest validation
            if "apiVersion" not in content:
                issues.append({
                    "severity": "error",
                    "message": "Kubernetes manifest must have an apiVersion field"
                })
            if "kind" not in content:
                issues.append({
                    "severity": "error",
                    "message": "Kubernetes manifest must have a kind field"
                })

        return issues

    def get_parameters(self) -> Dict[str, Dict[str, Any]]:
        """
        Extract parameters from template.

        Returns:
            Dict mapping parameter names to parameter definitions

        Raises:
            TemplateError: If parameters cannot be extracted
        """
        content = self.get_content()
        parameters = {}

        # Extract parameters based on provider
        if self.provider == "aws":
            # CloudFormation parameters
            if "Parameters" in content:
                parameters = content["Parameters"]
        elif self.provider == "azure":
            # ARM template parameters
            if "parameters" in content:
                parameters = content["parameters"]
        elif self.provider == "gcp":
            # GCP template parameters (not standardized, implementation would vary)
            pass
        elif self.provider == "kubernetes":
            # Kubernetes doesn't have standard parameters, but we could look for ${VAR} patterns
            # This is a simplified implementation
            template_str = json.dumps(content)
            param_pattern = r'\$\{([A-Za-z0-9_]+)\}'
            matches = re.findall(param_pattern, template_str)
            for param in matches:
                parameters[param] = {
                    "description": f"Parameter {param}",
                    "default": ""
                }

        return parameters

    def apply_parameters(self, parameters: Dict[str, Any]) -> 'Template':
        """
        Apply parameters to template.

        Args:
            parameters: Dict mapping parameter names to values

        Returns:
            New Template instance with parameters applied

        Raises:
            TemplateError: If parameters cannot be applied
        """
        content = self.get_content()
        
        # Create a deep copy of content
        import copy
        new_content = copy.deepcopy(content)

        # Apply parameters based on provider
        if self.provider == "aws":
            # CloudFormation doesn't require parameter substitution in the template
            pass
        elif self.provider == "azure":
            # ARM template doesn't require parameter substitution in the template
            pass
        elif self.provider == "gcp":
            # GCP template parameter substitution would be implemented here
            pass
        elif self.provider == "kubernetes":
            # Replace ${VAR} patterns in the template
            template_str = json.dumps(new_content)
            for name, value in parameters.items():
                template_str = template_str.replace(f"${{{name}}}", str(value))
            new_content = json.loads(template_str)

        # Create new template with applied parameters
        return Template(
            template_id=f"{self.template_id}-instance",
            template_type=self.template_type,
            provider=self.provider,
            content=new_content
        )

    def generate_parameter_file(self, 
                               output_path: Optional[str] = None, 
                               format: str = 'yaml',
                               include_defaults: bool = True) -> str:
        """
        Generate parameter file from template.

        Args:
            output_path: Path to save parameter file (optional)
            format: Output format ('yaml' or 'json')
            include_defaults: Whether to include default values

        Returns:
            Path to saved parameter file

        Raises:
            TemplateError: If parameter file cannot be generated
        """
        parameters = self.get_parameters()
        param_values = {}

        # Create parameter values based on provider
        if self.provider == "aws":
            # CloudFormation parameters
            for name, param in parameters.items():
                if include_defaults and "Default" in param:
                    param_values[name] = param["Default"]
                else:
                    param_values[name] = f"<{name}>"
        elif self.provider == "azure":
            # ARM template parameters
            for name, param in parameters.items():
                if include_defaults and "defaultValue" in param:
                    param_values[name] = {"value": param["defaultValue"]}
                else:
                    param_values[name] = {"value": f"<{name}>"}
        elif self.provider == "gcp":
            # GCP template parameters
            for name, param in parameters.items():
                if include_defaults and "default" in param:
                    param_values[name] = param["default"]
                else:
                    param_values[name] = f"<{name}>"
        elif self.provider == "kubernetes":
            # Kubernetes parameters
            for name, param in parameters.items():
                if include_defaults and "default" in param:
                    param_values[name] = param["default"]
                else:
                    param_values[name] = f"<{name}>"

        # Determine output path
        if not output_path:
            if self.template_path:
                # Use template path with different extension
                base_path = os.path.splitext(self.template_path)[0]
                output_path = f"{base_path}.parameters.{format.lower()}"
            else:
                # Use a default path
                config = get_config()
                base_dir = os.path.expanduser(config.get_global().state_dir)
                params_dir = os.path.join(base_dir, "templates", self.provider)
                os.makedirs(params_dir, exist_ok=True)
                output_path = os.path.join(params_dir, f"{self.template_id}.parameters.{format.lower()}")

        try:
            with open(output_path, 'w') as f:
                if format.lower() == 'yaml':
                    yaml.dump(param_values, f, default_flow_style=False)
                elif format.lower() == 'json':
                    json.dump(param_values, f, indent=2)
                else:
                    raise TemplateError(f"Unsupported output format: {format}")
            
            return output_path
        except Exception as e:
            raise TemplateError(f"Error generating parameter file: {str(e)}")


class TemplateLibrary:
    """
    Manager for infrastructure templates.
    """

    def __init__(self, library_dir: Optional[str] = None):
        """
        Initialize template library.

        Args:
            library_dir: Directory to store templates (optional)
                Defaults to config value or ~/.devops-toolkit/templates
        """
        # Get library directory from config if not provided
        if library_dir is None:
            config = get_config()
            base_dir = os.path.expanduser(config.get_global().state_dir)
            library_dir = os.path.join(base_dir, "templates")
        
        self.library_dir = os.path.expanduser(library_dir)
        
        # Ensure library directory exists
        os.makedirs(self.library_dir, exist_ok=True)
        
        # Initialize provider directories
        for provider in ["aws", "azure", "gcp", "kubernetes"]:
            provider_dir = os.path.join(self.library_dir, provider)
            os.makedirs(provider_dir, exist_ok=True)

        # Template catalog
        self._catalog: Dict[str, Dict[str, Any]] = {}
        self._loaded = False

    def _load_catalog(self) -> None:
        """
        Load template catalog from disk.
        """
        catalog_file = os.path.join(self.library_dir, "catalog.json")
        
        if os.path.exists(catalog_file):
            try:
                with open(catalog_file, 'r') as f:
                    self._catalog = json.load(f)
            except Exception as e:
                logger.warning(f"Error loading template catalog: {str(e)}")
                self._catalog = {}
        else:
            self._catalog = {}
        
        self._loaded = True

    def _save_catalog(self) -> None:
        """
        Save template catalog to disk.
        """
        catalog_file = os.path.join(self.library_dir, "catalog.json")
        
        try:
            with open(catalog_file, 'w') as f:
                json.dump(self._catalog, f, indent=2)
        except Exception as e:
            logger.warning(f"Error saving template catalog: {str(e)}")

    def add_template(self, 
                    template_id: str, 
                    template_type: str,
                    provider: str,
                    template_path: str,
                    description: Optional[str] = None,
                    tags: Optional[List[str]] = None) -> Template:
        """
        Add a template to the library.

        Args:
            template_id: Unique identifier for the template
            template_type: Type of template (e.g., "compute", "network", "database")
            provider: Infrastructure provider (e.g., "aws", "azure", "gcp")
            template_path: Path to template file
            description: Template description (optional)
            tags: List of tags for the template (optional)

        Returns:
            Template object

        Raises:
            TemplateError: If template cannot be added
        """
        if not self._loaded:
            self._load_catalog()
        
        # Check if template already exists
        if template_id in self._catalog:
            raise TemplateError(f"Template {template_id} already exists in library")
        
        # Create template object to validate
        template = Template(template_id, template_type, provider, template_path)
        
        # Validate template
        issues = template.validate()
        error_issues = [issue for issue in issues if issue["severity"] == "error"]
        if error_issues:
            issues_str = "\n".join([f"- {issue['message']}" for issue in error_issues])
            raise TemplateError(f"Template validation failed:\n{issues_str}")
        
        # Copy template to library
        provider_dir = os.path.join(self.library_dir, provider)
        target_path = os.path.join(provider_dir, f"{template_id}{os.path.splitext(template_path)[1]}")
        
        try:
            shutil.copy2(template_path, target_path)
        except Exception as e:
            raise TemplateError(f"Error copying template to library: {str(e)}")
        
        # Extract parameters
        parameters = template.get_parameters()
        
        # Generate parameter file
        param_file = template.generate_parameter_file(
            output_path=os.path.join(provider_dir, f"{template_id}.parameters.yaml")
        )
        
        # Add to catalog
        self._catalog[template_id] = {
            "id": template_id,
            "type": template_type,
            "provider": provider,
            "path": target_path,
            "parameters_path": param_file,
            "description": description or "",
            "tags": tags or [],
            "added_at": datetime.now().isoformat(),
            "parameter_count": len(parameters)
        }
        
        # Save catalog
        self._save_catalog()
        
        # Return template with updated path
        return Template(template_id, template_type, provider, target_path)

    def get_template(self, template_id: str) -> Template:
        """
        Get a template from the library.

        Args:
            template_id: Unique identifier for the template

        Returns:
            Template object

        Raises:
            TemplateError: If template cannot be found
        """
        if not self._loaded:
            self._load_catalog()
        
        # Check if template exists
        if template_id not in self._catalog:
            raise TemplateError(f"Template {template_id} not found in library")
        
        # Get template info
        template_info = self._catalog[template_id]
        
        # Create and return template object
        return Template(
            template_id=template_info["id"],
            template_type=template_info["type"],
            provider=template_info["provider"],
            template_path=template_info["path"]
        )

    def delete_template(self, template_id: str) -> None:
        """
        Delete a template from the library.

        Args:
            template_id: Unique identifier for the template

        Raises:
            TemplateError: If template cannot be deleted
        """
        if not self._loaded:
            self._load_catalog()
        
        # Check if template exists
        if template_id not in self._catalog:
            raise TemplateError(f"Template {template_id} not found in library")
        
        # Get template info
        template_info = self._catalog[template_id]
        
        # Delete template file
        try:
            if os.path.exists(template_info["path"]):
                os.remove(template_info["path"])
            
            # Delete parameter file if it exists
            if "parameters_path" in template_info and os.path.exists(template_info["parameters_path"]):
                os.remove(template_info["parameters_path"])
        except Exception as e:
            logger.warning(f"Error deleting template files: {str(e)}")
        
        # Remove from catalog
        del self._catalog[template_id]
        
        # Save catalog
        self._save_catalog()

    def list_templates(self, 
                      provider: Optional[str] = None, 
                      template_type: Optional[str] = None,
                      tags: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        List templates in the library.

        Args:
            provider: Filter by provider (optional)
            template_type: Filter by template type (optional)
            tags: Filter by tags (optional)

        Returns:
            List of template information
        """
        if not self._loaded:
            self._load_catalog()
        
        templates = []
        
        for template_id, template_info in self._catalog.items():
            # Apply filters
            if provider and template_info["provider"] != provider:
                continue
            
            if template_type and template_info["type"] != template_type:
                continue
            
            if tags:
                # Check if template has all specified tags
                if not all(tag in template_info["tags"] for tag in tags):
                    continue
            
            templates.append(template_info)
        
        return templates

    def export_template(self, 
                       template_id: str, 
                       output_path: str,
                       include_parameters: bool = True) -> Dict[str, str]:
        """
        Export a template from the library.

        Args:
            template_id: Unique identifier for the template
            output_path: Directory to export template to
            include_parameters: Whether to include parameter file

        Returns:
            Dict with paths to exported files

        Raises:
            TemplateError: If template cannot be exported
        """
        if not self._loaded:
            self._load_catalog()
        
        # Check if template exists
        if template_id not in self._catalog:
            raise TemplateError(f"Template {template_id} not found in library")
        
        # Get template info
        template_info = self._catalog[template_id]
        
        # Create output directory if it doesn't exist
        os.makedirs(output_path, exist_ok=True)
        
        # Copy template file
        template_path = template_info["path"]
        template_filename = os.path.basename(template_path)
        export_template_path = os.path.join(output_path, template_filename)
        
        result = {
            "template": export_template_path
        }
        
        try:
            shutil.copy2(template_path, export_template_path)
            
            # Copy parameter file if requested and available
            if include_parameters and "parameters_path" in template_info:
                param_path = template_info["parameters_path"]
                if os.path.exists(param_path):
                    param_filename = os.path.basename(param_path)
                    export_param_path = os.path.join(output_path, param_filename)
                    shutil.copy2(param_path, export_param_path)
                    result["parameters"] = export_param_path
        except Exception as e:
            raise TemplateError(f"Error exporting template: {str(e)}")
        
        return result

    def import_directory(self, 
                        directory: str, 
                        provider: str,
                        template_type: str,
                        tags: Optional[List[str]] = None) -> List[str]:
        """
        Import all templates from a directory.

        Args:
            directory: Directory containing templates
            provider: Provider for imported templates
            template_type: Type for imported templates
            tags: Tags for imported templates (optional)

        Returns:
            List of imported template IDs

        Raises:
            TemplateError: If directory cannot be imported
        """
        if not os.path.exists(directory) or not os.path.isdir(directory):
            raise TemplateError(f"Directory not found: {directory}")
        
        imported_templates = []
        
        # Find template files in directory
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            
            # Skip directories and non-template files
            if os.path.isdir(file_path):
                continue
            
            _, ext = os.path.splitext(filename)
            if ext.lower() not in ('.yaml', '.yml', '.json'):
                continue
            
            # Skip parameter files
            if "parameters" in filename:
                continue
            
            try:
                # Generate template ID from filename
                template_id = os.path.splitext(filename)[0].lower().replace(' ', '-')
                
                # Add template to library
                template = self.add_template(
                    template_id=template_id,
                    template_type=template_type,
                    provider=provider,
                    template_path=file_path,
                    description=f"Imported from {directory}",
                    tags=tags
                )
                
                imported_templates.append(template_id)
            except Exception as e:
                logger.warning(f"Error importing template {filename}: {str(e)}")
        
        return imported_templates

    def combine_templates(self, 
                         template_ids: List[str], 
                         output_id: str,
                         output_type: str) -> Template:
        """
        Combine multiple templates into one.

        Args:
            template_ids: List of template IDs to combine
            output_id: ID for the combined template
            output_type: Type for the combined template

        Returns:
            Combined Template object

        Raises:
            TemplateError: If templates cannot be combined
        """
        if not self._loaded:
            self._load_catalog()
        
        if len(template_ids) < 2:
            raise TemplateError("At least two templates are required for combining")
        
        # Check if all templates exist and have the same provider
        templates = []
        provider = None
        
        for template_id in template_ids:
            if template_id not in self._catalog:
                raise TemplateError(f"Template {template_id} not found in library")
            
            template_info = self._catalog[template_id]
            
            if provider is None:
                provider = template_info["provider"]
            elif provider != template_info["provider"]:
                raise TemplateError(f"Cannot combine templates from different providers: {provider} and {template_info['provider']}")
            
            templates.append(self.get_template(template_id))
        
        # Combine templates based on provider
        if provider == "aws":
            # Combine CloudFormation templates
            combined_content = {
                "AWSTemplateFormatVersion": "2010-09-09",
                "Description": f"Combined template from {', '.join(template_ids)}",
                "Parameters": {},
                "Resources": {},
                "Outputs": {}
            }
            
            for template in templates:
                content = template.get_content()
                
                # Merge parameters
                if "Parameters" in content:
                    for param_name, param in content["Parameters"].items():
                        if param_name in combined_content["Parameters"]:
                            # Rename parameter to avoid conflicts
                            new_param_name = f"{template.template_id}_{param_name}"
                            combined_content["Parameters"][new_param_name] = param
                        else:
                            combined_content["Parameters"][param_name] = param
                
                # Merge resources
                if "Resources" in content:
                    for resource_name, resource in content["Resources"].items():
                        if resource_name in combined_content["Resources"]:
                            # Rename resource to avoid conflicts
                            new_resource_name = f"{template.template_id}_{resource_name}"
                            combined_content["Resources"][new_resource_name] = resource
                        else:
                            combined_content["Resources"][resource_name] = resource
                
                # Merge outputs
                if "Outputs" in content:
                    for output_name, output in content["Outputs"].items():
                        if output_name in combined_content["Outputs"]:
                            # Rename output to avoid conflicts
                            new_output_name = f"{template.template_id}_{output_name}"
                            combined_content["Outputs"][new_output_name] = output
                        else:
                            combined_content["Outputs"][output_name] = output
        
        elif provider == "azure":
            # Combine ARM templates
            combined_content = {
                "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
                "contentVersion": "1.0.0.0",
                "parameters": {},
                "variables": {},
                "resources": [],
                "outputs": {}
            }
            
            for template in templates:
                content = template.get_content()
                
                # Merge parameters
                if "parameters" in content:
                    for param_name, param in content["parameters"].items():
                        if param_name in combined_content["parameters"]:
                            # Rename parameter to avoid conflicts
                            new_param_name = f"{template.template_id}_{param_name}"
                            combined_content["parameters"][new_param_name] = param
                        else:
                            combined_content["parameters"][param_name] = param
                
                # Merge variables
                if "variables" in content:
                    for var_name, var in content["variables"].items():
                        if var_name in combined_content["variables"]:
                            # Rename variable to avoid conflicts
                            new_var_name = f"{template.template_id}_{var_name}"
                            combined_content["variables"][new_var_name] = var
                        else:
                            combined_content["variables"][var_name] = var
                
                # Merge resources
                if "resources" in content:
                    combined_content["resources"].extend(content["resources"])
                
                # Merge outputs
                if "outputs" in content:
                    for output_name, output in content["outputs"].items():
                        if output_name in combined_content["outputs"]:
                            # Rename output to avoid conflicts
                            new_output_name = f"{template.template_id}_{output_name}"
                            combined_content["outputs"][new_output_name] = output
                        else:
                            combined_content["outputs"][output_name] = output
        
        elif provider == "gcp":
            # Combine GCP templates
            combined_content = {
                "resources": []
            }
            
            for template in templates:
                content = template.get_content()
                
                # Merge resources
                if "resources" in content:
                    combined_content["resources"].extend(content["resources"])
        
        elif provider == "kubernetes":
            # For Kubernetes, create a list of manifests
            combined_content = {
                "apiVersion": "v1",
                "kind": "List",
                "items": []
            }
            
            for template in templates:
                content = template.get_content()
                combined_content["items"].append(content)
        
        else:
            raise TemplateError(f"Unsupported provider for template combination: {provider}")
        
        # Create combined template
        combined_template = Template(
            template_id=output_id,
            template_type=output_type,
            provider=provider,
            content=combined_content
        )
        
        # Save combined template to library
        provider_dir = os.path.join(self.library_dir, provider)
        output_path = os.path.join(provider_dir, f"{output_id}.yaml")
        combined_template.save(output_path=output_path)
        
        # Add to catalog
        self._catalog[output_id] = {
            "id": output_id,
            "type": output_type,
            "provider": provider,
            "path": output_path,
            "description": f"Combined template from {', '.join(template_ids)}",
            "tags": ["combined"],
            "added_at": datetime.now().isoformat(),
            "combined_from": template_ids
        }
        
        # Save catalog
        self._save_catalog()
        
        return combined_template


# Global template library instance
_template_library_instance = None


def get_template_library() -> TemplateLibrary:
    """
    Get the global template library instance.

    Returns:
        TemplateLibrary object
    """
    global _template_library_instance
    if _template_library_instance is None:
        _template_library_instance = TemplateLibrary()
    return _template_library_instance
