"""41810 Dragon Shire neutral camp lifecycle from map placements and independent tracker signals."""

import argparse
from collections import Counter, defaultdict
from contextlib import closing
from dataclasses import dataclass, field
from hashlib import sha256
from heapq import heappop, heappush
import json
from pathlib import Path

from encoders import encode_tracker_events
from mpq_reader import MPQArchive
from predict_camp_captures import CONTROLS, MAP, SOURCE, birth_keys, map_camps
from protocol_loader import load_protocol
from verify_first_defender_wave import map_wave

RESPAWN_SECONDS = {"SiegeGiants": 180, "Knights": 240}


def need(value, message):
    if not value:
        raise ValueError(message)


@dataclass
class Camp:
    kind: str
    slots: frozenset
    state: str = "unopened"
    alive: set = field(default_factory=set)
    generation: int = 0


class WaveClock:
    """Per-camp clock. No input for observed neutral births. Deaths affect state checks only."""

    def __init__(self, kinds, slots, *, hibernate=True):
        self.camps = {
            cid: Camp(kind, frozenset(slot for slot, group in slots.items() if group == cid))
            for cid, kind in kinds.items()
        }
        need(
            all(
                c.kind in RESPAWN_SECONDS and len(c.slots) == (2 if c.kind == "SiegeGiants" else 4)
                for c in self.camps.values()
            ),
            "Unsupported camp or incomplete authored slots",
        )
        self.queue = []
        self.waves = []
        self.faults = Counter()
        self.holds = 0
        self.dragon = False
        self.hibernate = hibernate
        self.gates = None
        self.loop = -1
        self.last_ready = None

    def _schedule(self, tick, cid, action):
        heappush(self.queue, (tick, cid, self.camps[cid].generation, action))

    def advance(self, tick):
        need(tick >= self.loop, "Clock went backwards")
        while self.queue and self.queue[0][0] <= tick:
            due, cid, generation, action = heappop(self.queue)
            camp = self.camps[cid]
            if generation != camp.generation:
                continue
            if action == "ready":
                self.last_ready = due
                if self.hibernate and self.dragon:
                    camp.state = "waiting_for_dragon_end"
                    self.holds += 1
                else:
                    camp.state = "spawning"
                    self._schedule(due + 2, cid, "birth")
            else:
                if camp.alive:
                    self.faults["birth_precedes_previous_wave_elimination"] += 1
                self.waves.append((due, cid, generation == 0))
                camp.state = "defending"
                camp.alive = set(camp.slots)
        self.loop = tick

    def event(self, tick, kind, cid=0, slot=None):
        self.advance(tick)
        if kind in ("dragon_on", "dragon_off") and self.last_ready == tick:
            self.faults["unverified_same_loop_dragon_transition_and_ready_timer"] += 1
        if kind == "gates":
            need(self.gates is None, "Duplicate GatesOpen")
            self.gates = tick
            for i in self.camps:
                self._schedule(tick + 1922, i, "birth")
        elif kind == "dragon_on":
            need(not self.dragon, "Second active Dragon Knight")
            self.dragon = True
        elif kind == "dragon_off":
            need(self.dragon, "Inactive Dragon Knight end")
            self.dragon = False
            for i, camp in self.camps.items():
                if camp.state == "waiting_for_dragon_end":
                    camp.state = "spawning"
                    self._schedule(tick + 3, i, "birth")
        elif kind == "death":
            camp = self.camps[cid]
            if camp.state != "defending" or slot not in camp.alive:
                self.faults["death_outside_living_defender_slot"] += 1
            else:
                camp.alive.remove(slot)
                if not camp.alive:
                    camp.state = "awaiting_capture"
        elif kind == "capture":
            camp = self.camps[cid]
            if camp.state != "awaiting_capture":
                self.faults["capture_without_complete_observed_defeat"] += 1
            camp.state = "cooldown"
            camp.alive.clear()
            camp.generation += 1
            self._schedule(tick + 16 * (RESPAWN_SECONDS[camp.kind] - 3), cid, "ready")
        else:
            raise ValueError("Unknown signal")


