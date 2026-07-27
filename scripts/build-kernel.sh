#!/usr/bin/env bash
#
# build-kernel.sh - Debian kernel efficient build script
#
# Usage: ./build-kernel.sh <arch> <distro> <branch> <kernel_version> <flavour>
#

set -euo pipefail

ARCH="${1:?Usage: $0 <arch> <distro> <branch> <kernel_version> <flavour>}"
DISTRO="${2:?Missing distro}"
BRANCH="${3:?Missing branch}"
KERNEL_VERSION="${4:?Missing kernel_version}"
FLAVOUR="${5:?Missing flavour}"

SRC_DIR="$(pwd)/linux-src"
ARTIFACT_DIR="$(pwd)/artifacts"
CCACHE_DIR="${CCACHE_DIR:-$HOME/.ccache}"
CCACHE_MAXSIZE="${CCACHE_MAXSIZE:-4G}"
CCACHE_COMPRESS="${CCACHE_COMPRESS:-1}"
NPROC="${NPROC:-$(nproc)}"

declare -A CROSS_COMPILE_MAP=(
  [arm64]="aarch64-linux-gnu-"
  [armhf]="arm-linux-gnueabihf-"
  [riscv64]="riscv64-linux-gnu-"
)

declare -A DEBIAN_BRANCH_MAP=(
  [stable]="bookworm"
  [testing]="trixie"
  [unstable]="sid"
  [experimental]="experimental"
)

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

install_dependencies() {
  log_info "Installing build dependencies..."
  sudo apt-get update -qq
  sudo apt-get install -y -qq \
    build-essential bc bison flex libssl-dev libelf-dev dwarves \
    ccache fakeroot devscripts debhelper git wget xz-utils kmod cpio rsync
  if [ "$ARCH" != "amd64" ]; then
    local gcc_pkg="gcc-${CROSS_COMPILE_MAP[$ARCH]%-}-linux-gnu"
    log_info "Installing cross-compilation toolchain: $gcc_pkg"
    sudo apt-get install -y -qq "$gcc_pkg"
  fi
}

setup_ccache() {
  log_info "Initializing ccache (max_size=${CCACHE_MAXSIZE}, compress=${CCACHE_COMPRESS})..."
  mkdir -p "$CCACHE_DIR"
  ccache --set-config=cache_dir="$CCACHE_DIR"
  ccache --set-config=max_size="$CCACHE_MAXSIZE"
  ccache --set-config=compression="$CCACHE_COMPRESS"
  ccache --set-config=base_dir="$(pwd)"
  ccache -z
  ccache -s
}

fetch_source() {
  local debian_branch="${DEBIAN_BRANCH_MAP[$BRANCH]:-$BRANCH}"
  log_info "Cloning Debian kernel source (branch: ${debian_branch})..."
  if [ -d "$SRC_DIR" ]; then
    log_warn "Source directory exists, skipping clone"
    return
  fi
  git clone --depth 1 --branch "$debian_branch" \
    https://salsa.debian.org/kernel/linux.git "$SRC_DIR"
  cd "$SRC_DIR"
  log_info "Source HEAD: $(git log --oneline -1)"
  log_info "Kernel version: $(make kernelversion 2>/dev/null || echo 'unknown')"
}

apply_liquorix() {
  if [ "$FLAVOUR" != "liquorix-amd64" ]; then return; fi
  log_info "Applying Liquorix patches..."
  cd "$SRC_DIR"
  git clone --depth 1 https://github.com/damentz/liquorix-package.git /tmp/liquorix
  local patch_file
  patch_file=$(find /tmp/liquorix -name "*${KERNEL_VERSION}*" -name "*.patch" | head -1)
  if [ -z "$patch_file" ]; then
    log_error "No Liquorix patch found for kernel ${KERNEL_VERSION}"
    find /tmp/liquorix -name "*.patch" | head -20
    exit 1
  fi
  log_info "Applying: $patch_file"
  git am "$patch_file" || { git am --3way "$patch_file"; }
}

