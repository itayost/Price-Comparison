#!/usr/bin/env python3
"""
Test runner script for the price comparison server.

This script helps run tests with proper configuration and error reporting.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def setup_environment():
    """Set up test environment variables"""
    os.environ["TESTING"] = "true"
    os.environ["SECRET_KEY"] = "test-secret-key-12345"
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    os.environ["ENVIRONMENT"] = "testing"


def run_tests(test_path=None, verbose=False, coverage=False, markers=None):
    """Run pytest with specified options"""
    setup_environment()
    
    # Base pytest command
    cmd = ["pytest"]
    
    # Add verbosity
    if verbose:
        cmd.append("-vv")
    else:
        cmd.append("-v")
    
    # Add coverage
    if coverage:
        cmd.extend([
            "--cov=services",
            "--cov=routes",
            "--cov=database",
            "--cov=parsers",
            "--cov-report=term-missing",
            "--cov-report=html"
        ])
    
    # Add markers
    if markers:
        cmd.extend(["-m", markers])
    
    # Add specific test path or run all tests
    if test_path:
        cmd.append(test_path)
    else:
        cmd.append("tests/")
    
    # Add additional options
    cmd.extend([
        "--tb=short",  # Shorter traceback format
        "--maxfail=5",  # Stop after 5 failures
        "-x",  # Stop on first failure
        "--disable-warnings"
    ])
    
    print(f"Running command: {' '.join(cmd)}")
    print("-" * 80)
    
    # Run tests
    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    
    return result.returncode


def list_test_categories():
    """List available test categories"""
    print("\nAvailable test categories:")
    print("  - unit: Unit tests that run in isolation")
    print("  - integration: Integration tests requiring database")
    print("  - api: API endpoint tests")
    print("  - auth: Authentication-related tests")
    print("  - cart: Cart functionality tests")
    print("  - hebrew: Tests involving Hebrew text")
    print("\nTest file categories:")
    print("  - tests/unit/: Unit tests")
    print("  - tests/api/: API tests")
    print("  - tests/integration/: Integration tests")


def check_dependencies():
    """Check if required dependencies are installed"""
    required = ["pytest", "pytest-cov", "fastapi", "sqlalchemy"]
    missing = []
    
    for package in required:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"Missing dependencies: {', '.join(missing)}")
        print("Please install them with: pip install -r requirements.txt")
        return False
    
    return True


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Run tests for price comparison server")
    parser.add_argument("path", nargs="?", help="Specific test file or directory to run")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("-c", "--coverage", action="store_true", help="Run with coverage")
    parser.add_argument("-m", "--markers", help="Run tests with specific markers (e.g., 'unit', 'not slow')")
    parser.add_argument("-l", "--list", action="store_true", help="List test categories")
    parser.add_argument("--check", action="store_true", help="Check dependencies")
    
    args = parser.parse_args()
    
    if args.list:
        list_test_categories()
        return
    
    if args.check or not check_dependencies():
        if not args.check:
            sys.exit(1)
        return
    
    # Run tests
    exit_code = run_tests(
        test_path=args.path,
        verbose=args.verbose,
        coverage=args.coverage,
        markers=args.markers
    )
    
    # Print summary
    print("\n" + "-" * 80)
    if exit_code == 0:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed.")
        print("\nTo debug specific failures:")
        print("  - Run with -v for verbose output")
        print("  - Run specific test file: python run_tests.py tests/api/test_auth_endpoints.py")
        print("  - Run with --pdb to drop into debugger on failure")
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