def map_slots(path):
    camps = map_camps(path)
    _, slots = map_wave(path)
    by_slot = {}
    for (name, x, y), count in slots.items():
        owners = [i for i, (_, pos, _) in camps.items() if (pos[0] - x) ** 2 + (pos[1] - y) ** 2 <= 64]
        need(count == 1 and len(owners) == 1, "Ambiguous authored defender slot")
        by_slot[name, x, y] = owners[0]
    return camps, by_slot


def read_case(path, digest):
    need(sha256(path.read_bytes()).hexdigest() == digest, "Input digest")
    protocol = load_protocol(41810)
    with closing(MPQArchive(path)) as arc:
        h = protocol.decode_replay_header(arc.header["user_data_header"]["content"])
        details = protocol.decode_replay_details(arc.read_file("replay.details"))
        need(
            (h["m_version"]["m_build"], h["m_version"]["m_baseBuild"], h["m_dataBuildNum"])
            == (41810,) * 3
            and details["m_cacheHandles"][-1][8:].hex() == MAP,
            "Build/map",
        )
        raw = arc.read_file("replay.tracker.events")
    events = list(protocol.decode_replay_tracker_events(raw))
    need(encode_tracker_events(events, protocol) == raw, "Tracker round-trip")
    horizon = h["m_elapsedGameLoops"]
    need(horizon >= events[-1]["_gameloop"], "Header horizon before final event")
    return events, horizon, sha256(raw).hexdigest()


def signals_and_targets(events, camps, slots):
    beacons = birth_keys(
        events, b"TownMercCampCaptureBeacon", {i: p for i, (_, p, _) in camps.items()}, initial=True
    )
    signals = []
    births = Counter()
    live = {}
    dragons = set()
    active_dragon = None
    unknown = Counter()
    observed_deaths = 0
    captures = 0
    for e in events:
        tick = e["_gameloop"]
        name = e["_event"].rsplit(".", 1)[-1]
        tag = e.get("m_unitTagIndex"), e.get("m_unitTagRecycle")
        if name == "SUnitBornEvent":
            unit = e["m_unitTypeName"].decode()
            if unit == "VehicleDragon":
                dragons.add(tag)
            elif unit.startswith("MercDefender") and (
                e["m_controlPlayerId"],
                e["m_upkeepPlayerId"],
            ) == (15, 15):
                key = unit, e["m_x"], e["m_y"]
                cid = slots.get(key)
                if cid is None:
                    unknown[key] += 1
                    births[tick, 0, *key] += 1
                else:
                    need(tag not in live, "Duplicate live neutral tag")
                    live[tag] = (cid, key)
                    births[tick, cid, *key] += 1
        elif name == "SUnitDiedEvent":
            if tag in live:
                cid, slot = live.pop(tag)
                signals.append((tick, "death", cid, slot))
                observed_deaths += 1
            if tag == active_dragon:
                signals.append((tick, "dragon_off", 0))
                active_dragon = None
            dragons.discard(tag)
        elif name == "SUnitOwnerChangeEvent" and tag in beacons:
            if e["m_controlPlayerId"] == e["m_upkeepPlayerId"] and e["m_controlPlayerId"] in (11, 12):
                # Previously tested 39/39 captures. No capture stats or captured laner birth time needed.
                signals.append((tick + 1, "capture", beacons[tag]))
                captures += 1
        elif e.get("m_eventName") == b"DragonKnightActivated":
            need(len(dragons) == 1 and active_dragon is None, "Ambiguous dragon activation")
            active_dragon = next(iter(dragons))
            signals.append((tick, "dragon_on", 0))
        elif e.get("m_eventName") == b"GatesOpen":
            signals.append((tick, "gates", 0))
    return (
        sorted(signals, key=lambda row: row[0]),
        births,
        dict(
            live_slots=Counter(live.values()),
            deaths=observed_deaths,
            captures=captures,
            off_slot=unknown.total(),
        ),
    )


def run_clock(kinds, slots, signals, horizon, *, deaths=True, hibernate=True):
    clock = WaveClock(kinds, slots, hibernate=hibernate)
    for signal in signals:
        if signal[0] <= horizon and (deaths or signal[1] != "death"):
            clock.event(*signal)
    clock.advance(horizon)
    return clock


def comparison(predicted, observed):
    return dict(
        matches=(predicted & observed).total(),
        false_positives=(predicted - observed).total(),
        misses=(observed - predicted).total(),
    )


