# Linux Kernel GitHub Action

自动编译 Debian、Ubuntu 和 Arch Linux 目标内核的 GitHub Actions 工作流。同时支持构建带桌面环境的 Live ISO 可安装镜像。

## 工作流结构

### 内核构建工作流

每个发行版有独立的工作流文件，确保版本选择精准匹配：

| 工作流 | 文件 | 说明 |
|--------|------|------|
| Build Kernel (Debian) | `.github/workflows/build-kernel-debian.yml` | Debian bookworm / trixie |
| Build Kernel (Ubuntu) | `.github/workflows/build-kernel-ubuntu.yml` | Ubuntu jammy / noble / oracular / plucky |
| Build Kernel (Arch) | `.github/workflows/build-kernel-arch.yml` | Arch Linux rolling |

### Live ISO 构建工作流

构建带 XFCE 桌面环境和 Calamares 安装器的可启动 Live ISO 镜像：

| 工作流 | 文件 | 说明 |
|--------|------|------|
| Build Live ISO (Debian) | `.github/workflows/build-live-debian.yml` | Debian bookworm / trixie, amd64 |
| Build Live ISO (Ubuntu) | `.github/workflows/build-live-ubuntu.yml` | Ubuntu jammy / noble / oracular / plucky, amd64 |
| Build Live ISO (Arch) | `.github/workflows/build-live-arch.yml` | Arch Linux rolling, amd64 |

**Live ISO 特性：**
- XFCE 桌面环境
- Calamares 图形安装器（U 盘启动后一键安装到硬盘）
- 自定义内核（使用与内核构建工作流相同的源码编译）
- 基础工具集（vim, git, curl, network-manager 等）
- 固件包（支持常见无线网卡和显卡）

## 使用方法

1. 进入 GitHub 仓库的 **Actions** 标签页。
2. 选择目标工作流。
3. 点击 **Run workflow**。
4. 按顺序选择架构、发布线、内核版本和 flavour。
5. 构建完成后，在该次运行页面的 **Artifacts** 区域下载产物。
## 本地一键编译脚本

除了使用 GitHub Actions，本项目还提供了一个跨平台的本地编译脚本 `scripts/build-kernel.py`。

### 功能特性

- **跨平台支持**: Linux / Windows / macOS
- **自动检测系统**: 自动识别当前操作系统和发行版
- **交互式操作**: 中文交互界面，引导式操作
- **灵活选择**: 内核版本、编译选项、调度器、架构均可选
- **完整性验证**: 编译后可验证内核符号一致性
- **一键安装**: 编译完成后可直接安装内核

### 使用方法

```bash
# Linux 系统
python3 scripts/build-kernel.py

# Windows 系统 (在 WSL 中运行)
wsl python3 scripts/build-kernel.py

# macOS 系统 (通过 SSH 远程编译)
python3 scripts/build-kernel.py
```

### 脚本交互选项

脚本启动后自动检测操作系统和发行版，然后依次提示：

1. **内核版本**（根据检测到的发行版显示对应选项）
2. **编译选项**: 标准编译 / 快速编译 / 最小化编译 / 完整调试编译
3. **内核调度器**: CFS / PREEMPT_VOLUNTARY / PREEMPT / PREEMPT_RT / NONE
4. **目标架构**: amd64 / arm64 / armhf / riscv64
5. **交叉编译**: 自动检测是否需要交叉编译，用户确认
6. **编译后安装**: 是 / 否
7. **完整性验证**: 是 / 否

### 各发行版支持的内核版本

| 发行版 | 可选内核版本 |
|--------|-------------|
| Debian | 6.1, 6.6, 6.12, 6.18 |
| Ubuntu | 5.15, 6.2, 6.5, 6.8, 6.18, 7.0, 7.1 |
| Arch Linux | 6.12, 6.18, 7.0, 7.1 |

> 脚本会根据当前系统自动筛选可选版本，例如在 Debian 上不会显示 7.x 选项。


### 一键执行

根据你的操作系统选择对应的命令：

**Linux (Debian/Ubuntu/Arch):**

```bash
curl -fsSL https://raw.githubusercontent.com/poying2018/kernel-/main/scripts/build-kernel.py -o /tmp/build-kernel.py && python3 /tmp/build-kernel.py
```

或使用 `wget`：

```bash
wget -qO /tmp/build-kernel.py https://raw.githubusercontent.com/poying2018/kernel-/main/scripts/build-kernel.py && python3 /tmp/build-kernel.py
```

**Windows (PowerShell):**

