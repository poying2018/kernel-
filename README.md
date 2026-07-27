# Debian Linux Kernel - GitHub Action Auto Build

[![Build Debian Linux Kernel](https://github.com/poying2018/debian-linux-github-action/actions/workflows/build-kernel.yml/badge.svg)](https://github.com/poying2018/debian-linux-github-action/actions/workflows/build-kernel.yml)

Automated Debian Linux kernel compilation via GitHub Actions with dropdown parameter selection.

## Features

- **One-click build** via GitHub Actions `workflow_dispatch`
- **5 dropdown parameters**: Architecture, Distribution, Branch, Kernel Version, Flavour
- **High-efficiency compilation** with ccache, parallel jobs, and debug info disabled
- **Auto-release** to GitHub Release with all build artifacts
- **All sources from official/open-source repos** (salsa.debian.org, github.com, git.kernel.org)

## Parameters

| # | Parameter | Options |
|---|-----------|---------|
| 1 | **Architecture** | `amd64`, `arm64`, `armhf`, `riscv64` |
| 2 | **Distribution** | `buster` (10), `bullseye` (11), `bookworm` (12), `trixie` (13) |
| 3 | **Branch** | `stable`, `testing`, `unstable` (sid), `experimental` |
| 4 | **Kernel Version** | `5.10`, `6.1`, `6.6`, `6.12` |
| 5 | **Flavour** | `amd64`, `amd64-cloud`, `arm64`, `arm64-cloud`, `rt-amd64`, `liquorix-amd64` |

## How to Use

### GitHub Actions (Cloud)

1. Go to **Actions** tab in your repository
2. Select **"Build Debian Linux Kernel"** workflow
3. Click **"Run workflow"**
4. Fill in the 5 dropdown parameters
5. Click **"Run workflow"** to start

Build time: ~30-60 minutes (first run), ~5-10 minutes (with ccache)

### Self-Hosted Runner

For faster builds or cross-compilation, use your own Linux machine:

#### 1. Register a Self-Hosted Runner

```bash
# On your Linux machine
mkdir actions-runner && cd actions-runner
curl -o actions-runner-linux-x64-2.319.0.tar.gz -L https://github.com/actions/runner/releases/download/v2.319.0/actions-runner-linux-x64-2.319.0.tar.gz
tar xzf actions-runner-linux-x64-2.319.0.tar.gz
./config.sh --url https://github.com/poying2018/debian-linux-github-action --token <YOUR_TOKEN>
./run.sh
```

Get your registration token from: **Settings > Actions > Runners > New self-hosted runner**

#### 2. Run Workflow on Self-Hosted Runner

Update the workflow `runs-on` field:

```yaml
runs-on: self-hosted
```

Or use labels for specific machines:

```yaml
runs-on: [self-hosted, linux, x64, high-mem]
```

#### 3. Local Build (Without GitHub Actions)

```bash
git clone https://github.com/poying2018/debian-linux-github-action.git
cd debian-linux-github-action/scripts
chmod +x build-kernel.sh
./build-kernel.sh amd64 bookworm stable 6.1 amd64
```

## Build Optimization

This project uses the most efficient kernel compilation methods:

| Optimization | Description | Impact |
|-------------|-------------|--------|
| **ccache** | Compiler cache persisted via `actions/cache` | **5-10x faster** on rebuilds |
| **Parallel compilation** | `make -j$(nproc)` uses all CPU cores | Linear speedup |
| **Debug info disabled** | `CONFIG_DEBUG_INFO_NONE=y` | **30-50% less** compile time |
| **Shallow clone** | `git clone --depth 1` | Faster source download |
| **ccache compression** | `CCACHE_COMPRESS=1` | More cache hits |

### Recommended: Self-Hosted Runner with tmpfs

For maximum speed on a self-hosted runner with 16GB+ RAM:

```bash
# Mount build directory in RAM
sudo mount -t tmpfs -o size=8G tmpfs /build
cd /build
./build-kernel.sh amd64 bookworm stable 6.1 amd64
```

## Source Repositories

| Source | URL | Description |
|--------|-----|-------------|
| Debian Kernel | https://salsa.debian.org/kernel/linux | Official Debian kernel packaging |
| Liquorix | https://github.com/damentz/liquorix-package | Low-latency kernel patches |
| Linux Stable | https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git | Official Linux kernel |
| Bootlin Toolchains | https://toolchains.bootlin.com/ | Pre-built cross-compilation toolchains |

## Build Artifacts

Each successful build produces:

- `*.deb` — Debian kernel packages (headers, image, modules)
- `bzImage` / `Image` — Bootable kernel image
- `vmlinux.xz` — Compressed kernel ELF (for debugging)
- `modules-*.tar.xz` — Kernel modules archive
- `config-*` — Kernel configuration file

## Architecture Mapping

| Architecture | Debian Name | Cross-Compiler |
|-------------|------------|----------------|
| `amd64` | x86_64 | Native (no cross-compile) |
| `arm64` | aarch64 | `aarch64-linux-gnu-` |
| `armhf` | armv7l | `arm-linux-gnueabihf-` |
| `riscv64` | riscv64 | `riscv64-linux-gnu-` |

## Distribution to Kernel Mapping

| Distribution | Debian Branch | Default Kernel |
|-------------|---------------|----------------|
| Buster (10) | `debian/5.10` | 5.10 |
| Bullseye (11) | `debian/6.1` | 6.1 |
| Bookworm (12) | `debian/6.6` | 6.6 |
| Trixie (13) | `debian/6.12` | 6.12 |

## FAQ

**Q: Build fails with "out of memory"?**
A: GitHub hosted runners have 7GB RAM. Reduce parallel jobs: `NPROC=2 ./build-kernel.sh ...`

**Q: How to check ccache effectiveness?**
A: Check the build logs for "ccache stats" — hit rate should be >80% on rebuilds.

**Q: Liquorix patch fails to apply?**
A: Liquorix only supports specific kernel versions. Check available patches in the Liquorix repo.

**Q: Cross-compilation is very slow?**
A: Use a self-hosted runner with more cores, or use Bootlin pre-built toolchains.

## License

This project is for building the Linux kernel. The Linux kernel is licensed under GPLv2.
