# RDP Levels

Read-Out Protection (RDP) controls external access to the STM32 flash memory. It is configured via the option bytes and takes effect after a reset.

## Level 0 — No protection

- Factory default (`RDP = 0xAA`).
- Full debug access. Flash can be read, written, and erased freely.
- Use only during development.

## Level 1 — Read-out protection

- Debug access is allowed, but reading flash contents over the debug interface is blocked.
- The firmware executes normally.
- **Reversible:** setting RDP back to Level 0 triggers a mass erase — the firmware is lost.
- Recommended for production when you need to keep the option of re-flashing in the field.

## Level 2 — Full debug lock ⚠️

- All debug interfaces (SWD, JTAG) are permanently disabled.
- **Irreversible:** there is no way to undo Level 2, ever.
- This level does **not** protect against firmware extraction by decapping or fault injection — it only locks the debug port.
- Use only when you are certain the device will never need firmware updates or debugging.

## Option byte values

| Level | RDP byte | NRDP byte |
|---|---|---|
| 0 | `0xAA` | `0x55` |
| 1 | `0xBB` | `0x44` |
| 2 | `0xCC` | `0x33` |

Values vary slightly between families (F1, G0/G4/L4, H7). The OpenOCD command used by this tool is family-specific and sourced from the respective ST reference manual.

## How this tool applies RDP

After a successful flash + verify, the tool sends the lock command for the selected level via OpenOCD. The device is then reset. The RDP takes effect immediately after reset — no re-flash is needed.

The app will show a confirmation popup before applying Level 1 or Level 2, describing the exact consequences.
