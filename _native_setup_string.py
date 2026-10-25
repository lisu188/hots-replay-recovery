"""Static model of Base98348 validator RVA1A6D7D0, not target execution.

The PE's nine row table is UTF8 scalar encoding with U+0000 excluded. Empty
input is accepted. Native decoded-count is the number of complete sequences,
including its already accepted prefix if validation later fails.
"""

# Rows at PE RVA289C970. Each row is its active inclusive byte ranges; unused
# zero bytes in each 12-byte PE row are not input ranges.
NATIVE_STRING_ROWS = (
    ((1, 127),),
    ((194, 223), (128, 191)),
    ((224, 224), (160, 191), (128, 191)),
    ((225, 236), (128, 191), (128, 191)),
    ((237, 237), (128, 159), (128, 191)),
    ((238, 239), (128, 191), (128, 191)),
    ((240, 240), (144, 191), (128, 191), (128, 191)),
    ((241, 243), (128, 191), (128, 191), (128, 191)),
    ((244, 244), (128, 143), (128, 191), (128, 191)),
)


def validate_native_string(data):
    """Return (accepted:bool, accepted_sequence_count:int), with no IO.

    This models the valid pointer/finite buffer domain. The caller owns buffer
    size budgets and descriptor character/encoded-length limits. This helper
    does not validate those descriptor-specific limits or emulate memory faults.
    """
    if type(data) is not bytes:
        raise TypeError("STRING input must be bytes")
    offset, count, total = 0, 0, len(data)
    while offset < total:
        first = data[offset]
        row = None
        for candidate in NATIVE_STRING_ROWS:
            low, high = candidate[0]
            if low <= first <= high:
                row = candidate
                break
        if row is None or total - offset < len(row):
            return False, count
        for i in range(1, len(row)):
            low, high = row[i]
            if not low <= data[offset + i] <= high:
                return False, count
        offset += len(row)
        count += 1
    return True, count


def count_native_string_sequences(data):
    """Return native sequence count, raising a value-free error if invalid."""
    accepted, count = validate_native_string(data)
    if not accepted:
        raise ValueError("Invalid native STRING encoding")
    return count
