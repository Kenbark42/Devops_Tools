"""
DevOps Toolkit - AWS Deployment Example

This example demonstrates how to use DevOps Toolkit to deploy an application to AWS.
"""
import os
import sys
import argparse
import logging

# Add parent directory to path to import DevOps Toolkit
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import DevOps Toolkit modules
from devops_toolkit.config import get_config
from devops_toolkit.logging import init_logging_from_config, get_logger
from devops_toolkit.state import get_state_manager
from devops_toolkit.tools import deployment
from devops_toolkit.secrets import get_secrets_manager

# Initialize logging
init_logging_from_config()
logger = get_logger(__name__)


def setup_aws_credentials():
    """
    Set up AWS credentials using the secrets manager.
    
    This function prompts for AWS credentials if they are not already stored
    in the secrets manager, and then sets them as environment variables.
    """
    secrets_manager = get_secrets_manager()
    
    # Check if secrets are unlocked
    if not secrets_manager.is_unlocked():
        password = input("Enter password to unlock secrets: ")
        if not secrets_manager.unlock(password):
            print("Failed to unlock secrets.")
            return False
    
    # Check if AWS credentials are already stored
    aws_access_key = secrets_manager.get_secret("aws", "access_key")
    aws_secret_key = secrets_manager.get_secret("aws", "secret_key")
    aws_region = secrets_manager.get_secret("aws", "region")
    
    if not aws_access_key or not aws_secret_key:
        # Prompt for AWS credentials
        aws_access_key = input("AWS Access Key ID: ")
        aws_secret_key = input("AWS Secret Access Key: ")
        aws_region = input("AWS Region [us-east-1]: ") or "us-east-1"
        
        # Store credentials in secrets manager
        secrets_manager.set_secret("aws", "access_key", aws_access_key)
        secrets_manager.set_secret("aws", "secret_key", aws_secret_key)
        secrets_manager.set_secret("aws", "region", aws_region)
    
    # Set credentials as environment variables
    os.environ["AWS_ACCESS_KEY_ID"] = aws_access_key
    os.environ["AWS_SECRET_ACCESS_KEY"] = aws_secret_key
    os.environ["AWS_DEFAULT_REGION"] = aws_region
    
    print(f"Using AWS region: {aws_region}")
    return True


def deploy_to_aws(app_name, version, environment, config_path=None):
    """
    Deploy an application to AWS.
    
    Args:
        app_name: Name of the application
        version: Version to deploy
        environment: Target environment
        config_path: Path to configuration file (optional)
    
    Returns:
        Dict with deployment status and details
    """
    # Set up AWS credentials
    if not setup_aws_credentials():
        logger.error("Failed to set up AWS credentials.")
        return None
    
    # Log deployment
    logger.info(f"Deploying {app_name} version {version} to {environment} environment on AWS")
    
    try:
        # Deploy application
        result = deployment.deploy(
            app_name=app_name,
            version=version,
            environment=environment,
            config_path=config_path or "config.yaml",
            wait=True,
            timeout=600
        )
        
        # Track deployment in state manager
        state_manager = get_state_manager()
        state = state_manager.get_state("deployment", f"{app_name}-{environment}")
        state.save({
            "app_name": app_name,
            "version": version,
            "environment": environment,
            "provider": "aws",
            "status": result["status"],
            "deployment_time": result["deployment_time"],
            "details": result["details"]
        })
        
        logger.info(f"Deployment of {app_name} version {version} to {environment} completed successfully")
        return result
    
    except Exception as e:
        logger.error(f"Deployment error: {str(e)}", exc_info=True)
        return None


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="DevOps Toolkit - AWS Deployment Example")
    parser.add_argument("--app-name", required=True, help="Name of the application to deploy")
    parser.add_argument("--version", required=True, help="Version to deploy")
    parser.add_argument("--env", required=True, choices=["dev", "staging", "production"], help="Target environment")
    parser.add_argument("--config", help="Path to configuration file")
    
    args = parser.parse_args()
    
    result = deploy_to_aws(args.app_name, args.version, args.env, args.config)
    
    if result:
        print("\nDeployment Successful!")
        print(f"Application: {result['app_name']}")
        print(f"Version: {result['version']}")
        print(f"Environment: {result['environment']}")
        print(f"Deployment time: {result['deployment_time']}")
        print("\nDetails:")
        for key, value in result["details"].items():
            print(f"  {key}: {value}")
    else:
        print("Deployment failed. Check the logs for details.")


if __name__ == "__main__":
    main()
