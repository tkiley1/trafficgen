#!/bin/bash

# Traffic Generator Runner Script
# This script provides easy commands to run different traffic generator configurations

set -e

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

# Function to show usage
show_usage() {
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  start          Start traffic generator in continuous mode"
    echo "  stop           Stop the traffic generator"
    echo "  restart        Restart the traffic generator"
    echo "  logs           Show logs"
    echo "  status         Show container status"
    echo "  build          Build the Docker image"
    echo "  test           Run a quick test (10 requests)"
    echo "  fast           Run fast traffic generation"
    echo "  slow           Run slow, realistic traffic"
    echo "  custom         Run with custom parameters"
    echo "  help           Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start"
    echo "  $0 test"
    echo "  $0 custom --requests 20 --workers 3"
}

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
}

# Function to check if docker-compose is available
check_docker_compose() {
    if ! command -v docker-compose > /dev/null 2>&1; then
        print_error "docker-compose is not installed. Please install docker-compose and try again."
        exit 1
    fi
}

# Main command handler
case "${1:-help}" in
    "start")
        print_status "Starting traffic generator in continuous mode..."
        check_docker
        check_docker_compose
        docker-compose up -d --build
        print_success "Traffic generator started!"
        print_status "Use '$0 logs' to view logs"
        ;;
    
    "stop")
        print_status "Stopping traffic generator..."
        check_docker
        check_docker_compose
        docker-compose down
        print_success "Traffic generator stopped!"
        ;;
    
    "restart")
        print_status "Restarting traffic generator..."
        check_docker
        check_docker_compose
        docker-compose restart
        print_success "Traffic generator restarted!"
        ;;
    
    "logs")
        check_docker
        check_docker_compose
        docker-compose logs -f
        ;;
    
    "status")
        check_docker
        check_docker_compose
        docker-compose ps
        ;;
    
    "build")
        print_status "Building Docker image..."
        check_docker
        check_docker_compose
        docker-compose build
        print_success "Docker image built successfully!"
        ;;
    
    "test")
        print_status "Running quick test (10 requests)..."
        check_docker
        check_docker_compose
        docker-compose run --rm traffic-generator python traffic_generator.py --requests 10 --workers 3
        ;;
    
    "fast")
        print_status "Starting fast traffic generation..."
        check_docker
        check_docker_compose
        docker-compose run --rm traffic-generator python traffic_generator.py --continuous --workers 10 --delay-min 1 --delay-max 3
        ;;
    
    "slow")
        print_status "Starting slow, realistic traffic generation..."
        check_docker
        check_docker_compose
        docker-compose run --rm traffic-generator python traffic_generator.py --continuous --workers 2 --delay-min 5 --delay-max 15
        ;;
    
    "custom")
        shift
        print_status "Running with custom parameters: $@"
        check_docker
        check_docker_compose
        docker-compose run --rm traffic-generator python traffic_generator.py "$@"
        ;;
    
    "help"|*)
        show_usage
        ;;
esac
