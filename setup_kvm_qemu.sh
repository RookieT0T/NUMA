#!/bin/bash

# KVM/QEMU Setup and Verification Script
# This script installs QEMU, sets up KVM, and verifies the installation

set -e  # Exit on error

echo "=========================================="
echo "KVM/QEMU Setup and Verification Script"
echo "=========================================="
echo ""

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print success message
success() {
    echo -e "${GREEN}✓${NC} $1"
}

# Function to print error message
error() {
    echo -e "${RED}✗${NC} $1"
}

# Function to print warning message
warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check if running as root for apt commands
if [ "$EUID" -ne 0 ]; then 
    echo "This script needs sudo privileges for package installation."
    echo "Please run with: sudo bash $0"
    echo "Or the script will use sudo for individual commands."
    echo ""
fi

# Step 1: Update package lists
echo "Step 1: Updating package lists..."
sudo apt update
success "Package lists updated"
echo ""

# Step 2: Install QEMU and related packages
echo "Step 2: Installing QEMU and related packages..."
sudo apt install -y \
    qemu-system-x86 \
    qemu-utils \
    qemu-system-common \
    qemu-system-data \
    cpu-checker \
    bridge-utils \
    virt-manager \
    libvirt-daemon-system \
    libvirt-clients
success "QEMU packages installed"
echo ""

# Step 3: Check KVM kernel modules
echo "Step 3: Checking KVM kernel modules..."
if lsmod | grep -q kvm; then
    success "KVM modules are loaded"
    lsmod | grep kvm
else
    error "KVM modules are NOT loaded"
    warning "Trying to load KVM modules..."
    sudo modprobe kvm
    if [ -f /proc/cpuinfo ] && grep -q "Intel" /proc/cpuinfo; then
        sudo modprobe kvm_intel
    elif [ -f /proc/cpuinfo ] && grep -q "AMD" /proc/cpuinfo; then
        sudo modprobe kvm_amd
    fi
fi
echo ""

# Step 4: Check CPU virtualization support
echo "Step 4: Checking CPU virtualization support..."
if grep -E '(vmx|svm)' /proc/cpuinfo > /dev/null; then
    success "CPU supports hardware virtualization"
    if grep -q vmx /proc/cpuinfo; then
        echo "  CPU: Intel VT-x (vmx)"
    elif grep -q svm /proc/cpuinfo; then
        echo "  CPU: AMD-V (svm)"
    fi
else
    error "CPU does NOT support hardware virtualization"
    warning "KVM will not work without CPU virtualization support"
fi
echo ""

# Step 5: Check /dev/kvm
echo "Step 5: Checking /dev/kvm device..."
if [ -e /dev/kvm ]; then
    success "/dev/kvm exists"
    ls -l /dev/kvm
else
    error "/dev/kvm does NOT exist"
    warning "KVM acceleration will not be available"
fi
echo ""

# Step 6: Add current user to kvm and libvirt groups
echo "Step 6: Adding user to kvm and libvirt groups..."
CURRENT_USER=${SUDO_USER:-$USER}
sudo usermod -aG kvm $CURRENT_USER
sudo usermod -aG libvirt $CURRENT_USER
success "User $CURRENT_USER added to kvm and libvirt groups"
warning "You need to log out and log back in for group changes to take effect"
warning "Or run: newgrp kvm"
echo ""

# Step 7: Verify QEMU installation
echo "Step 7: Verifying QEMU installation..."
if command -v qemu-system-x86_64 &> /dev/null; then
    success "qemu-system-x86_64 is installed"
    qemu-system-x86_64 --version | head -1
else
    error "qemu-system-x86_64 is NOT installed"
fi
echo ""

# Step 8: Check available accelerators
echo "Step 8: Checking available accelerators..."
if command -v qemu-system-x86_64 &> /dev/null; then
    echo "Available accelerators:"
    qemu-system-x86_64 -accel help
    if qemu-system-x86_64 -accel help 2>&1 | grep -q kvm; then
        success "KVM acceleration is available"
    else
        warning "KVM acceleration is NOT available"
    fi
fi
echo ""

# Step 9: Run kvm-ok
echo "Step 9: Running kvm-ok diagnostic..."
if command -v kvm-ok &> /dev/null; then
    kvm-ok
else
    warning "kvm-ok is not installed"
fi
echo ""

# Step 10: Check libvirt service
echo "Step 10: Checking libvirt service..."
if systemctl is-active --quiet libvirtd; then
    success "libvirtd service is running"
else
    warning "libvirtd service is not running"
    echo "Starting libvirtd..."
    sudo systemctl start libvirtd
    sudo systemctl enable libvirtd
    success "libvirtd service started and enabled"
fi
echo ""

# Summary
echo "=========================================="
echo "Setup Summary"
echo "=========================================="
echo ""
echo "Installed packages:"
echo "  - qemu-system-x86 (with KVM support)"
echo "  - qemu-utils"
echo "  - cpu-checker"
echo "  - libvirt (virtualization management)"
echo ""
echo "User configuration:"
echo "  - User '$CURRENT_USER' added to 'kvm' group"
echo "  - User '$CURRENT_USER' added to 'libvirt' group"
echo ""
echo "Next steps:"
echo "  1. Log out and log back in (or run: newgrp kvm)"
echo "  2. Verify groups with: groups"
echo "  3. Test KVM with: qemu-system-x86_64 -enable-kvm -m 512 -nographic"
echo ""
echo "Example QEMU commands:"
echo ""
echo "# Create a disk image:"
echo "  qemu-img create -f qcow2 mydisk.qcow2 20G"
echo ""
echo "# Run VM with KVM acceleration:"
echo "  qemu-system-x86_64 -enable-kvm -m 2G -smp 2 -hda mydisk.qcow2"
echo ""
echo "# Share a directory with 9p virtfs:"
echo "  qemu-system-x86_64 -enable-kvm -m 2G \\"
echo "    -virtfs local,path=/host/path,mount_tag=shared,security_model=passthrough"
echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="

# Install virtme-ng
sudo apt install python3-pip
pip install virtme-ng
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Install linux
sudo apt-get update
sudo apt-get install flex bison
sudo apt-get install libelf-dev
sudo apt-get install -y libnuma-dev
sudo apt-get install linux-tools-common linux-tools-generic linux-tools-$(uname -r)
sudo sysctl kernel.perf_event_paranoid=1
git clone git://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git
echo "linux/" > .gitignore
cd linux
vng --build --commit v6.2-rc4

# Install numa controls && libraries for NPB
sudo apt-get install -y numactl
sudo apt-get install gfortran

cat >> .gitignore << 'EOF'
.bash_history
.bash_logout
.bashrc
.cache/
.dotnet/
.forward
.local/
.profile
.ssh/
.vscode-server/
.wget-hsts
EOF