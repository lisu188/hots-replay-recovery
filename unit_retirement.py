"""Bounded late-pass arithmetic for a build 98348 unit. Clocks use native units."""

from dataclasses import dataclass


STAGED = 0x10
FINAL = 0x20


@dataclass(frozen=True)
class Timer:
    remaining: int
    mode: int


def mark_timer(mode, special, first_delay, final_delay):
    """Timer-arm path of 0xaa91c0 after its early guards."""
    if special:
        return Timer(1, mode | FINAL)
    if first_delay > 0:
        return Timer(first_delay, mode | STAGED)
    mode = (mode & ~FINAL) | (FINAL if final_delay >= 0 else 0)
    return Timer(max(1, final_delay), mode)


def retirement_step(timer, *, clock, due, state_flags, debit, final_delay):
    """Evaluate one visited node. Supply +0x39 after optional native update hooks."""
    if (clock & 0xffffffff) < (due & 0xffffffff) or not state_flags & 6:
        return "retain", timer
    if timer.remaining > 0:
        return "debit", Timer(timer.remaining - debit, timer.mode)
    if timer.mode & STAGED:
        mode = timer.mode & ~STAGED
        mode = (mode & ~FINAL) | (FINAL if final_delay >= 0 else 0)
        return "stage", Timer(max(0, final_delay), mode)
    if timer.mode & FINAL:
        return "retire", timer
    return "retain", timer
