"""Auto-detection of STM32 family and debug interface using OpenOCD.

Strategy:
  1. For each interface in priority order, run a short OpenOCD session that
     executes 'jtag arp_init' (or 'init') followed by 'dap info' / idcode read.
  2. Parse stdout/stderr for a known IDCODE pattern.
  3. Map the IDCODE to a FamilyConfig entry.
  4. Return the matched interface label and family label on success.

The probe script is intentionally minimal so it exits quickly even on failure.
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from typing import Optional

from core.family_config import FAMILY_MAP, INTERFACE_MAP

# ── IDCODE → family mapping ───────────────────────────────────────────────────
# Key: hex mask (applied with bitwise-AND before comparison)
# Each entry: (mask, expected_value, family_label)
#
# STM32 IDCODE format:  bits[31:28]=version, bits[27:12]=part_no, bits[11:1]=mfg_id
# We match on part_no (bits 27:12) only, using mask 0x0FFFF000.
#
# Values sourced from ST RM0008, RM0090, RM0385, RM0394, RM0440, RM0468.
_PART_MASK = 0x0FFFF000

_IDCODE_TABLE: list[tuple[int, int, str]] = [
    # STM32F0 / F1 (stm32f1x.cfg)
    (0x0FFFF000, 0x00006000, "STM32F0/F1"),   # F100
    (0x0FFFF000, 0x00010000, "STM32F0/F1"),   # F101
    (0x0FFFF000, 0x00012000, "STM32F0/F1"),   # F102
    (0x0FFFF000, 0x00014000, "STM32F0/F1"),   # F103
    (0x0FFFF000, 0x00018000, "STM32F0/F1"),   # F105/F107
    (0x0FFFF000, 0x00020000, "STM32F0/F1"),   # F0 (410)
    (0x0FFFF000, 0x00080000, "STM32F0/F1"),   # F0 (411)
    # STM32F2 / F4
    (0x0FFFF000, 0x00411000, "STM32F2/F4"),   # F2xx
    (0x0FFFF000, 0x00413000, "STM32F2/F4"),   # F40x / F41x
    (0x0FFFF000, 0x00419000, "STM32F2/F4"),   # F42x / F43x
    (0x0FFFF000, 0x00434000, "STM32F2/F4"),   # F469 / F479
    (0x0FFFF000, 0x00423000, "STM32F2/F4"),   # F401xB/C
    (0x0FFFF000, 0x00433000, "STM32F2/F4"),   # F401xD/E
    (0x0FFFF000, 0x00458000, "STM32F2/F4"),   # F410
    (0x0FFFF000, 0x00431000, "STM32F2/F4"),   # F411
    (0x0FFFF000, 0x00441000, "STM32F2/F4"),   # F412
    (0x0FFFF000, 0x00463000, "STM32F2/F4"),   # F413 / F423
    (0x0FFFF000, 0x00421000, "STM32F2/F4"),   # F446
    (0x0FFFF000, 0x00449000, "STM32F2/F4"),   # F74x / F75x
    (0x0FFFF000, 0x00451000, "STM32F7"),       # F76x / F77x
    # STM32F7
    (0x0FFFF000, 0x00452000, "STM32F7"),       # F72x / F73x
    # STM32G0
    (0x0FFFF000, 0x00460000, "STM32G0"),       # G07x / G08x
    (0x0FFFF000, 0x00466000, "STM32G0"),       # G03x / G04x
    (0x0FFFF000, 0x00467000, "STM32G0"),       # G0B1 / G0C1
    # STM32G4 / L4
    (0x0FFFF000, 0x00468000, "STM32G4/L4"),   # G431 / G441
    (0x0FFFF000, 0x00469000, "STM32G4/L4"),   # G47x / G48x
    (0x0FFFF000, 0x00479000, "STM32G4/L4"),   # G491 / G4A1
    (0x0FFFF000, 0x00415000, "STM32G4/L4"),   # L4x1 / L4x2
    (0x0FFFF000, 0x00435000, "STM32G4/L4"),   # L43x / L44x
    (0x0FFFF000, 0x00462000, "STM32G4/L4"),   # L45x / L46x
    (0x0FFFF000, 0x00470000, "STM32G4/L4"),   # L4Rx / L4Sx (L4+)
    (0x0FFFF000, 0x00471000, "STM32G4/L4"),   # L4P5 / L4Q5 (L4+)
    # STM32H7
    (0x0FFFF000, 0x00450000, "STM32H7"),       # H74x / H75x
    (0x0FFFF000, 0x00480000, "STM32H7"),       # H7A3 / H7B3 / H7B0
    (0x0FFFF000, 0x00483000, "STM32H7"),       # H723 / H725 / H730 / H733 / H735
    # STM32L0 / L1
    (0x0FFFF000, 0x00426000, "STM32L0/L1"),   # L1xx Cat.1
    (0x0FFFF000, 0x00436000, "STM32L0/L1"),   # L1xx Cat.5/6
    (0x0FFFF000, 0x00427000, "STM32L0/L1"),   # L1xx Cat.2
    (0x0FFFF000, 0x00437000, "STM32L0/L1"),   # L152
    (0x0FFFF000, 0x00447000, "STM32L0/L1"),   # L0xx Cat.5
    (0x0FFFF000, 0x00425000, "STM32L0/L1"),   # L0xx Cat.1
    (0x0FFFF000, 0x00417000, "STM32L0/L1"),   # L0xx Cat.3
]

# Probe interfaces in this order (most common first)
_INTERFACE_PRIORITY = ["ST-Link V2", "ST-Link V3", "CMSIS-DAP", "J-Link"]

# Regex to capture a 32-bit hex IDCODE from OpenOCD output
_IDCODE_RE = re.compile(r"idcode[:\s]+0x([0-9A-Fa-f]{8})", re.IGNORECASE)
_IDCODE_RE2 = re.compile(r"tap/device found:\s*0x([0-9A-Fa-f]{8})", re.IGNORECASE)
_IDCODE_RE3 = re.compile(r"0x([0-9A-Fa-f]{8})\s+\(mfg:", re.IGNORECASE)

# Minimal OpenOCD script that probes IDCODE then exits
_PROBE_SCRIPT = """
adapter speed 500
init
set idcode [expr {[dap apreg 0 0xFC] & 0x0FFFFFFF}]
echo "PROBE_IDCODE: $idcode"
shutdown
"""

# Fallback script for older OpenOCD without dap command
_PROBE_SCRIPT_LEGACY = """
adapter speed 500
init
echo "PROBE_IDCODE: [format 0x%08x [jtag cget [target current] -idcode]]"
shutdown
"""


@dataclass
class DetectionResult:
    interface_label: str
    family_label: str
    idcode: int
    raw_output: str


def _match_family(idcode: int) -> Optional[str]:
    for mask, expected, family in _IDCODE_TABLE:
        if (idcode & mask) == (expected & mask):
            return family
    return None


def _parse_idcode(text: str) -> Optional[int]:
    for pattern in (_IDCODE_RE, _IDCODE_RE2, _IDCODE_RE3):
        m = pattern.search(text)
        if m:
            val = int(m.group(1), 16)
            if val not in (0x00000000, 0xFFFFFFFF):
                return val
    # Also try the custom PROBE_IDCODE echo
    m2 = re.search(r"PROBE_IDCODE:\s*(0x[0-9A-Fa-f]+|[0-9]+)", text)
    if m2:
        raw = m2.group(1)
        val = int(raw, 16) if raw.startswith("0x") else int(raw)
        if val not in (0, 0xFFFFFFFF):
            return val
    return None


def _run_probe(
    openocd_path: str,
    interface_cfg: str,
    timeout: float = 5.0,
) -> str:
    """Run a quick OpenOCD probe and return combined stdout+stderr."""
    script = (
        f"source [find {interface_cfg}]\n"
        "transport select swd\n"
        + _PROBE_SCRIPT
    )
    try:
        result = subprocess.run(
            [openocd_path, "-c", script],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout + result.stderr
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return ""


def detect_device(
    openocd_path: str,
    progress_cb=None,
) -> Optional[DetectionResult]:
    """
    Attempt to auto-detect the connected STM32 family and debug interface.

    Args:
        openocd_path: Full path to the openocd executable.
        progress_cb:  Optional callable(str) for status messages.

    Returns:
        DetectionResult on success, None if detection fails.
    """
    def _emit(msg: str) -> None:
        if progress_cb:
            progress_cb(msg)

    for iface_label in _INTERFACE_PRIORITY:
        if iface_label not in INTERFACE_MAP:
            continue
        iface_cfg = INTERFACE_MAP[iface_label]
        _emit(f"Probing via {iface_label}...")

        output = _run_probe(openocd_path, iface_cfg)
        idcode = _parse_idcode(output)

        if idcode is None:
            continue

        family = _match_family(idcode)
        if family is None:
            _emit(f"Unknown IDCODE 0x{idcode:08X} on {iface_label} — not matched.")
            continue

        return DetectionResult(
            interface_label=iface_label,
            family_label=family,
            idcode=idcode,
            raw_output=output,
        )

    return None
