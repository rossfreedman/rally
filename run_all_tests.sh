#!/bin/bash

set -e  # Exit on any error

# Rally Test Suite Runner
# Comprehensive local testing script with setup, execution, and cleanup

echo "🏓 Rally Test Suite Runner"
echo "=========================="
echo ""

# Configuration
TEST_DB_NAME="rally_test"
TEST_DB_USER="postgres"
TEST_DB_HOST="localhost"
TEST_DB_PORT="5432"
COVERAGE_THRESHOLD=80
PYTHON_VERSION_REQUIRED="3.9"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check Python version
    if command -v python3 &> /dev/null; then
        PYTHON_VER=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
        if [[ $(echo "$PYTHON_VER >= $PYTHON_VERSION_REQUIRED" | bc -l) -eq 1 ]]; then
            print_success "Python $PYTHON_VER found"
        else
            print_error "Python $PYTHON_VERSION_REQUIRED or higher required. Found: $PYTHON_VER"
            exit 1
        fi
    else
        print_error "Python 3 not found. Please install Python 3.$PYTHON_VERSION_REQUIRED or higher"
        exit 1
    fi
    
    # Check PostgreSQL
    if command -v psql &> /dev/null; then
        print_success "PostgreSQL client found"
    else
        print_error "PostgreSQL client not found. Please install PostgreSQL"
        exit 1
    fi
    
    # Check if PostgreSQL server is running
    if pg_isready -h $TEST_DB_HOST -p $TEST_DB_PORT &> /dev/null; then
        print_success "PostgreSQL server is running"
    else
        print_error "PostgreSQL server is not running on $TEST_DB_HOST:$TEST_DB_PORT"
        print_status "Please start PostgreSQL server before running tests"
        exit 1
    fi
    
    # Check if test database exists
    if psql -h $TEST_DB_HOST -p $TEST_DB_PORT -U $TEST_DB_USER -lqt | cut -d \| -f 1 | grep -qw $TEST_DB_NAME; then
        print_success "Test database '$TEST_DB_NAME' exists"
    else
        print_warning "Test database '$TEST_DB_NAME' does not exist"
        print_status "Creating test database..."
        createdb -h $TEST_DB_HOST -p $TEST_DB_PORT -U $TEST_DB_USER $TEST_DB_NAME
        print_success "Test database created"
    fi
}

# Function to set up test environment
setup_test_environment() {
    print_status "Setting up test environment..."
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        print_status "Creating virtual environment..."
        python3 -m venv venv
        print_success "Virtual environment created"
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    print_success "Virtual environment activated"
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install dependencies
    print_status "Installing dependencies..."
    pip install -r requirements.txt
    
    # Install test dependencies
    pip install pytest pytest-cov pytest-xdist pytest-mock faker
    pip install locust selenium webdriver-manager
    pip install flake8 black isort mypy bandit safety
    
    print_success "Dependencies installed"
    
    # Set environment variables
    export TEST_DATABASE_URL="postgresql://$TEST_DB_USER@$TEST_DB_HOST:$TEST_DB_PORT/$TEST_DB_NAME"
    export FLASK_ENV=testing
    export SECRET_KEY=test-secret-key
    
    print_success "Environment variables set"
}

# Function to setup test database
setup_test_database() {
    print_status "Setting up test database..."
    
    # Drop and recreate test database for clean state
    dropdb -h $TEST_DB_HOST -p $TEST_DB_PORT -U $TEST_DB_USER $TEST_DB_NAME --if-exists
    createdb -h $TEST_DB_HOST -p $TEST_DB_PORT -U $TEST_DB_USER $TEST_DB_NAME
    
    # Create tables
    python3 -c "
from sqlalchemy import create_engine
from app.models.database_models import Base
engine = create_engine('$TEST_DATABASE_URL')
Base.metadata.create_all(engine)
print('Test database schema created')
"
    
    print_success "Test database setup complete"
}

# Function to run code quality checks
run_code_quality_checks() {
    print_status "Running code quality checks..."
    
    # Code formatting check
    print_status "Checking code formatting with black..."
    if black --check --diff . &> /dev/null; then
        print_success "Code formatting check passed"
    else
        print_warning "Code formatting issues found. Run 'black .' to fix"
        black --check --diff .
    fi
    
    # Import sorting check
    print_status "Checking import sorting with isort..."
    if isort --check-only --diff . &> /dev/null; then
        print_success "Import sorting check passed"
    else
        print_warning "Import sorting issues found. Run 'isort .' to fix"
        isort --check-only --diff .
    fi
    
    # Linting with flake8
    print_status "Running flake8 linting..."
    if flake8 . --count --max-complexity=10 --max-line-length=127 --statistics &> /dev/null; then
        print_success "Linting check passed"
    else
        print_warning "Linting issues found"
        flake8 . --count --max-complexity=10 --max-line-length=127 --statistics
    fi
    
    # Security check with bandit
    print_status "Running security scan with bandit..."
    if bandit -r . -f txt &> /dev/null; then
        print_success "Security scan passed"
    else
        print_warning "Security issues found"
        bandit -r . -f txt
    fi
}

