#!/usr/bin/env bash
#
# install-kernel.sh - One-click kernel installation script
# Detects system type, lists available kernels, backs up current kernel, installs selected kernel
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="${SCRIPT_DIR}/kernel-build"
OUTPUT_DIR="${SCRIPT_DIR}/kernel-output"
BACKUP_DIR="${SCRIPT_DIR}/../kernel-backup-$(date +%Y%m%d-%H%M%S)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }
log_step()  { echo -e "
${CYAN}${BOLD}=== $1 ===${NC}"; }

# ============================================================
# 1. Detect system type
# ============================================================
detect_system() {
    log_step "检测系统信息"
    
    local distro=""
    local pkg_manager=""
    local initramfs_cmd=""
    local grub_cmd=""
    
    if [ -f /etc/os-release ]; then
        source /etc/os-release
        distro="${ID}"
        log_info "发行版: ${PRETTY_NAME:-$ID}"
    fi
    
    # Detect package manager and tools
    if command -v dpkg &>/dev/null && command -v apt-get &>/dev/null; then
        pkg_manager="debian"
        initramfs_cmd="update-initramfs"
        grub_cmd="update-grub"
        log_info "包管理器: dpkg/apt (Debian/Ubuntu)"
    elif command -v dnf &>/dev/null; then
        pkg_manager="fedora"
        initramfs_cmd="dracut"
        grub_cmd="grub2-mkconfig -o /boot/grub2/grub.cfg"
        log_info "包管理器: dnf (Fedora/RHEL)"
    elif command -v pacman &>/dev/null; then
        pkg_manager="arch"
        initramfs_cmd="mkinitcpio"
        grub_cmd="grub-mkconfig -o /boot/grub/grub.cfg"
        log_info "包管理器: pacman (Arch Linux)"
    elif command -v zypper &>/dev/null; then
        pkg_manager="suse"
        initramfs_cmd="mkinitrd"
        grub_cmd="grub2-mkconfig -o /boot/grub2/grub.cfg"
        log_info "包管理器: zypper (openSUSE)"
    else
        pkg_manager="unknown"
        initramfs_cmd=""
        grub_cmd=""
        log_warn "未知包管理器，将使用通用安装方式"
    fi
    
    # Detect boot loader
    if [ -d /boot/grub2 ]; then
        GRUB_DIR="/boot/grub2"
    elif [ -d /boot/grub ]; then
        GRUB_DIR="/boot/grub"
    else
        GRUB_DIR=""
    fi
    
    # Detect EFI
    if [ -d /sys/firmware/efi ]; then
        log_info "启动模式: UEFI"
        IS_EFI=true
    else
        log_info "启动模式: Legacy BIOS"
        IS_EFI=false
    fi
    
    # Export variables
    echo "$pkg_manager"
}

# ============================================================
# 2. Find available kernels in build directory
# ============================================================
find_kernels() {
    log_step "查找编译好的内核"
    
    local kernels=()
    local kernel_names=()
    local idx=0
    
    # Search for deb packages
    for deb in "$BUILD_DIR"/linux-image-*.deb; do
        [ -f "$deb" ] || continue
        local ver=$(basename "$deb" | sed 's/linux-image-//; s/_//; s/_.*//')
        kernels+=("deb:$deb")
        kernel_names+=("$deb (deb 包)")
        ((idx++))
    done
    
    # Search for compiled kernel source directories
    for src_dir in "$BUILD_DIR"/linux-*; do
        [ -d "$src_dir" ] || continue
        local dirname=$(basename "$src_dir")
        # Skip if it's a tarball
        [[ "$dirname" == *.tar.* ]] && continue
        
        # Check for bzImage or Image
        local arch_name=""
        for arch_dir in "$src_dir"/arch/*/boot; do
            if [ -f "$arch_dir/bzImage" ]; then
                arch_name="$arch_dir/bzImage"
                break
            elif [ -f "$arch_dir/Image" ]; then
                arch_name="$arch_dir/Image"
                break
            fi
        done
        
        if [ -n "$arch_name" ]; then
            local ver=$(echo "$dirname" | sed 's/linux-//')
            kernels+=("source:$src_dir")
            kernel_names+=("$dirname (源码目录)")
            ((idx++))
        fi
    done
    
    if [ ${#kernels[@]} -eq 0 ]; then
        log_error "未找到编译好的内核！"
        log_info "请先运行 build-kernel.py 编译内核"
        exit 1
    fi
    
    echo ""
    echo "找到以下编译好的内核："
    echo ""
    for i in "${!kernel_names[@]}"; do
        local num=$((i + 1))
        local size=""
        if [[ "${kernels[$i]}" == deb:* ]]; then
            size=$(du -h "${kernels[$i]#deb:}" | cut -f1)
        else
            size=$(du -sh "${kernels[$i]#source:}" | cut -f1)
        fi
        echo "  ${BOLD}${num}.${NC} ${kernel_names[$i]} (${size})"
    done
    echo ""
    
    # Let user select
    local choice=""
    while true; do
        read -rp "请选择要安装的内核 [1-${#kernels[@]}]: " choice
        if [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -ge 1 ] && [ "$choice" -le ${#kernels[@]} ]; then
            break
        fi
        log_error "无效选择，请输入 1-${#kernels[@]} 之间的数字"
    done
    
    SELECTED_KERNEL="${kernels[$((choice - 1))]}"
    log_info "已选择: ${kernel_names[$((choice - 1))]}"
}

# ============================================================
# 3. Backup current kernel
# ============================================================
backup_kernel() {
    log_step "备份当前内核"
    
    mkdir -p "$BACKUP_DIR"
    log_info "备份目录: $BACKUP_DIR"
    
    local current_kernel=$(uname -r)
    log_info "当前内核版本: $current_kernel"
    
    # Backup kernel image
    if [ -f "/boot/vmlinuz-$current_kernel" ]; then
        cp -v "/boot/vmlinuz-$current_kernel" "$BACKUP_DIR/"
    elif [ -f "/boot/vmlinuz-linux" ]; then
        cp -v "/boot/vmlinuz-linux" "$BACKUP_DIR/"
    fi
    
# Backup initramfs
    if [ -f "/boot/initrd.img-$current_kernel" ]; then
        cp -v "/boot/initrd.img-$current_kernel" "$BACKUP_DIR/"
    elif [ -f "/boot/initramfs-$current_kernel.img" ]; then
        cp -v "/boot/initramfs-$current_kernel.img" "$BACKUP_DIR/"
    fi
    
    # Backup System.map
    if [ -f "/boot/System.map-$current_kernel" ]; then
        cp -v "/boot/System.map-$current_kernel" "$BACKUP_DIR/"
    fi
    
    # Backup config
    if [ -f "/boot/config-$current_kernel" ]; then
        cp -v "/boot/config-$current_kernel" "$BACKUP_DIR/"
    fi
    
    # Backup modules
    if [ -d "/lib/modules/$current_kernel" ]; then
        log_info "备份内核模块..."
        cp -a "/lib/modules/$current_kernel" "$BACKUP_DIR/modules-$current_kernel"
    fi
    
    # Backup GRUB config
    if [ -f /boot/grub/grub.cfg ]; then
        cp -v /boot/grub/grub.cfg "$BACKUP_DIR/"
    elif [ -f /boot/grub2/grub.cfg ]; then
        cp -v /boot/grub2/grub.cfg "$BACKUP_DIR/"
    fi
    
    log_success "备份完成！备份保存在: $BACKUP_DIR"
}

# ============================================================
# 4. Install kernel (deb package)
# ============================================================
install_deb() {
    local deb_path="$1"
    log_step "安装 deb 包"
    
    log_info "安装 $deb_path ..."
    sudo dpkg -i "$deb_path" || {
        log_warn "dpkg 安装遇到问题，尝试修复依赖..."
        sudo apt-get install -f -y
    }
    
    # Also install headers if available
    local headers_deb="${deb_path/linux-image/linux-headers}"
    if [ -f "$headers_deb" ]; then
        log_info "安装头文件包..."
        sudo dpkg -i "$headers_deb" || sudo apt-get install -f -y
    fi
    
    log_success "deb 包安装完成"
}

# ============================================================
# 5. Install kernel (from source directory)
# ============================================================
install_from_source() {
    local src_dir="$1"
    log_step "从源码目录安装内核"
    
    cd "$src_dir"
    
    local kver=$(make kernelversion 2>/dev/null || echo "unknown")
    log_info "内核版本: $kver"
    
    # Install modules
    log_info "安装内核模块..."
    sudo make modules_install
    
    # Install kernel image
    log_info "安装内核镜像..."
    sudo make install
    
    log_success "源码安装完成"
}

# ============================================================
# 6. Post-installation
# ============================================================
post_install() {
    log_step "安装后配置"
    
    local pkg_manager="$1"
    
    # Update initramfs
    log_info "更新 initramfs..."
    case "$pkg_manager" in
        debian)
            sudo update-initramfs -u -k all
            ;;
        fedora)
            sudo dracut --regenerate-all --force
            ;;
        arch)
            sudo mkinitcpio -P
            ;;
        suse)
            sudo mkinitrd
            ;;
        *)
            log_warn "未知发行版，请手动更新 initramfs"
            ;;
    esac
    
    # Update GRUB
    log_info "更新 GRUB 配置..."
    if command -v update-grub &>/dev/null; then
        sudo update-grub
    elif command -v grub2-mkconfig &>/dev/null; then
        sudo grub2-mkconfig -o /boot/grub2/grub.cfg
    elif command -v grub-mkconfig &>/dev/null; then
        sudo grub-mkconfig -o /boot/grub/grub.cfg
    else
        log_warn "未找到 GRUB 更新命令，请手动更新"
    fi
    
    log_success "安装后配置完成"
}

# ============================================================
# 7. Verify installation
# ============================================================
verify_install() {
    log_step "验证安装"
    
    echo ""
    echo "已安装的内核："
    if command -v dpkg &>/dev/null; then
        dpkg -l | grep linux-image | grep -v meta | awk '{print "  " $2 " " $3}'
    fi
    
    echo ""
    echo "/boot 目录中的内核镜像："
    ls -lh /boot/vmlinuz-* 2>/dev/null | awk '{print "  " $9 " " $5}'
    
    echo ""
    log_info "当前运行内核: $(uname -r)"
    log_info "重启后将使用新内核"
}

# ============================================================
# Main
# ============================================================
main() {
    echo -e "${BOLD}╔══════════════════════════════════════════════════════════════╗"
    echo -e "║           Linux 内核一键安装脚本                             ║"
    echo -e "╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    # Check root
    if [ "$EUID" -ne 0 ]; then
        log_warn "需要 root 权限，将在安装步骤提示输入密码"
    fi
    
    # Step 1: Detect system
    local pkg_manager=$(detect_system)
    
    # Step 2: Find and select kernel
    find_kernels
    
    # Step 3: Confirm
    echo ""
    read -rp "确认安装此内核？[y/N]: " confirm
    if [[ ! "$confirm" =~ ^[Yy] ]]; then
        log_info "已取消安装"
        exit 0
    fi
    
    # Step 4: Backup
    echo ""
    read -rp "是否备份当前内核？[Y/n]: " backup_confirm
    if [[ ! "$backup_confirm" =~ ^[Nn] ]]; then
        backup_kernel
    fi
    
    # Step 5: Install
    if [[ "$SELECTED_KERNEL" == deb:* ]]; then
        install_deb "${SELECTED_KERNEL#deb:}"
    else
        install_from_source "${SELECTED_KERNEL#source:}"
    fi
    
    # Step 6: Post-install
    post_install "$pkg_manager"
    
    # Step 7: Verify
    verify_install
    
    echo ""
    log_success "内核安装完成！"
    log_info "请重启系统以使用新内核: sudo reboot"
    log_info "如果新内核有问题，可以从备份恢复: $BACKUP_DIR"
}

main "$@"
