"""Build the 98348 unit spatial descriptor and advance its raw CRC for known operations."""

from struct import Struct, pack
from zlib import crc32

LAYOUT = Struct("<IHHI")
U32 = 0xFFFFFFFF


def signed32(value):
    word = value & U32
    return word if word < 1 << 31 else word - (1 << 32)


def position_fields(tag, owner, x, y):
    """Return the known low 24 bits, X cell and Y cell for native fixed-point coordinates."""
    if not 0 <= tag <= U32 or not 0 <= owner <= 255:
        raise ValueError("Tag or owner outside its native field")
    if (x, y) != (signed32(x), signed32(y)):
        raise ValueError("Expected signed native fixed-point XY")
    low = (tag >> 22) | ((owner & 15) << 14) | (((x >> 10) & 7) << 18) | (((y >> 10) & 7) << 21)
    # Native cdq/sub/sar divides by two toward zero before its cell shift.
    return low, (((x + (x < 0)) >> 1) >> 12) & 0xffff, (((y + (y < 0)) >> 1) >> 12) & 0xffff


def descriptor(tag, owner, x, y, radius, *, collision_flags, state38, type_de, state4c, state3c, state41):
    """Supply the selected Radius/DeadRadius and effective collision flags for this unit state."""
    if radius != signed32(radius) or not 0 <= collision_flags <= U32:
        raise ValueError("Invalid radius or effective flags")
    if any(not 0 <= v <= 255 for v in (state38, type_de, state4c, state3c, state41)):
        raise ValueError("Expected native state bytes")
    low, cell_x, cell_y = position_fields(tag, owner, x, y)
    word = low | (((signed32(radius + 0x3ff) >> 10) & 15) << 24)
    if collision_flags & 0xff000000 and not collision_flags & 0xffffff:
        word |= 1 << 28
    if state38 & 0x40:
        word |= 1 << 29
    if type_de & 8:
        word |= 1 << 30
    if 0 < state4c < 128 or (state3c | state41) & 0x10:
        word |= 1 << 31
    return LAYOUT.pack(word, cell_x, cell_y, radius & U32)


def small_handle(cell_x, cell_y, depth, occupied):
    """Successful ordinary insertion into the first non-full 15-entry bucket."""
    if not 0 <= occupied < 15 or not 0 <= depth < 0x3ff or not all(0 <= v <= 65535 for v in (cell_x, cell_y)):
        raise ValueError("Invalid cell or bucket position")
    cell = 128 * cell_y + cell_x
    if cell >= 0x4000:
        raise ValueError("Cell outside the initialized small grid")
    return 1 | ((cell & 0x7fff) << 2) | (((15 * depth + occupied) & 0x3fff) << 17)


def append_handle(count, *, deferred):
    """Large-object insertion, or queued small-object insertion during deferral."""
    if not 0 <= count <= U32:
        raise ValueError("Invalid list count")
    return (0x10001 if deferred else 0x10003) | ((count & 0x3fff) << 17)


def advance(raw_crc, entry, *handles):
    """For an enabled operation hash descriptor/new, descriptor/old/new, or the removed handle."""
    if not 0 <= raw_crc <= U32 or any(not 0 <= h <= U32 for h in handles):
        raise ValueError("Expected unsigned CRC and handles")
    if entry is None:
        if len(handles) != 1:
            raise ValueError("Removal takes its prior handle")
        entry = b""
    elif len(entry) != LAYOUT.size or len(handles) not in (1, 2):
        raise ValueError("Creation or update requires a complete descriptor and its handles")
    payload = entry + b"".join(pack("<I", value) for value in handles)
    return crc32(payload, raw_crc ^ U32) ^ U32
