#!/usr/bin/env python3
"""
Test Runner for OPTIX Trading Platform
Runs database and rate limiting tests with coverage reporting
"""
import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd: list[str], description: str) -> bool:
    """Run a command and return success status"""
    print(f"\n{'='*60}")
    print(f"  {description}")
    print(f"{'='*60}\n")
    
    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Run OPTIX platform tests")
    parser.add_argument(
        "--type",
        choices=["all", "db", "ratelimit", "unit", "integration"],
        default="all",
        help="Type of tests to run"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Generate coverage report"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    # Build base command
    base_cmd = ["pytest"]
    
    if args.verbose:
        base_cmd.append("-v")
    else:
        base_cmd.append("-q")
    
    if args.coverage:
        base_cmd.extend([
            "--cov=src.user_service",
            "--cov-report=term-missing",
            "--cov-report=html"
        ])
    
    # Determine which tests to run
    success = True
    
    if args.type == "all":
        # Run all tests
        cmd = base_cmd + ["tests/unit/"]
        success = run_command(cmd, "Running All Tests")
        
    elif args.type == "db":
        # Database repository tests
        cmd = base_cmd + ["tests/unit/test_db_repository.py"]
        success = run_command(cmd, "Running Database Repository Tests")
        
    elif args.type == "ratelimit":
        # Rate limiter tests
        cmd = base_cmd + ["tests/unit/test_rate_limiter.py"]
        success = run_command(cmd, "Running Rate Limiter Tests")
        
    elif args.type == "unit":
        # All unit tests
        cmd = base_cmd + ["tests/unit/"]
        success = run_command(cmd, "Running Unit Tests")
        
    elif args.type == "integration":
        # Integration tests
        cmd = base_cmd + ["tests/integration/"]
        success = run_command(cmd, "Running Integration Tests")
    
    # Print summary
    print(f"\n{'='*60}")
    if success:
        print("  ✅ All tests passed!")
    else:
        print("  ❌ Some tests failed")
    print(f"{'='*60}\n")
    
    if args.coverage and success:
        print("Coverage report generated:")
        print("  - Terminal: See above")
        print("  - HTML: open htmlcov/index.html")
        print()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
