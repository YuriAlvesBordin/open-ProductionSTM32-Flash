# STM32 Production Flasher

A desktop GUI tool built with **PyQt6** to automate firmware flashing and **Read Protection (RDP)** activation on STM32 microcontrollers in production environments, using [OpenOCD](https://openocd.org/) as the backend.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![PyQt6](https://img.shields.io/badge/PyQt6-6.4%2B-green)
![OpenOCD](https://img.shields.io/badge/OpenOCD-0.12%2B-orange)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

---

## Overview

This tool is designed for **embedded firmware engineers** who need a reliable, repeatable flashing process on the production line. It removes human error by automatically:

1. Connecting to the target via SWD/JTAG through OpenOCD
2. Erasing and flashing the firmware binary
3. Verifying the written data against the source file
4. Activating the RDP (Read-Out Protection) at the configured level
5. Resetting the MCU into normal execution

All steps run sequentially in a background thread — the UI stays responsive and the operator always sees exactly what is happening.

---

## Screenshots

> _Coming soon — screenshots of the production UI will be added here._

---

## Supported MCU Families

| Family | Flash Command | RDP Command |
|--------|--------------|-------------|
| STM32F0 / F1 | `flash write_image erase` | `stm32f1x lock 0` |
| STM32F2 / F4 | `flash write_image erase` | `stm32f2x lock 0` |
| STM32F7 | `flash write_image erase` | `stm32f7x lock 0` |
| STM32G0 | `flash write_image erase` | `stm32l4x lock 0` |
| STM32G4 / L4 | `flash write_image erase` | `stm32l4x lock 0` |
| STM32H7 | `flash write_image erase` | `stm32h7x lock 0` |
| STM32L0 / L1 | `flash write_image erase` | `stm32lx lock 0` |

Adding a new family requires only one entry in `src/core/family_config.py` — no other changes needed.

---

## Project Structure

```
stm32-production-flasher/
├── src/
│   ├── core/
│   │   ├── family_config.py   # MCU family → OpenOCD command mapping
│   │   ├── flash_worker.py    # QThread: flash + RDP pipeline
│   │   └── openocd_runner.py  # Low-level subprocess wrapper for OpenOCD
│   ├── ui/
│   │   ├── main_window.py     # Top-level QWidget: layout and wiring
│   │   ├── settings_tab.py    # Password-protected settings tab with logs and stats
│   │   └── log_panel.py       # Legacy log panel (kept for compatibility)
│   └── main.py                # Entry point: QApplication bootstrap
├── config/
│   └── interfaces/
│       ├── stlink_swd.cfg     # ST-LINK v2 SWD config (ready to use)
│       └── jlink_swd.cfg      # J-Link SWD config (ready to use)
├── docs/
│   ├── ARCHITECTURE.md        # Component diagram and data-flow description
│   ├── RDP_LEVELS.md          # RDP Level 0/1/2 explanation and risks
│   └── ADDING_FAMILIES.md     # Step-by-step guide to add a new MCU family
├── tests/
│   ├── test_family_config.py  # Unit tests for family_config lookups
│   └── test_openocd_runner.py # Unit tests with mocked subprocess
├── .github/
│   └── workflows/
│       └── ci.yml             # GitHub Actions: lint + test on push
├── .gitignore
├── pyproject.toml
├── requirements.txt
└── LICENSE
```

---

## Requirements

- Python 3.10+
- [OpenOCD 0.12+](https://openocd.org/pages/getting-started.html)
- An ST-Link v2, J-Link, or compatible SWD/JTAG probe

---

## Installation

```bash
git clone https://github.com/YuriAlvesBordin/open-ProductionSTM32-Flash.git
cd open-ProductionSTM32-Flash
pip install -r requirements.txt
```

### Installing OpenOCD

If OpenOCD is not installed on your system, install it using the appropriate command for your platform:

**Debian / Ubuntu**
```sh
sudo apt install openocd
```

**Fedora**
```sh
sudo dnf install openocd
```

**macOS (via Homebrew)**
```sh
brew install open-ocd
```

**Windows (via MSYS2)**
```sh
pacman -S mingw-w64-x86_64-openocd
```

> The application will attempt to auto-detect OpenOCD at startup. If it is not found automatically, set the path manually in the **Settings** tab.

---

## Usage

```bash
python src/main.py
```

### Step-by-step

1. Click **Browse** and select your firmware file (`.bin`, `.hex`, or `.elf`)
2. Choose the **MCU Family** from the dropdown
3. Select the **Interface** (SWD or JTAG)
4. Toggle **RDP Level 1** if read protection should be enabled after flashing (see [`docs/RDP_LEVELS.md`](docs/RDP_LEVELS.md) before using Level 2)
5. Click **▶ FLASH** and monitor progress

A green completion message confirms the device is flashed and protected.

---

## RDP Levels — Quick Reference

| Level | Value | Reversible | Effect |
|-------|-------|------------|--------|
| 0 | `0xAA` | Yes | No protection (factory default) |
| 1 | `0xBB` | Yes\* | Blocks debug readout; code still runs normally |
| 2 | `0xCC` | **Never** | Permanently disables all debug access |

\* _Level 1 → Level 0 requires a full flash erase (firmware is lost)._

See [`docs/RDP_LEVELS.md`](docs/RDP_LEVELS.md) for the full technical reference.

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/your-feature`
3. Commit using [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `docs:`, `refactor:`
4. Open a Pull Request against `main`

---

## License

MIT — see [`LICENSE`](LICENSE) for details.
