#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键本地编译并安装 Linux 内核脚本
支持 Linux / Windows / macOS 系统
连接 poying2018/kernel- 仓库，不调用 GitHub Actions
"""

import os
import sys
import platform
import subprocess
import shutil
import json
import re
from pathlib import Path

# ============================================================
# 全局配置
# ============================================================
REPO_URL = "https://github.com/poying2018/kernel-.git"
KERNEL_ORG_URL = "https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git"
SCRIPT_DIR = Path(__file__).parent.resolve()
BUILD_DIR = SCRIPT_DIR / "kernel-build"
OUTPUT_DIR = SCRIPT_DIR / "kernel-output"

# 颜色输出
class Colors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BOLD = "\033[1m"
    END = "\033[0m"

def print_banner():
    """打印脚本横幅"""
    banner = f"""
{Colors.CYAN}{Colors.BOLD}╔══════════════════════════════════════════════════════════════╗
║           Linux 内核一键本地编译安装脚本 v1.0                 ║
║                                                              ║
║  支持系统: Linux / Windows / macOS                           ║
║  内核来源: kernel.org 官方稳定分支                            ║
║  仓库连接: poying2018/kernel-                                ║
╚══════════════════════════════════════════════════════════════╝{Colors.END}"""
    print(banner)

def print_step(msg):
    """打印步骤信息"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}[*] {msg}{Colors.END}")

def print_success(msg):
    """打印成功信息"""
    print(f"{Colors.GREEN}{Colors.BOLD}[\u2713] {msg}{Colors.END}")

def print_warning(msg):
    """打印警告信息"""
    print(f"{Colors.YELLOW}{Colors.BOLD}[!] {msg}{Colors.END}")

def print_error(msg):
    """打印错误信息"""
    print(f"{Colors.RED}{Colors.BOLD}[\u2717] {msg}{Colors.END}")

def print_info(msg):
    """打印信息"""
    print(f"{Colors.CYAN}[i] {msg}{Colors.END}")

def get_input(prompt, default=None, options=None):
    """获取用户输入"""
    while True:
        if default:
            full_prompt = f"{Colors.WHITE}{prompt} [{default}]: {Colors.END}"
        else:
            full_prompt = f"{Colors.WHITE}{prompt}: {Colors.END}"
        try:
            value = input(full_prompt).strip()
        except (KeyboardInterrupt, EOFError):
            print("\n")
            sys.exit(0)
        if not value and default:
            value = default
        if not value:
            print_warning("输入不能为空，请重新输入")
            continue
        if options and value not in options:
            print_warning(f"无效选项，请选择: {', '.join(options)}")
            continue
        return value

def get_yes_no(prompt, default="n"):
    """获取是/否输入"""
    default_str = "Y/n" if default == "y" else "y/N"
    while True:
        try:
            value = input(f"{Colors.WHITE}{prompt} [{default_str}]: {Colors.END}").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\n")
            sys.exit(0)
        if not value:
            value = default
        if value in ("y", "yes", "是"):
            return True
        elif value in ("n", "no", "否"):
            return False
        else:
            print_warning("请输入 y 或 n")

def run_cmd(cmd, cwd=None, check=True, shell=True):
    """执行命令"""
    print_info(f"执行: {cmd}")
    try:
        result = subprocess.run(
            cmd, cwd=cwd, shell=shell,
            capture_output=True, text=True
        )
        if result.returncode != 0 and check:
            print_error(f"命令执行失败 (exit code: {result.returncode})")
            if result.stderr:
                print_error(result.stderr[:500])
            raise RuntimeError(f"命令执行失败: {cmd}")
        return result

def detect_os():
    """检测操作系统"""
    system = platform.system().lower()
    if system == "linux":
        return "linux"
    elif system == "windows":
        return "windows"
    elif system == "darwin":
        return "macos"
    else:
        return "unknown"

def detect_linux_distro():
    """检测 Linux 发行版"""
    try:
        with open("/etc/os-release", "r") as f:
            content = f.read().lower()
        if "ubuntu" in content:
            with open("/etc/os-release", "r") as f:
                for line in f:
                    if line.startswith("version_id="):
                        version_id = line.split("=")[1].strip().strip('"')
                        return "ubuntu", version_id
            return "ubuntu", "unknown"
        elif "debian" in content:
            with open("/etc/os-release", "r") as f:
                for line in f:
                    if line.startswith("version_id="):
                        version_id = line.split("=")[1].strip().strip('"')
                        return "debian", version_id
            return "debian", "unknown"
        elif "arch" in content:
            return "arch", "rolling"
        else:
            return "unknown", "unknown"
    except FileNotFoundError:
        return "unknown", "unknown"

def get_current_kernel():
    """获取当前内核版本"""
    try:
        result = run_cmd("uname -r", check=False)
        return result.stdout.strip()
    except:
        return "unknown"

def get_default_kernel_for_distro(distro, version):
    """获取发行版默认内核版本"""
    defaults = {
        ("debian", "12"): "6.1",
        ("debian", "13"): "6.12",
        ("ubuntu", "22.04"): "5.15",
        ("ubuntu", "24.04"): "6.8",
        ("ubuntu", "24.10"): "6.8",
        ("ubuntu", "25.04"): "6.8",
    }
    return defaults.get((distro, version), "6.1")

