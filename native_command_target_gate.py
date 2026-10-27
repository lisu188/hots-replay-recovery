"""Selected Base98348 post-callback target gate, not full command validation.

Static source: RVA202B475..202B4E7 within command validator202AFB0.
The caller must already have reached this block with valid native objects.
`callback_class` and `context_bit2` are uninterpreted native results/fields;
neither is recovered from a replay alone. No historical flag mapping follows.
"""


def selected_target_gate(flags, target_tag, callback_class, context_bit2=False):
    """Model only native callback classes0..3 and the selected final branch.

    True means this block reaches its success continuation at202B4E7;
    False means its cleanup/failure continuation at202B3C4. Earlier checks,
    callbacks, catalogs, target resolution and live object state are external.
    """
    if type(flags) is not int or not 0 <= flags < 1 << 26:
        raise ValueError('flags must fit the native26-bit payload')
    if type(target_tag) is not int or target_tag not in (0, 1, 2, 3):
        raise ValueError('unsupported target tag')
    if type(callback_class) is not int or callback_class not in (0, 1, 2, 3):
        raise ValueError('unsupported native callback class')
    if type(context_bit2) is not bool:
        raise ValueError('context bit must be a boolean')
    bit18 = bool(flags & (1 << 18))
    bit23 = bool(flags & (1 << 23))
    if callback_class == 0:
        return target_tag not in (1, 2) and not bit18 and not bit23
    if callback_class == 1:
        return target_tag == 2 or bit18
    if callback_class == 2:
        return context_bit2 or target_tag == 1 or bit18
    return target_tag in (1, 2) or bit18