```powershell
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/poying2018/kernel-/main/scripts/build-kernel.py" -OutFile "$env:TEMP\build-kernel.py"; python "$env:TEMP\build-kernel.py"
```

或使用 WSL（推荐，可直接在 Windows 上编译 Linux 内核）：

```powershell
wsl bash -c "curl -fsSL https://raw.githubusercontent.com/poying2018/kernel-/main/scripts/build-kernel.py -o /tmp/build-kernel.py && python3 /tmp/build-kernel.py"
```

**macOS (Terminal):**

```bash
curl -fsSL https://raw.githubusercontent.com/poying2018/kernel-/main/scripts/build-kernel.py -o /tmp/build-kernel.py && python3 /tmp/build-kernel.py
```

> **提示**: 运行脚本需要 root 权限（用于安装内核包），脚本会在需要时提示输入密码。

### 系统要求

- **磁盘空间**: 至少 **10GB** 可用空间（源码 ~3GB + 编译产物 ~5GB + 余量）
- **内存**: 建议 2GB 以上
- **网络**: 能够访问 kernel.org 或国内镜像

如果磁盘空间不足，脚本会自动检测并提示清理方法。

### 国内网络加速

脚本会自动检测网络环境并智能选择下载源：
- **海外网络**: 直接从 kernel.org 官方源克隆源码
- **国内网络**: 自动使用清华/USTC/阿里云镜像加速

**智能下载策略**：
- **国内网络**: 优先 tarball 下载（更稳定，支持断点续传），Git 作为备选
- **海外网络**: 优先 git clone（更快），tarball 作为备选
- **自动回退**: Git 镜像 → Git 官方源 → tarball 镜像 → tarball 官方源
- **稳定性优化**: 自动配置 Git HTTP/1.1、增大超时、SSL 容错
- **进度显示**: tarball 下载显示实时进度百分比

检测方式：脚本连接 kernel.org 测量延迟，<2s 判定为海外，≥2s 或超时判定为国内。

### 一键安装脚本

编译完成后，可以使用 `scripts/install-kernel.sh` 一键安装内核。脚本会自动检测系统类型、列出可用内核、备份原内核、安装新内核并更新引导。

**一键执行：**
```bash
curl -fsSL https://raw.githubusercontent.com/poying2018/kernel-/main/scripts/install-kernel.sh -o /tmp/install-kernel.sh && sudo bash /tmp/install-kernel.sh
```

**或手动执行：**
```bash
chmod +x scripts/install-kernel.sh
sudo ./scripts/install-kernel.sh
```

**脚本工作流程：**
1. **自动检测系统** — 识别 Debian/Ubuntu/Fedora/RHEL/Arch/openSUSE
2. **列出可用内核** — 从 `kernel-build/` 目录中查找已编译好的内核（支持 deb 包和源码目录）
3. **选择内核** — 用户交互式选择要安装的内核
4. **备份原内核** — 自动备份当前内核镜像、模块、initramfs、GRUB 配置到 `kernel-backup-时间戳/` 目录
5. **安装内核** — 根据系统类型自动选择安装方式（deb 包或 make install）
6. **更新引导** — 自动更新 initramfs 和 GRUB 配置
7. **验证安装** — 显示已安装的内核列表

**备份内容：**
- 内核镜像（`vmlinuz-*`）
- initramfs（`initrd.img-*` 或 `initramfs-*.img`）
- System.map
- 内核配置
- 内核模块（`/lib/modules/<版本>`）
- GRUB 配置

**恢复备份：**
```bash
# 如果新内核有问题，可以从备份恢复
sudo cp kernel-backup-*/vmlinuz-* /boot/
sudo cp kernel-backup-*/initrd.img-* /boot/  # 或 initramfs-*.img
sudo cp -a kernel-backup-*/modules-* /lib/modules/
sudo update-grub
sudo reboot
```

### 手动安装方法

如果一键脚本无法使用，也可以手动安装：

#### 方式一：deb 包安装（Debian/Ubuntu）

```bash
# 安装 deb 包
sudo dpkg -i kernel-build/linux-*/linux-image-*.deb

# 修复依赖
sudo apt-get install -f

# 更新引导
sudo update-grub
sudo reboot
```

#### 方式二：源码目录安装（通用）

```bash
cd kernel-build/linux-*

# 安装模块
sudo make modules_install

# 安装内核镜像
sudo make install

# 更新 initramfs（根据发行版选择）
# Debian/Ubuntu:
sudo update-initramfs -c -k $(make kernelversion)
# Fedora/RHEL:
sudo dracut --force --kver $(make kernelversion)
# Arch:
sudo mkinitcpio -P

# 更新 GRUB
sudo update-grub  # 或 grub2-mkconfig -o /boot/grub2/grub.cfg

# 重启
sudo reboot
```

