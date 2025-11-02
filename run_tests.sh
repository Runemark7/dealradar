#!/bin/bash
# DealRadar Test Runner Script

set -e  # Exit on error

echo "========================================"
echo "DealRadar Test Suite"
echo "========================================"
echo ""

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed"
    echo "Please install uv: https://docs.astral.sh/uv/"
    exit 1
fi

# Ensure test dependencies are installed
echo "Installing/syncing dependencies..."
uv pip install -e .
uv pip install -r requirements.txt
echo ""

# Parse command line arguments
COVERAGE=false
VERBOSE=""
PARALLEL=""
MARKERS=""
EXTRA_ARGS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --coverage|-c)
            COVERAGE=true
            shift
            ;;
        --verbose|-v)
            VERBOSE="-v"
            shift
            ;;
        --vv)
            VERBOSE="-vv"
            shift
            ;;
        --parallel|-p)
            PARALLEL="-n auto"
            shift
            ;;
        --unit)
            MARKERS="-m unit"
            shift
            ;;
        --help|-h)
            echo "Usage: ./run_tests.sh [OPTIONS] [PYTEST_ARGS]"
            echo ""
            echo "Options:"
            echo "  --coverage, -c     Run with coverage report"
            echo "  --verbose, -v      Verbose output"
            echo "  --vv               Extra verbose output"
            echo "  --parallel, -p     Run tests in parallel"
            echo "  --unit             Run only unit tests"
            echo "  --help, -h         Show this help message"
            echo ""
            echo "Examples:"
            echo "  ./run_tests.sh                    # Run all tests"
            echo "  ./run_tests.sh --coverage         # Run with coverage"
            echo "  ./run_tests.sh -c -v -p           # Coverage, verbose, parallel"
            echo "  ./run_tests.sh --unit             # Only unit tests"
            echo "  ./run_tests.sh --ignore=tests/test_main.py  # Ignore specific test"
            exit 0
            ;;
        *)
            EXTRA_ARGS="$EXTRA_ARGS $1"
            shift
            ;;
    esac
done

# Build pytest command
PYTEST_CMD="uv run pytest $VERBOSE $PARALLEL $MARKERS $EXTRA_ARGS"

if [ "$COVERAGE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=. --cov-report=term-missing --cov-report=html"
fi

# Run tests
echo "Running: $PYTEST_CMD"
echo ""

$PYTEST_CMD

# Show coverage report location if generated
if [ "$COVERAGE" = true ]; then
    echo ""
    echo "========================================"
    echo "Coverage report generated:"
    echo "  HTML: htmlcov/index.html"
    echo "========================================"
fi

echo ""
echo "✅ Tests completed successfully!"
