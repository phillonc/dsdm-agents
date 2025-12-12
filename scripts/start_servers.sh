#!/bin/bash
#
# OPTIX Platform Server Management Script
# Starts all servers or individual applications
#
# Usage:
#   ./scripts/start_servers.sh           # Start all servers
#   ./scripts/start_servers.sh all       # Start all servers
#   ./scripts/start_servers.sh optix     # Start OPTIX main API (port 8000)
#   ./scripts/start_servers.sh gex       # Start GEX Visualizer (port 8001)
#   ./scripts/start_servers.sh postgres  # Start PostgreSQL container
#   ./scripts/start_servers.sh redis     # Start Redis container
#   ./scripts/start_servers.sh infra     # Start infrastructure (PostgreSQL + Redis)
#   ./scripts/start_servers.sh status    # Check status of all services
#   ./scripts/start_servers.sh stop      # Stop all services
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project paths
PROJECT_ROOT="/Users/phillonmorris/dsdm-agents"
OPTIX_PATH="$PROJECT_ROOT/generated/optix/optix-trading-platform"
GEX_PATH="$PROJECT_ROOT/generated/optix/gex_visualizer"

# Ports
OPTIX_PORT=8000
GEX_PORT=8001
POSTGRES_PORT=5432
GEX_POSTGRES_PORT=5432
REDIS_PORT=6379

# Log directory
LOG_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOG_DIR"

