"""
DevOps Toolkit - Command Line Interface

A comprehensive CLI for DevOps automation tasks with enhanced rollback functionality.
"""
import sys
from typing import Optional, List

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Import required modules
from devops_toolkit.config import get_config
from devops_toolkit.logging import get_logger, init_logging_from_config
from devops_toolkit.state import get_state_manager
from devops_toolkit.tools import deployment, infrastructure, monitoring, security

# Initialize logger
logger = get_logger(__name__)

# Initialize rich console for pretty output
console = Console()


@click.group()
@click.version_option()
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.option("--config", "-c", help="Path to configuration file")
def main(debug: bool, config: Optional[str]) -> None:
    """DevOps Toolkit - Simplify your DevOps workflows."""
    try:
        # Initialize configuration and logging
        if config:
            # Use specified config file
            from devops_toolkit.config import Config
            Config(config).load()
        
        # Initialize logging
        init_logging_from_config()
        
        # Override log level if debug flag is set
        if debug:
            import logging
            logging.getLogger("devops_toolkit").setLevel(logging.DEBUG)
            logger.debug("Debug logging enabled")
    
    except Exception as e:
        console.print(f"[bold red]Error initializing:[/bold red] {str(e)}")
        sys.exit(1)


@main.command()
@click.option("--app-name", required=True, help="Name of the application to deploy")
@click.option("--version", required=True, help="Version to deploy")
@click.option(
    "--env",
    required=True,
    type=click.Choice(["dev", "staging", "production"]),
    help="Target environment",
)
@click.option(
    "--config", "-c", default="config.yaml", help="Path to configuration file"
)
@click.option(
    "--wait/--no-wait", default=True, help="Wait for deployment to complete"
)
@click.option(
    "--timeout", type=int, default=300, help="Timeout in seconds when waiting"
)
def deploy(app_name: str, version: str, env: str, config: str, wait: bool, timeout: int) -> None:
    """Deploy an application to the target environment."""
    try:
        logger.info(f"Starting deployment of {app_name} version {version} to {env}")
        
        # Log deployment to state manager
        state_manager = get_state_manager()
        state = state_manager.get_state("deployment", f"{app_name}-{env}")
        
        # Call deployment function
        result = deployment.deploy(
            app_name=app_name,
            version=version,
            environment=env,
            config_path=config,
            wait=wait,
            timeout=timeout
        )
        
        # Save deployment state
        state.save({
            "app_name": app_name,
            "version": version,
            "environment": env,
            "status": result["status"],
            "deployment_time": result["deployment_time"],
            "details": result["details"]
        })
        
        # Show result
        console.print(
            Panel(
                f"Deployed [bold]{app_name}[/bold] version [bold]{version}[/bold] to [bold]{env}[/bold]",
                title="Deployment Successful",
                border_style="green",
            )
        )
        
        # Show details
        console.print("Deployment Details:")
        console.print(f"  Status: [green]{result['status']}[/green]")
        console.print(f"  Time: {result['deployment_time']}")
        console.print(f"  Replicas: {result['details']['replicas']}")
        console.print(f"  Status URL: {result['details']['status_url']}")
        console.print(f"  Logs URL: {result['details']['logs_url']}")
        
        logger.info(f"Deployment of {app_name} version {version} to {env} completed successfully")
    
    except Exception as e:
        logger.error(f"Deployment error: {str(e)}", exc_info=True)
        console.print(
            f"[bold red]Error during deployment:[/bold red] {str(e)}")
        sys.exit(1)


