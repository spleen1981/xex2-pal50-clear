#!/usr/bin/env python3
import argparse
import io
import struct
import sys
from pathlib import Path

# --- XEX2 field constants and IDs ---
# sizeof(xex::XexHeader) for XEX2 (24 bytes)
XEX2_HEADER_SIZE = 0x18

# XEX_HEADER_PRIVILEGES = XEX_HEADER_FLAG(0x0300) => (0x0300 << 8) = 0x00030000 (big-endian in file)
KEY_PRIVILEGES = 0x00030000

# PAL-50 bitmask in Title Privileges (TitlePal50Incompatible) = 0x00000400
PAL50_MASK = 0x00000400

def be32(b: bytes) -> int:
    return struct.unpack(">I", b)[0]

def be32_bytes(v: int) -> bytes:
    return struct.pack(">I", v & 0xFFFFFFFF)

def read_xex_header(bio: io.BytesIO):
    bio.seek(0)
    header = bio.read(XEX2_HEADER_SIZE)
    if len(header) != XEX2_HEADER_SIZE:
        raise ValueError("File too short to contain an XEX2 header.")
    magic = header[0:4]
    if magic != b"XEX2":
        raise ValueError(f"Non-XEX2 magic: {magic!r}")
    # Magic | ModuleFlags | SizeOfHeaders | SizeOfDiscardableHeaders | SecurityInfo | HeaderDirectoryEntryCount (all BE)
    _, module_flags, size_hdrs, size_discard, sec_off, dir_count = struct.unpack(">6I", header)
    return {
        "module_flags": module_flags,
        "size_of_headers": size_hdrs,
        "security_off": sec_off,
        "dir_count": dir_count,
    }

def parse_directory_entries(bio: io.BytesIO, dir_count: int, start_offset: int = XEX2_HEADER_SIZE):
    """
    Returns a list of (entry_offset, key, value), where entry_offset is the file offset of the 8-byte (Key,Value).
    Key and Value are host-endian integers (we read BE).
    """
    entries = []
    bio.seek(start_offset)
    for i in range(dir_count):
        off = bio.tell()
        chunk = bio.read(8)
        if len(chunk) != 8:
            raise ValueError(f"Directory truncated at entry {i}/{dir_count}.")
        key = be32(chunk[0:4])
        val = be32(chunk[4:8])
        entries.append((off, key, val))
    return entries

def main():
    p = argparse.ArgumentParser(description="Clears the PAL-50 bit (0x00000400) in Title Privileges of an XEX2.")
    p.add_argument("input", help="Path to the XEX (can also be encrypted/compressed: the directory is always in the header).")
    p.add_argument("-o", "--output", help="Output path (default: <input>.patched.xex).")
    p.add_argument("--dry-run", action="store_true", help="Does not write: only shows what would be done.")
    p.add_argument("--verbose", "-v", action="store_true", help="Print extra details.")
    args = p.parse_args()

    in_path = Path(args.input)
    if not in_path.is_file():
        print(f"[ERROR] File not found: {in_path}", file=sys.stderr)
        sys.exit(1)

    out_path = Path(args.output) if args.output else in_path.with_suffix(in_path.suffix + ".patched.xex")

    data = bytearray(in_path.read_bytes())
    bio = io.BytesIO(data)

    # 1) XEX2 Header
    hdr = read_xex_header(bio)
    if args.verbose:
        print(f"[HDR] size_of_headers=0x{hdr['size_of_headers']:X}  sec_off=0x{hdr['security_off']:X}  dir_count={hdr['dir_count']}")

    # 2) Directory entries (Key/Value BE)
    entries = parse_directory_entries(bio, hdr["dir_count"], start_offset=XEX2_HEADER_SIZE)
    if args.verbose:
        for off, k, v in entries:
            print(f"[DIR] off=0x{off:08X}  key=0x{k:08X}  val=0x{v:08X}")

    # 3) Find PRIVILEGES
    priv = next(((off, k, v) for (off, k, v) in entries if k == KEY_PRIVILEGES), None)
    if not priv:
        print("[ERROR] 'Privileges' entry (key 0x00030000) not found in directory.", file=sys.stderr)
        sys.exit(3)

    off, key, val = priv
    print(f"[OK] Privileges @ 0x{off:08X}  key=0x{key:08X}  value=0x{val:08X}")

    if (val & PAL50_MASK) == 0:
        print("[INFO] PAL-50 bit (0x00000400) is already 0: no patch needed.")
        sys.exit(0)

    new_val = val & ~PAL50_MASK
    print(f"[PATCH] 0x{val:08X}  ->  0x{new_val:08X}  (clear TitlePal50Incompatible)")

    if args.dry_run:
        print("[DRY-RUN] No write performed.")
        sys.exit(0)

    # 4) Write Value BE (the 4 bytes after Key = off+4)
    data[off+4:off+8] = be32_bytes(new_val)
    out_path.write_bytes(data)

    print(f"[DONE] Saved: {out_path}")
    print("\nVerify with:")
    print(f'  xex1tool -l "{out_path}"')
    print("You should NO LONGER see:  0xA: PAL-50 Incompatible")

if __name__ == "__main__":
    main()