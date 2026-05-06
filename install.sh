#!/bin/bash

# legal-mcp Installation Script
# Automatically installs legal-mcp to local environment

set -e

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored messages
info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Detect operating system
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        OS="windows"
    else
        error "Unsupported operating system: $OSTYPE"
        exit 1
    fi
    info "Detected operating system: $OS"
}

# Get user home directory
get_user_home() {
    echo "$HOME"
}

# Ask for installation directory
ask_install_dir() {
    local default_dir="$HOME/.legal-mcp"
    
    echo ""
    info "Please select installation directory"
    echo "Default directory: $default_dir"
    read -p "Enter installation directory (press Enter for default): " install_dir
    
    if [ -z "$install_dir" ]; then
        install_dir="$default_dir"
    fi
    
    # Convert to absolute path
    install_dir=$(cd "$(dirname "$install_dir")" 2>/dev/null && pwd)/$(basename "$install_dir") 2>/dev/null || install_dir="$install_dir"
    
    echo ""
    info "Installation directory: $install_dir"
    
    # Check if directory exists
    if [ -d "$install_dir" ]; then
        warn "Directory already exists: $install_dir"
        
        # Check if it's an old legal-mcp installation
        if [ -d "$install_dir/legal-mcp" ] && [ -f "$install_dir/legal-mcp/pyproject.toml" ]; then
            info "Detected old legal-mcp installation"
            read -p "Update existing installation? (y/n): " update_choice
            if [[ "$update_choice" =~ ^[Yy]$ ]]; then
                UPDATE_MODE=true
                info "Will update existing installation"
            else
                error "Installation aborted"
                exit 1
            fi
        else
            error "Directory is not empty and is not a legal-mcp installation directory, please clear the directory or choose another one"
            exit 1
        fi
    else
        # Create directory
        mkdir -p "$install_dir"
        success "Created directory: $install_dir"
        UPDATE_MODE=false
    fi
    
    INSTALL_DIR="$install_dir"
}

# Check and install uv
check_and_install_uv() {
    info "Checking if uv is installed..."
    
    if command -v uv &> /dev/null; then
        UV_PATH=$(which uv)
        success "uv is already installed: $UV_PATH"
        UV_VERSION=$(uv --version 2>&1 || echo "unknown")
        info "uv version: $UV_VERSION"
    else
        warn "uv is not installed, starting installation..."
        
        detect_os
        
        if [ "$OS" = "windows" ]; then
            info "Installing uv on Windows..."
            powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
        else
            info "Installing uv on Unix/Linux/macOS..."
            curl -LsSf https://astral.sh/uv/install.sh | sh
        fi
        
        # Refresh PATH
        export PATH="$HOME/.local/bin:$PATH"
        
        # Verify installation
        if command -v uv &> /dev/null; then
            UV_PATH=$(which uv)
            success "uv installed successfully: $UV_PATH"
            UV_VERSION=$(uv --version 2>&1 || echo "unknown")
            info "uv version: $UV_VERSION"
        else
            error "uv installation failed, please install manually"
            exit 1
        fi
    fi
}

# Clone or update project
clone_or_update_project() {
    local project_dir="$INSTALL_DIR/legal-mcp"
    
    if [ "$UPDATE_MODE" = true ] && [ -d "$project_dir/.git" ]; then
        info "Updating existing project..."
        cd "$project_dir"
        git pull origin main || git pull origin master
        success "Project update completed"
    else
        info "Cloning project..."
        cd "$INSTALL_DIR"
        git clone git@github.com:lijunjie2232/legal-mcp.git
        
        if [ ! -d "$project_dir" ]; then
            error "Project cloning failed"
            exit 1
        fi
        success "Project cloning completed"
    fi
    
    PROJECT_DIR="$project_dir"
}

# Create virtual environment and install dependencies
setup_venv_and_install() {
    cd "$PROJECT_DIR"
    
    info "Creating virtual environment..."
    uv venv --python 3.14 venv
    
    if [ ! -d "venv" ]; then
        error "Virtual environment creation failed"
        exit 1
    fi
    
    success "Virtual environment created: $PROJECT_DIR/venv"
    
    # Get Python interpreter path
    if [ "$OS" = "windows" ]; then
        PYTHON_PATH="$PROJECT_DIR/venv/Scripts/python.exe"
    else
        PYTHON_PATH="$PROJECT_DIR/venv/bin/python"
    fi
    
    info "Installing dependencies..."
    "$PYTHON_PATH" -m pip install -e . -v
    
    if [ $? -eq 0 ]; then
        success "Dependencies installed"
    else
        error "Dependency installation failed"
        exit 1
    fi
    
    PYTHON_EXEC="$PYTHON_PATH"
}

# Output MCP configuration and usage instructions
output_usage() {
    echo ""
    echo "=========================================="
    success "legal-mcp installation completed!"
    echo "=========================================="
    echo ""
    
    info "Installation information:"
    echo "  Installation directory: $INSTALL_DIR"
    echo "  Project directory: $PROJECT_DIR"
    echo "  Python interpreter: $PYTHON_EXEC"
    echo ""
    
    info "MCP server configuration:"
    echo ""
    echo 'Please add the following configuration to your MCP client configuration file:'
    echo ""
    cat << EOF
{
  "mcpServers": {
    "legal_mcp": {
      "command": "$PYTHON_EXEC",
      "args": [
        "-m",
        "legal_mcp.mcp_runner"
      ]
    }
  }
}
EOF
    echo ""
    
    info "Common commands:"
    echo "  Activate virtual environment:"
    if [ "$OS" = "windows" ]; then
        echo "    $PROJECT_DIR\\venv\\Scripts\\activate"
    else
        echo "    source $PROJECT_DIR/venv/bin/activate"
    fi
    echo ""
    echo "  Run MCP server:"
    echo "    $PYTHON_EXEC -m legal_mcp.mcp_runner"
    echo ""
    echo "  Update project:"
    echo "    cd $PROJECT_DIR && git pull"
    echo ""
    echo "  Reinstall dependencies:"
    echo "    $PYTHON_EXEC -m pip install -e ."
    echo ""
    
    info "Next steps:"
    echo "  1. Add the above MCP configuration to your MCP client configuration file"
    echo "  2. Restart MCP client to load new configuration"
    echo "  3. Start using legal-mcp service"
    echo ""
    
    success "Enjoy using legal-mcp!"
    echo ""
}

# Main function
main() {
    echo ""
    echo "=========================================="
    echo "  legal-mcp Installation Script"
    echo "=========================================="
    echo ""
    
    # 1. Ask for installation directory
    ask_install_dir
    
    # 2. Check and install uv
    check_and_install_uv
    
    # 3. Clone or update project
    clone_or_update_project
    
    # 4. Create virtual environment and install dependencies
    setup_venv_and_install
    
    # 5. Output usage instructions
    output_usage
}

# Execute main function
main