@main.command()
@click.option("--app-name", required=True, help="Name of the application to rollback")
@click.option(
    "--env",
    required=True,
    type=click.Choice(["dev", "staging", "production"]),
    help="Target environment",
)
@click.option(
    "--version", help="Specific version to rollback to (default: previous version)"
)
@click.option(
    "--deployment-id", help="Specific deployment ID to rollback to"
)
def rollback(app_name: str, env: str, version: Optional[str], deployment_id: Optional[str]) -> None:
    """Rollback a deployment to a previous version."""
    try:
        logger.info(f"Starting rollback of {app_name} in {env}")
        
        # Log rollback to state manager
        state_manager = get_state_manager()
        state = state_manager.get_state("deployment", f"{app_name}-{env}")
        
        # Get current state
        current_state = state.get()
        
        # Display confirmation
        console.print(
            Panel(
                f"Rolling back [bold]{app_name}[/bold] in [bold]{env}[/bold]",
                title="Rollback Confirmation",
                border_style="yellow",
            )
        )
        
        console.print("Current deployment details:")
        console.print(f"  Version: [bold]{current_state.get('version', 'Unknown')}[/bold]")
        console.print(f"  Deployed at: {current_state.get('deployment_time', 'Unknown')}")
        
        # Determine target version
        target = version
        if not target and deployment_id:
            # Try to find version from deployment ID
            # In a real implementation, this would look up the deployment by ID
            target = "Determined from deployment ID"
        
        if not click.confirm(f"Rollback to {'previous version' if not target else target}?"):
            console.print("[yellow]Rollback cancelled[/yellow]")
            return
        
        # Call rollback function
        result = deployment.rollback(
            app_name=app_name,
            environment=env,
            version=version
        )
        
        # Save rollback state
        state.save({
            "app_name": app_name,
            "version": result.get("rollback_to", "previous"),
            "environment": env,
            "status": result["status"],
            "rollback_time": result["rollback_time"],
            "previous_version": current_state.get("version", "Unknown")
        })
        
        # Show result
        console.print(
            Panel(
                f"Rolled back [bold]{app_name}[/bold] in [bold]{env}[/bold] to version [bold]{result['rollback_to']}[/bold]",
                title="Rollback Successful",
                border_style="green",
            )
        )
        
        logger.info(f"Rollback of {app_name} in {env} to {result['rollback_to']} completed successfully")
    
    except Exception as e:
        logger.error(f"Rollback error: {str(e)}", exc_info=True)
        console.print(
            f"[bold red]Error during rollback:[/bold red] {str(e)}")
        sys.exit(1)


@main.command()
@click.option("--app-name", required=True, help="Name of the application to monitor")
@click.option(
    "--env",
    required=True,
    type=click.Choice(["dev", "staging", "production"]),
    help="Target environment",
)
@click.option("--watch", is_flag=True, help="Watch mode - continuously monitor")
@click.option("--interval", type=int, default=60, help="Interval between checks in watch mode (seconds)")
@click.option("--max-checks", type=int, help="Maximum number of checks in watch mode")
def monitor(app_name: str, env: str, watch: bool, interval: int, max_checks: Optional[int]) -> None:
    """Monitor an application in the specified environment."""
    try:
        mode = "continuous" if watch else "one-time"
        logger.info(f"Starting {mode} monitoring of {app_name} in {env}")
        
        console.print(
            Panel(
                f"Monitoring [bold]{app_name}[/bold] in [bold]{env}[/bold] environment ([italic]{mode}[/italic] mode)",
                title="Monitoring",
                border_style="blue",
            )
        )
        
        # Call monitoring function
        result = monitoring.check_status(
            app_name=app_name,
            environment=env,
            continuous=watch,
            interval=interval,
            max_checks=max_checks
        )
        
        if not watch:
            # Single check
            metrics = result["metrics"]
            
            # Display results
            console.print(f"Status: [{'green' if result['status'] == 'healthy' else 'red'}]{result['status']}[/{'green' if result['status'] == 'healthy' else 'red'}]")
            console.print(f"Timestamp: {result['timestamp']}")
            
            # Create metrics table
            table = Table(title="Metrics")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="magenta")
            table.add_column("Unit", style="green")
            
            for metric_name, metric_data in metrics.items():
                table.add_row(
                    metric_name.replace("_", " ").title(),
                    str(metric_data["value"]),
                    metric_data["unit"]
                )
            
            console.print(table)
        else:
            # Watch mode results would be handled by the monitoring function directly
            console.print("[green]Monitoring completed[/green]")
        
        logger.info(f"Monitoring of {app_name} in {env} completed")
    
    except Exception as e:
        logger.error(f"Monitoring error: {str(e)}", exc_info=True)
        console.print(
            f"[bold red]Error during monitoring:[/bold red] {str(e)}")
        sys.exit(1)


