"""
DevOps Toolkit - Interactive CLI Mode

This module provides an interactive CLI interface for DevOps Toolkit,
guiding users through common operations with menu-driven interfaces.
"""
import os
import sys
import time
from typing import Dict, Any, Optional, List, Callable, Union, Tuple
import tempfile

# Try to import prompt_toolkit for enhanced CLI experience
try:
    from prompt_toolkit import prompt
    from prompt_toolkit.completion import WordCompleter
    from prompt_toolkit.validation import Validator
    from prompt_toolkit.formatted_text import HTML
    PROMPT_TOOLKIT_AVAILABLE = True
except ImportError:
    PROMPT_TOOLKIT_AVAILABLE = False

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.markdown import Markdown
from rich import box

# Local imports
from devops_toolkit.config import get_config, ConfigError
from devops_toolkit.logging import get_logger, init_logging_from_config
from devops_toolkit.state import get_state_manager, StateError
from devops_toolkit.secrets import get_secrets_manager, SecretsError
from devops_toolkit.tools import deployment, infrastructure, monitoring, security

# Initialize logger
logger = get_logger(__name__)

# Initialize rich console for pretty output
console = Console()


class InteractiveError(Exception):
    """Raised when interactive operations encounter an error."""
    pass


class InteractiveCLI:
    """
    Interactive CLI for DevOps Toolkit.
    """

    def __init__(self):
        """Initialize interactive CLI."""
        self.exit_requested = False
        self.current_menu = "main"
        self.menu_history = []
        self.context = {}  # Store context for operations

    def run(self) -> None:
        """Run the interactive CLI session."""
        # Initialize configuration and logging
        try:
            # Initialize logging from config
            from devops_toolkit.logging import init_logging_from_config
            init_logging_from_config()
        except Exception as e:
            # Fall back to basic logging if initialization fails
            import logging
            logging.basicConfig(level=logging.INFO)
            logger = logging.getLogger("devops_toolkit")
            logger.error(f"Error initializing configuration: {str(e)}")
            logger.info("Using default configuration")

        # Display welcome message
        self.display_header()
        console.print(Panel(
            "[bold]Welcome to DevOps Toolkit Interactive CLI![/bold]\n\n"
            "This interface provides a guided, menu-driven way to use DevOps Toolkit.\n"
            "Navigate through the menus to access various features for deployments,\n"
            "infrastructure, monitoring, security, and more.",
            title="DevOps Toolkit",
            border_style="green"
        ))
        console.print()
        input("Press Enter to start...")

        # Main loop
        while not self.exit_requested:
            self.display_header()
            self.show_current_menu()

            choice = self.get_input("Select an option")
            self.process_input(choice)

        # Display exit message
        self.display_header()
        console.print(Panel(
            "[bold]Thank you for using DevOps Toolkit![/bold]\n\n"
            "For more information and documentation, visit:\n"
            "https://github.com/kenbark42/devops-toolkit",
            title="Goodbye!",
            border_style="green"
        ))
        console.print()


def main() -> None:
    """Main entry point for the interactive CLI."""
    try:
        cli = InteractiveCLI()
        cli.run()
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        console.print("\n\n[yellow]Operation interrupted. Exiting...[/yellow]")
    except Exception as e:
        console.print(
            f"\n\n[bold red]An unexpected error occurred:[/bold red] {str(e)}")
        logger.error(
            f"Unexpected error in interactive CLI: {str(e)}", exc_info=True)


