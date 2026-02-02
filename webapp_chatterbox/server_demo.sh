#!/bin/bash
###############################################################################
# WebApp Chatterbox - One-Command Setup Script for New Server
# Usage: ./setup_new_server.sh
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BASE_DIR="/nvme0n1-disk/nvme01/HeyGem/webapp_chatterbox"
DATA_DIR="/home/administrator/heygem_data"
PYTHON_VERSION="3.11.0"
SARVAM_API_KEY="${SARVAM_API_KEY:-}"

# Functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

check_root() {
    if [ "$EUID" -eq 0 ]; then 
        log_error "Please do not run as root. Run as normal user with sudo access."
        exit 1
    fi
}

check_gpu() {
    log_info "Checking NVIDIA GPUs..."
    if ! command -v nvidia-smi &> /dev/null; then
        log_error "nvidia-smi not found. Please install NVIDIA drivers first."
        exit 1
    fi
    
    gpu_count=$(nvidia-smi --list-gpus | wc -l)
    log_success "Found $gpu_count GPU(s)"
    
    if [ "$gpu_count" -lt 3 ]; then
        log_warning "This setup requires 3 GPUs. Found only $gpu_count."
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

check_docker() {
    log_info "Checking Docker..."
    if ! command -v docker &> /dev/null; then
        log_error "Docker not found. Installing Docker..."
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh
        sudo usermod -aG docker $USER
        log_success "Docker installed. Please log out and back in for group changes."
        exit 0
    fi
    log_success "Docker found: $(docker --version)"
}

install_system_deps() {
    log_info "Installing system dependencies..."
    sudo apt-get update -qq
    sudo apt-get install -y -qq \
        python3-pip \
        python3-venv \
        ffmpeg \
        git \
        curl \
        build-essential \
        libssl-dev \
        zlib1g-dev \
        libbz2-dev \
        libreadline-dev \
        libsqlite3-dev \
        libncursesw5-dev \
        xz-utils \
        tk-dev \
        libxml2-dev \
        libxmlsec1-dev \
        libffi-dev \
        liblzma-dev \
        netcat \
        jq
    log_success "System dependencies installed"
}

setup_pyenv() {
    log_info "Setting up pyenv..."
    
    if [ ! -d "$HOME/.pyenv" ]; then
        log_info "Installing pyenv..."
        curl https://pyenv.run | bash
        
        # Add to shell config
        {
            echo 'export PYENV_ROOT="$HOME/.pyenv"'
            echo 'export PATH="$PYENV_ROOT/bin:$PATH"'
            echo 'eval "$(pyenv init - bash)"'
        } >> ~/.bashrc
        
        export PYENV_ROOT="$HOME/.pyenv"
        export PATH="$PYENV_ROOT/bin:$PATH"
        eval "$(pyenv init - bash)"
        
        log_success "pyenv installed"
    else
        log_info "pyenv already installed"
    fi
}

setup_python() {
    log_info "Setting up Python $PYTHON_VERSION..."
    
    if ! pyenv versions | grep -q "$PYTHON_VERSION"; then
        log_info "Installing Python $PYTHON_VERSION (this may take a while)..."
        pyenv install $PYTHON_VERSION
    fi
    
    cd "$BASE_DIR"
    pyenv local $PYTHON_VERSION
    
    log_success "Python $PYTHON_VERSION ready"
}

setup_venv() {
    log_info "Creating virtual environment..."
    
    cd "$BASE_DIR"
    
    if [ ! -d "chatterbox_venv" ]; then
        python -m venv chatterbox_venv
        log_success "Virtual environment created"
    else
        log_info "Virtual environment already exists"
    fi
    
    source chatterbox_venv/bin/activate
    
    log_info "Installing Python packages..."
    pip install --upgrade pip -q
    pip install -r requirements.txt -q
    
    log_success "Python packages installed"
}

setup_directories() {
    log_info "Creating required directories..."
    
    # GPU data directories
    sudo mkdir -p "$DATA_DIR/gpu"{0,1,2}
    sudo chown -R $USER:$USER "$DATA_DIR"
    
    # Application directories
    cd "$BASE_DIR"
    mkdir -p uploads outputs temp library/videos library/audios
    
    log_success "Directories created"
}

setup_docker_containers() {
    log_info "Setting up GPU containers..."
    
    # Pull image
    log_info "Pulling Docker image..."
    docker pull guiji2025/heygem.ai
    
    # Create containers if they don't exist
    for i in 0 1 2; do
        container_name="heygem-gpu$i"
        port=$((8390 + i))
        
        if docker ps -a | grep -q "$container_name"; then
            log_info "Container $container_name already exists"
        else
            log_info "Creating container $container_name..."
            docker create --name "$container_name" \
                --gpus "\"device=$i\"" \
                -p "$port:8383" \
                -v "$DATA_DIR/gpu$i:/code/data" \
                guiji2025/heygem.ai \
                python /code/app_local.py --port 8383
            log_success "Container $container_name created"
        fi
    done
}

setup_services() {
    log_info "Setting up systemd services..."
    
    cd "$BASE_DIR"
    
    # Make scripts executable
    chmod +x start_service.sh restart_all.sh
    
    # Copy service files
    sudo cp heygem-chatterbox-containers.service /etc/systemd/system/
    sudo cp heygem-chatterbox.service /etc/systemd/system/
    
    # Reload and enable
    sudo systemctl daemon-reload
    sudo systemctl enable heygem-chatterbox-containers
    sudo systemctl enable heygem-chatterbox
    
    log_success "Systemd services configured"
}

configure_environment() {
    log_info "Configuring environment variables..."
    
    if [ -z "$SARVAM_API_KEY" ]; then
        log_warning "SARVAM_API_KEY not set!"
        echo "Please set it in the service file: /etc/systemd/system/heygem-chatterbox.service"
        echo "Environment=SARVAM_API_KEY=your_key_here"
    else
        log_success "SARVAM_API_KEY configured"
    fi
}

verify_setup() {
    log_info "Verifying setup..."
    
    # Check if files exist
    if [ ! -f "$BASE_DIR/default.mp4" ]; then
        log_warning "default.mp4 not found. Please add your default video."
    fi
    
    if [ ! -f "$BASE_DIR/reference_audio.wav" ]; then
        log_warning "reference_audio.wav not found. Please add your reference audio for voice cloning."
    fi
    
    log_success "Setup verification complete"
}

start_services() {
    log_info "Starting services..."
    
    # Start containers
    log_info "Starting GPU containers..."
    sudo systemctl start heygem-chatterbox-containers
    
    log_info "Waiting for containers to initialize (20 seconds)..."
    sleep 20
    
    # Start main service
    log_info "Starting main service..."
    sudo systemctl start heygem-chatterbox
    
    log_info "Waiting for service to initialize (60 seconds)..."
    sleep 60
    
    log_success "Services started"
}

check_health() {
    log_info "Checking service health..."
    
    # Check systemd service
    if sudo systemctl is-active --quiet heygem-chatterbox; then
        log_success "Service is active"
    else
        log_error "Service is not active!"
        sudo systemctl status heygem-chatterbox --no-pager
        return 1
    fi
    
    # Check API
    if curl -s http://localhost:5004/api/health > /dev/null 2>&1; then
        log_success "API is responding"
    else
        log_error "API is not responding on port 5004"
        return 1
    fi
    
    # Check TTS services
    for port in 20182 20183 20184; do
        if curl -s http://localhost:$port/health > /dev/null 2>&1; then
            log_success "TTS service on port $port is healthy"
        else
            log_warning "TTS service on port $port not responding"
        fi
    done
}

print_summary() {
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    log_success "WebApp Chatterbox Setup Complete!"
    echo "═══════════════════════════════════════════════════════════"
    echo ""
    echo "📊 Service Status:"
    echo "   Main API:       http://localhost:5004"
    echo "   TTS Services:   Ports 20182, 20183, 20184"
    echo "   GPU Containers: Ports 8390, 8391, 8392"
    echo ""
    echo "🔧 Quick Commands:"
    echo "   Check status:   sudo systemctl status heygem-chatterbox"
    echo "   View logs:      sudo journalctl -u heygem-chatterbox -f"
    echo "   Restart all:    cd $BASE_DIR && ./restart_all.sh"
    echo "   Stop service:   sudo systemctl stop heygem-chatterbox"
    echo ""
    echo "🧪 Test API:"
    echo "   curl http://localhost:5004/api/health"
    echo ""
    echo "📖 Full documentation: $BASE_DIR/README.md"
    echo ""
    echo "═══════════════════════════════════════════════════════════"
}

main() {
    echo "═══════════════════════════════════════════════════════════"
    echo "🚀 WebApp Chatterbox - Automated Setup"
    echo "═══════════════════════════════════════════════════════════"
    echo ""
    
    check_root
    check_gpu
    check_docker
    install_system_deps
    setup_pyenv
    setup_python
    setup_venv
    setup_directories
    setup_docker_containers
    setup_services
    configure_environment
    verify_setup
    
    echo ""
    read -p "Start services now? (Y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
        start_services
        check_health
    else
        log_info "Skipping service startup. Start manually with:"
        echo "   sudo systemctl start heygem-chatterbox-containers"
        echo "   sudo systemctl start heygem-chatterbox"
    fi
    
    print_summary
}

# Run main function
main "$@"