configure_kernel() {
  log_info "Configuring kernel (arch=${ARCH}, flavour=${FLAVOUR})..."
  cd "$SRC_DIR"
  local cross_args=""
  [ "$ARCH" != "amd64" ] && cross_args="CROSS_COMPILE=${CROSS_COMPILE_MAP[$ARCH]}"
  make ARCH="$ARCH" $cross_args defconfig
  ./scripts/config --disable CONFIG_DEBUG_INFO
  ./scripts/config --enable CONFIG_DEBUG_INFO_NONE
  ./scripts/config --disable CONFIG_DEBUG_INFO_DWARF_TOOLCHAIN_DEFAULT
  ./scripts/config --disable CONFIG_DEBUG_INFO_DWARF4
  ./scripts/config --disable CONFIG_DEBUG_INFO_DWARF5
  ./scripts/config --disable CONFIG_KGDB
  ./scripts/config --disable CONFIG_DEBUG_KERNEL
  ./scripts/config --disable CONFIG_DEBUG_MISC
  ./scripts/config --set-val CONFIG_CC_OPTIMIZE_FOR_PERFORMANCE 1
  make ARCH="$ARCH" $cross_args olddefconfig
  log_info "Kernel configuration complete"
}

build_kernel() {
  log_info "Building kernel (${NPROC} parallel jobs)..."
  cd "$SRC_DIR"
  local cross_args=""
  local cc="ccache gcc"
  if [ "$ARCH" != "amd64" ]; then
    cross_args="CROSS_COMPILE=${CROSS_COMPILE_MAP[$ARCH]}"
    cc="ccache ${CROSS_COMPILE_MAP[$ARCH]}gcc"
  fi
  echo "=== ccache stats before build ==="
  ccache -s
  local start_time=$(date +%s)
  make -j"$NPROC" ARCH="$ARCH" $cross_args CC="$cc" \
    LOCALVERSION=-"$FLAVOUR" KDEB_PKGVERSION="${KERNEL_VERSION}-1" deb-pkg
  local end_time=$(date +%s)
  local elapsed=$((end_time - start_time))
  echo ""
  echo "=== ccache stats after build ==="
  ccache -s
  log_info "Build complete! Elapsed: $((elapsed / 60))m $((elapsed % 60))s"
}

collect_artifacts() {
  log_info "Collecting build artifacts..."
  mkdir -p "$ARTIFACT_DIR"
  cd "$SRC_DIR"
  find .. -maxdepth 1 -name "*.deb" -exec cp {} "$ARTIFACT_DIR"/ \;
  [ -f "arch/$ARCH/boot/bzImage" ] && cp "arch/$ARCH/boot/bzImage" "$ARTIFACT_DIR"/
  [ -f "arch/$ARCH/boot/Image" ] && cp "arch/$ARCH/boot/Image" "$ARTIFACT_DIR"/
  if [ -f vmlinux ]; then
    xz -z -k -T0 vmlinux
    cp vmlinux.xz "$ARTIFACT_DIR"/
  fi
  cp .config "$ARTIFACT_DIR/config-${KERNEL_VERSION}-${FLAVOUR}"
  local cross_args=""
  [ "$ARCH" != "amd64" ] && cross_args="CROSS_COMPILE=${CROSS_COMPILE_MAP[$ARCH]}"
  make ARCH="$ARCH" $cross_args INSTALL_MOD_PATH="$ARTIFACT_DIR/modules" modules_install
  pushd "$ARTIFACT_DIR/modules" > /dev/null
  tar cJf "../modules-${KERNEL_VERSION}-${FLAVOUR}-${ARCH}.tar.xz" .
  popd > /dev/null
  rm -rf "$ARTIFACT_DIR/modules"
  echo ""
  echo "=== Artifacts ==="
  ls -lh "$ARTIFACT_DIR"/
  log_info "Artifacts saved to: $ARTIFACT_DIR"
}

main() {
  echo "========================================"
  echo "  Debian Kernel Build"
  echo "========================================"
  echo "  Arch:       $ARCH"
  echo "  Distro:     $DISTRO"
  echo "  Branch:     $BRANCH"
  echo "  Kernel:     $KERNEL_VERSION"
  echo "  Flavour:    $FLAVOUR"
  echo "  Jobs:       $NPROC"
  echo "========================================"
  echo ""
  install_dependencies
  setup_ccache
  fetch_source
  apply_liquorix
  configure_kernel
  build_kernel
  collect_artifacts
  log_info "All done!"
}

main "$@"
