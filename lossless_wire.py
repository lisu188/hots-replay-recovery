"""Bounded lossless versioned-wire nodes for private header experiments.

Tags follow Blizzard's versioned decoder. This module does not infer fields,
reconstruct package metadata, fetch data, or write files. Parsed varint spellings
are retained, including a negative-zero or nonminimal representation. Changed
logical integers use the canonical signed-magnitude encoding.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import copy

MAX_BYTES = 2 * 1024 * 1024
MAX_NODES = 200000
MAX_DEPTH = 64
MAX_COUNT = 200000
MAX_VINT_BYTES = 10
MAX_VINT_MAGNITUDE = (1 << 69) - 1


class WireError(ValueError):
    pass


@dataclass(frozen=True)
class _Spelling:
    value: int
    raw: bytes


@dataclass
class Node:
    """A mutable node; tag5 value is an ordered list of (integer key, Node)."""
    tag: int
    value: object
    _spellings: dict = field(default_factory=dict, repr=False, compare=False)

    def field(self, key: int) -> Node:
        """Return an existing map child without converting or copying it."""
        if self.tag != 5 or type(key) is not int or type(self.value) is not list:
            raise WireError('An integer-keyed struct node is required')
        if len(self.value) > MAX_COUNT:
            raise WireError('Struct field count exceeds its bound')
        matches, seen = [], set()
        for pair in self.value:
            if type(pair) not in (tuple, list) or len(pair) != 2:
                raise WireError('Invalid struct field pair')
            found, child = pair
            if type(found) is not int or found in seen or type(child) is not Node:
                raise WireError('Invalid or duplicate struct field')
            seen.add(found)
            if found == key:
                matches.append(child)
        if len(matches) != 1 or type(matches[0]) is not Node:
            raise WireError('Expected one existing struct field')
        return matches[0]

    def set_field(self, key: int, child: Node) -> None:
        """Replace an existing field in place, retaining its order and key spelling."""
        self.field(key)
        if type(child) is not Node:
            raise WireError('A Node child is required')
        for index, (found, _) in enumerate(self.value):
            if found == key:
                self.value[index] = (key, child)
                return


def _integer(value):
    if type(value) is not int or abs(value) > MAX_VINT_MAGNITUDE:
        raise WireError('Expected a bounded signed-magnitude integer')
    return value


def _canonical_vint(value):
    value = _integer(value)
    unsigned = (abs(value) << 1) | int(value < 0)
    out = bytearray()
    while unsigned >= 128:
        out.append((unsigned & 127) | 128)
        unsigned >>= 7
    out.append(unsigned)
    return bytes(out)


class _Reader:
    def __init__(self, raw):
        self.raw, self.position, self.nodes = raw, 0, 0

    def take(self, size):
        if type(size) is not int or size < 0 or size > len(self.raw)-self.position:
            raise WireError('Truncated versioned-wire payload')
        out = self.raw[self.position:self.position+size]
        self.position += size
        return out

    def vint(self):
        start, unsigned = self.position, 0
        for index in range(MAX_VINT_BYTES):
            byte = self.take(1)[0]
            unsigned |= (byte & 127) << (index*7)
            if byte < 128:
                value = -(unsigned >> 1) if unsigned & 1 else unsigned >> 1
                return value, _Spelling(value, self.raw[start:self.position])
        raise WireError('Overlong versioned-wire integer')

    def count(self):
        count, spelling = self.vint()
        if not 0 <= count <= MAX_COUNT:
            raise WireError('Versioned-wire count exceeds its bound')
        return count, spelling

    def node(self, depth=0):
        self.nodes += 1
        if self.nodes > MAX_NODES or depth > MAX_DEPTH:
            raise WireError('Versioned-wire node or depth budget exceeded')
        tag = self.take(1)[0]
        spellings = {}
        if tag in (0, 1, 2, 5):
            count, spellings['count'] = self.count()
        if tag == 0:
            value = [self.node(depth+1) for _ in range(count)]
        elif tag == 1:
            value = (count, self.take((count+7)//8))
        elif tag == 2:
            value = self.take(count)
        elif tag == 3:
            choice, spellings['choice'] = self.vint()
            value = (choice, self.node(depth+1))
        elif tag == 4:
            present = self.take(1)[0]
            if present not in (0, 1):
                raise WireError('Noncanonical optional flag')
            value = self.node(depth+1) if present else None
        elif tag == 5:
            value, seen = [], set()
            for _ in range(count):
                key, spelling = self.vint()
                if key in seen:
                    raise WireError('Duplicate struct field')
                seen.add(key)
                spellings[('key', key)] = spelling
                value.append((key, self.node(depth+1)))
        elif tag == 6:
            value = self.take(1)[0]
        elif tag in (7, 8):
            value = self.take(4 if tag == 7 else 8)
        elif tag == 9:
            value, spellings['value'] = self.vint()
        else:
            raise WireError('Unknown versioned-wire tag')
        return Node(tag, value, spellings)


def parse(raw: bytes) -> Node:
    """Read exactly one bounded node, retaining type, ordering and wire spellings."""
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_BYTES:
        raise WireError('Expected bounded nonempty bytes')
    reader = _Reader(raw)
    node = reader.node()
    if reader.position != len(raw):
        raise WireError('Trailing bytes after versioned-wire node')
    return node


class _Writer:
    def __init__(self):
        self.raw, self.nodes, self.active = bytearray(), 0, set()

    def put(self, raw):
        if len(raw) > MAX_BYTES-len(self.raw):
            raise WireError('Encoded versioned-wire byte budget exceeded')
        self.raw.extend(raw)

    def vint(self, value, spelling=None):
        _integer(value)
        if spelling is not None:
            if type(spelling) is not _Spelling or type(spelling.raw) is not bytes or not 1 <= len(spelling.raw) <= MAX_VINT_BYTES:
                raise WireError('Invalid retained integer spelling')
            reader = _Reader(spelling.raw)
            original, _ = reader.vint()
            if reader.position != len(spelling.raw) or original != spelling.value:
                raise WireError('Retained integer spelling disagrees with its value')
            if value == original:
                self.put(spelling.raw)
                return
        self.put(_canonical_vint(value))

    def count(self, value, node):
        if type(value) is not int or not 0 <= value <= MAX_COUNT:
            raise WireError('Versioned-wire count exceeds its bound')
        self.vint(value, node._spellings.get('count'))

    def node(self, node, depth=0):
        self.nodes += 1
        if self.nodes > MAX_NODES or depth > MAX_DEPTH:
            raise WireError('Versioned-wire node or depth budget exceeded')
        if type(node) is not Node or type(node.tag) is not int or not 0 <= node.tag <= 9 or type(node._spellings) is not dict:
            raise WireError('Expected a supported Node')
        identity = id(node)
        if identity in self.active:
            raise WireError('Cyclic Node graph')
        self.active.add(identity)
        try:
            tag, value = node.tag, node.value
            self.put(bytes([tag]))
            if tag == 0:
                if type(value) is not list:
                    raise WireError('Array node requires a list')
                self.count(len(value), node)
                for child in value:
                    self.node(child, depth+1)
            elif tag == 1:
                if type(value) is not tuple or len(value) != 2:
                    raise WireError('Bit array requires (count, bytes)')
                count, raw = value
                self.count(count, node)
                if type(raw) is not bytes or len(raw) != (count+7)//8:
                    raise WireError('Bit array size disagrees with its count')
                self.put(raw)
            elif tag == 2:
                if type(value) is not bytes:
                    raise WireError('Blob node requires bytes')
                self.count(len(value), node)
                self.put(value)
            elif tag == 3:
                if type(value) is not tuple or len(value) != 2:
                    raise WireError('Choice requires (integer tag, Node)')
                choice, child = value
                self.vint(choice, node._spellings.get('choice'))
                self.node(child, depth+1)
            elif tag == 4:
                self.put(b'\x00' if value is None else b'\x01')
                if value is not None:
                    self.node(value, depth+1)
            elif tag == 5:
                if type(value) is not list:
                    raise WireError('Struct node requires an ordered field list')
                self.count(len(value), node)
                seen = set()
                for pair in value:
                    if type(pair) not in (tuple, list) or len(pair) != 2:
                        raise WireError('Struct field requires (integer key, Node)')
                    key, child = pair
                    _integer(key)
                    if key in seen:
                        raise WireError('Duplicate struct field')
                    seen.add(key)
                    self.vint(key, node._spellings.get(('key', key)))
                    self.node(child, depth+1)
            elif tag == 6:
                if type(value) is not int or not 0 <= value <= 255:
                    raise WireError('Byte node requires an unsigned8 integer')
                self.put(bytes([value]))
            elif tag in (7, 8):
                if type(value) is not bytes or len(value) != (4 if tag == 7 else 8):
                    raise WireError('Fixed byte node has the wrong width')
                self.put(value)
            elif tag == 9:
                self.vint(value, node._spellings.get('value'))
        finally:
            self.active.remove(identity)


def encode(node: Node) -> bytes:
    """Validate and encode a bounded acyclic tree; no file operation is performed."""
    writer = _Writer()
    writer.node(node)
    return bytes(writer.raw)


def clone(node: Node) -> Node:
    """Return an independent mutable copy of a validated bounded tree."""
    encode(node)
    return copy.deepcopy(node)


def to_generic(node: Node):
    """Return values comparable with the separately implemented depot decoder.

    Only this comparison adapter imports depot_s2mh_wire's Choice/BitArray types;
    parsing, copying and encoding use the Python standard library alone.
    """
    from depot_s2mh_wire import Choice, BitArray
    encode(node)

    def visit(item):
        tag, value = item.tag, item.value
        if tag == 0:
            return [visit(child) for child in value]
        if tag == 1:
            return BitArray(*value)
        if tag == 3:
            return Choice(value[0], visit(value[1]))
        if tag == 4:
            return None if value is None else visit(value)
        if tag == 5:
            return {key: visit(child) for key, child in value}
        return value

    return visit(node)
