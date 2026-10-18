"""
Setup script for the Government Construction Opportunities platform.
This script installs dependencies and initializes the project structure.
"""

import os
import subprocess
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("setup")

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

def setup_python_dependencies():
    """Install Python dependencies from requirements.txt."""
    logger.info("Installing Python dependencies...")
    return run_command(f"{sys.executable} -m pip install -r requirements.txt")

def setup_frontend():
    """Install frontend dependencies."""
    logger.info("Setting up frontend dependencies...")
    frontend_dir = Path("frontend")
    
    if not run_command("npm install", cwd=frontend_dir):
        logger.error("Failed to install frontend dependencies")
        return False
    
    logger.info("Frontend dependencies installed successfully")
    return True

def create_env_file():
    """Create .env file from template if it doesn't exist."""
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if env_file.exists():
        logger.info(".env file already exists, skipping creation")
        return True
    
    if not env_example.exists():
        logger.error(".env.example file not found")
        return False
    
    logger.info("Creating .env file from .env.example")
    try:
        with open(env_example, "r") as example_file:
            example_content = example_file.read()
        
        with open(env_file, "w") as new_file:
            new_file.write(example_content)
        
        logger.info(".env file created successfully")
        return True
    except Exception as e:
        logger.error(f"Error creating .env file: {str(e)}")
        return False

def initialize_database():
    """Initialize the database."""
    logger.info("Initializing database...")
    return run_command(f"{sys.executable} main.py --init-db")

def main():
    """Main setup function."""
    logger.info("Starting setup for Government Construction Opportunities platform")
    
    # Create necessary directories if they don't exist
    for directory in ["logs", "database"]:
        os.makedirs(directory, exist_ok=True)
    
    # Setup steps
    steps = [
        ("Installing Python dependencies", setup_python_dependencies),
        ("Setting up frontend", setup_frontend),
        ("Creating environment file", create_env_file),
        ("Initializing database", initialize_database),
    ]
    
    # Run all setup steps
    for step_name, step_func in steps:
        logger.info(f"Step: {step_name}")
        if not step_func():
            logger.error(f"Setup failed at step: {step_name}")
            return False
        logger.info(f"Completed: {step_name}")
    
    logger.info("Setup completed successfully")
    logger.info("You can now run the application with: python main.py")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