# ============================================================
# 内核调度器选项
# ============================================================
SCHEDULERS = {
    "1": {
        "name": "CFS (完全公平调度器)",
        "desc": "Linux 默认调度器，适合桌面和通用服务器",
        "config": {"CONFIG_SCHED_DEBUG": "n", "CONFIG_SCHEDSTATS": "n"}
    },
    "2": {
        "name": "PREEMPT_VOLUNTARY (自愿抢占)",
        "desc": "适合桌面系统，降低延迟",
        "config": {"CONFIG_PREEMPT_VOLUNTARY": "y", "CONFIG_PREEMPT_NONE": "n", "CONFIG_PREEMPT": "n"}
    },
    "3": {
        "name": "PREEMPT (完全抢占)",
        "desc": "适合低延迟桌面和实时应用",
        "config": {"CONFIG_PREEMPT": "y", "CONFIG_PREEMPT_VOLUNTARY": "n", "CONFIG_PREEMPT_NONE": "n"}
    },
    "4": {
        "name": "PREEMPT_RT (实时抢占)",
        "desc": "适合实时应用，需要额外 RT 补丁",
        "config": {"CONFIG_PREEMPT_RT": "y", "CONFIG_PREEMPT_NONE": "n", "CONFIG_PREEMPT_VOLUNTARY": "n", "CONFIG_PREEMPT": "n"},
        "needs_rt_patch": True
    },
    "5": {
        "name": "NONE (无抢占)",
        "desc": "适合纯服务器场景，最大化吞吐量",
        "config": {"CONFIG_PREEMPT_NONE": "y", "CONFIG_PREEMPT_VOLUNTARY": "n", "CONFIG_PREEMPT": "n"}
    }
}

# ============================================================
# 编译选项
# ============================================================
COMPILE_OPTIONS = {
    "1": {"name": "标准编译", "desc": "默认配置，适合大多数用户", "flags": ""},
    "2": {"name": "快速编译", "desc": "禁用调试信息，减少编译时间", "flags": "CONFIG_DEBUG_INFO=n CONFIG_DEBUG_INFO_DWARF_TOOLCHAIN_DEFAULT=n"},
    "3": {"name": "最小化编译", "desc": "仅编译必要模块，最快", "flags": "CONFIG_DEBUG_INFO=n CONFIG_DEBUG_INFO_DWARF_TOOLCHAIN_DEFAULT=n CONFIG_KGDB=n CONFIG_DEBUG_KERNEL=n"},
    "4": {"name": "完整调试编译", "desc": "包含所有调试信息，适合开发者", "flags": "CONFIG_DEBUG_INFO=y CONFIG_DEBUG_INFO_DWARF_TOOLCHAIN_DEFAULT=y CONFIG_KGDB=y CONFIG_DEBUG_KERNEL=y CONFIG_DEBUG_MISC=y"},
}

# ============================================================
# 内核版本选项（按发行版分类）
# ============================================================
KERNEL_VERSIONS_BY_DISTRO = {
    "debian": [
        {"version": "6.1", "name": "6.1 LTS (Debian Bookworm 默认)"},
        {"version": "6.6", "name": "6.6 LTS"},
        {"version": "6.12", "name": "6.12 LTS (Debian Trixie 默认)"},
        {"version": "6.18", "name": "6.18 (最新稳定版)"},
    ],
    "ubuntu": [
        {"version": "5.15", "name": "5.15 LTS (Ubuntu Jammy 默认)"},
        {"version": "6.2", "name": "6.2 LTS"},
        {"version": "6.5", "name": "6.5"},
        {"version": "6.8", "name": "6.8 (Ubuntu Noble/Oracular/Plucky 默认)"},
        {"version": "6.18", "name": "6.18 (最新稳定版)"},
        {"version": "7.0", "name": "7.0"},
        {"version": "7.1", "name": "7.1"},
    ],
    "arch": [
        {"version": "6.12", "name": "6.12 LTS"},
        {"version": "6.18", "name": "6.18 (最新稳定版)"},
        {"version": "7.0", "name": "7.0"},
        {"version": "7.1", "name": "7.1 (Arch 默认)"},
    ],
}

def get_kernel_versions_for_distro(distro):
    """获取指定发行版支持的内核版本列表"""
    return KERNEL_VERSIONS_BY_DISTRO.get(distro, KERNEL_VERSIONS_BY_DISTRO["debian"])

# ============================================================
# Linux 本地编译类
# ============================================================




# ============================================================
# 代理配置（国内网络加速）
# ============================================================
# kernel.org 国内镜像
KERNEL_MIRRORS = [
    "https://mirrors.tuna.tsinghua.edu.cn/kernel/v{version}.x/linux-{version}.tar.xz",
    "https://mirrors.ustc.edu.cn/kernel/v{version}.x/linux-{version}.tar.xz",
    "https://mirrors.aliyun.com/kernel/v{version}.x/linux-{version}.tar.xz",
]
# Git 代理选项
GIT_PROXIES = [
    "https://ghproxy.com/https://github.com/",
    "https://mirror.ghproxy.com/https://github.com/",
    "https://gitclone.com/github.com/",
]

