"""Ordinary build-98348 unit-slot selection from an ordered stream of pool operations."""

SLOT_LIMIT = 1023
GENERATION_MASK = (1 << 22) - 1


class UnitSlotPool:
    """A clean pool. The caller supplies actual allocations, retirements and drains."""

    def __init__(self):
        self._generations = []
        self._occupied = set()
        self._pending = []
        self._ready = []

    def allocate(self):
        if self._ready:
            slot = self._ready.pop()
        elif len(self._generations) < SLOT_LIMIT:
            slot = len(self._generations)
            self._generations.append(1)
        else:
            return None
        self._occupied.add(slot)
        return slot, self._generations[slot]

    def retire(self, tag):
        slot, generation = tag
        if slot not in self._occupied or self._generations[slot] != generation:
            raise ValueError("Stale or inactive unit tag")
        self._occupied.remove(slot)
        self._generations[slot] = generation + 1
        if self._generations[slot] < GENERATION_MASK:
            self._pending.append(slot)

    def drain(self):
        """Move pending units ahead of old ready entries, oldest retirement first."""
        self._ready.extend(reversed(self._pending))
        self._pending.clear()
