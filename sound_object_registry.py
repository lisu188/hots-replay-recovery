"""Ordinary build-98348 Galaxy object registry, including class 15 (sound)."""


class ObjectRegistry:
    def __init__(self):
        self.generations = [0, 0]
        self.live = {}
        self.free = []

    def allocate(self, object_class):
        if type(object_class) is not int or not 0 <= object_class < 255:
            raise ValueError("Invalid live class")
        if self.free:
            slot = self.free.pop()
        elif len(self.generations) < 65536:
            slot = len(self.generations)
            self.generations.append(0)
        else:
            return 0
        generation = (self.generations[slot] + 1) & 65535
        self.generations[slot] = generation
        self.live[slot] = object_class
        return (generation << 16) | slot

    def retire_slot(self, slot):
        """Use the slot of an already-live object, as required by this ordinary-path model."""
        if type(slot) is not int or slot not in self.live:
            raise ValueError("Expected a live ordinary slot")
        del self.live[slot]
        self.free.append(slot)


def minimum_allocations(handles):
    """Lower bound from fresh reset through observation, with no restored/rebound objects."""
    highest = {}
    for word in handles:
        if type(word) is not int or not 0 <= word <= 0xffffffff or (word & 65535)<2:
            raise ValueError("Expected an ordinary native handle")
        slot, generation = word & 65535, word >> 16
        highest[slot] = max(highest.get(slot,0),generation or 65536)
    if not highest:
        return 0
    return max(highest)-1 + sum(generation-1 for generation in highest.values())