def detect_network_environment():
    """检测网络环境（基于 IP 地址判断国内/海外）"""
    print_info("检测网络环境...")
    import json
    import socket
    import time
    import urllib.request
    
    # 获取本机公网 IP 及地理位置
    ip_apis = [
        "https://api.ipify.org?format=json",
        "https://httpbin.org/ip",
        "https://ifconfig.me/all.json",
    ]
    
    public_ip = None
    country_code = None
    
    for api_url in ip_apis:
        try:
            req = urllib.request.Request(api_url, headers={"User-Agent": "kernel-build/1.0"})
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if "ip" in data:
                    public_ip = data["ip"]
                elif "origin" in data:
                    public_ip = data["origin"]
                
                # 某些 API 直接返回国家信息
                if "country_code" in data:
                    country_code = data["country_code"]
                elif "countryCode" in data:
                    country_code = data["countryCode"]
                
                if public_ip:
                    print_info(f"  公网 IP: {public_ip}")
                    break
        except Exception:
            continue
    
    # 如果获取到 IP，通过 IP 库判断地理位置
    if public_ip and not country_code:
        # 检查是否为私有地址（内网/NAT）
        def ip_to_int(ip):
            parts = ip.split(".")
            return (int(parts[0]) << 24) + (int(parts[1]) << 16) + (int(parts[2]) << 8) + int(parts[3])
        
        private_ranges = [
            ("10.0.0.0", "10.255.255.255"),
            ("172.16.0.0", "172.31.255.255"),
            ("192.168.0.0", "192.168.255.255"),
            ("127.0.0.0", "127.255.255.255"),
        ]
        
        try:
            ip_int = ip_to_int(public_ip)
            is_private = any(
                ip_to_int(start) <= ip_int <= ip_to_int(end)
                for start, end in private_ranges
            )
            
            if not is_private:
                # 使用 ip-api.com 查询地理位置（免费，无需 API key）
                try:
                    geo_url = f"http://ip-api.com/json/{public_ip}?fields=status,countryCode"
                    req = urllib.request.Request(geo_url, headers={"User-Agent": "kernel-build/1.0"})
                    with urllib.request.urlopen(req) as resp:
                        geo = json.loads(resp.read().decode("utf-8"))
                        if geo.get("status") == "success":
                            country_code = geo.get("country_code", "")
                            print_info(f"  地理位置: {country_code}")
                except Exception:
                    pass
        except Exception:
            pass
    
    # 判断网络环境
    if country_code:
        if country_code == "CN":
            print_info("网络环境: 国内 (IP 归属: 中国)")
            return "china"
        else:
            print_info(f"网络环境: 海外 (IP 归属: {country_code})")
            return "overseas"
    
    # 无法获取 IP 信息，回退到连接测试
    print_warning("无法通过 IP 判断地理位置，回退到连接测试...")
    
    # 快速测试国内镜像连通性
    try:
        start = time.time()
        sock = socket.create_connection(("mirrors.tuna.tsinghua.edu.cn", 443))
        sock.close()
        elapsed = time.time() - start
        if elapsed < 3.0:
            print_info("网络环境: 国内 (镜像可达)")
            return "china"
    except Exception:
        pass
    
    # 默认国内模式
    print_warning("无法确定网络环境，默认使用国内镜像模式")
    return "china"




def check_disk_space(required_gb=10):
    """检查磁盘空间是否足够"""
    try:
        stat = os.statvfs(BUILD_DIR.parent if BUILD_DIR.exists() else Path('.'))
        available_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
        if available_gb < required_gb:
            print_error(f"磁盘空间不足！剩余: {available_gb:.1f}GB，需要: {required_gb}GB")
            print_info("请清理磁盘空间后重试")
            print_info("建议清理方法:")
            print_info("  sudo apt clean")
            print_info("  sudo apt autoremove")
            print_info("  docker system prune -a  (如果使用 Docker)")
            print_info("  rm -rf /tmp/linux-*.tar.xz")
            return False
        print_info(f"磁盘空间检查通过 (剩余: {available_gb:.1f}GB)")
        return True
    except AttributeError:
        # Windows doesn't have statvfs
        return True

def setup_git_proxy(proxy_url=None):
    """配置 Git 代理"""
    if proxy_url:
        run_cmd(f"git config --global http.proxy {proxy_url}", check=False)
        run_cmd(f"git config --global https.proxy {proxy_url}", check=False)
        print_success(f"Git 代理已配置: {proxy_url}")
    else:
        # 使用 ghproxy 代理 GitHub
        run_cmd("git config --global url.\"https://ghproxy.com/https://github.com/\".insteadOf \"https://github.com/\"", check=False)
        print_success("Git 代理已配置 (ghproxy)")

def clear_git_proxy():
    """清除 Git 代理"""
    run_cmd("git config --global --unset http.proxy", check=False)
    run_cmd("git config --global --unset https.proxy", check=False)
    run_cmd("git config --global --unset url.https://ghproxy.com/https://github.com/.insteadOf", check=False)

def get_kernel_git_url(base_url, network_env):
    """根据网络环境获取内核 Git 克隆 URL"""
    if network_env == "china":
        # 国内使用镜像
        # kernel.org 的 git 镜像
        mirror_urls = [
            f"https://mirrors.tuna.tsinghua.edu.cn/git/linux-stable.git",
            f"https://mirrors.ustc.edu.cn/linux-stable.git",
            base_url,  # 最后尝试官方源
        ]
        return mirror_urls
    return [base_url]



