import re
import urllib.request
from .utils import run_cmd, prefix_to_mask, mask_to_prefix

def get_adapters() -> list[str]:
    out, _, _ = run_cmd(
        'powershell -Command "Get-NetAdapter | Where-Object {$_.Status -eq \'Up\'} | Select-Object -ExpandProperty Name"'
    )
    return [a.strip() for a in out.strip().splitlines() if a.strip()]

def get_adapter_info(adapter: str) -> dict:
    """Return a dict with IP config of a given adapter."""
    info = {
        "dhcp": True,
        "ip": "", "mask": "", "prefix": "", "gateway": "",
        "dns1": "", "dns2": "",
        "mac": "", "speed": "", "status": "Unknown",
        "desc": "",
    }
    if not adapter:
        return info

    # ── IP / Mask / Gateway / DNS via netsh (reliable, no JSON parsing) ────
    out_netsh, _, _ = run_cmd(f'netsh interface ip show config name="{adapter}"')
    for line in out_netsh.splitlines():
        line = line.strip()
        low = line.lower()
        if "ip address" in low and "subnet" not in low:
            m = re.search(r"(\d+\.\d+\.\d+\.\d+)", line)
            if m:
                info["ip"] = m.group(1)
        elif "subnet prefix" in low or "subnet mask" in low:
            m_prefix = re.search(r"/(\d+)", line)
            m_mask   = re.search(r"mask\s+(\d+\.\d+\.\d+\.\d+)", line, re.IGNORECASE)
            if not m_mask:
                m_mask = re.search(r"(\d+\.\d+\.\d+\.\d+)\s*\)", line)
            if m_prefix:
                info["prefix"] = m_prefix.group(1)
            if m_mask:
                info["mask"] = m_mask.group(1)
            elif info["prefix"]:
                info["mask"] = prefix_to_mask(int(info["prefix"]))
        elif "default gateway" in low:
            m = re.search(r"(\d+\.\d+\.\d+\.\d+)", line)
            if m:
                info["gateway"] = m.group(1)
        elif "dns servers" in low or "statically configured dns" in low:
            m = re.search(r"(\d+\.\d+\.\d+\.\d+)", line)
            if m:
                if not info["dns1"]:
                    info["dns1"] = m.group(1)
                elif not info["dns2"]:
                    info["dns2"] = m.group(1)
        elif re.match(r"^\d+\.\d+\.\d+\.\d+$", line):
            if info["dns1"] and not info["dns2"]:
                info["dns2"] = line

    # Derive missing prefix/mask
    if info["ip"] and info["mask"] and not info["prefix"]:
        p = mask_to_prefix(info["mask"])
        info["prefix"] = str(p) if p is not None else "24"
    if info["ip"] and info["prefix"] and not info["mask"]:
        info["mask"] = prefix_to_mask(int(info["prefix"]))

    # ── DHCP check ───────────────────────────────────────────────────────────
    dhcp_flag = False
    for line in out_netsh.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("dhcp enabled"):
            dhcp_flag = "yes" in stripped.lower()
            break
    if not any(l.strip().lower().startswith("dhcp enabled") for l in out_netsh.splitlines()):
        out2, _, _ = run_cmd(
            f'powershell -Command "(Get-NetIPInterface -InterfaceAlias \'{adapter}\' -AddressFamily IPv4).Dhcp"'
        )
        dhcp_flag = out2.strip().lower() == "enabled"
    info["dhcp"] = dhcp_flag

    # ── MAC / Speed / Desc via powershell Format-List ────────────────────────
    out3, _, _ = run_cmd(
        f'powershell -Command "Get-NetAdapter -Name \'{adapter}\' | Format-List MacAddress,LinkSpeed,InterfaceDescription"'
    )
    for line in out3.splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip().lower()
        val = val.strip()
        if key == "macaddress":
            info["mac"] = val
        elif key == "linkspeed":
            info["speed"] = val
        elif key == "interfacedescription":
            info["desc"] = val

    info["status"] = "Connected"
    return info

def apply_static(adapter: str, ip: str, prefix: str, gateway: str, dns1: str, dns2: str) -> tuple[bool, str]:
    cmds = []
    mask = prefix_to_mask(int(prefix))

    cmds.append(
        f'netsh interface ip set address name="{adapter}" static {ip} {mask} {gateway}'
    )

    dns_cmds = []
    if dns1:
        dns_cmds.append(f'netsh interface ip set dns name="{adapter}" static {dns1}')
    if dns2:
        dns_cmds.append(f'netsh interface ip add dns name="{adapter}" {dns2} index=2')
    if not dns1:
        dns_cmds.append(f'netsh interface ip set dns name="{adapter}" none')

    for cmd in cmds + dns_cmds:
        _, err, code = run_cmd(cmd)
        if code != 0:
            return False, err.strip()
    return True, ""

def apply_dhcp(adapter: str) -> tuple[bool, str]:
    cmds = [
        f'netsh interface ip set address name="{adapter}" dhcp',
        f'netsh interface ip set dns name="{adapter}" dhcp',
    ]
    for cmd in cmds:
        _, err, code = run_cmd(cmd)
        if code != 0:
            return False, err.strip()
    return True, ""

def apply_extra_ips(adapter: str, extra_ips: list) -> tuple[bool, str]:
    """Add secondary IP addresses to an adapter."""
    for ip, mask in extra_ips:
        cmd = f'netsh interface ip add address name="{adapter}" {ip} {mask}'
        _, err, code = run_cmd(cmd)
        if code != 0:
            return False, err.strip()
    return True, ""

def get_extra_ips(adapter: str) -> list:
    """Return list of (ip, mask) secondary addresses on the adapter."""
    out, _, _ = run_cmd(f'netsh interface ip show address name="{adapter}"')
    results = []
    lines = out.splitlines()
    for i, line in enumerate(lines):
        stripped = line.strip()
        low = stripped.lower()
        if "ip address" in low and "subnet" not in low:
            m_ip = re.search(r"(\d+\.\d+\.\d+\.\d+)", stripped)
            if not m_ip:
                continue
            found_ip = m_ip.group(1)
            mask = ""
            for j in range(i+1, min(i+4, len(lines))):
                nxt = lines[j].strip()
                if "subnet mask" in nxt.lower():
                    m_mask = re.search(r"(\d+\.\d+\.\d+\.\d+)", nxt)
                    if m_mask:
                        mask = m_mask.group(1)
                    break
            results.append((found_ip, mask))
    return results[1:] if len(results) > 1 else []

def ping_host(host: str, count: int = 4) -> str:
    out, _, _ = run_cmd(f"ping -n {count} {host}")
    return out

def get_public_ip() -> str:
    try:
        with urllib.request.urlopen("https://api.ipify.org", timeout=5) as r:
            return r.read().decode()
    except Exception:
        return "Unavailable"
