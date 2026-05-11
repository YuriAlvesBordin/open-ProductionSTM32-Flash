# Architecture

## Component Overview

```
┌─────────────────────────────────────────────────────┐
│                   MainWindow (UI)                   │
│                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │
│  │ OpenOCD path│  │  Combos     │  │ FlashButton│  │
│  │  + Browse   │  │ Iface/Family│  │ + RDP tog. │  │
│  └─────────────┘  └─────────────┘  └────────────┘  │
│  ┌─────────────────────────────────────────────┐    │
│  │               LogPanel                      │    │
│  └─────────────────────────────────────────────┘    │
└──────────────────────────┬──────────────────────────┘
                           │ spawns
                           ▼
          ┌────────────────────────────┐
          │       FlashWorker          │  ← QThread
          │  1. init + reset init      │
          │  2. flash write_image erase│
          │  3. flash verify_image     │
          │  4. rdp lock (optional)    │
          │  5. reset run              │
          └──────────────┬─────────────┘
                         │ calls
                         ▼
          ┌────────────────────────────┐
          │      OpenOCDRunner         │  ← subprocess wrapper
          │  openocd -f iface.cfg      │
          │          -f target.cfg     │
          │          -c cmd1           │
          │          -c cmd2 ...       │
          └────────────────────────────┘
```

## Data Flow

1. The operator sets the OpenOCD path (auto-detected via `shutil.which` on startup), selects the firmware file, MCU family, interface, and toggles the RDP option.
2. `MainWindow` calls `get_config()` and `get_interface_cfg()` to resolve the `FamilyConfig` and interface `.cfg` path.
3. A `FlashWorker` is created and started on a background `QThread`.
4. `FlashWorker` calls `OpenOCDRunner.run()` once per pipeline stage, passing each OpenOCD command as a separate `-c` argument.
5. Each call emits `log(message, level)` and `progress(value)` signals consumed by `MainWindow`.
6. `LogPanel` renders colored HTML lines; `QProgressBar` advances in real time.
7. On `finished(success, message)`, `MainWindow` shows a `QMessageBox` and re-enables the Flash button.

## Why Each Command is a Separate `-c` Argument

OpenOCD's TCL interpreter evaluates each `-c` argument as a separate statement. Passing them individually (instead of joining with `;`) avoids quoting issues on Windows paths and makes the command list easy to inspect in logs.

## Error Detection

OpenOCD frequently returns exit code `0` even when an error occurs (e.g., USB permission denied, target not responding). `OpenOCDRunner.run()` therefore checks **both** `returncode != 0` **and** `"Error" in stderr` to determine failure — mirroring the behavior of the reference implementation.

## Threading Model

- All `subprocess.run()` calls run exclusively inside `FlashWorker.run()` on a background thread.
- Qt signals (`log`, `progress`, `finished`) are the only communication channel between worker and UI — they are thread-safe by design.
- The UI thread never blocks.
