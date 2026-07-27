# Linux Kernel GitHub Action

自动编译 Debian、Ubuntu 和 Arch Linux 目标内核的 GitHub Actions 工作流。

## 支持的选择

- 架构必须首先选择：amd64、arm64、armhf、riscv64
- 发行版：Debian、Ubuntu、Arch Linux
- 发布线：Debian Bookworm、Debian Trixie、Ubuntu Jammy、Ubuntu Noble、Arch Rolling
- 分支：stable、testing、unstable、experimental、main、rolling
- 内核版本：distro-default、5.10、6.1、6.6、6.8、6.12
- 内核 flavour：amd64、amd64-cloud、arm64、arm64-cloud、rt-amd64、liquorix-amd64

## 使用方法

1. 进入 GitHub 仓库的 **Actions** 标签页。
2. 选择 **Build Linux Kernel (Debian, Ubuntu, Arch Linux)**。
3. 点击 **Run workflow**。
4. 按顺序选择架构、发行版、发布线、分支、内核版本和 flavour。
5. 构建完成后，在该次运行页面的 **Artifacts** 区域下载产物。

发行版与发布线必须匹配，例如 `debian` 配 `debian-bookworm`，`ubuntu` 配 `ubuntu-noble`，`archlinux` 配 `arch-rolling`。工作流会在源码步骤中校验不匹配组合并立即给出明确错误。

## 源码来源

所有源码均来自已公开、可验证的官方项目：

- Debian：Debian Kernel Team 的 Salsa 仓库，使用 `debian/6.1/bookworm` 或 `debian/6.12/trixie`。
- Ubuntu：Ubuntu Kernel Team 的 Launchpad 仓库，使用 Jammy 或 Noble 的 `master`/官方 Ubuntu 标签。
- Arch Linux：Arch Linux 官方 GitLab packaging 仓库读取默认 `pkgver`，再从 Linux 官方 kernel.org 稳定源码获取对应版本。
- RT：kernel.org 官方 RT 镜像。
- Liquorix：公开的 Liquorix 项目仓库。

## 编译优化

- ccache 缓存重复编译结果。
- `make -j$(nproc)` 使用运行器全部 CPU 核心。
- 浅克隆减少源码下载时间。
- 禁用调试信息以减少编译时间和产物体积。
- 对格式警告关闭 fatal warning，避免旧发行版源码在新 GCC 上因兼容性警告中断。

## 输出产物

- `*.deb`：统一的内核 Debian 构建包。
- `bzImage` / `Image`：内核启动镜像。
- `vmlinux.xz`：压缩内核 ELF 文件。
- `modules-*.tar.xz`：内核模块。
- `config-*`：最终内核配置。

## 本地脚本

```bash
chmod +x scripts/build-kernel.sh
./scripts/build-kernel.sh amd64 bookworm stable 6.1 amd64
```

本地脚本仍用于原有 Debian/上游 Linux 构建流程；GitHub Actions 工作流提供完整的发行版源码选择。