#### 方式三：手动复制（不推荐）

```bash
cd kernel-build/linux-*
KVERSION=$(make kernelversion)

# 安装模块
sudo make modules_install

# 复制内核镜像
sudo cp arch/x86_64/boot/bzImage /boot/vmlinuz-custom-$KVERSION

# 复制配置
sudo cp .config /boot/config-custom-$KVERSION

# 更新 initramfs 和 GRUB（同上）
```

### 各平台说明

| 平台 | 说明 |
|------|------|
| Linux | 直接在本地编译，支持 Debian/Ubuntu/Arch |
| Windows | 通过 WSL 或 SSH 远程编译 |
| macOS | 通过 SSH 连接到远程 Linux 服务器编译 |



## 选择项详解

### 1. 架构（Architecture）— 第一个选择

所有工作流都支持：
- `amd64` — x86_64
- `arm64` — ARM 64-bit
- `armhf` — ARM 32-bit hard-float（Debian）
- `riscv64` — RISC-V 64-bit（Debian）

> **注意**：Live ISO 工作流目前仅支持 amd64 架构。

### 2. 发行版发布线（Release Line）

**Debian:**
| 发布线 | 默认内核 | 可用内核版本 |
|--------|----------|-------------|
| bookworm | 6.1 | distro-default, 6.1, 6.12, 6.18 |
| trixie | 6.12 | distro-default, 6.1, 6.12, 6.18 |

> **注意**：Debian 官方仅提供 6.x 系列内核。`distro-default` 使用 Debian 官方内核源码，其他版本从 kernel.org 上游源码编译。

**Ubuntu:**
| 发布线 | 默认内核 | 可用内核版本 |
|--------|----------|-------------|
| jammy | 5.15 | distro-default, 5.15, 6.2, 6.5, 6.8, 6.18, 7.0, 7.1 |
| noble | 6.8 | distro-default, 5.15, 6.2, 6.5, 6.8, 6.18, 7.0, 7.1 |
| oracular | 6.8 | distro-default, 5.15, 6.2, 6.5, 6.8, 6.18, 7.0, 7.1 |
| plucky | 6.8 | distro-default, 5.15, 6.2, 6.5, 6.8, 6.18, 7.0, 7.1 |

**Arch:**
| 发布线 | 默认内核 | 可用内核版本 |
|--------|----------|-------------|
| rolling | 7.1 (最新) | distro-default, 6.12, 6.18, 7.0, 7.1 |

### 3. 内核版本说明

- `distro-default` — 使用该发行版默认的内核版本
- 其他选项 — 从 kernel.org 官方稳定分支获取对应版本
- 所有列出的版本均经过验证，存在于 kernel.org 或发行版官方仓库

### 4. Flavour（内核插件/变体）

| Flavour | 说明 | 适用架构 |
|---------|------|----------|
| `amd64` | 标准 x86_64 内核 | amd64 |
| `amd64-cloud` | 云优化（禁用图形、声音、无线等） | amd64 |
| `arm64` | 标准 ARM64 内核 | arm64 |
| `arm64-cloud` | ARM64 云优化 | arm64 |
| `rt-amd64` | 实时内核（PREEMPT_RT） | amd64 |
| `liquorix-amd64` | Liquorix 低延迟内核 | amd64 |
| `zen-amd64` | Zen 交互内核（仅 Arch） | amd64 |

## 安装内核

构建完成后，在 Actions 运行页面的 **Artifacts** 区域下载产物包。

### Debian / Ubuntu

产物包含 `.deb` 包，可直接用 `dpkg` 安装：

```bash
# 下载产物并解压
unzip kernel-ubuntu-jammy-5.15-amd64-amd64.zip -d kernel-artifacts
cd kernel-artifacts

# 安装内核包
sudo dpkg -i linux-image-*.deb

# 如果依赖有问题，运行：
sudo apt-get install -f
```

安装后重启系统以使用新内核：

```bash
sudo reboot
```

查看已安装的内核：

```bash
dpkg -l | grep linux-image
```

如果需要删除旧内核：

```bash
sudo apt-get purge linux-image-<版本号>
```

### Arch Linux

产物包含内核模块包 `modules-*.tar.xz` 和内核镜像 `bzImage`：

