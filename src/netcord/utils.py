import subprocess
import re
import ctypes

def run_cmd(cmd: str) -> tuple[str, str, int]:
    """Run a shell command, return (stdout, stderr, returncode)."""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True
    )
    return result.stdout, result.stderr, result.returncode

def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def validate_ip(ip: str) -> bool:
    pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
    if not re.match(pattern, ip):
        return False
    try:
        return all(0 <= int(p) <= 255 for p in ip.split("."))
    except ValueError:
        return False

def validate_prefix(prefix: str) -> bool:
    try:
        n = int(prefix)
        return 0 <= n <= 32
    except ValueError:
        return False

def prefix_to_mask(prefix: int) -> str:
    mask = (0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF
    return ".".join(str((mask >> (8 * i)) & 0xFF) for i in reversed(range(4)))

def mask_to_prefix(mask: str):
    try:
        parts = [int(p) for p in mask.split(".")]
        bits = sum(bin(p).count("1") for p in parts)
        return bits
    except Exception:
        return None