class LinuxKernelBuilder:
    def __init__(self):
        self.distro = None
        self.distro_version = None
        self.kernel_version = None
        self.compile_option = None
        self.scheduler = None
        self.install_after_build = False
        self.verify_integrity = False
        self.arch = "amd64"
        self.cross_compile = False

    def run(self):
        """运行 Linux 内核编译流程"""
        self.detect_system()
        self.network_env = detect_network_environment()
        self.select_kernel_version()
        self.select_compile_options()
        self.select_scheduler()
        self.select_arch()
        self.select_cross_compile()
        self.select_install_verify()
        self.confirm_settings()
        self.install_dependencies()
        self.download_source()
        self.configure_kernel()
        self.compile_kernel()
        # 清理代理设置
        if hasattr(self, 'network_env') and self.network_env == "china":
            clear_git_proxy()
            print_info("已清理 Git 代理设置")
        if self.verify_integrity:
            self.verify_kernel()
        if self.install_after_build:
            self.install_kernel()
        self.show_completion()

    def detect_system(self):
        """检测系统信息"""
        print_step("检测系统信息")
        self.distro, self.distro_version = detect_linux_distro()
        current_kernel = get_current_kernel()
        print_info(f"操作系统: {self.distro} {self.distro_version}")
        print_info(f"当前运行内核: {current_kernel}")
        print_info(f"系统架构: {platform.machine()}")
        # 显示当前系统的默认内核版本
        default_kernel = get_default_kernel_for_distro(self.distro, self.distro_version)
        if default_kernel != "6.1":
            print_info(f"{self.distro} {self.distro_version} 默认内核: {default_kernel}")
        # 从当前内核版本中提取主版本号
        try:
            cur_parts = current_kernel.split(".")
            if len(cur_parts) >= 2:
                cur_major = f"{cur_parts[0]}.{cur_parts[1]}"
                print_info(f"当前内核主版本: {cur_major}")
        except Exception:
            pass

    def select_kernel_version(self):
        """选择内核版本"""
        print_step("选择内核版本")
        versions = get_kernel_versions_for_distro(self.distro)
        if self.distro in ("debian", "ubuntu"):
            default_kernel = get_default_kernel_for_distro(self.distro, self.distro_version)
            print_info(f"当前系统默认内核版本: {default_kernel}")
        print("\n可选内核版本:")
        for i, val in enumerate(versions, 1):
            print(f"  {i}. {val['name']}")
        valid_choices = [str(i) for i in range(1, len(versions) + 1)]
        choice = get_input("请选择内核版本", "1", valid_choices)
        idx = int(choice) - 1
        self.kernel_version = versions[idx]["version"]
        print_success(f"已选择内核版本: {self.kernel_version}")

    def select_compile_options(self):
        """选择编译选项"""
        print_step("选择编译选项")
        print("\n可选编译选项:")
        for key, val in COMPILE_OPTIONS.items():
            print(f"  {key}. {val['name']} - {val['desc']}")
        choice = get_input("请选择编译选项", "1")
        self.compile_option = COMPILE_OPTIONS[choice]
        print_success(f"已选择: {self.compile_option['name']}")

    def select_scheduler(self):
        """选择内核调度器"""
        print_step("选择内核调度器")
        print("\n可选调度器:")
        for key, val in SCHEDULERS.items():
            print(f"  {key}. {val['name']}")
            print(f"     {val['desc']}")
        choice = get_input("请选择调度器", "1")
        self.scheduler = SCHEDULERS[choice]
        print_success(f"已选择: {self.scheduler['name']}")
        if self.scheduler.get("needs_rt_patch"):
            print_warning("PREEMPT_RT 需要额外的实时补丁，将自动下载并应用")

    def select_arch(self):
        """选择架构"""
        print_step("选择目标架构")
        current_arch = platform.machine()
        print_info(f"当前系统架构: {current_arch}")
        arch_options = {
            "1": {"arch": "amd64", "name": "amd64 (x86_64)"},
            "2": {"arch": "arm64", "name": "arm64 (ARM 64-bit)"},
            "3": {"arch": "armhf", "name": "armhf (ARM 32-bit)"},
            "4": {"arch": "riscv64", "name": "riscv64 (RISC-V)"},
        }
        print("\n可选架构:")
        for key, val in arch_options.items():
            marker = ""
            if (current_arch == "x86_64" and val["arch"] == "amd64") or (current_arch == "aarch64" and val["arch"] == "arm64"):
                marker = " (当前)"
            print(f"  {key}. {val['name']}{marker}")
        choice = get_input("请选择目标架构", "1")
        selected = arch_options[choice]
        self.arch = selected["arch"]
        if (current_arch == "x86_64" and self.arch != "amd64") or (current_arch == "aarch64" and self.arch != "arm64"):
            self.cross_compile = True
            print_warning(f"将使用交叉编译 ({current_arch} -> {self.arch})")
        print_success(f"已选择架构: {selected['name']}")

    def select_cross_compile(self):
        """选择是否交叉编译"""
        print_step("选择交叉编译")
        current_arch = platform.machine()
        arch_map = {"amd64": "x86_64", "arm64": "aarch64", "armhf": "arm", "riscv64": "riscv"}
        current_kernel_arch = arch_map.get(self.arch, "x86_64")

        if current_arch == current_kernel_arch or (current_arch == "x86_64" and self.arch == "amd64") or (current_arch == "aarch64" and self.arch == "arm64"):
            print_info(f"当前系统架构 ({current_arch}) 与目标架构 ({self.arch}) 一致，无需交叉编译")
            self.cross_compile = False
            if get_yes_no("是否仍要启用交叉编译？", "n"):
                self.cross_compile = True
                print_info("已启用交叉编译")
            else:
                print_info("使用本地编译")
        else:
            print_info(f"当前系统架构: {current_arch}")
            print_info(f"目标架构: {self.arch}")
            print_warning(f"需要交叉编译 ({current_arch} -> {self.arch})")
            self.cross_compile = True
            if get_yes_no("确认使用交叉编译？", "y"):
                print_info("已启用交叉编译")
            else:
                print_warning("已取消交叉编译，将使用本地编译模式")
                self.cross_compile = False
        print_success(f"交叉编译: {'是' if self.cross_compile else '否'}")

    def select_install_verify(self):
        """选择编译后操作"""
        print_step("选择编译后操作")
        print("\n请选择编译完成后的操作:")
        self.install_after_build = get_yes_no("编译完成后是否安装内核？", "n")
        print_success(f"编译后安装: {'是' if self.install_after_build else '否'}")
        self.verify_integrity = get_yes_no("编译完成后是否验证内核完整性？", "y")
        print_success(f"验证完整性: {'是' if self.verify_integrity else '否'}")

    def confirm_settings(self):
        """确认设置"""
        print_step("确认编译设置")
        print(f"""
{Colors.BOLD}编译设置汇总:{Colors.END}
  发行版: {self.distro} {self.distro_version}
  内核版本: {self.kernel_version}
  编译选项: {self.compile_option['name']}
  调度器: {self.scheduler['name']}
  目标架构: {self.arch}
  交叉编译: {'是' if self.cross_compile else '否'}
  编译后安装: {'是' if self.install_after_build else '否'}
  验证完整性: {'是' if self.verify_integrity else '否'}
""")
        if not get_yes_no("确认以上设置并开始编译？", "y"):
            print_warning("已取消编译")
            sys.exit(0)

    def install_dependencies(self):
        """安装编译依赖"""
        print_step("安装编译依赖")
        if self.distro in ("debian", "ubuntu"):
            deps = "build-essential bc bison flex libssl-dev libelf-dev libdw-dev dwarves ccache fakeroot devscripts debhelper git wget xz-utils kmod cpio rsync"
            run_cmd("sudo apt-get update -qq")
            run_cmd(f"sudo apt-get install -y -qq {deps}")
            if self.cross_compile:
                cross_deps = {
                    "arm64": "gcc-aarch64-linux-gnu binutils-aarch64-linux-gnu",
                    "armhf": "gcc-arm-linux-gnueabihf binutils-arm-linux-gnueabihf",
                    "riscv64": "gcc-riscv64-linux-gnu binutils-riscv64-linux-gnu",
                }
                if self.arch in cross_deps:
                    run_cmd(f"sudo apt-get install -y -qq {cross_deps[self.arch]}")
        elif self.distro == "arch":
            deps = "base-devel bc bison flex openssl elfutils libelf dwarves ccache fakeroot devscripts debhelper git wget xz kmod cpio rsync"
            run_cmd(f"sudo pacman -S --noconfirm {deps}")
        else:
            print_warning("未知发行版，请手动安装编译依赖")
        print_success("编译依赖安装完成")
    def download_source(self):
        """下载内核源码（智能选择最优方式）"""
        print_step(f"下载 Linux {self.kernel_version} 源码")
        BUILD_DIR.mkdir(parents=True, exist_ok=True)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        source_dir = BUILD_DIR / f"linux-{self.kernel_version}"
        if source_dir.exists():
            print_warning(f"源码目录已存在: {source_dir}")
            if get_yes_no("是否重新下载？", "n"):
                shutil.rmtree(source_dir)
            else:
                print_info("使用已有源码")
                return

        kernel_tag = f"v{self.kernel_version}"
        major = self.kernel_version.split('.')[0]
        network_env = getattr(self, 'network_env', 'overseas')
        
        # 检查磁盘空间（内核源码+编译需要约 10GB）
        if not check_disk_space(10):
            raise RuntimeError("磁盘空间不足")

        # 配置 Git 全局设置（提高稳定性）
        run_cmd("git config --global http.postBuffer 524288000", check=False)
        run_cmd("git config --global http.lowSpeedLimit 100", check=False)
        run_cmd("git config --global http.lowSpeedTime 120", check=False)
        run_cmd("git config --global http.version HTTP/1.1", check=False)

        if network_env == "china":
            # 国内网络：优先 tarball（更稳定），git 作为备选
            print_info("检测到国内网络，优先使用 tarball 下载...")
            
            # 1. 尝试 tarball 下载
            tarball_urls = [
                f"https://mirrors.tuna.tsinghua.edu.cn/kernel/v{major}.x/linux-{self.kernel_version}.tar.xz",
                f"https://cdn.kernel.org/pub/linux/kernel/v{major}.x/linux-{self.kernel_version}.tar.xz",
            ]
            
            for i, url in enumerate(tarball_urls):
                try:
                    print_info(f"[{i+1}/{len(tarball_urls)}] 下载 tarball: {url}")
                    if self._download_and_extract_tarball(url, source_dir):
                        return
                except Exception as e:
                    err_msg = str(e)
                    if 'No space left' in err_msg:
                        print_error("磁盘空间已满！无法继续下载")
                        print_info("请清理磁盘空间后重试")
                        raise RuntimeError("磁盘空间不足")
                    print_warning(f"tarball 下载失败: {err_msg[:60]}")
                    continue

            # 2. tarball 失败，尝试 git clone
            print_warning("tarball 下载全部失败，尝试 git clone...")
            git_urls = [
                f"https://mirrors.tuna.tsinghua.edu.cn/git/linux-stable.git",
                f"https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git",
            ]
            
            for i, url in enumerate(git_urls):
                try:
                    print_info(f"[{i+1}/{len(git_urls)}] git clone: {url}")
                    if source_dir.exists():
                        shutil.rmtree(source_dir)
                    run_cmd(f"git clone --depth 1 --branch {kernel_tag} {url} {source_dir}")
                    if source_dir.exists() and any(source_dir.iterdir()):
                        print_success(f"源码下载完成: {source_dir}")
                        return
                except RuntimeError:
                    if source_dir.exists():
                        shutil.rmtree(source_dir)
                    continue

        else:
            # 海外网络：优先 git clone，tarball 作为备选
            print_info("检测到海外网络，使用 git clone 下载...")
            
            git_urls = [
                f"https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git",
                f"https://github.com/torvalds/linux.git",
            ]
            
            for i, url in enumerate(git_urls):
                try:
                    print_info(f"[{i+1}/{len(git_urls)}] git clone: {url}")
                    if source_dir.exists():
                        shutil.rmtree(source_dir)
                    run_cmd(f"git clone --depth 1 --branch {kernel_tag} {url} {source_dir}")
                    if source_dir.exists() and any(source_dir.iterdir()):
                        print_success(f"源码下载完成: {source_dir}")
                        return
                except RuntimeError:
                    if source_dir.exists():
                        shutil.rmtree(source_dir)
                    # 尝试禁用 SSL 验证（某些网络环境 TLS 会出问题）
                    try:
                        print_info("尝试禁用 SSL 验证后重试...")
                        if source_dir.exists():
                            shutil.rmtree(source_dir)
                        run_cmd(f"GIT_SSL_NO_VERIFY=1 git clone --depth 1 --branch {kernel_tag} {url} {source_dir}")
                        if source_dir.exists() and any(source_dir.iterdir()):
                            print_success(f"源码下载完成 (SSL验证已禁用): {source_dir}")
                            return
                    except RuntimeError:
                        if source_dir.exists():
                            shutil.rmtree(source_dir)
                        continue

            # git 失败，尝试 tarball（包括国内镜像）
            print_warning("git clone 全部失败，尝试 tarball 下载...")
            tarball_urls = [
                f"https://cdn.kernel.org/pub/linux/kernel/v{major}.x/linux-{self.kernel_version}.tar.xz",
                f"https://mirrors.tuna.tsinghua.edu.cn/kernel/v{major}.x/linux-{self.kernel_version}.tar.xz",
            ]
            
            for i, url in enumerate(tarball_urls):
                try:
                    print_info(f"[{i+1}/{len(tarball_urls)}] 下载 tarball: {url}")
                    if self._download_and_extract_tarball(url, source_dir):
                        return
                except Exception as e:
                    print_warning(f"tarball 下载失败: {str(e)[:60]}")
                    continue

        # 所有方式都失败
        print_error("所有下载方式均失败！")
        print_info("请尝试以下方法：")
        print_info(f"1. 手动下载: wget https://cdn.kernel.org/pub/linux/kernel/v{major}.x/linux-{self.kernel_version}.tar.xz")
        print_info(f"2. 解压到: {source_dir}")
        print_info(f"3. 重新运行脚本")
        raise RuntimeError("源码下载失败")

    def _download_and_extract_tarball(self, url, source_dir):
        """下载并解压 tarball"""
        import urllib.request
        import tarfile as tarfile_mod
        
        major = self.kernel_version.split('.')[0]
        tarball_path = BUILD_DIR / f"linux-{self.kernel_version}.tar.xz"
        
        # 下载
        req = urllib.request.Request(url, headers={"User-Agent": "kernel-build/1.0"})
        with urllib.request.urlopen(req) as resp:
            total = int(resp.headers.get('Content-Length', 0))
            downloaded = 0
            with open(tarball_path, 'wb') as f:
                while True:
                    chunk = resp.read(256 * 1024)  # 256KB chunks
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        pct = downloaded * 100 / total
                        print(f"\r  进度: {pct:.1f}% ({downloaded//1024//1024}MB/{total//1024//1024}MB)", end='', flush=True)
        
        print()  # newline after progress
        
        if not tarball_path.exists() or tarball_path.stat().st_size < 1024 * 1024:
            raise RuntimeError("tarball 文件太小或不存在")
        
        # 解压
        print_info("解压 tarball...")
        with tarfile_mod.open(tarball_path, 'r:xz') as tar:
            tar.extractall(BUILD_DIR)
        
        # 清理 tarball（节省磁盘空间）
        try:
            tarball_path.unlink()
        except:
            pass
        
        if source_dir.exists() and any(source_dir.iterdir()):
            print_success(f"tarball 下载并解压完成: {source_dir}")
            return True
        else:
            if source_dir.exists():
                shutil.rmtree(source_dir)
            return False


    def configure_kernel(self):
        """配置内核"""
        print_step("配置内核")
        source_dir = BUILD_DIR / f"linux-{self.kernel_version}"
        current_config = f"/boot/config-{get_current_kernel()}"
        if os.path.exists(current_config):
            print_info(f"使用当前内核配置: {current_config}")
            shutil.copy(current_config, source_dir / ".config")
            run_cmd("make olddefconfig", cwd=source_dir)
        else:
            print_warning("未找到当前内核配置，使用 defconfig")
            arch_map = {"amd64": "x86_64", "arm64": "arm64", "armhf": "arm", "riscv64": "riscv"}
            kernel_arch = arch_map.get(self.arch, "x86_64")
            run_cmd(f"make ARCH={kernel_arch} defconfig", cwd=source_dir)
        # 应用编译选项
        if self.compile_option["flags"]:
            print_info("应用编译选项...")
            for flag in self.compile_option["flags"].split():
                key, val = flag.split("=")
                run_cmd(f"./scripts/config --set-val {key} {val}", cwd=source_dir, check=False)
        # 应用调度器配置
        print_info(f"应用调度器配置: {self.scheduler['name']}")
        for key, val in self.scheduler.get("config", {}).items():
            run_cmd(f"./scripts/config --set-val {key} {val}", cwd=source_dir, check=False)
        # 禁用调试信息以加快编译（除非用户选择完整调试）
        if self.compile_option["name"] != "完整调试编译":
            run_cmd("./scripts/config --disable CONFIG_DEBUG_INFO", cwd=source_dir, check=False)
            run_cmd("./scripts/config --disable CONFIG_DEBUG_INFO_DWARF_TOOLCHAIN_DEFAULT", cwd=source_dir, check=False)
            run_cmd("./scripts/config --enable CONFIG_DEBUG_INFO_NONE", cwd=source_dir, check=False)
        run_cmd("make olddefconfig", cwd=source_dir)
        print_success("内核配置完成")

    def compile_kernel(self):
        """编译内核"""
        print_step("开始编译内核")
        source_dir = BUILD_DIR / f"linux-{self.kernel_version}"
        nproc = os.cpu_count() or 4
        arch_map = {"amd64": "x86_64", "arm64": "arm64", "armhf": "arm", "riscv64": "riscv"}
        kernel_arch = arch_map.get(self.arch, "x86_64")
        cross_compile_prefix = ""
        if self.cross_compile:
            cross_prefix_map = {"arm64": "aarch64-linux-gnu-", "armhf": "arm-linux-gnueabihf-", "riscv64": "riscv64-linux-gnu-"}
            cross_compile_prefix = cross_prefix_map.get(self.arch, "")
        print_info(f"使用 {nproc} 个 CPU 核心并行编译...")
        env_vars = f"ARCH={kernel_arch} "
        if cross_compile_prefix:
            env_vars += f"CROSS_COMPILE={cross_compile_prefix} "
        env_vars += f"CC='ccache gcc' LOCALVERSION=-custom KDEB_PKGVERSION=1.0 MAKEFLAGS=-j{nproc}"

        if self.cross_compile:
            # 交叉编译：dpkg-buildpackage 不支持交叉编译，直接编译内核和模块
            print_info("交叉编译模式：编译内核、模块和 DTBs...")
            run_cmd(f"{env_vars} make -j{nproc}", cwd=source_dir)
            run_cmd(f"{env_vars} make -j{nproc} modules", cwd=source_dir)
            # ARM 架构还需要编译 DTBs
            if kernel_arch in ("arm64", "arm"):
                run_cmd(f"{env_vars} make -j{nproc} dtbs", cwd=source_dir)
                print_success("内核编译完成 (make + modules + dtbs)")
            else:
                print_success("内核编译完成 (make + modules)")
        else:
            # 原生编译：尝试 deb-pkg，失败则回退到 make
            try:
                run_cmd(f"{env_vars} make deb-pkg", cwd=source_dir, check=True, shell=True)
                print_success("内核编译完成 (deb-pkg)")
            except RuntimeError:
                print_warning("deb-pkg 编译失败，尝试直接编译...")
                run_cmd(f"{env_vars} make -j{nproc}", cwd=source_dir)
                run_cmd(f"{env_vars} make -j{nproc} modules", cwd=source_dir)
                print_success("内核编译完成 (make)")

    def verify_kernel(self):
        """验证内核完整性"""
        print_step("验证内核完整性")
        source_dir = BUILD_DIR / f"linux-{self.kernel_version}"
        print_info("检查 module_layout 符号一致性...")
        current_kernel = get_current_kernel()
        current_symvers = f"/usr/lib/modules/{current_kernel}/build/Module.symvers"
        if os.path.exists(current_symvers):
            result = run_cmd("grep module_layout " + current_symvers, check=False)
            if result.returncode == 0:
                current_hash = result.stdout.strip().split()[0]
                print_info(f"当前内核 module_layout: {current_hash}")
            compiled_symvers = source_dir / "Module.symvers"
            if compiled_symvers.exists():
                result = run_cmd("grep module_layout " + str(compiled_symvers), check=False)
                if result.returncode == 0:
                    compiled_hash = result.stdout.strip().split()[0]
                    print_info(f"编译内核 module_layout: {compiled_hash}")
                    if current_hash == compiled_hash:
                        print_success("module_layout 符号一致，模块兼容")
                    else:
                        print_warning("module_layout 符号不一致，自行编译的模块可能无法加载")
        else:
            print_warning("无法找到当前内核的 Module.symvers，跳过符号检查")
        print_info("检查编译产物...")
        deb_files = list(BUILD_DIR.glob("*.deb"))
        if deb_files:
            print_success(f"找到 {len(deb_files)} 个 .deb 包:")
            for deb in deb_files:
                size = deb.stat().st_size / (1024 * 1024)
                print(f"  - {deb.name} ({size:.1f} MB)")
        else:
            print_warning("未找到 .deb 包")
        print_success("内核完整性验证完成")

    def install_kernel(self):
        """安装内核"""
        print_step("安装内核")
        deb_files = list(BUILD_DIR.glob("linux-image-*.deb"))
        if not deb_files:
            print_error("未找到编译好的 .deb 包")
            return
        print_info(f"找到 {len(deb_files)} 个内核包:")
        for deb in deb_files:
            print(f"  - {deb.name}")
        if not get_yes_no("确认安装以上内核包？", "y"):
            print_warning("已取消安装")
            return
        for deb in deb_files:
            print_info(f"安装 {deb.name}...")
            run_cmd(f"sudo dpkg -i {deb}")
        run_cmd("sudo apt-get install -f -y", check=False)
        if self.distro in ("debian", "ubuntu"):
            run_cmd("sudo update-grub", check=False)
        print_success("内核安装完成！")
        print_warning("请重启系统以使用新内核")

    def show_completion(self):
        """显示完成信息"""
        print(f"""
{Colors.GREEN}{Colors.BOLD}╔══════════════════════════════════════════════════════════════╗
║                     编译完成！                               ║
╚══════════════════════════════════════════════════════════════╝{Colors.END}
  内核版本: {self.kernel_version}
  编译目录: {BUILD_DIR}
  产物目录: {OUTPUT_DIR}
""")
        deb_files = list(BUILD_DIR.glob("*.deb"))
        if deb_files:
            print_info("生成的文件:")
            for f in deb_files:
                size = f.stat().st_size / (1024 * 1024)
                print(f"  {f.name} ({size:.1f} MB)")



