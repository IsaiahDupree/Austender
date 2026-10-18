#!/usr/bin/env python
"""
Script to run the notification system tests.

This script executes the tests for the notification system components, 
including unit tests and integration tests, and displays a summary report.
"""

import os
import sys
import unittest
import time
import argparse
from colorama import init, Fore, Style

# Initialize colorama for cross-platform colored output
init()

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def run_tests(test_pattern=None, verbosity=2, failfast=False):
    """
    Run tests matching the specified pattern.
    
    Args:
        test_pattern (str): Pattern to match test files
        verbosity (int): Verbosity level (1-3)
        failfast (bool): Stop on first failure
    
    Returns:
        unittest.TestResult: Result of the test run
    """
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Running tests: {test_pattern or 'All notification tests'}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
    
    if test_pattern:
        if not test_pattern.startswith("test_"):
            test_pattern = f"test_{test_pattern}"
        if not test_pattern.endswith(".py"):
            test_pattern = f"{test_pattern}*.py"
    else:
        test_pattern = "test_*notification*.py"
    
    # Discover and load tests
    start_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests")
    test_suite = unittest.defaultTestLoader.discover(start_dir, pattern=test_pattern)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=verbosity, failfast=failfast)
    result = runner.run(test_suite)
    
    return result


def print_summary(result):
    """
    Print a summary of the test results.
    
    Args:
        result (unittest.TestResult): Result of the test run
    """
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Test Summary{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
    
    print(f"Tests run: {result.testsRun}")
    
    if result.wasSuccessful():
        print(f"{Fore.GREEN}All tests passed!{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}Tests failed: {len(result.failures) + len(result.errors)}{Style.RESET_ALL}")
        
        if result.failures:
            print(f"\n{Fore.YELLOW}Failures:{Style.RESET_ALL}")
            for i, (test, traceback) in enumerate(result.failures, 1):
                print(f"{Fore.YELLOW}{i}. {test}{Style.RESET_ALL}")
                print(f"{traceback}\n")
        
        if result.errors:
            print(f"\n{Fore.RED}Errors:{Style.RESET_ALL}")
            for i, (test, traceback) in enumerate(result.errors, 1):
                print(f"{Fore.RED}{i}. {test}{Style.RESET_ALL}")
                print(f"{traceback}\n")
    
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")


def main():
    """Main function to parse arguments and run tests."""
    parser = argparse.ArgumentParser(description="Run notification system tests")
    parser.add_argument(
        "--pattern", "-p", 
        help="Pattern to match test files (e.g., 'email' for test_email*.py)",
        default=None
    )
    parser.add_argument(
        "--verbosity", "-v", 
        type=int, choices=[1, 2, 3], 
        default=2,
        help="Verbosity level (1=quiet, 2=normal, 3=verbose)"
    )
    parser.add_argument(
        "--failfast", "-f", 
        action="store_true",
        help="Stop on first failure"
    )
    
    args = parser.parse_args()
    
    # Run tests and print summary
    start_time = time.time()
    result = run_tests(args.pattern, args.verbosity, args.failfast)
    elapsed_time = time.time() - start_time
    
    print_summary(result)
    print(f"Time elapsed: {elapsed_time:.2f} seconds")
    
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