print_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  OPTIX Platform Server Manager${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

print_status() {
    local service=$1
    local status=$2
    local port=$3

    if [ "$status" == "running" ]; then
        echo -e "  ${GREEN}●${NC} $service ${GREEN}running${NC} (port $port)"
    else
        echo -e "  ${RED}○${NC} $service ${RED}stopped${NC} (port $port)"
    fi
}

check_port() {
    local port=$1
    if lsof -ti:$port > /dev/null 2>&1; then
        echo "running"
    else
        echo "stopped"
    fi
}

kill_port() {
    local port=$1
    local pids=$(lsof -ti:$port 2>/dev/null)
    if [ -n "$pids" ]; then
        echo -e "${YELLOW}Killing processes on port $port...${NC}"
        echo "$pids" | xargs kill -9 2>/dev/null || true
        sleep 1
    fi
}

start_postgres() {
    echo -e "${BLUE}Starting PostgreSQL...${NC}"

    # Check if Docker is running
    if ! docker info > /dev/null 2>&1; then
        echo -e "${YELLOW}Docker is not running. Checking Homebrew PostgreSQL...${NC}"

        # Try Homebrew PostgreSQL
        if command -v brew &> /dev/null; then
            if brew services list | grep -q "postgresql"; then
                brew services start postgresql@15 2>/dev/null || brew services start postgresql 2>/dev/null || true
                echo -e "${GREEN}PostgreSQL started via Homebrew${NC}"
                return 0
            fi
        fi

        echo -e "${RED}Please start Docker Desktop or install PostgreSQL via Homebrew${NC}"
        return 1
    fi

    # Use Docker
    cd "$OPTIX_PATH"

    # Remove existing container if exists
    docker rm -f optix-postgres 2>/dev/null || true

    # Start PostgreSQL container
    docker run -d \
        --name optix-postgres \
        -e POSTGRES_USER=postgres \
        -e POSTGRES_PASSWORD=postgres_password \
        -e POSTGRES_DB=optix \
        -p 5433:5432 \
        -v optix_postgres_data:/var/lib/postgresql/data \
        postgres:15-alpine

    echo -e "${GREEN}PostgreSQL started on port 5433${NC}"

    # Wait for PostgreSQL to be ready
    echo -e "${YELLOW}Waiting for PostgreSQL to be ready...${NC}"
    sleep 3

    for i in {1..30}; do
        if docker exec optix-postgres pg_isready -U postgres > /dev/null 2>&1; then
            echo -e "${GREEN}PostgreSQL is ready!${NC}"
            return 0
        fi
        sleep 1
    done

    echo -e "${RED}PostgreSQL failed to start${NC}"
    return 1
}

start_redis() {
    echo -e "${BLUE}Starting Redis...${NC}"

    # Check if Docker is running
    if ! docker info > /dev/null 2>&1; then
        echo -e "${YELLOW}Docker is not running. Checking Homebrew Redis...${NC}"

        # Try Homebrew Redis
        if command -v brew &> /dev/null; then
            if brew services list | grep -q "redis"; then
                brew services start redis 2>/dev/null || true
                echo -e "${GREEN}Redis started via Homebrew${NC}"
                return 0
            fi
        fi

        echo -e "${RED}Please start Docker Desktop or install Redis via Homebrew${NC}"
        return 1
    fi

    # Use Docker
    cd "$OPTIX_PATH"

    # Remove existing container if exists
    docker rm -f optix-redis 2>/dev/null || true

    # Start Redis container
    docker run -d \
        --name optix-redis \
        -p 6379:6379 \
        redis:7-alpine

    echo -e "${GREEN}Redis started on port 6379${NC}"
    return 0
}

start_optix() {
    echo -e "${BLUE}Starting OPTIX Main API...${NC}"

    # Kill any existing process on the port
    kill_port $OPTIX_PORT

    cd "$OPTIX_PATH"

    # Find virtual environment and use its uvicorn directly
    local VENV_PATH=""
    if [ -d "env" ]; then
        VENV_PATH="env"
    elif [ -d "venv" ]; then
        VENV_PATH="venv"
    else
        echo -e "${RED}No virtual environment found in $OPTIX_PATH${NC}"
        return 1
    fi

    # Start uvicorn using the venv's Python directly
    nohup "$OPTIX_PATH/$VENV_PATH/bin/python" -m uvicorn src.main:app --host 0.0.0.0 --port $OPTIX_PORT > "$LOG_DIR/optix.log" 2>&1 &

    echo -e "${GREEN}OPTIX API starting on port $OPTIX_PORT${NC}"
    echo -e "${YELLOW}Logs: $LOG_DIR/optix.log${NC}"

    # Wait for server to start
    sleep 3

    if [ "$(check_port $OPTIX_PORT)" == "running" ]; then
        echo -e "${GREEN}OPTIX API is running!${NC}"
        echo -e "  Health: http://localhost:$OPTIX_PORT/health"
        echo -e "  Docs:   http://localhost:$OPTIX_PORT/docs"
    else
        echo -e "${RED}OPTIX API failed to start. Check logs: $LOG_DIR/optix.log${NC}"
        return 1
    fi
}

start_gex() {
    echo -e "${BLUE}Starting GEX Visualizer API...${NC}"

    # Kill any existing process on the port
    kill_port $GEX_PORT

    cd "$GEX_PATH"

    # Find virtual environment and use its uvicorn directly
    local VENV_PATH=""
    if [ -d "venv" ]; then
        VENV_PATH="venv"
    elif [ -d "env" ]; then
        VENV_PATH="env"
    else
        echo -e "${RED}No virtual environment found in $GEX_PATH${NC}"
        return 1
    fi

    # Start uvicorn using the venv's Python directly
    nohup "$GEX_PATH/$VENV_PATH/bin/python" -m uvicorn src.main:app --host 0.0.0.0 --port $GEX_PORT > "$LOG_DIR/gex.log" 2>&1 &

    echo -e "${GREEN}GEX Visualizer starting on port $GEX_PORT${NC}"
    echo -e "${YELLOW}Logs: $LOG_DIR/gex.log${NC}"

    # Wait for server to start
    sleep 3

    if [ "$(check_port $GEX_PORT)" == "running" ]; then
        echo -e "${GREEN}GEX Visualizer is running!${NC}"
        echo -e "  Health: http://localhost:$GEX_PORT/health"
        echo -e "  Docs:   http://localhost:$GEX_PORT/api/docs"
    else
        echo -e "${RED}GEX Visualizer failed to start. Check logs: $LOG_DIR/gex.log${NC}"
        return 1
    fi
}

start_infra() {
    echo -e "${BLUE}Starting Infrastructure Services...${NC}"
    start_postgres
    start_redis
}

start_all() {
    print_header
    echo -e "${BLUE}Starting all OPTIX services...${NC}"
    echo ""

    start_infra
    echo ""

    # Give infrastructure time to fully start
    sleep 2

    start_optix
    echo ""

    start_gex
    echo ""

    echo -e "${GREEN}All services started!${NC}"
    show_status
}

stop_all() {
    print_header
    echo -e "${YELLOW}Stopping all OPTIX services...${NC}"
    echo ""

    # Stop API servers
    echo -e "${YELLOW}Stopping OPTIX API...${NC}"
    kill_port $OPTIX_PORT

    echo -e "${YELLOW}Stopping GEX Visualizer...${NC}"
    kill_port $GEX_PORT

    # Stop Docker containers
    echo -e "${YELLOW}Stopping Docker containers...${NC}"
    docker stop optix-postgres optix-redis 2>/dev/null || true
    docker rm optix-postgres optix-redis 2>/dev/null || true

    # Stop Homebrew services if running
    if command -v brew &> /dev/null; then
        brew services stop postgresql@15 2>/dev/null || true
        brew services stop redis 2>/dev/null || true
    fi

    echo ""
    echo -e "${GREEN}All services stopped!${NC}"
}

show_status() {
    print_header
    echo -e "${BLUE}Service Status:${NC}"
    echo ""

    # Check PostgreSQL
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "optix-postgres"; then
        print_status "PostgreSQL (Docker)" "running" "5433"
    elif pgrep -f "Postgres.app" > /dev/null 2>&1; then
        print_status "PostgreSQL (Postgres.app)" "running" "5432"
    elif brew services list 2>/dev/null | grep -q "postgresql.*started"; then
        print_status "PostgreSQL (Homebrew)" "running" "5432"
    elif lsof -ti:5432 > /dev/null 2>&1; then
        print_status "PostgreSQL" "running" "5432"
    else
        print_status "PostgreSQL" "stopped" "5432/5433"
    fi

    # Check Redis
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "optix-redis"; then
        print_status "Redis (Docker)" "running" "6379"
    elif brew services list 2>/dev/null | grep -q "redis.*started"; then
        print_status "Redis (Homebrew)" "running" "6379"
    else
        print_status "Redis" "stopped" "6379"
    fi

    # Check OPTIX API
    print_status "OPTIX Main API" "$(check_port $OPTIX_PORT)" "$OPTIX_PORT"

    # Check GEX Visualizer
    print_status "GEX Visualizer" "$(check_port $GEX_PORT)" "$GEX_PORT"

    echo ""
    echo -e "${BLUE}Endpoints:${NC}"
    if [ "$(check_port $OPTIX_PORT)" == "running" ]; then
        echo -e "  OPTIX Health: ${GREEN}http://localhost:$OPTIX_PORT/health${NC}"
        echo -e "  OPTIX Docs:   ${GREEN}http://localhost:$OPTIX_PORT/docs${NC}"
    fi
    if [ "$(check_port $GEX_PORT)" == "running" ]; then
        echo -e "  GEX Health:   ${GREEN}http://localhost:$GEX_PORT/health${NC}"
        echo -e "  GEX Docs:     ${GREEN}http://localhost:$GEX_PORT/api/docs${NC}"
    fi
    echo ""
}

show_logs() {
    local service=$1

    case $service in
        optix)
            echo -e "${BLUE}OPTIX API Logs:${NC}"
            tail -f "$LOG_DIR/optix.log"
            ;;
        gex)
            echo -e "${BLUE}GEX Visualizer Logs:${NC}"
            tail -f "$LOG_DIR/gex.log"
            ;;
        *)
            echo -e "${YELLOW}Usage: $0 logs [optix|gex]${NC}"
            ;;
    esac
}