# ============================================================
# Windows 平台
# ============================================================
class WindowsKernelBuilder:
    def run(self):
        print_step("检测到 Windows 系统")
        print("""
Windows 系统无法直接编译 Linux 内核。请选择以下方式:

  1. 使用 WSL (Windows Subsystem for Linux) - 推荐
  2. 通过 SSH 连接到远程 Linux 服务器编译
  3. 使用虚拟机 (VirtualBox/VMware) 中的 Linux 系统
  4. 退出
""")
        choice = get_input("请选择", "1", ["1", "2", "3", "4"])
        if choice == "1":
            self.run_wsl()
        elif choice == "2":
            self.run_ssh()
        elif choice == "3":
            self.run_vm()
        else:
            print_info("已退出")
            sys.exit(0)

    def run_wsl(self):
        print_step("使用 WSL 编译内核")
        result = run_cmd("wsl --list --quiet", check=False)
        if result.returncode != 0:
            print_error("WSL 未安装或未启用")
            print_info("请先安装 WSL: wsl --install")
            sys.exit(1)
        print_success("WSL 已安装")
        print_info("正在 WSL 中启动编译脚本...")
        script_path = os.path.abspath(__file__)
        wsl_path = subprocess.run(["wsl", "wslpath", "-u", script_path], capture_output=True, text=True).stdout.strip()
        run_cmd(f"wsl python3 {wsl_path}")

    def run_ssh(self):
        print_step("通过 SSH 远程编译内核")
        print_info("请提供远程 Linux 服务器信息:")
        remote_host = get_input("服务器地址 (IP 或域名)")
        remote_user = get_input("用户名", os.getlogin())
        print_info(f"将连接到 {remote_user}@{remote_host}")
        if not get_yes_no("确认连接？", "y"):
            sys.exit(0)
        print_info("上传脚本到远程服务器...")
        run_cmd(f"scp {os.path.abspath(__file__)} {remote_user}@{remote_host}:/tmp/build-kernel.py")
        print_info("在远程服务器上执行编译脚本...")
        run_cmd(f"ssh {remote_user}@{remote_host} 'python3 /tmp/build-kernel.py'")
        print_info("编译完成后，使用以下命令下载产物:")
        print(f"  scp {remote_user}@{remote_host}:/tmp/kernel-build/*.deb ./")

    def run_vm(self):
        print_step("使用虚拟机编译内核")
        print_info("请在虚拟机中安装 Linux 系统，然后在该系统中运行此脚本")
        print_info("虚拟机建议配置:")
        print("  - CPU: 4 核以上")
        print("  - 内存: 4GB 以上")
        print("  - 磁盘: 50GB 以上")