@main.command()
@click.option(
    "--provider",
    type=click.Choice(["aws", "azure", "gcp", "kubernetes"]),
    required=True,
    help="Infrastructure provider",
)
@click.option("--template", required=True, help="Infrastructure template file")
@click.option("--params", help="Parameters file for the template")
@click.option("--dry-run", is_flag=True, help="Validate without deploying")
@click.option("--timeout", type=int, default=600, help="Timeout in seconds")
def provision(
    provider: str, template: str, params: Optional[str], dry_run: bool, timeout: int
) -> None:
    """Provision infrastructure based on templates."""
    try:
        action = "Validating" if dry_run else "Provisioning"
        logger.info(f"{action} infrastructure on {provider} using template {template}")
        
        console.print(
            Panel(
                f"{action} infrastructure on [bold]{provider}[/bold] using template [bold]{template}[/bold]",
                title="Infrastructure",
                border_style="yellow",
            )
        )
        
        if params:
            console.print(f"Using parameters from: {params}")
        
        # Call infrastructure provision function
        result = infrastructure.provision(
            provider=provider,
            template_path=template,
            params_path=params,
            dry_run=dry_run,
            timeout=timeout
        )
        
        # Save infrastructure state if not dry run
        if not dry_run:
            state_manager = get_state_manager()
            state = state_manager.get_state("infrastructure", result["provision_id"])
            state.save({
                "provider": provider,
                "template": template,
                "parameters": params,
                "provision_id": result["provision_id"],
                "provision_time": result["provision_time"],
                "resources": result["resources"],
                "outputs": result["outputs"]
            })
        
        # Show result
        if dry_run:
            console.print("[green]Template validation successful![/green]")
        else:
            console.print(
                f"[green]Infrastructure provisioned successfully![/green] Provision ID: {result['provision_id']}"
            )
            
            # Display resources
            console.print("\nProvisioned Resources:")
            table = Table()
            table.add_column("Type", style="cyan")
            table.add_column("ID", style="magenta")
            table.add_column("Name", style="blue")
            table.add_column("Status", style="green")
            
            for resource in result["resources"]:
                table.add_row(
                    resource["type"],
                    resource["id"],
                    resource["name"],
                    resource["status"]
                )
            
            console.print(table)
            
            # Display outputs
            if result["outputs"]:
                console.print("\nOutputs:")
                for key, value in result["outputs"].items():
                    console.print(f"  {key}: [bold]{value}[/bold]")
        
        logger.info(f"Infrastructure {action.lower()} completed successfully")
    
    except Exception as e:
        logger.error(f"Infrastructure error: {str(e)}", exc_info=True)
        console.print(
            f"[bold red]Error during {action.lower()}:[/bold red] {str(e)}")
        sys.exit(1)


@main.command()
@click.option("--app-name", required=True, help="Name of the application to scan")
@click.option("--scan-type", type=click.Choice(["dependencies", "code", "container", "all"]), default="all", help="Type of security scan to perform")
@click.option("--report-format", type=click.Choice(["text", "json", "html"]), default="text", help="Format for the security report")
@click.option("--output", "-o", help="Output file for the report")
@click.option("--compliance", is_flag=True, help="Include compliance check in the scan")
@click.option("--compliance-framework", type=click.Choice(["owasp-top10", "pci-dss", "hipaa"]), default="owasp-top10", help="Compliance framework to check against")
def security_scan(app_name: str, scan_type: str, report_format: str, output: Optional[str], compliance: bool, compliance_framework: str) -> None:
    """Perform security scans on applications."""
    try:
        logger.info(f"Starting {scan_type} security scan on {app_name}")
        
        console.print(
            Panel(
                f"Running [bold]{scan_type}[/bold] security scan on [bold]{app_name}[/bold]",
                title="Security Scan",
                border_style="red",
            )
        )
        
        # Call security scan function
        if compliance:
            result = security.generate_security_report(
                app_name=app_name,
                include_compliance=True,
                compliance_framework=compliance_framework,
                output_file=output,
                report_format=report_format
            )
        else:
            result = security.scan(
                app_name=app_name,
                scan_type=scan_type,
                report_format=report_format,
                output_file=output
            )
        
        # Extract summary information
        if compliance:
            summary = result["scan_results"]["summary"]
            compliance_info = result["compliance"]
        else:
            summary = result["summary"]
            compliance_info = None
        
        # Display results
        console.print("[green]Security scan completed![/green]")
        
        # Display summary
        console.print("\nVulnerability Summary:")
        severity_counts = summary["severity_counts"]
        console.print(f"  Critical: [bold red]{severity_counts.get('critical', 0)}[/bold red]")
        console.print(f"  High: [bold orange]{severity_counts.get('high', 0)}[/bold orange]")
        console.print(f"  Medium: [bold yellow]{severity_counts.get('medium', 0)}[/bold yellow]")
        console.print(f"  Low: [bold green]{severity_counts.get('low', 0)}[/bold green]")
        console.print(f"  Total Issues: [bold]{summary['total_issues']}[/bold]")
        
        # Display compliance results if available
        if compliance_info:
            console.print(f"\nCompliance Status ([bold]{compliance_framework}[/bold]):")
            compliance_percentage = compliance_info["compliance_percentage"]
            compliance_color = "green" if compliance_percentage >= 90 else "yellow" if compliance_percentage >= 70 else "red"
            console.print(f"  Compliance: [bold {compliance_color}]{compliance_percentage}%[/bold {compliance_color}]")
            console.print(f"  Status: [bold {compliance_color}]{compliance_info['overall_status']}[/bold {compliance_color}]")
            console.print(f"  Requirements Met: {compliance_info['compliant_count']}/{compliance_info['requirements_count']}")
        
        if output:
            console.print(f"\nReport saved to: [bold]{output}[/bold]")
        
        logger.info(f"Security scan of {app_name} completed successfully")
    
    except Exception as e:
        logger.error(f"Security scan error: {str(e)}", exc_info=True)
        console.print(
            f"[bold red]Error during security scan:[/bold red] {str(e)}")
        sys.exit(1)