```bash
# 解压产物
tar xzf kernel-arch-rolling-distro-default-amd64-amd64.zip -d kernel-artifacts
cd kernel-artifacts

# 安装内核模块到系统
sudo tar xJf modules-*.tar.xz -C /

# 复制内核镜像到 /boot
sudo cp bzImage /boot/vmlinuz-linux-custom

# 更新 initramfs（根据使用的引导加载器选择）
# 对于 mkinitcpio：
sudo mkinitcpio -P

# 更新引导加载器配置（GRUB 示例）
grub-mkconfig -o /boot/grub/grub.cfg
```

### 多架构交叉编译

对于 `arm64`、`armhf`、`riscv64` 等非 x86 架构，编译在 x86_64 运行器上通过交叉编译器完成。产物需要复制到目标架构设备上安装：

```bash
# 在目标设备上
sudo dpkg -i linux-image-*.deb   # Debian/Ubuntu
```

## 源码来源

所有源码均来自已公开、可验证的官方项目：

- **Debian**：kernel.org 稳定上游源码（Debian Bookworm 基于 6.1，Trixie 基于 6.12）
- **Ubuntu**：Ubuntu Kernel Team 官方 Launchpad 仓库，使用精确的 Ubuntu 标签
- **Arch Linux**：kernel.org 稳定上游源码（distro-default 解析 Arch PKGBUILD 获取当前版本）
- **RT 补丁**：kernel.org 官方 RT 镜像
- **Liquorix**：公开的 Liquorix 项目仓库
- **Zen**：zen-kernel/zen-kernel 官方仓库

## 自动同步与监控

工作流 `.github/workflows/sync-kernel-versions.yml` 每天自动（UTC 06:00）执行全面监控：

### 监测内容

1. **新内核版本检测** — 发现 kernel.org 新稳定版本时自动记录
2. **源码变动检测** — 跟踪所有源码的 commit SHA，检测是否有变更（标签更新、分支移动等）
3. **旧内核支持状态** — 通过 kernel.org releases.json API 监测各版本的支持状态：
   - 🟢 **Active** — 仍在维护，接收安全更新
   - 🔴 **EOL** — 已结束生命周期

### 监测源

| 来源 | 监测内容 | 频率 |
|------|----------|------|
| kernel.org | 6.1, 6.6, 6.12, 6.18, 7.0, 7.1 稳定版本的标签 SHA | 每日 |
| Ubuntu Launchpad | jammy/noble/oracular/plucky 各版本内核标签 SHA | 每日 |
| Arch Linux GitLab | PKGBUILD pkgver 及对应 kernel.org 标签 SHA | 每日 |
| Debian | bookworm/trixie 对应 kernel.org 标签 SHA | 每日 |

### 输出

- `kernel-status.json` — 所有跟踪源及其 commit SHA 和支持状态
- 工作流会自动推送检测到的变更
- 可以在 Actions → Sync Kernel Versions 中查看每次运行的详细报告

### 手动触发

Actions → Sync Kernel Versions → Run workflow

## 编译优化

- **ccache** 缓存重复编译结果，大幅提升重复构建速度
- **make -j$(nproc)** 使用运行器全部 CPU 核心并行编译
- **浅克隆** `--depth 1` 减少源码下载时间
- **禁用调试信息** 减少编译时间和产物体积
- **禁用 fatal warning** 避免旧发行版源码在新 GCC 上因兼容性警告中断
- **bindeb-pkg** 直接构建二进制包

## 输出产物

- `linux-image-*.deb` — 内核 Debian 包
- `linux-headers-*.deb` — 内核头文件包
- `linux-libc-dev_*.deb` — libc 开发包
- `bzImage` / `Image` — 内核启动镜像
- `vmlinux.xz` — 压缩内核 ELF 文件
- `modules-*.tar.xz` — 内核模块
- `config-*` — 最终内核配置

## 已验证构建矩阵

| 发行版 | 发布线 | 内核版本 | 架构 | 状态 |
|--------|--------|----------|------|------|
| Debian | bookworm | 6.1 | amd64 | ✅ |
| Debian | trixie | 6.12 | amd64 | ✅ |
| Ubuntu | jammy | 5.15 | amd64 | ✅ |
| Ubuntu | jammy | 6.2 | amd64 | ✅ |
| Ubuntu | jammy | 6.5 | amd64 | ✅ |
| Ubuntu | jammy | 6.8 | amd64 | ✅ |
| Ubuntu | noble | 6.8 | amd64 | ✅ |
| Ubuntu | oracular | 6.8 | amd64 | ✅ |
| Ubuntu | plucky | 6.8 | amd64 | ✅ |
| Ubuntu | plucky | 7.0 | amd64 | ✅ |
| Arch | rolling | distro-default | amd64 | ✅ |
| Debian | trixie | 6.12 (cloud) | amd64 | ✅ |