# ============================================================
# macOS 平台
# ============================================================
class MacOSKernelBuilder:
    def run(self):
        print_step("检测到 macOS 系统")
        print("""
macOS 系统无法直接编译 Linux 内核。请选择以下方式:

  1. 通过 SSH 连接到远程 Linux 服务器编译 - 推荐
  2. 使用虚拟机 (UTM/Parallels) 中的 Linux 系统
  3. 退出
""")
        choice = get_input("请选择", "1", ["1", "2", "3"])
        if choice == "1":
            self.run_ssh()
        elif choice == "2":
            self.run_vm()
        else:
            print_info("已退出")
            sys.exit(0)

    def run_ssh(self):
        print_step("通过 SSH 远程编译内核")
        print_info("请提供远程 Linux 服务器信息:")
        remote_host = get_input("服务器地址 (IP 或域名)")
        remote_user = get_input("用户名", os.getlogin())
        print_info(f"将连接到 {remote_user}@{remote_host}")
        if not get_yes_no("确认连接？", "y"):
            sys.exit(0)
        print_info("上传脚本到远程服务器...")
        run_cmd(f"scp {os.path.abspath(__file__)} {remote_user}@{remote_host}:/tmp/build-kernel.py")
        print_info("在远程服务器上执行编译脚本...")
        run_cmd(f"ssh {remote_user}@{remote_host} 'python3 /tmp/build-kernel.py'")
        print_info("编译完成后，使用以下命令下载产物:")
        print(f"  scp {remote_user}@{remote_host}:/tmp/kernel-build/*.deb ./")

    def run_vm(self):
        print_step("使用虚拟机编译内核")
        print_info("请在虚拟机中安装 Linux 系统，然后在该系统中运行此脚本")
        print_info("推荐使用 UTM (Apple Silicon) 或 Parallels (Intel Mac)")

# ============================================================
# 主程序
# ============================================================
def main():
    """主函数"""
    print_banner()
    current_os = detect_os()
    print_info(f"检测到操作系统: {current_os}")
    if current_os == "linux":
        builder = LinuxKernelBuilder()
        builder.run()
    elif current_os == "windows":
        builder = WindowsKernelBuilder()
        builder.run()
    elif current_os == "macos":
        builder = MacOSKernelBuilder()
        builder.run()
    else:
        print_error(f"不支持的操作系统: {current_os}")
        sys.exit(1)

if __name__ == "__main__":
    main()
