"""Auto-detection of STM32 family and debug interface using OpenOCD.

Strategy
--------
For each interface (ST-Link → CMSIS-DAP → J-Link) we run a minimal OpenOCD
session using proper -f / -c arguments.  When OpenOCD successfully initialises
the DAP it always prints a line like:

    Info : STM32F4xx.cpu: hardware has 6 breakpoints, 4 watchpoints
    Info : IDCODE: 0x2BA01477          ← SWD DP IDCODE  (not the MCU IDCODE)

More usefully, it prints the *device* IDCODE via the target examination:

    Info : stm32f4x.cpu: target halted due to debug-request ...
    Info : device id = 0x10006413      ← this is the MCU part number

We capture ALL of stdout+stderr and run several regexes that cover the
different formats OpenOCD 0.11, 0.12 and git-master use.  The first
non-trivial 32-bit value whose bits[27:12] match a known STM32 part wins.
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from typing import Optional

from core.family_config import FAMILY_MAP, INTERFACE_MAP

# ── IDCODE table ──────────────────────────────────────────────────────────────
# Tuple: (mask, expected, family_label)
# Mask and expected are applied to the raw 32-bit value read from the device.
# Source: ST reference manuals (RM0008, RM0090, RM0385, RM0394, RM0440, RM0468)
# and OpenOCD source (src/flash/nor/stm32*).
_IDCODE_TABLE: list[tuple[int, int, str]] = [
    # STM32F0 / F1
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
    # STM32F7
    (0x0FFFF000, 0x00451000, "STM32F7"),       # F76x / F77x
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
    (0x0FFFF000, 0x00483000, "STM32H7"),       # H723 / H725 / H733 / H735
    # STM32L0 / L1
    (0x0FFFF000, 0x00426000, "STM32L0/L1"),   # L1xx Cat.1
    (0x0FFFF000, 0x00436000, "STM32L0/L1"),   # L1xx Cat.5/6
    (0x0FFFF000, 0x00427000, "STM32L0/L1"),   # L1xx Cat.2
    (0x0FFFF000, 0x00437000, "STM32L0/L1"),   # L152
    (0x0FFFF000, 0x00447000, "STM32L0/L1"),   # L0xx Cat.5
    (0x0FFFF000, 0x00425000, "STM32L0/L1"),   # L0xx Cat.1
    (0x0FFFF000, 0x00417000, "STM32L0/L1"),   # L0xx Cat.3
]

# Interface probe order (most common first).
# Each entry: (interface_label, cfg_file, transport)
# transport is passed as a -c argument so we don't rely on the cfg default.
_PROBE_SEQUENCE: list[tuple[str, str, str]] = [
    ("ST-Link V2",  "interface/stlink.cfg",    "swd"),
    ("ST-Link V3",  "interface/stlink.cfg",    "swd"),
    ("CMSIS-DAP",   "interface/cmsis-dap.cfg", "swd"),
    ("J-Link",      "interface/jlink.cfg",     "swd"),
]

# ── IDCODE patterns emitted by OpenOCD ───────────────────────────────────────
# OpenOCD prints the MCU device id in several formats depending on version:
#
#   "device id = 0x10006413"          (most flash drivers, very reliable)
#   "idcode: 0x2BA01477"              (SWD DP — this is the ARM DAP id, NOT the MCU)
#   "tap/device found: 0x2BA01477"    (JTAG tap scan)
#   "0x10006413 (mfg: ..."            (some versions)
#
# We prioritise "device id" because it is the MCU part number.
# The DAP IDCODE (0x2BA01477 for Cortex-M4 etc.) is ARM-standard and will
# NOT match any STM32 entry in our table — so even if we accidentally capture
# it, the family lookup will fail and we skip to the next pattern.

_PATTERNS: list[re.Pattern] = [
    re.compile(r"device\s+id\s*=\s*0x([0-9A-Fa-f]{8})", re.IGNORECASE),
    re.compile(r"device_id\s*=\s*0x([0-9A-Fa-f]{8})", re.IGNORECASE),
    re.compile(r"\bchip\s+id\s*[=:]\s*0x([0-9A-Fa-f]{8})", re.IGNORECASE),
    re.compile(r"tap/device found:\s*0x([0-9A-Fa-f]{8})", re.IGNORECASE),
    re.compile(r"idcode[:\s]+0x([0-9A-Fa-f]{8})", re.IGNORECASE),
    re.compile(r"0x([0-9A-Fa-f]{8})\s+\(mfg:", re.IGNORECASE),
]

_SKIP_VALUES = {0x00000000, 0xFFFFFFFF, 0x2BA01477, 0x1BA01477, 0x0BA01477}


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
    """Return the first MCU device ID found in OpenOCD output, or None."""
    for pattern in _PATTERNS:
        for m in pattern.finditer(text):
            val = int(m.group(1), 16)
            if val in _SKIP_VALUES:
                continue
            # Only consider values that look like STM32 device IDs:
            # manufacturer bits [11:1] = 0x20 (ST) → bits[11:1] & 0xFFE = 0x040
            # We accept anything not in the skip list and try the family match.
            return val
    return None


def _build_args(openocd_path: str, iface_cfg: str, transport: str) -> list[str]:
    """Build the openocd command-line for a probe run.

    Uses -f for config files and individual -c for each command so OpenOCD
    parses them correctly on all platforms (avoids newline/quoting issues).
    """
    return [
        openocd_path,
        "-f", iface_cfg,
        "-c", f"transport select {transport}",
        "-c", "adapter speed 1000",
        "-c", "init",
        "-c", "shutdown",
    ]


def _run_probe(openocd_path: str, iface_cfg: str, transport: str,
               timeout: float = 6.0) -> str:
    """Run OpenOCD and return combined stdout + stderr."""
    try:
        result = subprocess.run(
            _build_args(openocd_path, iface_cfg, transport),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return ""
    except (FileNotFoundError, OSError):
        return ""


def detect_device(
    openocd_path: str,
    progress_cb=None,
) -> Optional[DetectionResult]:
    """Probe the connected device and return interface + family labels.

    Args:
        openocd_path: Absolute path to the openocd executable.
        progress_cb:  Optional callable(str) for live status messages.

    Returns:
        DetectionResult on success, None if no device was matched.
    """
    def _emit(msg: str) -> None:
        if progress_cb:
            progress_cb(msg)

    for iface_label, iface_cfg, transport in _PROBE_SEQUENCE:
        _emit(f"Probing {iface_label}...")

        output = _run_probe(openocd_path, iface_cfg, transport)

        if not output:
            # Timeout or binary not found — skip silently.
            continue

        idcode = _parse_idcode(output)

        if idcode is None:
            # OpenOCD ran but produced no recognisable device ID.
            # Log the first meaningful error line to help diagnostics.
            for line in output.splitlines():
                line = line.strip()
                if line and ("Error" in line or "Warn" in line or "failed" in line.lower()):
                    _emit(f"  {line}")
                    break
            continue

        family = _match_family(idcode)
        if family is None:
            _emit(f"  IDCODE 0x{idcode:08X} not in table — update device_detector.py")
            # Still return partial result so the user can set family manually.
            return DetectionResult(
                interface_label=iface_label,
                family_label="",
                idcode=idcode,
                raw_output=output,
            )

        return DetectionResult(
            interface_label=iface_label,
            family_label=family,
            idcode=idcode,
            raw_output=output,
        )

    return None