if __name__ == "__main__":
    main()

    def clear_screen(self) -> None:
        """Clear the terminal screen."""
        os.system('cls' if os.name == 'nt' else 'clear')

    def display_header(self) -> None:
        """Display application header."""
        self.clear_screen()
        console.print(Panel(
            "[bold blue]DevOps Toolkit Interactive CLI[/bold blue]\n"
            "[italic]Simplify your DevOps workflows with interactive commands[/italic]",
            border_style="blue"
        ))
        console.print()

    def get_input(self, prompt_text: str, default: str = "",
                  choices: Optional[List[str]] = None,
                  validator: Optional[Callable[[str], bool]] = None) -> str:
        """
        Get user input with validation and auto-completion.

        Args:
            prompt_text: Prompt text to display
            default: Default value (optional)
            choices: List of valid choices (optional)
            validator: Function to validate input (optional)

        Returns:
            User input
        """
        if PROMPT_TOOLKIT_AVAILABLE and (choices or validator):
            # Create completer if choices provided
            completer = WordCompleter(choices) if choices else None

            # Create validator if needed
            if validator:
                class InputValidator(Validator):
                    def validate(self, document):
                        text = document.text
                        if not validator(text):
                            raise ValidationError(
                                message="Invalid input",
                                cursor_position=len(text)
                            )

                prompt_validator = InputValidator()
            elif choices:
                class ChoiceValidator(Validator):
                    def validate(self, document):
                        text = document.text
                        if text and text not in choices:
                            raise ValidationError(
                                message=f"Invalid choice. Valid options: {', '.join(choices)}",
                                cursor_position=len(text)
                            )

                prompt_validator = ChoiceValidator()
            else:
                prompt_validator = None

            # Prompt with auto-completion and validation
            result = prompt(
                prompt_text + ": ",
                default=default,
                completer=completer,
                validator=prompt_validator
            )

            return result
        else:
            # Use rich prompt as fallback
            if choices:
                return Prompt.ask(
                    prompt_text,
                    default=default,
                    choices=choices,
                    show_choices=True
                )
            else:
                return Prompt.ask(prompt_text, default=default)

    def get_confirmation(self, prompt_text: str, default: bool = False) -> bool:
        """
        Get yes/no confirmation from user.

        Args:
            prompt_text: Prompt text to display
            default: Default value (True=yes, False=no)

        Returns:
            True if confirmed, False otherwise
        """
        return Confirm.ask(prompt_text, default=default)

    def display_menu(self, title: str, options: List[Tuple[str, str]],
                     back_option: bool = True, exit_option: bool = True) -> None:
        """
        Display a menu of options.

        Args:
            title: Menu title
            options: List of (option_key, option_description) tuples
            back_option: Whether to include back option
            exit_option: Whether to include exit option
        """
        table = Table(show_header=False, box=box.SIMPLE)
        table.add_column("Key", style="cyan", justify="right")
        table.add_column("Description")

        for key, description in options:
            table.add_row(key, description)

        if back_option and self.menu_history:
            table.add_row("b", "Back to previous menu")

        if exit_option:
            table.add_row("q", "Quit interactive mode")

        console.print(Panel(title, style="bold blue"))
        console.print(table)
        console.print()

    def process_input(self, input_text: str) -> None:
        """
        Process user input based on current menu.

        Args:
            input_text: User input
        """
        # Handle global commands
        if input_text.lower() == "q":
            self.exit_requested = True
            return

        if input_text.lower() == "b" and self.menu_history:
            self.current_menu = self.menu_history.pop()
            return

        # Process menu-specific commands
        if self.current_menu == "main":
            self._process_main_menu(input_text)
        elif self.current_menu == "deployment":
            self._process_deployment_menu(input_text)
        elif self.current_menu == "infrastructure":
            self._process_infrastructure_menu(input_text)
        elif self.current_menu == "monitoring":
            self._process_monitoring_menu(input_text)
        elif self.current_menu == "security":
            self._process_security_menu(input_text)
        elif self.current_menu == "configuration":
            self._process_configuration_menu(input_text)
        elif self.current_menu == "utilities":
            self._process_utilities_menu(input_text)
        else:
            console.print("[red]Unknown menu state.[/red]")
            self.current_menu = "main"

    def _process_main_menu(self, input_text: str) -> None:
        """Process main menu input."""
        if input_text == "1":
            # Deployment
            self.menu_history.append(self.current_menu)
            self.current_menu = "deployment"
        elif input_text == "2":
            # Infrastructure
            self.menu_history.append(self.current_menu)
            self.current_menu = "infrastructure"
        elif input_text == "3":
            # Monitoring
            self.menu_history.append(self.current_menu)
            self.current_menu = "monitoring"
        elif input_text == "4":
            # Security
            self.menu_history.append(self.current_menu)
            self.current_menu = "security"
        elif input_text == "5":
            # Configuration
            self.menu_history.append(self.current_menu)
            self.current_menu = "configuration"
        elif input_text == "6":
            # Utilities
            self.menu_history.append(self.current_menu)
            self.current_menu = "utilities"
        else:
            console.print("[red]Invalid option. Please try again.[/red]")
            console.print()

    def _process_deployment_menu(self, input_text: str) -> None:
        """Process deployment menu input."""
        if input_text == "1":
            # Deploy application
            self._deploy_application()
        elif input_text == "2":
            # Rollback deployment
            self._rollback_deployment()
        elif input_text == "3":
            # View deployment history
            self._view_deployment_history()
        else:
            console.print("[red]Invalid option. Please try again.[/red]")
            console.print()

    def _process_infrastructure_menu(self, input_text: str) -> None:
        """Process infrastructure menu input."""
        if input_text == "1":
            # Provision infrastructure
            self._provision_infrastructure()
        elif input_text == "2":
            # Destroy infrastructure
            self._destroy_infrastructure()
        elif input_text == "3":
            # Scale infrastructure
            self._scale_infrastructure()
        elif input_text == "4":
            # View infrastructure status
            self._view_infrastructure_status()
        else:
            console.print("[red]Invalid option. Please try again.[/red]")
            console.print()

    def _process_monitoring_menu(self, input_text: str) -> None:
        """Process monitoring menu input."""
        if input_text == "1":
            # Check application status
            self._check_application_status()
        elif input_text == "2":
            # View monitoring dashboard
            self._view_monitoring_dashboard()
        elif input_text == "3":
            # Create alert rule
            self._create_alert_rule()
        else:
            console.print("[red]Invalid option. Please try again.[/red]")
            console.print()

    def _process_security_menu(self, input_text: str) -> None:
        """Process security menu input."""
        if input_text == "1":
            # Scan application
            self._scan_application()
        elif input_text == "2":
            # Check compliance
            self._check_compliance()
        elif input_text == "3":
            # Generate security report
            self._generate_security_report()
        else:
            console.print("[red]Invalid option. Please try again.[/red]")
            console.print()

    def _process_configuration_menu(self, input_text: str) -> None:
        """Process configuration menu input."""
        if input_text == "1":
            # Configure global settings
            self._configure_global_settings()
        elif input_text == "2":
            # Manage secrets
            self._manage_secrets()
        elif input_text == "3":
            # View current configuration
            self._view_current_configuration()
        else:
            console.print("[red]Invalid option. Please try again.[/red]")
            console.print()

    def _process_utilities_menu(self, input_text: str) -> None:
        """Process utilities menu input."""
        if input_text == "1":
            # View resource state
            self._view_resource_state()
        elif input_text == "2":
            # Export state
            self._export_state()
        elif input_text == "3":
            # Manage templates
            self._manage_templates()
        else:
            console.print("[red]Invalid option. Please try again.[/red]")
            console.print()

    def show_main_menu(self) -> None:
        """Show main menu."""
        options = [
            ("1", "Deployment - Deploy and manage applications"),
            ("2", "Infrastructure - Provision and manage infrastructure"),
            ("3", "Monitoring - Monitor applications and infrastructure"),
            ("4", "Security - Scan and secure applications"),
            ("5", "Configuration - Configure toolkit settings"),
            ("6", "Utilities - Additional tools and utilities")
        ]

        self.display_menu("Main Menu", options, back_option=False)

    def show_deployment_menu(self) -> None:
        """Show deployment menu."""
        options = [
            ("1", "Deploy Application - Deploy an application to target environment"),
            ("2", "Rollback Deployment - Rollback to a previous version"),
            ("3", "View Deployment History - See deployment history for an application")
        ]

        self.display_menu("Deployment Menu", options)

    def show_infrastructure_menu(self) -> None:
        """Show infrastructure menu."""
        options = [
            ("1", "Provision Infrastructure - Create new infrastructure"),
            ("2", "Destroy Infrastructure - Remove existing infrastructure"),
            ("3", "Scale Infrastructure - Scale resources up or down"),
            ("4", "View Infrastructure Status - Check status of infrastructure")
        ]

        self.display_menu("Infrastructure Menu", options)

    def show_monitoring_menu(self) -> None:
        """Show monitoring menu."""
        options = [
            ("1", "Check Application Status - Get current status of an application"),
            ("2", "View Monitoring Dashboard - Open monitoring dashboard"),
            ("3", "Create Alert Rule - Set up monitoring alerts")
        ]

        self.display_menu("Monitoring Menu", options)

    def show_security_menu(self) -> None:
        """Show security menu."""
        options = [
            ("1", "Scan Application - Run security scan on an application"),
            ("2", "Check Compliance - Check compliance against a framework"),
            ("3", "Generate Security Report - Create comprehensive security report")
        ]

        self.display_menu("Security Menu", options)

    def show_configuration_menu(self) -> None:
        """Show configuration menu."""
        options = [
            ("1", "Configure Global Settings - Set up toolkit configuration"),
            ("2", "Manage Secrets - Store and retrieve sensitive information"),
            ("3", "View Current Configuration - Display current configuration")
        ]

        self.display_menu("Configuration Menu", options)

    def show_utilities_menu(self) -> None:
        """Show utilities menu."""
        options = [
            ("1", "View Resource State - Check state of resources"),
            ("2", "Export State - Export state information"),
            ("3", "Manage Templates - Work with infrastructure templates")
        ]

        self.display_menu("Utilities Menu", options)

    def show_current_menu(self) -> None:
        """Show the current menu based on state."""
        if self.current_menu == "main":
            self.show_main_menu()
        elif self.current_menu == "deployment":
            self.show_deployment_menu()
        elif self.current_menu == "infrastructure":
            self.show_infrastructure_menu()
        elif self.current_menu == "monitoring":
            self.show_monitoring_menu()
        elif self.current_menu == "security":
            self.show_security_menu()
        elif self.current_menu == "configuration":
            self.show_configuration_menu()
        elif self.current_menu == "utilities":
            self.show_utilities_menu()
        else:
            # Unknown menu, reset to main
            self.current_menu = "main"
            self.show_main_menu()

    def _deploy_application(self) -> None:
        """Deploy an application interactively."""
        self.display_header()
        console.print(Panel("Deploy Application", style="green"))
        console.print()

        try:
            # Get deployment details
            app_name = self.get_input("Application Name")
            version = self.get_input("Version")

            # Get environment with validation
            env_choices = ["dev", "staging", "production"]
            environment = self.get_input(
                "Environment",
                default="dev",
                choices=env_choices
            )

            # Get configuration file
            config_path = self.get_input(
                "Configuration File (leave empty for default)", default="config.yaml")

            # Confirm deployment
            console.print()
            console.print(f"[bold]Deployment Details:[/bold]")
            console.print(f"  Application: [cyan]{app_name}[/cyan]")
            console.print(f"  Version: [cyan]{version}[/cyan]")
            console.print(f"  Environment: [cyan]{environment}[/cyan]")
            console.print(f"  Config: [cyan]{config_path}[/cyan]")
            console.print()

            if not self.get_confirmation("Proceed with deployment?", default=True):
                console.print("[yellow]Deployment cancelled.[/yellow]")
                time.sleep(1)
                return

            # Execute deployment
            console.print("[green]Starting deployment...[/green]")
            wait = self.get_confirmation(
                "Wait for deployment to complete?", default=True)

            # Call deployment function
            result = deployment.deploy(
                app_name=app_name,
                version=version,
                environment=environment,
                config_path=config_path,
                wait=wait
            )

            # Save deployment state
            state_manager = get_state_manager()
            state = state_manager.get_state(
                "deployment", f"{app_name}-{environment}")
            state.save({
                "app_name": app_name,
                "version": version,
                "environment": environment,
                "status": result["status"],
                "deployment_time": result["deployment_time"],
                "details": result["details"]
            })

            # Show results
            console.print()
            console.print(Panel(
                f"Deployment of [bold]{app_name}[/bold] version [bold]{version}[/bold] to [bold]{environment}[/bold] completed successfully", style="green"))
            console.print(f"Deployment Time: {result['deployment_time']}")
            console.print("Details:")
            for key, value in result["details"].items():
                console.print(f"  {key}: {value}")

            # Wait for user to continue
            console.print()
            input("Press Enter to continue...")

        except Exception as e:
            console.print(
                f"[bold red]Error during deployment:[/bold red] {str(e)}")
            logger.error(f"Deployment error: {str(e)}", exc_info=True)
            console.print()
            input("Press Enter to continue...")

    def _rollback_deployment(self) -> None:
        """Rollback a deployment interactively."""
        self.display_header()
        console.print(Panel("Rollback Deployment", style="yellow"))
        console.print()

        try:
            # Get rollback details
            app_name = self.get_input("Application Name")

            # Get environment with validation
            env_choices = ["dev", "staging", "production"]
            environment = self.get_input(
                "Environment",
                default="dev",
                choices=env_choices
            )

            # Check for deployments
            state_manager = get_state_manager()
            state_id = f"{app_name}-{environment}"

            try:
                state = state_manager.get_state("deployment", state_id)
                current_state = state.get()

                # Display current version
                console.print(f"[bold]Current Deployment:[/bold]")
                console.print(f"  Application: [cyan]{app_name}[/cyan]")
                console.print(f"  Environment: [cyan]{environment}[/cyan]")
                console.print(
                    f"  Current Version: [cyan]{current_state.get('version', 'Unknown')}[/cyan]")
                console.print(
                    f"  Deployed at: [cyan]{current_state.get('deployment_time', 'Unknown')}[/cyan]")
                console.print()

                # Get rollback target
                version = self.get_input(
                    "Version to rollback to (leave empty for previous version)", default="")

                # Confirm rollback
                console.print()
                if not self.get_confirmation("Proceed with rollback?", default=True):
                    console.print("[yellow]Rollback cancelled.[/yellow]")
                    time.sleep(1)
                    return

                # Execute rollback
                console.print("[yellow]Starting rollback...[/yellow]")

                # Call rollback function
                result = deployment.rollback(
                    app_name=app_name,
                    environment=environment,
                    version=version if version else None
                )

                # Save rollback state
                state.save({
                    "app_name": app_name,
                    "version": result.get("rollback_to", "previous"),
                    "environment": environment,
                    "status": result["status"],
                    "rollback_time": result["rollback_time"],
                    "previous_version": current_state.get("version", "Unknown")
                })

                # Show results
                console.print()
                console.print(Panel(
                    f"Rolled back [bold]{app_name}[/bold] in [bold]{environment}[/bold] to version [bold]{result['rollback_to']}[/bold]", style="green"))
                console.print(f"Rollback Time: {result['rollback_time']}")

                # Wait for user to continue
                console.print()
                input("Press Enter to continue...")

            except StateError:
                console.print(
                    f"[bold yellow]No deployment state found for {app_name} in {environment}.[/bold yellow]")
                console.print(
                    "Please make sure you have deployed the application first.")
                console.print()
                input("Press Enter to continue...")

        except Exception as e:
            console.print(
                f"[bold red]Error during rollback:[/bold red] {str(e)}")
            logger.error(f"Rollback error: {str(e)}", exc_info=True)
            console.print()
            input("Press Enter to continue...")

    def _view_deployment_history(self) -> None:
        """View deployment history interactively."""
        self.display_header()
        console.print(Panel("Deployment History", style="blue"))
        console.print()

        try:
            # Get application details
            app_name = self.get_input("Application Name")

            # Get environment with validation
            env_choices = ["dev", "staging", "production"]
            environment = self.get_input(
                "Environment",
                default="dev",
                choices=env_choices
            )

            # Check for deployments
            state_manager = get_state_manager()
            state_id = f"{app_name}-{environment}"

            try:
                state = state_manager.get_state("deployment", state_id)
                versions = state.list_versions()

                if not versions:
                    console.print(
                        f"[bold yellow]No deployment history found for {app_name} in {environment}.[/bold yellow]")
                    console.print()
                    input("Press Enter to continue...")
                    return

                # Create table of versions
                table = Table(
                    title=f"Deployment History for {app_name} in {environment}")
                table.add_column("Version", style="cyan")
                table.add_column("Deployed At", style="green")
                table.add_column("Status")

                for version_info in versions:
                    version_data = state.get_version(version_info["version"])
                    table.add_row(
                        str(version_info["version"]),
                        version_info["timestamp"],
                        version_data.get("status", "Unknown")
                    )

                console.print(table)

                # Option to view detail
                console.print()
                if self.get_confirmation("View details of a specific version?", default=False):
                    version_num = self.get_input(
                        "Enter version number",
                        validator=lambda v: v.isdigit() and int(
                            v) in [info["version"] for info in versions]
                    )

                    version_data = state.get_version(int(version_num))

                    console.print()
                    console.print(
                        Panel(f"Details for Version {version_num}", style="blue"))
                    console.print(f"Application: [cyan]{app_name}[/cyan]")
                    console.print(f"Environment: [cyan]{environment}[/cyan]")
                    console.print(
                        f"Version: [cyan]{version_data.get('version', 'Unknown')}[/cyan]")
                    console.print(
                        f"Status: [cyan]{version_data.get('status', 'Unknown')}[/cyan]")
                    console.print(
                        f"Deployment Time: [cyan]{version_data.get('deployment_time', 'Unknown')}[/cyan]")

                    if "details" in version_data:
                        console.print("\nDetails:")
                        for key, value in version_data["details"].items():
                            console.print(f"  {key}: {value}")

                # Wait for user to continue
                console.print()
                input("Press Enter to continue...")

            except StateError:
                console.print(
                    f"[bold yellow]No deployment state found for {app_name} in {environment}.[/bold yellow]")
                console.print(
                    "Please make sure you have deployed the application first.")
                console.print()
                input("Press Enter to continue...")

        except Exception as e:
            console.print(
                f"[bold red]Error retrieving deployment history:[/bold red] {str(e)}")
            logger.error(f"Deployment history error: {str(e)}", exc_info=True)
            console.print()
            input("Press Enter to continue...")

    def _provision_infrastructure(self) -> None:
        """Provision infrastructure interactively."""
        self.display_header()
        console.print(Panel("Provision Infrastructure", style="green"))
        console.print()

        try:
            # Get provider
            provider_choices = ["aws", "azure", "gcp", "kubernetes"]
            provider = self.get_input(
                "Provider",
                default="aws",
                choices=provider_choices
            )

            # Get template file
            template_path = self.get_input(
                "Template File Path", validator=lambda p: os.path.exists(p))

            # Get parameters file (optional)
            params_path = self.get_input(
                "Parameters File Path (leave empty for none)", default="")
            if params_path and not os.path.exists(params_path):
                console.print(
                    f"[yellow]Parameters file not found: {params_path}[/yellow]")
                console.print("Proceeding without parameters file.")
                params_path = None

            # Validation option
            dry_run = self.get_confirmation(
                "Validate template without deploying?", default=False)

            # Confirm provisioning
            console.print()
            console.print(f"[bold]Provisioning Details:[/bold]")
            console.print(f"  Provider: [cyan]{provider}[/cyan]")
            console.print(f"  Template: [cyan]{template_path}[/cyan]")
            if params_path:
                console.print(f"  Parameters: [cyan]{params_path}[/cyan]")
            console.print(
                f"  Dry Run: [cyan]{'Yes' if dry_run else 'No'}[/cyan]")
            console.print()

            if not self.get_confirmation("Proceed with provisioning?", default=True):
                console.print("[yellow]Provisioning cancelled.[/yellow]")
                time.sleep(1)
                return

            # Execute provisioning
            action = "Validating" if dry_run else "Provisioning"
            console.print(f"[green]{action} infrastructure...[/green]")

            # Call infrastructure provision function
            result = infrastructure.provision(
                provider=provider,
                template_path=template_path,
                params_path=params_path,
                dry_run=dry_run
            )

            # Save state if not dry run
            if not dry_run:
                state_manager = get_state_manager()
                state = state_manager.get_state(
                    "infrastructure", result["provision_id"])
                state.save({
                    "provider": provider,
                    "template": template_path,
                    "parameters": params_path,
                    "provision_id": result["provision_id"],
                    "provision_time": result["provision_time"],
                    "resources": result["resources"],
                    "outputs": result["outputs"]
                })

            # Show results
            console.print()
            if dry_run:
                console.print(
                    Panel("Template validation successful!", style="green"))
            else:
                console.print(Panel(
                    f"Infrastructure provisioned successfully! Provision ID: [bold]{result['provision_id']}[/bold]", style="green"))

                # Display resources
                if "resources" in result:
                    resource_table = Table(title="Provisioned Resources")
                    resource_table.add_column("Type", style="cyan")
                    resource_table.add_column("ID", style="magenta")
                    resource_table.add_column("Name", style="blue")
                    resource_table.add_column("Status", style="green")

                    for resource in result["resources"]:
                        resource_table.add_row(
                            resource["type"],
                            resource["id"],
                            resource["name"],
                            resource["status"]
                        )

                    console.print(resource_table)

                # Display outputs
                if "outputs" in result and result["outputs"]:
                    console.print("\nOutputs:")
                    for key, value in result["outputs"].items():
                        console.print(f"  {key}: [bold]{value}[/bold]")

            # Wait for user to continue
            console.print()
            input("Press Enter to continue...")

        except Exception as e:
            console.print(
                f"[bold red]Error during provisioning:[/bold red] {str(e)}")
            logger.error(f"Provisioning error: {str(e)}", exc_info=True)
            console.print()
            input("Press Enter to continue...")

    def _destroy_infrastructure(self) -> None:
        """Destroy infrastructure interactively."""
        self.display_header()
        console.print(Panel("Destroy Infrastructure", style="red"))
        console.print()

        try:
            # Get provider
            provider_choices = ["aws", "azure", "gcp", "kubernetes"]
            provider = self.get_input(
                "Provider",
                default="aws",
                choices=provider_choices
            )

            # List available infrastructure
            state_manager = get_state_manager()
            resources = state_manager.list_resources("infrastructure")

            # Filter by provider
            provider_resources = [
                r for r in resources if r["metadata"].get("provider") == provider]

            if not provider_resources:
                console.print(
                    f"[bold yellow]No infrastructure found for provider {provider}.[/bold yellow]")
                console.print()
                input("Press Enter to continue...")
                return

            # Display available infrastructure
            resource_table = Table(
                title=f"Available {provider.upper()} Infrastructure")
            resource_table.add_column("Provision ID", style="cyan")
            resource_table.add_column("Created At", style="green")
            resource_table.add_column("Resources")

            for resource in provider_resources:
                state = state_manager.get_state(
                    "infrastructure", resource["resource_id"])
                state_data = state.get()

                resource_count = len(state_data.get(
                    "resources", [])) if "resources" in state_data else 0

                resource_table.add_row(
                    resource["resource_id"],
                    resource["metadata"].get("created_at", "Unknown"),
                    str(resource_count)
                )

            console.print(resource_table)
            console.print()

            # Get provision ID to destroy
            provision_id = self.get_input(
                "Provision ID to destroy",
                validator=lambda id: id in [r["resource_id"]
                                            for r in provider_resources]
            )

            # Confirm destruction
            console.print()
            console.print(
                f"[bold red]Warning:[/bold red] This action will destroy infrastructure with ID [bold]{provision_id}[/bold].")
            console.print("This action is irreversible!")
            console.print()

            if not self.get_confirmation("Are you ABSOLUTELY SURE you want to destroy this infrastructure?", default=False):
                console.print("[yellow]Destruction cancelled.[/yellow]")
                time.sleep(1)
                return

            # Double confirm for production
            state = state_manager.get_state("infrastructure", provision_id)
            state_data = state.get()

            if "environment" in state_data and state_data["environment"] == "production":
                console.print()
                console.print(
                    "[bold red]PRODUCTION ENVIRONMENT DETECTED![/bold red]")
                console.print(
                    "You are about to destroy infrastructure in a production environment.")
                console.print()

                if not self.get_confirmation("Type 'DESTROY' to confirm destruction of production infrastructure:", default=False):
                    console.print("[yellow]Destruction cancelled.[/yellow]")
                    time.sleep(1)
                    return

            # Execute destruction
            console.print("[red]Destroying infrastructure...[/red]")

            # Call infrastructure destroy function
            result = infrastructure.destroy(
                provider=provider,
                provision_id=provision_id
            )

            # Update state
            state.save({
                "status": "destroyed",
                "destroy_time": result["destroy_time"]
            })

            # Show results
            console.print()
            console.print(Panel(
                f"Infrastructure with ID [bold]{provision_id}[/bold] destroyed successfully", style="green"))
            console.print(f"Destroy Time: {result['destroy_time']}")

            # Wait for user to continue
            console.print()
            input("Press Enter to continue...")

        except Exception as e:
            console.print(
                f"[bold red]Error during destruction:[/bold red] {str(e)}")
            logger.error(f"Destruction error: {str(e)}", exc_info=True)
            console.print()
            input("Press Enter to continue...")

    def _scale_infrastructure(self) -> None:
        """Scale infrastructure interactively."""
        self.display_header()
        console.print(Panel("Scale Infrastructure", style="yellow"))
        console.print()

        try:
            # Get provider
            provider_choices = ["aws", "azure", "gcp", "kubernetes"]
            provider = self.get_input(
                "Provider",
                default="aws",
                choices=provider_choices
            )

            # List available infrastructure
            state_manager = get_state_manager()
            resources = state_manager.list_resources("infrastructure")

            # Filter by provider
            provider_resources = [
                r for r in resources if r["metadata"].get("provider") == provider]

            if not provider_resources:
                console.print(
                    f"[bold yellow]No infrastructure found for provider {provider}.[/bold yellow]")
                console.print()
                input("Press Enter to continue...")
                return

            # Display available infrastructure
            resource_table = Table(
                title=f"Available {provider.upper()} Infrastructure")
            resource_table.add_column("Provision ID", style="cyan")
            resource_table.add_column("Created At", style="green")
            resource_table.add_column("Resources")

            for resource in provider_resources:
                state = state_manager.get_state(
                    "infrastructure", resource["resource_id"])
                state_data = state.get()

                resource_count = len(state_data.get(
                    "resources", [])) if "resources" in state_data else 0

                resource_table.add_row(
                    resource["resource_id"],
                    resource["metadata"].get("created_at", "Unknown"),
                    str(resource_count)
                )

            console.print(resource_table)
            console.print()

            # Get provision ID to scale
            provision_id = self.get_input(
                "Provision ID to scale",
                validator=lambda id: id in [r["resource_id"]
                                            for r in provider_resources]
            )

            # Get resource details
            state = state_manager.get_state("infrastructure", provision_id)
            state_data = state.get()

            if "resources" not in state_data or not state_data["resources"]:
                console.print(
                    "[yellow]No resources found for this infrastructure.[/yellow]")
                console.print()
                input("Press Enter to continue...")
                return

            # Display available resources
            resource_types = set()
            for resource in state_data["resources"]:
                if "type" in resource:
                    resource_types.add(resource["type"])

            console.print(f"[bold]Available Resource Types:[/bold]")
            for rt in resource_types:
                console.print(f"  - {rt}")
            console.print()

            # Get resource type to scale
            resource_type = self.get_input(
                "Resource type to scale",
                choices=list(resource_types)
            )

            # Get new resource count
            current_count = sum(
                1 for r in state_data["resources"] if r.get("type") == resource_type)
            console.print(
                f"Current count for {resource_type}: {current_count}")

            count = self.get_input(
                "New resource count",
                validator=lambda c: c.isdigit() and int(c) > 0
            )
            count = int(count)

            # Confirm scaling
            console.print()
            console.print(f"[bold]Scaling Details:[/bold]")
            console.print(f"  Provider: [cyan]{provider}[/cyan]")
            console.print(f"  Provision ID: [cyan]{provision_id}[/cyan]")
            console.print(f"  Resource Type: [cyan]{resource_type}[/cyan]")
            console.print(f"  Current Count: [cyan]{current_count}[/cyan]")
            console.print(f"  New Count: [cyan]{count}[/cyan]")
            console.print()

            if not self.get_confirmation("Proceed with scaling?", default=True):
                console.print("[yellow]Scaling cancelled.[/yellow]")
                time.sleep(1)
                return

            # Execute scaling
            console.print("[yellow]Scaling infrastructure...[/yellow]")

            # Call infrastructure scale function
            result = infrastructure.scale(
                provider=provider,
                provision_id=provision_id,
                resource_type=resource_type,
                count=count
            )

            # Update state
            resources = state_data.get("resources", [])

            # Update existing resources or add new ones based on scaling direction
            if count > current_count:
                # Scale up - add new resources
                for i in range(current_count, count):
                    resources.append({
                        "type": resource_type,
                        "id": f"{resource_type}-{i+1}",
                        "name": f"{resource_type}-{i+1}",
                        "status": "running"
                    })
            elif count < current_count:
                # Scale down - remove resources
                resources = [r for r in resources if r.get("type") != resource_type] + \
                    [r for r in resources if r.get(
                        "type") == resource_type][:count]

            state_data["resources"] = resources
            state.save(state_data)

            # Show results
            console.print()
            console.print(Panel(
                f"Scaled [bold]{resource_type}[/bold] from [bold]{result['previous_count']}[/bold] to [bold]{result['new_count']}[/bold]", style="green"))
            console.print(f"Scale Time: {result['scale_time']}")

            # Wait for user to continue
            console.print()
            input("Press Enter to continue...")

        except Exception as e:
            console.print(
                f"[bold red]Error during scaling:[/bold red] {str(e)}")
            logger.error(f"Scaling error: {str(e)}", exc_info=True)
            console.print()
            input("Press Enter to continue...")

    def _view_infrastructure_status(self) -> None:
        """View infrastructure status interactively."""
        self.display_header()
        console.print(Panel("Infrastructure Status", style="blue"))
        console.print()

        try:
            # Get provider
            provider_choices = ["aws", "azure", "gcp", "kubernetes", "all"]
            provider = self.get_input(
                "Provider (or 'all' for all providers)",
                default="all",
                choices=provider_choices
            )

            # Get all infrastructure resources
            state_manager = get_state_manager()
            resources = state_manager.list_resources("infrastructure")

            # Filter by provider if needed
            if provider != "all":
                resources = [r for r in resources if r["metadata"].get(
                    "provider") == provider]

            if not resources:
                console.print(
                    f"[bold yellow]No infrastructure found{' for provider ' + provider if provider != 'all' else ''}.[/bold yellow]")
                console.print()
                input("Press Enter to continue...")
                return

            # Display infrastructure resources
            resource_table = Table(title="Infrastructure Resources")
            resource_table.add_column("Provider", style="cyan")
            resource_table.add_column("Provision ID", style="magenta")
            resource_table.add_column("Created At", style="green")
            resource_table.add_column("Status", style="yellow")
            resource_table.add_column("Resources")

            for resource in resources:
                state = state_manager.get_state(
                    "infrastructure", resource["resource_id"])
                state_data = state.get()

                resource_count = len(state_data.get(
                    "resources", [])) if "resources" in state_data else 0

                resource_table.add_row(
                    state_data.get("provider", "Unknown"),
                    resource["resource_id"],
                    resource["metadata"].get("created_at", "Unknown"),
                    state_data.get("status", "Unknown"),
                    str(resource_count)
                )

            console.print(resource_table)
            console.print()

            # Option to view detail
            if self.get_confirmation("View details of a specific infrastructure?", default=False):
                provision_id = self.get_input(
                    "Enter Provision ID",
                    validator=lambda id: id in [
                        r["resource_id"] for r in resources]
                )

                # Get detailed status
                state = state_manager.get_state("infrastructure", provision_id)
                state_data = state.get()

                # In a real implementation, this would call infrastructure.get_infrastructure_status
                # For demonstration, we'll use the state data

                console.print()
                console.print(
                    Panel(f"Details for Infrastructure {provision_id}", style="blue"))
                console.print(
                    f"Provider: [cyan]{state_data.get('provider', 'Unknown')}[/cyan]")
                console.print(
                    f"Provision Time: [cyan]{state_data.get('provision_time', 'Unknown')}[/cyan]")
                console.print(
                    f"Status: [cyan]{state_data.get('status', 'Unknown')}[/cyan]")

                # Display resources
                if "resources" in state_data and state_data["resources"]:
                    detail_table = Table(title="Resources")
                    detail_table.add_column("Type", style="cyan")
                    detail_table.add_column("ID", style="magenta")
                    detail_table.add_column("Name", style="blue")
                    detail_table.add_column("Status", style="green")

                    for resource in state_data["resources"]:
                        detail_table.add_row(
                            resource.get("type", "Unknown"),
                            resource.get("id", "Unknown"),
                            resource.get("name", "Unknown"),
                            resource.get("status", "Unknown")
                        )

                    console.print(detail_table)

                # Display outputs
                if "outputs" in state_data and state_data["outputs"]:
                    console.print("\nOutputs:")
                    for key, value in state_data["outputs"].items():
                        console.print(f"  {key}: [bold]{value}[/bold]")

            # Wait for user to continue
            console.print()
            input("Press Enter to continue...")

        except Exception as e:
            console.print(
                f"[bold red]Error retrieving infrastructure status:[/bold red] {str(e)}")
            logger.error(
                f"Infrastructure status error: {str(e)}", exc_info=True)
            console.print()
            input("Press Enter to continue...")

    def _check_application_status(self) -> None:
        """Check application status interactively."""
        self.display_header()
        console.print(Panel("Check Application Status", style="blue"))
        console.print()

        try:
            # Get application details
            app_name = self.get_input("Application Name")

            # Get environment with validation
            env_choices = ["dev", "staging", "production"]
            environment = self.get_input(
                "Environment",
                default="dev",
                choices=env_choices
            )

            # Continuous monitoring option
            continuous = self.get_confirmation(
                "Continuous monitoring (watch mode)?", default=False)

            interval = 60
            max_checks = None

            if continuous:
                interval = self.get_input(
                    "Interval between checks (seconds)",
                    default="60",
                    validator=lambda i: i.isdigit() and int(i) > 0
                )
                interval = int(interval)

                max_checks_input = self.get_input(
                    "Maximum number of checks (leave empty for unlimited)",
                    default=""
                )

                if max_checks_input and max_checks_input.isdigit():
                    max_checks = int(max_checks_input)

            # Execute monitoring
            console.print(
                f"[green]Checking status of {app_name} in {environment}...[/green]")

            # Call monitoring function
            result = monitoring.check_status(
                app_name=app_name,
                environment=environment,
                continuous=continuous,
                interval=interval,
                max_checks=max_checks
            )

            # Show results
            console.print()

            if not continuous:
                # Single check
                metrics = result["metrics"]

                status_color = "green" if result["status"] == "healthy" else "red"
                console.print(
                    f"Status: [{status_color}]{result['status']}[/{status_color}]")
                console.print(f"Timestamp: {result['timestamp']}")

                # Display metrics
                metrics_table = Table(title="Metrics")
                metrics_table.add_column("Metric", style="cyan")
                metrics_table.add_column("Value", style="magenta")
                metrics_table.add_column("Unit", style="green")

                for metric_name, metric_data in metrics.items():
                    metrics_table.add_row(
                        metric_name.replace("_", " ").title(),
                        str(metric_data["value"]),
                        metric_data["unit"]
                    )

                console.print(metrics_table)

            # Wait for user to continue
            console.print()
            input("Press Enter to continue...")

        except Exception as e:
            console.print(
                f"[bold red]Error checking application status:[/bold red] {str(e)}")
            logger.error(f"Application status error: {str(e)}", exc_info=True)
            console.print()
            input("Press Enter to continue...")

    def _view_monitoring_dashboard(self) -> None:
        """View monitoring dashboard interactively."""
        self.display_header()
        console.print(Panel("Monitoring Dashboard", style="blue"))
        console.print()

        try:
            # Check if visualization module is available
            try:
                from devops_toolkit.visualization import create_monitoring_dashboard
                visualization_available = True
            except ImportError:
                visualization_available = False
                console.print(
                    "[yellow]Visualization module not available.[/yellow]")
                console.print(
                    "Please install the visualization module to use this feature.")
                console.print()
                input("Press Enter to continue...")
                return

            # Get application details
            app_name = self.get_input("Application Name")

            # Get environment with validation
            env_choices = ["dev", "staging", "production"]
            environment = self.get_input(
                "Environment",
                default="dev",
                choices=env_choices
            )

            # Get time range
            time_range_choices = ["1h", "6h", "24h", "7d", "30d"]
            time_range = self.get_input(
                "Time Range",
                default="24h",
                choices=time_range_choices
            )

            # Create and show dashboard
            console.print(
                f"[green]Creating monitoring dashboard for {app_name} in {environment}...[/green]")

            dashboard = create_monitoring_dashboard(
                app_name=app_name,
                environment=environment,
                time_range=time_range,
                auto_refresh=True,
                refresh_interval=60
            )

            # Save dashboard to file and open
            dashboard_file = dashboard.to_html_file()

            console.print(f"[green]Dashboard created![/green]")
            console.print(f"Dashboard saved to: {dashboard_file}")
            console.print()
            console.print("Opening dashboard in web browser...")

            # Open dashboard in browser
            import webbrowser
            webbrowser.open(f"file://{dashboard_file}")

            # Wait for user to continue
            console.print()
            input("Press Enter to continue...")

        except Exception as e:
            console.print(
                f"[bold red]Error creating monitoring dashboard:[/bold red] {str(e)}")
            logger.error(
                f"Monitoring dashboard error: {str(e)}", exc_info=True)
            console.print()
            input("Press Enter to continue...")

    def _create_alert_rule(self) -> None:
        """Create alert rule interactively."""
        self.display_header()
        console.print(Panel("Create Alert Rule", style="yellow"))
        console.print()

        try:
            # Get alert details
            name = self.get_input("Alert Rule Name")
            app_name = self.get_input("Application Name")

            # Get metric
            metric_choices = ["cpu_usage", "memory_usage",
                              "request_rate", "error_rate", "response_time"]
            metric = self.get_input(
                "Metric to Monitor",
                choices=metric_choices
            )

            # Get threshold
            threshold = self.get_input(
                "Threshold Value",
                validator=lambda t: t.replace(".", "", 1).isdigit()
            )
            threshold = float(threshold)

            # Get operator
            operator_choices = [">", "<", "==", ">=", "<="]
            operator = self.get_input(
                "Comparison Operator",
                default=">",
                choices=operator_choices
            )

            # Get severity
            severity_choices = ["info", "warning", "error", "critical"]
            severity = self.get_input(
                "Alert Severity",
                default="warning",
                choices=severity_choices
            )

            # Get duration
            duration = self.get_input("Duration (e.g., 5m, 1h)", default="5m")

            # Get notification channels
            channels_input = self.get_input(
                "Notification Channels (comma-separated)", default="email")
            notification_channels = [
                c.strip() for c in channels_input.split(",") if c.strip()]

            # Confirm alert creation
            console.print()
            console.print(f"[bold]Alert Rule Details:[/bold]")
            console.print(f"  Name: [cyan]{name}[/cyan]")
            console.print(f"  Application: [cyan]{app_name}[/cyan]")
            console.print(f"  Metric: [cyan]{metric}[/cyan]")
            console.print(
                f"  Condition: [cyan]{metric} {operator} {threshold} for {duration}[/cyan]")
            console.print(f"  Severity: [cyan]{severity}[/cyan]")
            console.print(
                f"  Notification Channels: [cyan]{', '.join(notification_channels)}[/cyan]")
            console.print()

            if not self.get_confirmation("Create alert rule?", default=True):
                console.print(
                    "[yellow]Alert rule creation cancelled.[/yellow]")
                time.sleep(1)
                return

            # Create alert rule
            console.print("[green]Creating alert rule...[/green]")

            # Call monitoring function
            result = monitoring.create_alert_rule(
                name=name,
                app_name=app_name,
                metric=metric,
                threshold=threshold,
                operator=operator,
                duration=duration,
                severity=severity,
                notification_channels=notification_channels
            )

            # Show results
            console.print()
            console.print(
                Panel(f"Alert rule [bold]{name}[/bold] created successfully", style="green"))
            console.print(f"Created At: {result['created_at']}")
            console.print(f"Status: {result['status']}")

            # Wait for user to continue
            console.print()
            input("Press Enter to continue...")

        except Exception as e:
            console.print(
                f"[bold red]Error creating alert rule:[/bold red] {str(e)}")
            logger.error(f"Alert rule creation error: {str(e)}", exc_info=True)
            console.print()
            input("Press Enter to continue...")

    def _scan_application(self) -> None:
        """Scan application interactively."""
        self.display_header()
        console.print(Panel("Security Scan", style="red"))
        console.print()

        try:
            # Get application details
            app_name = self.get_input("Application Name")

            # Get scan type
            scan_type_choices = ["dependencies", "code", "container", "all"]
            scan_type = self.get_input(
                "Scan Type",
                default="all",
                choices=scan_type_choices
            )

            # Get report format
            format_choices = ["text", "json", "html"]
            report_format = self.get_input(
                "Report Format",
                default="text",
                choices=format_choices
            )

            # Get output file
            output_file = self.get_input(
                "Output File (leave empty for no file)", default="")

            # Confirm scan
            console.print()
            console.print(f"[bold]Scan Details:[/bold]")
            console.print(f"  Application: [cyan]{app_name}[/cyan]")
            console.print(f"  Scan Type: [cyan]{scan_type}[/cyan]")
            console.print(f"  Report Format: [cyan]{report_format}[/cyan]")
            if output_file:
                console.print(f"  Output File: [cyan]{output_file}[/cyan]")
            console.print()

            if not self.get_confirmation("Start security scan?", default=True):
                console.print("[yellow]Security scan cancelled.[/yellow]")
                time.sleep(1)
                return

            # Execute scan
            console.print("[red]Starting security scan...[/red]")

            # Call security scan function
            result = security.scan(
                app_name=app_name,
                scan_type=scan_type,
                report_format=report_format,
                output_file=output_file if output_file else None
            )

            # Show results
            console.print()
            console.print(
                Panel(f"Security scan of [bold]{app_name}[/bold] completed", style="green"))

            # Display summary
            console.print("\nVulnerability Summary:")
            severity_counts = result["summary"]["severity_counts"]
            console.print(
                f"  Critical: [bold red]{severity_counts.get('critical', 0)}[/bold red]")
            console.print(
                f"  High: [bold orange]{severity_counts.get('high', 0)}[/bold orange]")
            console.print(
                f"  Medium: [bold yellow]{severity_counts.get('medium', 0)}[/bold yellow]")
            console.print(
                f"  Low: [bold green]{severity_counts.get('low', 0)}[/bold green]")
            console.print(
                f"  Total Issues: [bold]{result['summary']['total_issues']}[/bold]")

            # Display detailed results if requested
            if self.get_confirmation("View detailed scan results?", default=True):
                for scan in result["scans"]:
                    console.print(f"\n[bold]{scan['scanner']}[/bold]:")

                    if "issues" in scan and scan["issues"]:
                        issue_table = Table()
                        issue_table.add_column("Severity", style="bold")
                        issue_table.add_column("Issue")
                        issue_table.add_column("Recommendation")

                        for issue in scan["issues"]:
                            severity = issue.get("severity", "low").lower()
                            severity_style = {
                                "critical": "bold red",
                                "high": "red",
                                "medium": "yellow",
                                "low": "green"
                            }.get(severity, "white")

                            # Format issue description
                            if "package" in issue:
                                description = f"{issue.get('package')} {issue.get('installed_version', '')} - {issue.get('description', '')}"
                            else:
                                description = f"{issue.get('file', '')}:{issue.get('line', '')} - {issue.get('description', '')}"

                            issue_table.add_row(
                                severity.capitalize(),
                                description,
                                issue.get("recommendation", "")
                            )

                        console.print(issue_table)
                    else:
                        console.print("  No issues found")

            if output_file:
                console.print(
                    f"\nDetailed report saved to: [bold]{output_file}[/bold]")

            # Wait for user to continue
            console.print()
            input("Press Enter to continue...")

        except Exception as e:
            console.print(
                f"[bold red]Error during security scan:[/bold red] {str(e)}")
            logger.error(f"Security scan error: {str(e)}", exc_info=True)
            console.print()
            input("Press Enter to continue...")

    def _check_compliance(self) -> None:
        """Check compliance interactively."""
        self.display_header()
        console.print(Panel("Compliance Check", style="blue"))
        console.print()

        try:
            # Get application details
            app_name = self.get_input("Application Name")

            # Get compliance framework
            framework_choices = ["owasp-top10", "pci-dss", "hipaa"]
            framework = self.get_input(
                "Compliance Framework",
                default="owasp-top10",
                choices=framework_choices
            )

            # Confirm compliance check
            console.print()
            console.print(f"[bold]Compliance Check Details:[/bold]")
            console.print(f"  Application: [cyan]{app_name}[/cyan]")
            console.print(f"  Framework: [cyan]{framework}[/cyan]")
            console.print()

            if not self.get_confirmation("Start compliance check?", default=True):
                console.print("[yellow]Compliance check cancelled.[/yellow]")
                time.sleep(1)
                return

            # Execute compliance check
            console.print(
                f"[blue]Checking {app_name} compliance against {framework} framework...[/blue]")

            # Call security compliance function
            result = security.check_compliance(
                app_name=app_name,
                framework=framework
            )

            # Show results
            console.print()
            console.print(Panel(
                f"Compliance check of [bold]{app_name}[/bold] against [bold]{framework}[/bold] completed", style="green"))

            # Display summary
            compliance_percentage = result["compliance_percentage"]
            compliance_color = "green" if compliance_percentage >= 90 else "yellow" if compliance_percentage >= 70 else "red"

            console.print(
                f"Overall Status: [bold {compliance_color}]{result['overall_status']}[/bold {compliance_color}]")
            console.print(
                f"Compliance Percentage: [bold {compliance_color}]{compliance_percentage}%[/bold {compliance_color}]")
            console.print(
                f"Requirements Met: {result['compliant_count']}/{result['requirements_count']}")

            # Display detailed results
            if "results" in result and result["results"]:
                console.print("\nDetailed Results:")

                compliance_table = Table()
                compliance_table.add_column("Requirement", style="cyan")
                compliance_table.add_column("Status", style="bold")
                compliance_table.add_column("Details")
                compliance_table.add_column("Recommendation")

                for req in result["results"]:
                    requirement = req["requirement"]
                    compliant = req["compliant"]
                    status = "Compliant" if compliant else "Non-Compliant"
                    status_style = "green" if compliant else "red"

                    compliance_table.add_row(
                        requirement.replace("-", " ").title(),
                        f"[{status_style}]{status}[/{status_style}]",
                        req.get("details", ""),
                        req.get("recommendation", "")
                    )

                console.print(compliance_table)

            # Wait for user to continue
            console.print()
            input("Press Enter to continue...")

        except Exception as e:
            console.print(
                f"[bold red]Error during compliance check:[/bold red] {str(e)}")
            logger.error(f"Compliance check error: {str(e)}", exc_info=True)
            console.print()
            input("Press Enter to continue...")

    def _generate_security_report(self) -> None:
        """Generate security report interactively."""
        self.display_header()
        console.print(Panel("Security Report", style="red"))
        console.print()

        try:
            # Get application details
            app_name = self.get_input("Application Name")

            # Get compliance option
            include_compliance = self.get_confirmation(
                "Include compliance check in report?", default=True)

            framework = None
            if include_compliance:
                # Get compliance framework
                framework_choices = ["owasp-top10", "pci-dss", "hipaa"]
                framework = self.get_input(
                    "Compliance Framework",
                    default="owasp-top10",
                    choices=framework_choices
                )

            # Get report format
            format_choices = ["text", "json", "html"]
            report_format = self.get_input(
                "Report Format",
                default="html",
                choices=format_choices
            )

            # Get output file
            output_file = self.get_input(
                "Output File",
                default=f"{app_name}_security_report.{report_format}"
            )

            # Confirm report generation
            console.print()
            console.print(f"[bold]Security Report Details:[/bold]")
            console.print(f"  Application: [cyan]{app_name}[/cyan]")
            if include_compliance:
                console.print(
                    f"  Compliance Framework: [cyan]{framework}[/cyan]")
            console.print(f"  Report Format: [cyan]{report_format}[/cyan]")
            console.print(f"  Output File: [cyan]{output_file}[/cyan]")
            console.print()

            if not self.get_confirmation("Generate security report?", default=True):
                console.print("[yellow]Report generation cancelled.[/yellow]")
                time.sleep(1)
                return

            # Execute report generation
            console.print("[red]Generating security report...[/red]")

            # Call security report function
            result = security.generate_security_report(
                app_name=app_name,
                include_compliance=include_compliance,
                compliance_framework=framework,
                output_file=output_file,
                report_format=report_format
            )

            # Show results
            console.print()
            console.print(Panel(
                f"Security report for [bold]{app_name}[/bold] generated successfully", style="green"))
            console.print(f"Report saved to: [bold]{output_file}[/bold]")

            # Wait for user to continue
            console.print()
            input("Press Enter to continue...")

        except Exception as e:
            console.print(
                f"[bold red]Error generating security report:[/bold red] {str(e)}")
            logger.error(f"Security report error: {str(e)}", exc_info=True)
            console.print()
            input("Press Enter to continue...")

    def _configure_global_settings(self) -> None:
        """Configure global settings interactively."""
        self.display_header()
        console.print(Panel("Configure Global Settings", style="blue"))
        console.print()

        try:
            from devops_toolkit.config import get_config, GlobalConfig

            config = get_config()
            global_config = config.get_global()

            # Display current configuration
            console.print(f"[bold]Current Configuration:[/bold]")
            console.print(
                f"  Log Level: [cyan]{global_config.log_level}[/cyan]")
            console.print(
                f"  Log File: [cyan]{global_config.log_file or 'None'}[/cyan]")
            console.print(
                f"  State Directory: [cyan]{global_config.state_dir}[/cyan]")
            console.print(
                f"  Secrets Directory: [cyan]{global_config.secrets_dir}[/cyan]")
            console.print(
                f"  Default Environment: [cyan]{global_config.default_environment}[/cyan]")
            console.print(
                f"  Environments: [cyan]{', '.join(global_config.environments)}[/cyan]")
            console.print()

            # Get new configuration
            log_level = self.get_input(
                "Log Level",
                default=global_config.log_level,
                choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            )

            log_file = self.get_input(
                "Log File (leave empty for none)",
                default=global_config.log_file or ""
            )

            state_dir = self.get_input(
                "State Directory",
                default=global_config.state_dir
            )

            secrets_dir = self.get_input(
                "Secrets Directory",
                default=global_config.secrets_dir
            )

            default_env = self.get_input(
                "Default Environment",
                default=global_config.default_environment,
                choices=["dev", "staging", "production"]
            )

            environments = self.get_input(
                "Environments (comma-separated)",
                default=",".join(global_config.environments)
            )
            environments = [e.strip()
                            for e in environments.split(",") if e.strip()]

            # Confirm configuration update
            console.print()
            console.print(f"[bold]New Configuration:[/bold]")
            console.print(f"  Log Level: [cyan]{log_level}[/cyan]")
            console.print(f"  Log File: [cyan]{log_file or 'None'}[/cyan]")
            console.print(f"  State Directory: [cyan]{state_dir}[/cyan]")
            console.print(f"  Secrets Directory: [cyan]{secrets_dir}[/cyan]")
            console.print(f"  Default Environment: [cyan]{default_env}[/cyan]")
            console.print(
                f"  Environments: [cyan]{', '.join(environments)}[/cyan]")
            console.print()

            if not self.get_confirmation("Update configuration?", default=True):
                console.print(
                    "[yellow]Configuration update cancelled.[/yellow]")
                time.sleep(1)
                return

            # Update configuration
            new_config = GlobalConfig(
                log_level=log_level,
                log_file=log_file if log_file else None,
                state_dir=state_dir,
                secrets_dir=secrets_dir,
                default_environment=default_env,
                environments=environments
            )

            # Save configuration
            config._global_config = new_config
            config_path = config.save()

            # Show results
            console.print()
            console.print(
                Panel("Configuration updated successfully", style="green"))
            console.print(
                f"Configuration saved to: [bold]{config_path}[/bold]")

            # Wait for user to continue
            console.print()
            input("Press Enter to continue...")

        except Exception as e:
            console.print(
                f"[bold red]Error updating configuration:[/bold red] {str(e)}")
            logger.error(f"Configuration error: {str(e)}", exc_info=True)
            console.print()
            input("Press Enter to continue...")

    def _manage_secrets(self) -> None:
        """Manage secrets interactively."""
        self.display_header()
        console.print(Panel("Manage Secrets", style="magenta"))
        console.print()

        try:
            from devops_toolkit.secrets import get_secrets_manager, SecretsError

            secrets_manager = get_secrets_manager()

            # Check if secrets are initialized
            if not secrets_manager.is_initialized():
                console.print(
                    "[yellow]Secrets storage is not initialized.[/yellow]")
                console.print(
                    "You need to set a password for secrets encryption.")
                console.print()

                password = self.get_input("New Password")
                if not password:
                    console.print("[red]Password cannot be empty.[/red]")
                    console.print()
                    input("Press Enter to continue...")
                    return

                # Confirm password
                confirm = self.get_input("Confirm Password")
                if password != confirm:
                    console.print("[red]Passwords do not match.[/red]")
                    console.print()
                    input("Press Enter to continue...")
                    return

                # Initialize secrets
                secrets_manager.unlock(password)
                console.print(
                    "[green]Secrets storage initialized successfully.[/green]")
                console.print()

            # Check if secrets are unlocked
            if not secrets_manager.is_unlocked():
                password = self.get_input("Enter Password to Unlock Secrets")
                if not secrets_manager.unlock(password):
                    console.print("[red]Incorrect password.[/red]")
                    console.print()
                    input("Press Enter to continue...")
                    return

                console.print("[green]Secrets unlocked successfully.[/green]")
                console.print()

            # Show secrets management menu
            while True:
                self.display_header()
                console.print(Panel("Secrets Management", style="magenta"))
                console.print()

                # Display menu
                options = [
                    ("1", "Set Secret - Store a new secret"),
                    ("2", "Get Secret - Retrieve a secret"),
                    ("3", "List Secrets - View available secrets"),
                    ("4", "Delete Secret - Remove a secret"),
                    ("5", "Change Password - Update encryption password"),
                    ("6", "Generate Password - Create a strong random password"),
                    ("b", "Back to Configuration Menu")
                ]

                self.display_menu("Secrets Management",
                                  options, exit_option=False)

                choice = self.get_input("Select an option")

                if choice == "b":
                    break

                if choice == "1":
                    # Set secret
                    namespace = self.get_input(
                        "Secret Namespace (e.g., aws, database)")
                    key = self.get_input("Secret Key")

                    # Hide input for sensitive values
                    import getpass
                    value = getpass.getpass("Secret Value: ")

                    try:
                        secrets_manager.set_secret(namespace, key, value)
                        console.print(
                            f"[green]Secret {namespace}/{key} set successfully.[/green]")
                    except SecretsError as e:
                        console.print(
                            f"[red]Error setting secret: {str(e)}[/red]")

                elif choice == "2":
                    # Get secret
                    namespace = self.get_input("Secret Namespace")
                    key = self.get_input("Secret Key")

                    try:
                        value = secrets_manager.get_secret(namespace, key)
                        if value is not None:
                            console.print(
                                f"Secret {namespace}/{key}: [green]{value}[/green]")
                        else:
                            console.print(
                                f"[yellow]Secret {namespace}/{key} not found.[/yellow]")
                    except SecretsError as e:
                        console.print(
                            f"[red]Error getting secret: {str(e)}[/red]")

                elif choice == "3":
                    # List secrets
                    namespace = self.get_input(
                        "Namespace (leave empty to list all)", default="")

                    try:
                        if namespace:
                            secrets = secrets_manager.list_secrets(namespace)
                            console.print(
                                f"Secrets in namespace [bold]{namespace}[/bold]:")

                            if not secrets:
                                console.print(
                                    "  [yellow]No secrets found.[/yellow]")
                            else:
                                for key in secrets:
                                    console.print(f"  - {key}")
                        else:
                            namespaces = secrets_manager.list_secrets()

                            if not namespaces:
                                console.print(
                                    "[yellow]No secrets found.[/yellow]")
                            else:
                                console.print("Available secret namespaces:")

                                for ns, keys in namespaces.items():
                                    console.print(
                                        f"[bold]{ns}[/bold] ({len(keys)} secrets)")
                                    for key in keys:
                                        console.print(f"  - {key}")
                    except SecretsError as e:
                        console.print(
                            f"[red]Error listing secrets: {str(e)}[/red]")

                elif choice == "4":
                    # Delete secret
                    namespace = self.get_input("Secret Namespace")
                    key = self.get_input("Secret Key")

                    try:
                        if self.get_confirmation(f"Delete secret {namespace}/{key}?", default=False):
                            if secrets_manager.delete_secret(namespace, key):
                                console.print(
                                    f"[green]Secret {namespace}/{key} deleted successfully.[/green]")
                            else:
                                console.print(
                                    f"[yellow]Secret {namespace}/{key} not found.[/yellow]")
                    except SecretsError as e:
                        console.print(
                            f"[red]Error deleting secret: {str(e)}[/red]")

                elif choice == "5":
                    # Change password
                    import getpass
                    old_password = getpass.getpass("Current Password: ")
                    new_password = getpass.getpass("New Password: ")
                    confirm = getpass.getpass("Confirm New Password: ")

                    if new_password != confirm:
                        console.print("[red]Passwords do not match.[/red]")
                    else:
                        try:
                            if secrets_manager.change_password(old_password, new_password):
                                console.print(
                                    "[green]Password changed successfully.[/green]")
                            else:
                                console.print(
                                    "[red]Failed to change password.[/red]")
                        except SecretsError as e:
                            console.print(
                                f"[red]Error changing password: {str(e)}[/red]")

                elif choice == "6":
                    # Generate password
                    length = self.get_input(
                        "Password Length",
                        default="16",
                        validator=lambda l: l.isdigit() and int(l) > 0
                    )
                    length = int(length)

                    use_uppercase = self.get_confirmation(
                        "Include uppercase letters?", default=True)
                    use_lowercase = self.get_confirmation(
                        "Include lowercase letters?", default=True)
                    use_digits = self.get_confirmation(
                        "Include digits?", default=True)
                    use_special = self.get_confirmation(
                        "Include special characters?", default=True)

                    try:
                        password = secrets_manager.generate_password(
                            length=length,
                            use_uppercase=use_uppercase,
                            use_lowercase=use_lowercase,
                            use_digits=use_digits,
                            use_special=use_special
                        )

                        console.print(
                            f"Generated Password: [green]{password}[/green]")

                        if self.get_confirmation("Save this password as a secret?", default=False):
                            namespace = self.get_input("Secret Namespace")
                            key = self.get_input("Secret Key")

                            try:
                                secrets_manager.set_secret(
                                    namespace, key, password)
                                console.print(
                                    f"[green]Password saved as secret {namespace}/{key}.[/green]")
                            except SecretsError as e:
                                console.print(
                                    f"[red]Error saving password: {str(e)}[/red]")
                    except Exception as e:
                        console.print(
                            f"[red]Error generating password: {str(e)}[/red]")

                console.print()
                input("Press Enter to continue...")

        except Exception as e:
            console.print(
                f"[bold red]Error managing secrets:[/bold red] {str(e)}")
            logger.error(f"Secrets management error: {str(e)}", exc_info=True)
            console.print()
            input("Press Enter to continue...")
