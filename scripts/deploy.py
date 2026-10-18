"""
Deployment script for the Government Construction Opportunities platform.

This script automates the deployment process for the application,
handling environment setup, database migrations, and service restarts.
"""

import argparse
import subprocess
import sys
import os
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/deploy.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("deploy")

def run_command(command, cwd=None):
    """Run a command and log its output."""
    logger.info(f"Running: {command}")
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            cwd=cwd
        )
        stdout, stderr = process.communicate()
        
        if stdout:
            logger.info(stdout.decode())
        
        if stderr:
            logger.error(stderr.decode())
            
        if process.returncode != 0:
            logger.error(f"Command failed with exit code {process.returncode}")
            return False
        
        return True
    except Exception as e:
        logger.error(f"Error running command: {str(e)}")
        return False

def setup_environment(env_file=".env"):
    """Set up environment variables."""
    logger.info("Setting up environment variables...")
    
    # Check if .env file exists
    if not os.path.exists(env_file):
        logger.error(f"Environment file {env_file} not found")
        return False
    
    # Load environment variables from .env file
    try:
        with open(env_file, "r") as f:
            for line in f:
                if line.strip() and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    os.environ[key] = value
        logger.info("Environment variables loaded successfully")
        return True
    except Exception as e:
        logger.error(f"Error loading environment variables: {str(e)}")
        return False

def deploy_docker():
    """Deploy the application using Docker Compose."""
    logger.info("Deploying with Docker Compose...")
    
    # Pull latest changes if in a git repository
    if os.path.exists(".git"):
        if not run_command("git pull"):
            logger.warning("Failed to pull latest changes from git")
    
    # Build and start Docker containers
    if not run_command("docker-compose build"):
        logger.error("Failed to build Docker images")
        return False
    
    if not run_command("docker-compose up -d"):
        logger.error("Failed to start Docker containers")
        return False
    
    logger.info("Docker deployment completed successfully")
    return True

def deploy_manual():
    """Deploy the application manually (without Docker)."""
    logger.info("Deploying manually...")
    
    # Install dependencies
    if not run_command(f"{sys.executable} -m pip install -r requirements.txt"):
        logger.error("Failed to install Python dependencies")
        return False
    
    # Setup frontend
    frontend_dir = Path("frontend")
    if not run_command("npm install", cwd=frontend_dir):
        logger.error("Failed to install frontend dependencies")
        return False
    
    if not run_command("npm run build", cwd=frontend_dir):
        logger.error("Failed to build frontend")
        return False
    
    # Initialize database
    if not run_command(f"{sys.executable} main.py --init-db"):
        logger.error("Failed to initialize database")
        return False
    
    logger.info("Manual deployment completed successfully")
    logger.info("To start the application:")
    logger.info("1. Run API server: python main.py --api-only")
    logger.info("2. Run scheduler: python main.py --scheduler-only")
    
    return True

def main():
    """Main deployment function."""
    parser = argparse.ArgumentParser(description="Deploy Government Construction Opportunities platform")
    parser.add_argument("--manual", action="store_true", help="Deploy manually without Docker")
    parser.add_argument("--env-file", default=".env", help="Path to environment file")
    
    args = parser.parse_args()
    
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Setup environment
    if not setup_environment(args.env_file):
        return False
    
    # Deploy
    if args.manual:
        return deploy_manual()
    else:
        return deploy_docker()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
