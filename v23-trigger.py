import json, sys

distro = sys.argv[1]
data = {
    "ref": "feature/live-iso",
    "inputs": {
        "release_line": "bookworm" if distro == "debian" else "noble",
        "kernel_version": "6.1" if distro == "debian" else "6.8"
    }
}

with open(f"v23-{distro}.json", "w", encoding="utf-8") as f:
    json.dump(data, f)
print(f"v23-{distro}.json written")
