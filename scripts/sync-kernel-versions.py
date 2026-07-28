#!/usr/bin/env python3
"""
sync-kernel-versions.py - Comprehensive kernel source monitoring.

Checks:
  1. New kernel versions from official sources
  2. Source changes (commit SHA shifts, tag updates)
  3. Kernel support/EOL status

Monitors all 3 per-distro workflows:
  - build-kernel-debian.yml
  - build-kernel-ubuntu.yml
  - build-kernel-arch.yml

Updates kernel-status.json and build workflow files when changes detected.
"""

import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STATUS_FILE = REPO_ROOT / "kernel-status.json"
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"

WORKFLOW_FILES = {
    "debian": WORKFLOW_DIR / "build-kernel-debian.yml",
    "ubuntu": WORKFLOW_DIR / "build-kernel-ubuntu.yml",
    "arch": WORKFLOW_DIR / "build-kernel-arch.yml",
}

# All known stable kernel versions (will be validated against kernel.org)
ALL_KERNEL_VERSIONS = ["5.15", "6.1", "6.2", "6.5", "6.6", "6.8", "6.12", "6.18", "7.0", "7.1"]

# Per-distro version availability (which versions are valid for each distro)
DISTRO_VERSIONS = {
    "debian": ["6.1", "6.6", "6.12", "6.18"],
    "ubuntu": ["5.15", "6.2", "6.5", "6.8", "6.18", "7.0", "7.1"],
    "arch": ["6.12", "6.18", "7.0", "7.1"],
}

# ─── Helpers ──────────────────────────────────────────────────────────────────