show_help() {
    print_header
    echo -e "${BLUE}Usage:${NC}"
    echo "  $0 [command]"
    echo ""
    echo -e "${BLUE}Commands:${NC}"
    echo "  all       Start all services (default)"
    echo "  optix     Start OPTIX Main API (port 8000)"
    echo "  gex       Start GEX Visualizer (port 8001)"
    echo "  postgres  Start PostgreSQL container (port 5433)"
    echo "  redis     Start Redis container (port 6379)"
    echo "  infra     Start infrastructure (PostgreSQL + Redis)"
    echo "  status    Show status of all services"
    echo "  stop      Stop all services"
    echo "  logs      View logs (usage: $0 logs [optix|gex])"
    echo "  help      Show this help message"
    echo ""
    echo -e "${BLUE}Examples:${NC}"
    echo "  $0                  # Start all services"
    echo "  $0 gex              # Start only GEX Visualizer"
    echo "  $0 status           # Check service status"
    echo "  $0 logs optix       # View OPTIX logs"
    echo ""
}

# Main command handler
case "${1:-all}" in
    all)
        start_all
        ;;
    optix)
        start_optix
        ;;
    gex)
        start_gex
        ;;
    postgres)
        start_postgres
        ;;
    redis)
        start_redis
        ;;
    infra)
        start_infra
        ;;
    status)
        show_status
        ;;
    stop)
        stop_all
        ;;
    logs)
        show_logs "$2"
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        show_help
        exit 1
        ;;
esac
