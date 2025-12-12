#!/bin/bash
# Test runner script for Volatility Compass

echo "=========================================="
echo "  Volatility Compass Test Suite"
echo "=========================================="
echo ""

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo "❌ pytest is not installed. Installing..."
    pip install pytest pytest-cov
fi

echo "Running tests with coverage..."
echo ""

# Run tests with coverage
pytest -v --cov=src --cov-report=term-missing --cov-report=html

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "  ✅ All tests passed!"
    echo "=========================================="
    echo ""
    echo "Coverage report generated: htmlcov/index.html"
    echo "Open with: open htmlcov/index.html (Mac) or xdg-open htmlcov/index.html (Linux)"
else
    echo ""
    echo "=========================================="
    echo "  ❌ Some tests failed"
    echo "=========================================="
    exit 1
fi
