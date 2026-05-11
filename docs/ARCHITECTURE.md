# Architecture

## Component Overview

```
┌─────────────────────────────────────────────────────────┐
│                      MainWindow (UI)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ FirmwarePicker│  │ OptionsCombos│  │  FlashButton  │  │
│  └──────────────┘  └──────────────┘  └───────────────┘  │
│  ┌──────────────────────────────────────────────────┐   │
│  │                   LogPanel                       │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
            │ spawns
            ▼
┌─────────────────────────┐
│      FlashWorker        │  ← QThread (non-blocking)
│  1. connect             │
│  2. flash write_image   │
│  3. verify_image        │
│  4. rdp lock            │
│  5. reset run           │
└────────────┬────────────┘
             │ calls
             ▼
┌─────────────────────────┐
│     OpenOCDRunner       │  ← subprocess wrapper
│  openocd -f iface.cfg   │
│         -f target.cfg   │
│         -c "commands"   │
└─────────────────────────┘
```

## Data Flow

1. The operator selects firmware, MCU family, interface, and RDP level in `MainWindow`.
2. `MainWindow` resolves the interface config path from `INTERFACE_MAP` and fetches `FamilyConfig` from `family_config.py`.
3. A `FlashWorker` instance is created and started — it runs entirely in a separate `QThread`.
4. `FlashWorker` calls `OpenOCDRunner.run()` for each pipeline step, emitting `log` and `progress` signals after each call.
5. `LogPanel` and `QProgressBar` in `MainWindow` update in real time via Qt signal-slot connections.
6. On `finished`, `MainWindow` re-enables the Flash button and displays the final status.

## Threading Model

- The UI thread (`QApplication` event loop) must never block.
- All `subprocess.run()` calls happen exclusively inside `FlashWorker.run()` on a background thread.
- Communication between the worker and UI uses Qt signals (`log`, `progress`, `finished`), which are thread-safe by design.

## Adding a New Pipeline Step

1. Add the OpenOCD command to the appropriate step in `FlashWorker.run()`.
2. Emit a `log` signal with a descriptive message.
3. Update `progress` to a value that keeps the bar advancing linearly.
