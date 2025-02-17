#!/bin/bash

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Required environment variables
declare -a REQUIRED_VARS=(
    # Database Configuration
    "NEO4J_URI"
    "NEO4J_USER"
    "NEO4J_PASSWORD"
    "NEO4J_DATABASE"

    # OAuth Configuration
    "OAUTH_DOMAIN"
    "OAUTH_CLIENT_ID"
    "OAUTH_CLIENT_SECRET"

    # AI Service Configuration
    "OPENAI_API_KEY"
    "ANTHROPIC_API_KEY"
    "PERPLEXITY_API_KEY"

    # Security Configuration
    "JWT_SECRET"
    "SESSION_SECRET"
    "ENCRYPTION_KEY"
)

# Optional environment variables with default values
declare -A OPTIONAL_VARS=(
    ["NODE_ENV"]="development"
    ["BACKEND_PORT"]="8000"
    ["FRONTEND_PORT"]="3000"
    ["LOG_LEVEL"]="debug"
    ["ENABLE_TRACING"]="true"
    ["RATE_LIMIT_WINDOW"]="15m"
    ["RATE_LIMIT_MAX_REQUESTS"]="100"
)

# Function to check if .env file exists
check_env_file() {
    if [ ! -f .env ]; then
        echo -e "${RED}Error: .env file not found${NC}"
        echo "Please copy .env.example to .env and configure the variables"
        exit 1
    fi
}

# Function to validate required variables
validate_required_vars() {
    local missing_vars=()

    for var in "${REQUIRED_VARS[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        fi
    done

    if [ ${#missing_vars[@]} -ne 0 ]; then
        echo -e "${RED}Error: Missing required environment variables:${NC}"
        printf '%s\n' "${missing_vars[@]}"
        exit 1
    fi
}

# Function to check optional variables
check_optional_vars() {
    for var in "${!OPTIONAL_VARS[@]}"; do
        if [ -z "${!var}" ]; then
            echo -e "${YELLOW}Warning: Optional variable $var not set, using default: ${OPTIONAL_VARS[$var]}${NC}"
            export "$var"="${OPTIONAL_VARS[$var]}"
        fi
    done
}

# Function to validate URL format
validate_url() {
    local url=$1
    if [[ ! $url =~ ^https?:// ]]; then
        echo -e "${RED}Error: Invalid URL format for $2: $url${NC}"
        echo "URL must start with http:// or https://"
        exit 1
    fi
}

# Function to validate port numbers
validate_port() {
    local port=$1
    if ! [[ $port =~ ^[0-9]+$ ]] || [ $port -lt 1 ] || [ $port -gt 65535 ]; then
        echo -e "${RED}Error: Invalid port number for $2: $port${NC}"
        echo "Port must be between 1 and 65535"
        exit 1
    fi
}

# Main validation logic
main() {
    echo "Validating environment variables..."

    # Check .env file
    check_env_file

    # Source .env file
    set -a
    source .env
    set +a

    # Validate required variables
    validate_required_vars

    # Check optional variables
    check_optional_vars

    # Validate URL formats
    validate_url "$NEO4J_URI" "NEO4J_URI"
    validate_url "$OAUTH_DOMAIN" "OAUTH_DOMAIN"

    # Validate port numbers
    validate_port "$BACKEND_PORT" "BACKEND_PORT"
    validate_port "$FRONTEND_PORT" "FRONTEND_PORT"

    echo -e "${GREEN}Environment validation successful!${NC}"
}

# Run main function
main
