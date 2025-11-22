# xex2-pal50-clear

A Python utility to patch Xbox 360 **XEX2** executables by **clearing the PAL-50 incompatibility bit** (`0x00000400`) in **Title Privileges** (`key 0x00030000`).  
This removes the "PAL-50 Incompatible" flag from the XEX header, which can help with region compatibility.

> ⚠️ This tool **only modifies the header directory entry**. It does **not** decrypt, decompress, or alter the code segment. Use at your own risk and always keep backups.

---

## Features

- Reads XEX2 header and directory entries (big-endian format).
- Locates the `Privileges` entry (`key = 0x00030000`).
- Clears the `PAL-50` mask (`0x00000400`) if present.
- Supports **dry-run** mode for safe preview.
- Verbose mode for detailed header and directory info.
- Writes a patched copy (`*.patched.xex`) by default.

---

## Requirements

- Python **3.8+**
- No external dependencies (uses only standard library).
- Works on Windows, macOS, and Linux.

---

## Installation

No installation required. Just download or copy the script locally.

```bash
# Optional: make it executable on Unix-like systems
chmod +x xex2-pal50-clear.py
```

---

## Usage

```bash
python3 xex2-pal50-clear.py INPUT.xex [-o OUTPUT.xex] [--dry-run] [-v]
```

---

## Arguments

- `INPUT.xex`  
  Path to the XEX file (encrypted/compressed is fine; header directory is always readable).

- `-o, --output OUTPUT.xex`  
  Output path. Default: `<INPUT>.patched.xex`.

- `--dry-run`  
  Do not write changes; only display what would be patched.

- `-v, --verbose`  
  Print extra details (header fields and directory entries).

---

## Examples

**Basic patch:**
```bash
python3 xex2-pal50-clear.py game.xex
```

**Dry-run (no writing):**
```bash
python3 xex2-pal50-clear.py game.xex --dry-run -v
```

**Custom output file:**
```bash
python3 xex2-pal50-clear.py game.xex -o game_no_pal50.xex
```

---

## Output Messages (What to Expect)

- When the `Privileges` entry is found:
  ```
  [OK] Privileges @ 0x00000080  key=0x00030000  value=0x00000C00
  ```

- If PAL-50 bit is already clear:
  ```
  [INFO] PAL-50 bit (0x00000400) is already 0: no patch needed.
  ```

- Patch action:
  ```
  [PATCH] 0x00000C00  ->  0x00000800  (clear TitlePal50Incompatible)
  [DONE] Saved: game.xex.patched.xex
  ```

---

## Exit Codes

- `0` — Success (patched or nothing to do).
- `1` — Input file not found.
- `3` — `Privileges` entry not found in header directory.
- Other — Unexpected errors (e.g., truncated header).

---

## How It Works (Technical Overview)

1. Reads the first `0x18` bytes (**XEX2 header**) and validates magic `XEX2`.
2. Parses the header directory (list of BE `(key, value)` pairs).
3. Searches for **`KEY_PRIVILEGES = 0x00030000`**.
4. If bit **`PAL50_MASK = 0x00000400`** is set in `value`, clears it and writes the updated big-endian value back to the file at `entry_offset + 4`.
5. Writes to the specified output path (or default `*.patched.xex`).

---

## Verification

You can verify the patched header with tools like `xex1tool`:

```bash
xex1tool -l "game.xex.patched.xex"
```

You should **no longer** see:
```
0xA: PAL-50 Incompatible
```

---

## Limitations & Notes

- Works **only** with **XEX2** files (magic `XEX2`).
- Does not decompress or decrypt payloads; modifies **header directory value only**.
- If a title enforces PAL-50 through other means (e.g., runtime checks), removing the flag may not change behavior.
- Always **back up your original** XEX file before patching.

---

## FAQ

**Q: Will this fix all PAL-50 issues?**  
A: No. It only clears the **header flag**. Any runtime enforcement or engine-level checks remain.

**Q: Can I use this on XEX1?**  
A: No. This tool expects the **XEX2** header format and magic.

**Q: Is it safe for compressed/encrypted XEX files?**  
A: Yes. The header directory is readable regardless. The payload is untouched.
