#!/usr/bin/env python
"""
Test Runner Script

This script runs tests for the Government Construction Opportunities platform
with customizable options for test selection and reporting.
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
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("test_runner")

# Ensure project root is in path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)


def run_tests(
    test_type=None,
    test_path=None,
    verbose=False,
    coverage=False,
    html_report=False,
    xml_report=False,
    junit_report=False
):
    """
    Run tests with the specified options.
    
    Args:
        test_type (str, optional): Type of tests to run (unit, integration, all)
        test_path (str, optional): Specific test file or directory to run
        verbose (bool): Enable verbose output
        coverage (bool): Enable code coverage reporting
        html_report (bool): Generate HTML coverage report
        xml_report (bool): Generate XML coverage report
        junit_report (bool): Generate JUnit XML report
    
    Returns:
        int: Return code from pytest (0 for success)
    """
    # Base command
    command = ["pytest"]
    
    # Add verbosity if requested
    if verbose:
        command.append("-v")
    
    # Add markers based on test type
    if test_type == "unit":
        command.append("-m unit")
    elif test_type == "integration":
        command.append("-m integration")
    
    # Add code coverage if requested
    if coverage:
        command.append("--cov=scrapers --cov=database --cov=utils --cov=api")
        
        if html_report:
            command.append("--cov-report=html")
        
        if xml_report:
            command.append("--cov-report=xml")
    
    # Add JUnit XML report if requested
    if junit_report:
        command.append("--junitxml=test-results.xml")
    
    # Add specific test path if provided
    if test_path:
        command.append(test_path)
    
    # Build the command string
    cmd_str = " ".join(command)
    logger.info(f"Running tests with command: {cmd_str}")
    
    # Run the command
    try:
        result = subprocess.run(cmd_str, shell=True, check=False)
        return result.returncode
    except Exception as e:
        logger.error(f"Error running tests: {str(e)}")
        return 1


def main():
    """Main entry point for the test runner."""
    parser = argparse.ArgumentParser(description="Run tests for the Government Construction Opportunities platform")
    
    # Test selection options
    parser.add_argument(
        "--type", 
        choices=["unit", "integration", "all"], 
        default="all",
        help="Type of tests to run (default: all)"
    )
    parser.add_argument(
        "--path", 
        help="Specific test file or directory to run"
    )
    
    # Output options
    parser.add_argument(
        "-v", "--verbose", 
        action="store_true", 
        help="Enable verbose output"
    )
    
    # Coverage options
    parser.add_argument(
        "--coverage", 
        action="store_true", 
        help="Enable code coverage reporting"
    )
    parser.add_argument(
        "--html-report", 
        action="store_true", 
        help="Generate HTML coverage report"
    )
    parser.add_argument(
        "--xml-report", 
        action="store_true", 
        help="Generate XML coverage report"
    )
    parser.add_argument(
        "--junit-report", 
        action="store_true", 
        help="Generate JUnit XML report"
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Run tests with the specified options
    return run_tests(
        test_type=None if args.type == "all" else args.type,
        test_path=args.path,
        verbose=args.verbose,
        coverage=args.coverage,
        html_report=args.html_report,
        xml_report=args.xml_report,
        junit_report=args.junit_report
    )


if __name__ == "__main__":
    sys.exit(main())
