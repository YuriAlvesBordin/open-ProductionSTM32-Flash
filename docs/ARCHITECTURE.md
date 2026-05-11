# Architecture

## Component diagram

```
┌──────────────────────────────────────────────────────────┐
│                     MainWindow                           │
│                                                          │
│  ┌─────────────────────────┐  ┌────────────────────────┐ │
│  │  FLASH tab              │  │  SETTINGS tab          │ │
│  │  · Interface / Family   │  │  · OpenOCD path        │ │
│  │  · Detect Device button │  │  · RDP level selector  │ │
│  │  · Firmware browser     │  │  · Password management │ │
│  │  · Statistics cards     │  │  · Timestamped log     │ │
│  │  · ▶ FLASH button       │  └────────────────────────┘ │
│  └─────────────────────────┘                             │
└───────────────────┬──────────────────────────────────────┘
                    │ spawns
          ┌─────────┴──────────┐
          │   _DetectorThread  │  (device auto-detect)
          │   FlashWorker      │  (flash + RDP pipeline)
          └─────────┬──────────┘
                    │ calls
          ┌─────────┴──────────┐
          │   OpenOCDRunner    │  subprocess wrapper
          └────────────────────┘
```

## Flash pipeline (FlashWorker)

| Step | OpenOCD command |
|---|---|
| 1. Init | `init` + `reset init` |
| 2. Erase & write | `flash write_image erase <firmware>` |
| 3. Verify | `flash verify_image <firmware>` |
| 4. RDP (optional) | family-specific lock command |
| 5. Reset | `reset run` |

Each step is a separate `-c` argument to avoid quoting issues on Windows and to make the command list easy to read in logs.

## Device detection (device_detector.py)

The detector opens a minimal OpenOCD session for each interface in priority order (ST-Link V2 → ST-Link V3 → CMSIS-DAP → J-Link). It reads the 32-bit **IDCODE** register (bits 27–12 identify the die), matches it against a table of ~40 known STM32 part numbers, and returns the matched interface and family labels. The whole probe times out in 5 seconds per interface.

## Threading model

- `subprocess.run()` only runs inside worker threads (`FlashWorker`, `_DetectorThread`) — never on the UI thread.
- Workers communicate back via Qt signals (`log`, `progress`, `finished`, `detected`) which are thread-safe by design.
- The UI thread never blocks.

## Error detection

OpenOCD returns exit code `0` even on some failures (USB permission denied, target not responding). `OpenOCDRunner` therefore checks **both** `returncode != 0` **and** `"Error" in stderr` to decide whether a step failed.

## Settings persistence

All settings (OpenOCD path, RDP level, password hash) are stored in `~/.stm32flash/settings.json`. Usage statistics live in `~/.stm32flash/stats.json`. Both files are plain JSON.
