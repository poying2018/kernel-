# Debian Linux Kernel GitHub Action

自动编译 Debian Linux 内核的 GitHub Actions 工作流。

## 功能特性

- 支持多种架构：amd64、arm64、armhf、riscv64
- 支持多个 Debian 发行版：buster、bullseye、bookworm、trixie
- 支持多个 Debian 分支：stable、testing、unstable、experimental
- 支持多种内核版本：5.10、6.1、6.6、6.12
- 支持多种内核 flavour：amd64、amd64-cloud、arm64、arm64-cloud、rt-amd64、liquorix-amd64
- 高效编译：ccache + 并行编译 + 禁用调试信息
- 自动上传到 GitHub Actions Artifact

## 使用方法

1. 进入 GitHub 仓库的 **Actions** 标签页
2. 选择 **Build Debian Linux Kernel** 工作流
3. 点击 **Run workflow**
4. 填写以下参数：

| 参数 | 说明 | 可选值 |
|------|------|--------|
| **Architecture** | 目标架构 | amd64, arm64, armhf, riscv64 |
| **Distribution** | Debian 发行版本 | buster, bullseye, bookworm, trixie |
| **Branch** | Debian 发布分支 | stable, testing, unstable, experimental |
| **Kernel Version** | 内核版本 | 5.10, 6.1, 6.6, 6.12 |
| **Flavour** | 内核插件/Flavour | amd64, amd64-cloud, arm64, arm64-cloud, rt-amd64, liquorix-amd64 |

5. 点击 **Run workflow** 开始编译

## 编译优化

- **ccache**：缓存编译结果，加速重复编译
- **并行编译**：使用 `make -j$(nproc)` 充分利用 CPU 核心
- **禁用调试信息**：`CONFIG_DEBUG_INFO_NONE=y` 大幅减少编译时间
- **浅克隆**：`git clone --depth 1` 减少源码下载时间
- **缓存持久化**：通过 `actions/cache` 在多次运行间保持 ccache

## 输出产物

编译完成后，在该次 GitHub Actions 运行页面的 Artifacts 区域下载，包含：

- `*.deb` — Debian 内核安装包
- `bzImage` / `Image` — 内核启动镜像
- `vmlinux.xz` — 压缩的内核 ELF 文件（用于调试）
- `modules-*.tar.xz` — 内核模块压缩包
- `config-*` — 内核配置文件

## 源码来源

所有源码均来自官方开源项目：

- **Linux 内核源码**：https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux
- **Liquorix 内核补丁**：https://github.com/damentz/liquorix-package
- **RT 内核补丁**：https://mirrors.edge.kernel.org/pub/linux/kernel/projects/rt/

## 本地构建

```bash
chmod +x scripts/build-kernel.sh
./scripts/build-kernel.sh amd64 bookworm stable 6.1 amd64
```

## 构建说明

`kernel_version` 用于选择 Linux 官方稳定源码标签；`distro` 和 `branch` 会写入构建参数与 Artifact 名称，便于区分目标 Debian 发布版本和分支。所有源码均从 Linux 官方源码库、kernel.org RT 镜像或公开的 Liquorix 项目获取。
