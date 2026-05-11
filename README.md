# STM32 Production Flasher

Desktop GUI for flashing STM32 firmware and configuring Read Protection (RDP) on the production line. Powered by [OpenOCD](https://openocd.org/) under the hood.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![PyQt6](https://img.shields.io/badge/PyQt6-6.4%2B-green)
![OpenOCD](https://img.shields.io/badge/OpenOCD-0.12%2B-orange)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

---

## What it does

- Connects to the target over SWD/JTAG, erases flash, writes the firmware and verifies it
- Auto-detects the connected MCU family and debug interface (ST-Link, J-Link, CMSIS-DAP)
- Applies the configured RDP level after a successful flash
- Keeps a timestamped system log and usage statistics
- Settings (OpenOCD path, RDP level, password) are protected behind an optional password

Everything runs in a background thread — the UI stays responsive throughout.

---

## Supported hardware

| MCU family | OpenOCD target config |
|---|---|
| STM32F0 / F1 | `target/stm32f1x.cfg` |
| STM32F2 / F4 | `target/stm32f4x.cfg` |
| STM32F7 | `target/stm32f7x.cfg` |
| STM32G0 | `target/stm32g0x.cfg` |
| STM32G4 / L4 | `target/stm32l4x.cfg` |
| STM32H7 | `target/stm32h7x.cfg` |
| STM32L0 / L1 | `target/stm32l0.cfg` |

To add a new family, add one entry to `src/core/family_config.py`. See [`docs/ADDING_FAMILIES.md`](docs/ADDING_FAMILIES.md).

**Debug interfaces:** ST-Link V2, ST-Link V3, J-Link, CMSIS-DAP.

---

## Requirements

- Python 3.10+
- OpenOCD 0.12+
- ST-Link V2/V3, J-Link, or any CMSIS-DAP probe

---

## Quick Install

The repository ships with installation scripts that handle everything in one step: virtual environment, dependencies, and an optional standalone build.

### Windows

```bat
git clone https://github.com/YuriAlvesBordin/open-ProductionSTM32-Flash.git
cd open-ProductionSTM32-Flash
install.bat
```

The script will:
1. Verify that Python 3.10+ is available in `PATH` (fails with a clear message if not)
2. Create a `.venv` virtual environment in the project folder
3. Install all dependencies from `requirements.txt` (PyQt6)
4. Ask at the end whether you want to build a standalone `.exe` with Nuitka

> **Tip — Python not found?**  
> Download from [python.org](https://www.python.org/downloads/) and check **"Add Python to PATH"** during installation.

### Linux / macOS

```bash
git clone https://github.com/YuriAlvesBordin/open-ProductionSTM32-Flash.git
cd open-ProductionSTM32-Flash
chmod +x install.sh
./install.sh
```

The script will:
1. Locate a compatible Python 3.10+ interpreter (`python3`, `python3.12`, etc.)
2. Create a `.venv` virtual environment
3. Install all dependencies
4. Ask at the end whether you want to build a standalone binary with Nuitka

> **Tip — Python not found?**  
> `sudo apt install python3` (Debian/Ubuntu) · `brew install python` (macOS)

### Building a standalone executable (optional)

At the end of either script you will be prompted:

```
Build a standalone executable with Nuitka? [y/N]:
```

Answer **`y`** to compile a self-contained binary that runs without Python installed. Nuitka will be installed automatically inside the virtual environment. The output lands in `dist/`:

| Platform | Output file |
|---|---|
| Windows | `dist\STM32Flash.exe` |
| Linux | `dist/STM32Flash` |
| macOS | `dist/STM32Flash` |

The build bundles the `config/` directory and disables the console window on Windows. It may take a few minutes depending on your machine.

> **Note:** Nuitka requires a C compiler. On Windows this means [Visual C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) or MinGW. On Linux/macOS `gcc` or `clang` will work.

---

## Manual installation

If you prefer to manage the environment yourself:

```bash
git clone https://github.com/YuriAlvesBordin/open-ProductionSTM32-Flash.git
cd open-ProductionSTM32-Flash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

### Installing OpenOCD

**Debian / Ubuntu**
```bash
sudo apt install openocd
```

**Fedora**
```bash
sudo dnf install openocd
```

**macOS**
```bash
brew install open-ocd
```

**Windows (MSYS2)**
```bash
pacman -S mingw-w64-x86_64-openocd
```

The app auto-detects OpenOCD at startup. If it is not found, set the path manually in **Settings**.

---

## Running

```bash
# Activate the virtual environment first
source .venv/bin/activate      # Linux / macOS
.venv\Scripts\activate          # Windows

python src/main.py
```

### Typical workflow

1. Click **Browse** and select the firmware file (`.bin`, `.hex`, or `.elf`)
2. Click **Detect Device** — the interface and MCU family are filled automatically
3. Set the RDP level in **Settings** (default: Level 1)
4. Click **▶ FLASH**

Flash, verify and RDP steps run in sequence. The status bar and log show progress in real time.

---

## RDP levels

| Level | Protection | Reversible |
|---|---|---|
| 0 | None (factory default) | Yes |
| 1 | Blocks debug read-out of flash | Yes — but reverting erases the firmware |
| 2 | Permanently disables all debug access | **Never** |

The app shows a confirmation popup before applying Level 1 or Level 2. See [`docs/RDP_LEVELS.md`](docs/RDP_LEVELS.md) for the full technical reference.

---

## Project layout

```
src/
  core/
    device_detector.py   # Auto-detect MCU family and interface via IDCODE probe
    family_config.py     # MCU family → OpenOCD command mapping
    flash_worker.py      # QThread: flash + verify + RDP pipeline
    openocd_runner.py    # subprocess wrapper for OpenOCD
  ui/
    main_window.py       # Main window, tabs, device detection UI
    settings_tab.py      # Password-protected settings, log, stats
  main.py                # Entry point
config/
  interfaces/            # Ready-to-use OpenOCD interface configs
docs/
  ARCHITECTURE.md
  RDP_LEVELS.md
  ADDING_FAMILIES.md
tests/
install.bat              # Windows installer
install.sh               # Linux / macOS installer
```

---

## Contributing

1. Fork the repo and create a branch: `git checkout -b feat/your-feature`
2. Use [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `docs:`, `refactor:`
3. Open a pull request against `main`

---

## License

MIT — see [`LICENSE`](LICENSE).