def score_case(path, digest, camps, slots):
    events, horizon, tracker_digest = read_case(path, digest)
    signals, observed, lives = signals_and_targets(events, camps, slots)
    kinds = {i: kind for i, (kind, _, _) in camps.items()}
    clock = run_clock(kinds, slots, signals, horizon)
    no_deaths = run_clock(kinds, slots, signals, horizon, deaths=False)
    need(no_deaths.waves == clock.waves, "Birth/death associations affected forecast")
    masked_events = [
        e
        for e in events
        if not (
            e["_event"].endswith(".SUnitBornEvent")
            and e.get("m_unitTypeName", b"").startswith(b"MercDefender")
        )
    ]
    masked_signals, masked_targets, _ = signals_and_targets(masked_events, camps, slots)
    need(
        not masked_targets and run_clock(kinds, slots, masked_signals, horizon).waves == clock.waves,
        "Forecast depended on held-out defender birth records",
    )
    naive = run_clock(kinds, slots, signals, horizon, hibernate=False)

    def expand(waves):
        return Counter(
            (tick, cid, *key) for tick, cid, _ in waves for key, i in slots.items() if i == cid
        )

    need(clock.gates is not None, "Missing first wave origin")
    first_end = clock.gates + 1922
    later = Counter({k: n for k, n in observed.items() if k[0] > first_end})
    expected = expand(clock.waves)
    later_expected = expand([w for w in clock.waves if not w[2]])
    later_groups = Counter({(tick, cid): 1 for tick, cid, *_ in later})
    pred_groups = Counter((tick, cid) for tick, cid, initial in clock.waves if not initial)
    state_alive = Counter((i, slot) for i, c in clock.camps.items() for slot in c.alive)
    return dict(
        replay_sha256=digest,
        tracker_sha256=tracker_digest,
        horizon=horizon,
        first_loop=first_end,
        all_births=comparison(expected, observed),
        later_births=comparison(later_expected, later),
        later_camp_waves=comparison(pred_groups, later_groups),
        dragon_deferred_waves=clock.holds,
        observed_captures=lives["captures"],
        mapped_neutral_unit_deaths=lives["deaths"],
        unmapped_defender_births=lives["off_slot"],
        observed_live_at_end=lives["live_slots"].total(),
        exact_living_defender_slots_at_end_agree=state_alive == lives["live_slots"],
        state_diagnostics=dict(clock.faults),
        no_defender_death_input_same_birth_forecast=True,
        all_neutral_birth_records_removed_same_forecast=True,
        negative_ignoring_dragon=comparison(expand(naive.waves), observed),
        in_cooldown_at_end=sum(
            c.state in ("cooldown", "waiting_for_dragon_end", "spawning") for c in clock.camps.values()
        ),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map", required=True, type=Path)
    parser.add_argument("--replay", required=True, nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    camps, slots = map_slots(args.map)
    files = {sha256(p.read_bytes()).hexdigest(): p for p in args.replay}
    need(
        set(files) <= {SOURCE, *CONTROLS} and len(files) == len(args.replay),
        "Unexpected/duplicate replay",
    )
    records = [score_case(files[d], d, camps, slots) for d in (SOURCE, *CONTROLS) if d in files]
    report = dict(
        map_sha256=MAP,
        development_replay_sha256=SOURCE,
        model="GatesOpen+1922 first births. Prior beacon changes project captures at +1. "
        "Siege/knight captures start 180s/240s cooldown. Ordinary ready time is three seconds "
        "before expiry; births occur two loops later. If that ready time falls within an active "
        "Dragon Knight, birth occurs three loops after the active vehicle dies. "
        "Neutral death signals track live slots and guard the defeat/capture transition. "
        "Target neutral birth times, capture stats and other same-loop outcomes never schedule births.",
        cases=records,
    )
    data = (json.dumps(report, indent=2) + "\n").encode("utf-8")
    if args.output.exists():
        need(args.output.read_bytes() == data, "Existing receipt differs")
    else:
        with args.output.open("xb") as f:
            f.write(data)
    print(
        json.dumps(
            [
                (
                    r["all_births"],
                    r["later_camp_waves"],
                    r["dragon_deferred_waves"],
                    r["state_diagnostics"],
                )
                for r in records
            ]
        )
    )


if __name__ == "__main__":
    main()
