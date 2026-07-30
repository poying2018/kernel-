#################
# archiso profile for Arch Linux Live ISO with XFCE + Calamares
#################

bootmodes=('bios.syslinux' 'uefi.grub')
iso_name="arch-live"
iso_label="ARCH_LIVE_$(date +%Y%m)"
iso_publisher="kernel- builder <https://github.com/poying2018/kernel->"
iso_application="Arch Linux Live CD"
iso_version="$(date +%Y.%m.%d)"
install_dir="arch"
pacman_conf="pacman.conf"
airootfs_image_type="squashfs"
airootfs_image_tool_options=('-comp' 'xz' '-Xbcj' 'x86' '-b' '1M' '-Xdict-size' '1M')
file_permissions=(
  ["/etc/shadow"]="0:0:400"
  ["/root"]="0:0:750"
)