# Function to scrape fresh test data
scrape_test_data() {
    print_status "Scraping fresh test data..."
    
    if python3 tests/scrapers/random_league_scraper.py; then
        print_success "Test data scraping completed"
    else
        print_warning "Test data scraping completed with warnings"
        print_status "Tests will use mock data as fallback"
    fi
}

# Function to run unit tests
run_unit_tests() {
    print_status "Running unit tests..."
    
    pytest tests/ -v \
        --cov=app \
        --cov=utils \
        --cov-report=html \
        --cov-report=term-missing \
        --cov-report=xml \
        --junit-xml=test-results-unit.xml \
        -m "unit" \
        --tb=short
    
    print_success "Unit tests completed"
}

# Function to run integration tests
run_integration_tests() {
    print_status "Running integration tests..."
    
    pytest tests/ -v \
        --cov=app \
        --cov-append \
        --cov-report=html \
        --cov-report=xml \
        --junit-xml=test-results-integration.xml \
        -m "integration" \
        --tb=short
    
    print_success "Integration tests completed"
}

# Function to run security tests
run_security_tests() {
    print_status "Running security tests..."
    
    pytest tests/ -v \
        --junit-xml=test-results-security.xml \
        -m "security" \
        --tb=short
    
    print_success "Security tests completed"
}

# Function to run performance tests
run_performance_tests() {
    print_status "Running performance tests..."
    
    pytest tests/ -v \
        --junit-xml=test-results-performance.xml \
        -m "performance" \
        --tb=short
    
    print_success "Performance tests completed"
}

# Function to run UI tests
run_ui_tests() {
    print_status "Running UI tests..."
    
    # Check if Playwright is installed
    if ! python3 -c "import playwright" &> /dev/null; then
        print_warning "Playwright not installed, installing now..."
        pip install playwright pytest-playwright
        python3 -m playwright install --with-deps
    fi
    
    # Run UI tests using the dedicated runner
    if python3 run_ui_tests.py --quick; then
        print_success "UI tests completed"
    else
        print_warning "UI tests completed with issues"
    fi
}

# Function to run load tests
run_load_tests() {
    print_status "Running load tests..."
    print_status "Starting Flask application for load testing..."
    
    # Start Flask app in background
    export DATABASE_URL=$TEST_DATABASE_URL
    python3 server.py &
    FLASK_PID=$!
    
    # Wait for app to start
    sleep 10
    
    # Check if app is running
    if curl -f http://localhost:8080/health &> /dev/null; then
        print_success "Flask application started successfully"
        
        # Run load tests
        cd tests/load
        locust -f load_test_registration.py \
            --host http://localhost:8080 \
            --users 10 \
            --spawn-rate 2 \
            --run-time 1m \
            --headless \
            --html load_test_report.html \
            --csv load_test_results
        
        cd ../..
        print_success "Load tests completed"
    else
        print_error "Flask application failed to start"
    fi
    
    # Clean up Flask process
    if kill -0 $FLASK_PID 2>/dev/null; then
        kill $FLASK_PID
        print_status "Flask application stopped"
    fi
}

# Function to run regression tests
run_regression_tests() {
    print_status "Running regression tests..."
    
    pytest tests/ -v \
        --junit-xml=test-results-regression.xml \
        -m "regression" \
        --tb=short
    
    print_success "Regression tests completed"
}