@main.command()
@click.option(
    "--resource-type",
    type=click.Choice(["deployment", "infrastructure", "all"]),
    default="all",
    help="Type of resource to list",
)
def list_resources(resource_type: str) -> None:
    """List resources tracked in the state management system."""
    try:
        logger.info(f"Listing {resource_type} resources")
        
        state_manager = get_state_manager()
        
        if resource_type == "all":
            resources = state_manager.list_resources()
        else:
            resources = state_manager.list_resources(resource_type)
        
        if not resources:
            console.print(f"No {resource_type} resources found")
            return
        
        # Display results
        console.print(
            Panel(
                f"Found [bold]{len(resources)}[/bold] resources",
                title="Resource List",
                border_style="blue",
            )
        )
        
        # Create table
        table = Table()
        table.add_column("Type", style="cyan")
        table.add_column("ID", style="magenta")
        table.add_column("Created", style="blue")
        table.add_column("Last Updated", style="green")
        table.add_column("Version", style="yellow")
        
        for resource in resources:
            metadata = resource["metadata"]
            table.add_row(
                resource["resource_type"],
                resource["resource_id"],
                metadata.get("created_at", "Unknown"),
                metadata.get("updated_at", "Unknown"),
                str(metadata.get("version", 0))
            )
        
        console.print(table)
    
    except Exception as e:
        logger.error(f"List resources error: {str(e)}", exc_info=True)
        console.print(
            f"[bold red]Error listing resources:[/bold red] {str(e)}")
        sys.exit(1)


@main.command()
@click.option(
    "--init-only", is_flag=True, help="Only initialize configuration without setting values"
)
def configure(init_only: bool) -> None:
    """Configure the DevOps Toolkit."""
    try:
        from devops_toolkit.config import get_config, GlobalConfig
        
        config = get_config()
        global_config = config.get_global()
        
        console.print(
            Panel(
                "Configure DevOps Toolkit settings",
                title="Configuration",
                border_style="blue",
            )
        )
        
        if not init_only:
            # Interactive configuration
            console.print("Configuring global settings:")
            
            # Log level
            log_level = click.prompt(
                "Log level", 
                type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
                default=global_config.log_level
            )
            
            # Log file
            log_file = click.prompt(
                "Log file path",
                default=global_config.log_file or "",
                show_default=True
            )
            
            # Update global config
            global_config = GlobalConfig(
                log_level=log_level,
                log_file=log_file if log_file else None,
                state_dir=global_config.state_dir,
                secrets_dir=global_config.secrets_dir,
                default_environment=global_config.default_environment,
                environments=global_config.environments
            )
            
            # Save configuration
            config_path = config.save()
            console.print(f"[green]Configuration saved to:[/green] {config_path}")
        else:
            # Just initialize configuration
            config_path = config.save()
            console.print(f"[green]Configuration initialized at:[/green] {config_path}")
        
        logger.info("Configuration updated successfully")
    
    except Exception as e:
        logger.error(f"Configuration error: {str(e)}", exc_info=True)
        console.print(
            f"[bold red]Error during configuration:[/bold red] {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