def run_git(*args, timeout=120):
    """Run a git command and return stdout."""
    try:
        result = subprocess.run(
            ["git"] + list(args),
            capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip()
    except Exception as e:
        print(f"  WARNING: git {' '.join(args)} failed: {e}")
        return ""

def fetch_url(url, timeout=30):
    """Fetch URL content."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "kernel-sync/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8")
    except Exception as e:
        print(f"  WARNING: fetch {url} failed: {e}")
        return ""

def get_tag_sha(url: str, tag: str) -> str:
    """Get the commit SHA for a specific tag."""
    output = run_git("ls-remote", "--tags", url, f"refs/tags/{tag}")
    for line in output.split("\n"):
        if tag in line and "^{}" not in line:
            parts = line.split("\t")
            if len(parts) >= 2:
                return parts[0]
    return ""

def get_branch_sha(url: str, branch: str) -> str:
    """Get the commit SHA for a branch HEAD."""
    output = run_git("ls-remote", "--heads", url, f"refs/heads/{branch}")
    for line in output.split("\n"):
        parts = line.split("\t")
        if len(parts) >= 2:
            return parts[0]
    return ""

# ─── Source change detection ──────────────────────────────────────────────────

def load_status() -> dict:
    """Load previous kernel-status.json."""
    if STATUS_FILE.exists():
        try:
            return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, IOError):
            pass
    return {"sources": {}, "last_sync": None}

def save_status(status: dict):
    """Save kernel-status.json."""
    status["last_sync"] = datetime.now(timezone.utc).isoformat()
    STATUS_FILE.write_text(
        json.dumps(status, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8"
    )

def detect_source_changes(old_sources: dict, new_sources: dict) -> list:
    """Detect changes between old and new source states."""
    changes = []
    for key, new_info in new_sources.items():
        if key not in old_sources:
            changes.append(f"NEW: {key} -> {new_info.get('ref', '?')} @ {new_info.get('sha', '?')[:8]}")
            continue
        old_info = old_sources[key]
        if old_info.get("sha") != new_info.get("sha"):
            changes.append(f"CHANGED: {key}: {old_info.get('sha', '?')[:8]} -> {new_info.get('sha', '?')[:8]}")
    for key in old_sources:
        if key not in new_sources:
            changes.append(f"REMOVED: {key}")
    return changes

# ─── Kernel.org EOL status ────────────────────────────────────────────────────

def build_eol_report(releases_data: dict) -> dict:
    """Build a report of kernel support status."""
    report = {}
    for rel in releases_data.get("releases", []):
        moniker = rel.get("moniker", "unknown")
        version = rel.get("version", "")
        is_eol = rel.get("iseol", False)
        date = rel.get("released", {}).get("isodate", "")
        m = re.match(r"^(\d+\.\d+)", version)
        if m and moniker in ("stable", "longterm"):
            mm = m.group(1)
            if mm not in report or not report[mm].get("iseol"):
                report[mm] = {"version": version, "iseol": is_eol, "date": date, "moniker": moniker}
    return report

# ─── Source collectors ────────────────────────────────────────────────────────

def get_kernel_org_versions() -> dict:
    """Fetch kernel.org releases.json for version + EOL status."""
    print("Fetching kernel.org releases.json...")
    data = fetch_url("https://www.kernel.org/releases.json")
    if not data:
        return {}
    try:
        return json.loads(data)
    except json.JSONDecodeError:
        return {}

def get_kernel_org_sources(versions: list) -> dict:
    """Track kernel.org stable tags for specified versions."""
    print("Checking kernel.org stable tags...")
    sources = {}
    repo = "https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git"
    for ver in versions:
        tag = f"v{ver}"
        sha = get_tag_sha(repo, tag)
        if sha:
            sources[f"kernel.org/{tag}"] = {"ref": tag, "sha": sha, "repo": repo}
            print(f"  {tag} @ {sha[:8]}")
        else:
            print(f"  {tag} -> NOT FOUND")
    return sources

def get_ubuntu_sources() -> dict:
    """Track Ubuntu Launchpad kernel tags."""
    print("Checking Ubuntu Launchpad kernel tags...")
    sources = {}
    repo_base = "https://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git"
    
    tags = {
        "jammy": ["Ubuntu-5.15.0-168.178", "Ubuntu-hwe-6.2-6.2.0-40.41_22.04.1",
                   "Ubuntu-hwe-6.5-6.5.0-41.41_22.04.1", "Ubuntu-lowlatency-hwe-6.8-6.8.0-134.134.1_22.04.1"],
        "noble": ["Ubuntu-6.8.0-57.59"],
        "oracular": ["Ubuntu-6.8.0-24.24"],
        "plucky": ["Ubuntu-6.8.0-26.26"],
    }
    
    for release, release_tags in tags.items():
        repo = f"{repo_base}/{release}"
        for tag in release_tags:
            sha = get_tag_sha(repo, tag)
            if sha:
                sources[f"ubuntu/{release}/{tag}"] = {"ref": tag, "sha": sha, "repo": repo}
                print(f"  {release}/{tag} @ {sha[:8]}")
            else:
                print(f"  {release}/{tag} -> NOT FOUND")
    return sources

def get_arch_source() -> dict:
    """Track Arch Linux kernel (resolves from PKGBUILD -> kernel.org tag)."""
    print("Checking Arch Linux kernel version...")
    sources = {}
    
    pkgbuild_url = "https://raw.githubusercontent.com/archlinux/svntogit-packages/packages/linux/trunk/PKGBUILD"
    pkgbuild = fetch_url(pkgbuild_url)
    pkgver = ""
    if pkgbuild:
        m = re.search(r'^pkgver=(.+)$', pkgbuild, re.MULTILINE)
        if m:
            pkgver = m.group(1).strip()
    
    if pkgver:
        ver = pkgver.rsplit(".", 1)[0]  # e.g., "7.1.5" -> "7.1"
        tag = f"v{ver}"
        repo = "https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git"
        sha = get_tag_sha(repo, tag)
        if sha:
            sources[f"arch/rolling/{tag}"] = {"ref": tag, "sha": sha, "repo": repo, "pkgver": pkgver}
            print(f"  Arch rolling: {tag} (pkgver={pkgver}) @ {sha[:8]}")
    return sources

def get_debian_sources() -> dict:
    """Track Debian kernel sources from kernel.org (Debian uses upstream stable)."""
    print("Checking Debian kernel sources...")
    sources = {}
    repo = "https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git"
    
    debian_versions = {"bookworm": "6.1", "trixie": "6.12"}
    for release, ver in debian_versions.items():
        tag = f"v{ver}"
        sha = get_tag_sha(repo, tag)
        if sha:
            sources[f"debian/{release}/{tag}"] = {"ref": tag, "sha": sha, "repo": repo}
            print(f"  Debian {release}: {tag} @ {sha[:8]}")
    return sources

# ─── Workflow file updater ────────────────────────────────────────────────────

def get_existing_versions_from_workflow(filepath: Path) -> list:
    """Extract existing kernel versions from a workflow YAML file."""
    if not filepath.exists():
        return []
    content = filepath.read_text(encoding="utf-8")
    versions = []
    lines = content.split("\n")
    in_kv_options = False
    base_indent = 0
    
    for line in lines:
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        
        # Detect options: after kernel_version
        if "kernel_version:" in line:
            in_kv_options = False
            base_indent = indent
            continue
        
        # Detect the options: line within kernel_version section
        if stripped.startswith("options:") and indent > base_indent:
            in_kv_options = True
            continue
        
        # Collect version options
        if in_kv_options:
            if stripped.startswith("- "):
                ver = stripped[2:].strip().strip('"').strip("'")
                versions.append(ver)
            elif stripped and indent <= base_indent:
                # Reached next field at same/higher level
                in_kv_options = False
            elif stripped.startswith("#"):
                # Skip comments
                continue
    
    return versions

def update_workflow_versions(filepath: Path, new_versions: list, distro: str) -> bool:
    """Update a workflow file's kernel_version options with new versions."""
    if not filepath.exists():
        print(f"  WARNING: {filepath} not found, skipping")
        return False
    
    content = filepath.read_text(encoding="utf-8")
    valid_versions = DISTRO_VERSIONS.get(distro, [])
    
    # Build the new options list
    options_lines = ["          - distro-default"]
    for ver in valid_versions:
        if ver in new_versions:
            options_lines.append(f'          - "{ver}"')
    
    # Use regex to find and replace the kernel_version options block
    # The pattern matches from "options:" after "kernel_version:" section
    # until the next field at the same indentation level
    import re as re_module
    
    # Find the kernel_version section and its options
    lines = content.split("\n")
    new_lines = []
    in_kv_section = False
    in_kv_options = False
    kv_indent = 0
    options_inserted = False
    
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        
        # Detect kernel_version: line
        if "kernel_version:" in line and not in_kv_section:
            in_kv_section = True
            kv_indent = indent
            new_lines.append(line)
            i += 1
            continue
        
        # Inside kernel_version section
        if in_kv_section:
            # Detect options: line
            if stripped.startswith("options:") and not in_kv_options:
                in_kv_options = True
                new_lines.append(line)
                i += 1
                # Skip all existing option lines
                while i < len(lines):
                    next_stripped = lines[i].lstrip()
                    next_indent = len(lines[i]) - len(next_stripped)
                    if next_stripped.startswith("- ") and next_indent > kv_indent:
                        i += 1
                        continue
                    else:
                        break
                # Insert new options
                for opt in options_lines:
                    new_lines.append(opt)
                options_inserted = True
                continue
            
            # Detect next field at same or lower indent level (end of section)
            if stripped and not stripped.startswith("#") and indent <= kv_indent and stripped != "":
                in_kv_section = False
                in_kv_options = False
        
        new_lines.append(line)
        i += 1
    
    new_content = "\n".join(new_lines)
    if new_content != content:
        filepath.write_text(new_content, encoding="utf-8")
        return True
    return False

def update_all_workflows(new_versions: set) -> list:
    """Update all build workflow files with newly detected versions."""
    changes = []
    for distro, filepath in WORKFLOW_FILES.items():
        existing = get_existing_versions_from_workflow(filepath)
        valid = DISTRO_VERSIONS.get(distro, [])
        # Find which new versions should be added for this distro
        to_add = [v for v in valid if v in new_versions and v not in existing]
        if to_add:
            if update_workflow_versions(filepath, new_versions, distro):
                changes.append(f"Updated {distro} workflow: added {', '.join(to_add)}")
                print(f"  ✓ {distro}: added versions {to_add}")
    return changes

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("  Kernel Source Monitor")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 70)
    print()

    old_status = load_status()
    old_sources = old_status.get("sources", {})
    new_sources = {}
    all_changes = []
    any_changed = False

    # ── 1. Kernel.org releases & EOL ────────────────────────────────────────
    releases_data = get_kernel_org_versions()
    eol_report = build_eol_report(releases_data)

    print("─── Kernel.org EOL Status ───")
    for mm in sorted(eol_report.keys(), key=lambda x: [int(p) for p in x.split(".")], reverse=True):
        info = eol_report[mm]
        status = "EOL" if info["iseol"] else "Active"
        print(f"  {mm} ({info['moniker']}): {status} - {info['version']}")
    print()

    # ── 2. Track kernel.org stable tags ─────────────────────────────────────
    print("─── kernel.org Stable Tags ───")
    kernel_org_sources = get_kernel_org_sources(ALL_KERNEL_VERSIONS)
    new_sources.update(kernel_org_sources)
    print()

    # ── 3. Track Ubuntu Launchpad sources ───────────────────────────────────
    print("─── Ubuntu Launchpad Sources ───")
    ubuntu_sources = get_ubuntu_sources()
    new_sources.update(ubuntu_sources)
    print()

    # ── 4. Track Arch Linux sources ────────────────────────────────────────
    print("─── Arch Linux Sources ───")
    arch_sources = get_arch_source()
    new_sources.update(arch_sources)
    print()

    # ── 5. Track Debian sources ────────────────────────────────────────────
    print("─── Debian Sources ───")
    debian_sources = get_debian_sources()
    new_sources.update(debian_sources)
    print()

    # ── 6. Detect changes ──────────────────────────────────────────────────
    print("─── Change Detection ───")
    changes = detect_source_changes(old_sources, new_sources)
    if changes:
        any_changed = True
        all_changes.extend(changes)
        for c in changes:
            print(f"  ⚡ {c}")
    else:
        print("  No source changes detected")
    print()

    # ── 7. Check for new kernel versions ───────────────────────────────────
    print("─── New Version Detection ───")
    old_versions = set()
    for key in old_sources:
        m = re.search(r"v(\d+\.\d+)", key)
        if m:
            old_versions.add(m.group(1))
    
    current_versions = set()
    for key in new_sources:
        m = re.search(r"v(\d+\.\d+)", key)
        if m:
            current_versions.add(m.group(1))
    
    added = current_versions - old_versions
    if added:
        any_changed = True
        for v in sorted(added, key=lambda x: [int(p) for p in x.split(".")]):
            all_changes.append(f"New kernel version detected: v{v}")
            print(f"  🆕 New: v{v}")
    print()

    # ── 8. Check for EOL status changes ────────────────────────────────────
    print("─── EOL Status Changes ───")
    old_eol = old_status.get("eol_report", {})
    for mm, info in eol_report.items():
        old_info = old_eol.get(mm, {})
        if old_info.get("iseol") != info.get("iseol"):
            any_changed = True
            status = "EOL" if info["iseol"] else "Active"
            all_changes.append(f"EOL change: {mm} is now {status}")
            print(f"  ⚠️  {mm}: {status}")
    print()

    # ── 9. Update build workflows if new versions detected ─────────────────
    print("─── Build Workflow Update ───")
    if added:
        print(f"  New versions found: {sorted(added)}")
        wf_changes = update_all_workflows(current_versions)
        if wf_changes:
            any_changed = True
            all_changes.extend(wf_changes)
        else:
            print("  No workflow updates needed")
    else:
        print("  No new versions to add to workflows")
    print()

    # ── 10. Save status ────────────────────────────────────────────────────
    new_status = {
        "sources": new_sources,
        "eol_report": eol_report,
        "last_sync": datetime.now(timezone.utc).isoformat(),
    }
    save_status(new_status)
    print(f"  Status saved to kernel-status.json")

    # ── 11. Generate summary ───────────────────────────────────────────────
    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_file:
        with open(summary_file, "a") as f:
            f.write("## Kernel Source Monitor Report\n\n")
            f.write(f"**Sync Time:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n")
            
            f.write("### Source Changes\n\n")
            if all_changes:
                for change in all_changes:
                    f.write(f"- ⚡ {change}\n")
            else:
                f.write("- No changes detected\n")
            
            f.write("\n### Kernel Support Status\n\n")
            f.write("| Version | Status | Latest | Date |\n")
            f.write("|---------|--------|--------|------|\n")
            for mm in sorted(eol_report.keys(), key=lambda x: [int(p) for p in x.split(".")], reverse=True):
                info = eol_report[mm]
                status = "🔴 EOL" if info["iseol"] else "🟢 Active"
                f.write(f"| {mm} | {status} | {info['version']} | {info['date']} |\n")
            
            f.write("\n### Tracked Sources\n\n")
            f.write(f"- **kernel.org:** {len(kernel_org_sources)} stable versions\n")
            f.write(f"- **Ubuntu:** {len(ubuntu_sources)} kernel sources\n")
            f.write(f"- **Arch:** {len(arch_sources)} sources\n")
            f.write(f"- **Debian:** {len(debian_sources)} sources\n")
            f.write(f"- **Total:** {len(new_sources)} tracked sources\n")

    # Output for GitHub Actions
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"changed={'true' if any_changed else 'false'}\n")
            f.write(f"changes={'|'.join(all_changes)}\n")

    print()
    print("=" * 70)
    print(f"  Changes: {len(all_changes)} | Sources tracked: {len(new_sources)}")
    print("=" * 70)

    return 0

if __name__ == "__main__":
    sys.exit(main())