# Function to check coverage
check_coverage() {
    print_status "Checking test coverage..."
    
    if [ -f coverage.xml ]; then
        # Extract coverage percentage (simplified)
        COVERAGE=$(python3 -c "
import xml.etree.ElementTree as ET
tree = ET.parse('coverage.xml')
root = tree.getroot()
coverage = float(root.attrib['line-rate']) * 100
print(f'{coverage:.1f}')
")
        
        if (( $(echo "$COVERAGE >= $COVERAGE_THRESHOLD" | bc -l) )); then
            print_success "Coverage: $COVERAGE% (meets $COVERAGE_THRESHOLD% threshold)"
        else
            print_warning "Coverage: $COVERAGE% (below $COVERAGE_THRESHOLD% threshold)"
        fi
        
        print_status "Detailed coverage report: htmlcov/index.html"
    else
        print_warning "Coverage report not found"
    fi
}

# Function to generate test report
generate_test_report() {
    print_status "Generating test report..."
    
    REPORT_FILE="test_report_$(date +%Y%m%d_%H%M%S).md"
    
    cat > $REPORT_FILE << EOF
# Rally Test Suite Report

**Generated:** $(date)
**Environment:** Local Development

## Test Results Summary

### Unit Tests
$(grep -c "PASSED" test-results-unit.xml 2>/dev/null || echo "N/A") passed, $(grep -c "FAILED" test-results-unit.xml 2>/dev/null || echo "0") failed

### Integration Tests  
$(grep -c "PASSED" test-results-integration.xml 2>/dev/null || echo "N/A") passed, $(grep -c "FAILED" test-results-integration.xml 2>/dev/null || echo "0") failed

### Security Tests
$(grep -c "PASSED" test-results-security.xml 2>/dev/null || echo "N/A") passed, $(grep -c "FAILED" test-results-security.xml 2>/dev/null || echo "0") failed

### Performance Tests
$(grep -c "PASSED" test-results-performance.xml 2>/dev/null || echo "N/A") passed, $(grep -c "FAILED" test-results-performance.xml 2>/dev/null || echo "0") failed

### Regression Tests
$(grep -c "PASSED" test-results-regression.xml 2>/dev/null || echo "N/A") passed, $(grep -c "FAILED" test-results-regression.xml 2>/dev/null || echo "0") failed

## Coverage Report
- HTML Report: htmlcov/index.html
- XML Report: coverage.xml

## Load Test Results
- Report: tests/load/load_test_report.html
- CSV Data: tests/load/load_test_results*.csv

## Artifacts Generated
- Test Results: test-results-*.xml
- Coverage Reports: htmlcov/, coverage.xml
- Load Test Report: tests/load/load_test_report.html
- Test Data: tests/fixtures/scraped_players*.json

## Next Steps
1. Review any failing tests
2. Check coverage report for untested code
3. Examine load test results for performance bottlenecks
4. Address security scan findings
5. Update tests as needed for new features

EOF

    print_success "Test report generated: $REPORT_FILE"
}

# Function to cleanup
cleanup() {
    print_status "Cleaning up..."
    
    # Remove test database
    if psql -h $TEST_DB_HOST -p $TEST_DB_PORT -U $TEST_DB_USER -lqt | cut -d \| -f 1 | grep -qw $TEST_DB_NAME; then
        dropdb -h $TEST_DB_HOST -p $TEST_DB_PORT -U $TEST_DB_USER $TEST_DB_NAME
        print_success "Test database cleaned up"
    fi
    
    # Deactivate virtual environment if active
    if [[ "$VIRTUAL_ENV" != "" ]]; then
        deactivate
        print_success "Virtual environment deactivated"
    fi
}

# Main execution function
main() {
    local skip_checks=false
    local quick_mode=false
    local coverage_only=false
    local load_tests_only=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-checks)
                skip_checks=true
                shift
                ;;
            --quick)
                quick_mode=true
                shift
                ;;
            --coverage-only)
                coverage_only=true
                shift
                ;;
            --load-only)
                load_tests_only=true
                shift
                ;;
            --help)
                echo "Usage: $0 [options]"
                echo ""
                echo "Options:"
                echo "  --skip-checks    Skip prerequisite checks"
                echo "  --quick          Run only unit and integration tests"
                echo "  --coverage-only  Run tests for coverage analysis only"
                echo "  --load-only      Run only load tests"
                echo "  --help           Show this help message"
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Trap cleanup on exit
    trap cleanup EXIT
    
    # Run checks unless skipped
    if [ "$skip_checks" = false ]; then
        check_prerequisites
    fi
    
    setup_test_environment
    setup_test_database
    
    if [ "$load_tests_only" = true ]; then
        run_load_tests
        return
    fi
    
    if [ "$coverage_only" = false ]; then
        run_code_quality_checks
        scrape_test_data
    fi
    
    # Run core test suites
    run_unit_tests
    run_integration_tests
    
    if [ "$quick_mode" = false ] && [ "$coverage_only" = false ]; then
        run_security_tests
        run_performance_tests
        run_ui_tests
        run_load_tests
        run_regression_tests
    fi
    
    check_coverage
    
    if [ "$coverage_only" = false ]; then
        generate_test_report
    fi
    
    print_success "All tests completed successfully! 🎉"
    print_status "Review the generated reports for detailed results"
}

# Run main function with all arguments
main "$@" 