# RDP Levels — Technical Reference

Read-Out Protection (RDP) is an STM32 security feature that restricts access to the internal flash memory through the debug port (SWD/JTAG).

---

## Level 0 — No Protection

- **Option byte value:** `0xAA`
- **Reversible:** Yes
- **Effect:** Factory default. Flash memory is fully readable via debugger. No restrictions.
- **When to use:** Development and bring-up only.

---

## Level 1 — Read Protection

- **Option byte value:** Any value except `0xAA` and `0xCC` (typically `0xBB`)
- **Reversible:** Yes, but at a cost
- **Effect:**
  - Flash and backup SRAM cannot be read or written via the debug port.
  - Code execution continues normally.
  - Going back to Level 0 triggers a **mass erase** of the entire flash — firmware is lost.
- **When to use:** Standard production use. Protects IP while still allowing rework.

---

## Level 2 — Chip Protection

- **Option byte value:** `0xCC`
- **Reversible:** **Never — this is a one-way, permanent operation.**
- **Effect:**
  - All debug ports (SWD, JTAG, JTAG-DP) are permanently disabled.
  - The device cannot be reprogrammed in any way.
  - ST cannot reverse this, even with physical access to the chip.
- **When to use:** Highest-security products only. Use only when you are 100% certain the firmware is final and no rework is ever needed.

---

## Risk Matrix

| Scenario | Level 1 | Level 2 |
|----------|---------|----------|
| Firmware bug found after production | Rework possible (mass erase + re-flash) | Device must be scrapped |
| Attacker with physical access | Cannot read flash via probe | Cannot read flash, cannot re-program |
| Rework / warranty repair | Possible with mass erase | Impossible |

---

## How OpenOCD Activates RDP

This tool uses the family-specific lock command after writing the option bytes:

```tcl
# Example for STM32F4
init
reset halt
stm32f2x lock 0
reset run
```

The MCU resets after the command to apply the new option bytes from its OTP area.
