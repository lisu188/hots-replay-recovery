"""Forecast camp captures and subsequent neutral waves from observed defender deaths on build 41810."""

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
from heapq import heappop, heappush
import json
from pathlib import Path

from legacy_camp_wave_model import WaveClock, comparison, map_slots, read_case
from predict_camp_captures import SOURCE, CONTROLS, MAP, number


def driver_signals(events, slots):
    """Bind birth tags to authored slots, then emit only gate, Dragon Knight and neutral death signals."""
    teams = {}
    live = {}
    dragons = set()
    dragon = None
    out = []
    for e in events:
        name = e["_event"].rsplit(".", 1)[-1]
        tick = e["_gameloop"]
        if name == "SStatGameEvent":
            stat = e["m_eventName"]
            if stat == b"PlayerInit":
                teams[number(e, "m_intData", "PlayerID")] = number(
                    e, "m_intData", "Team"
                )
            elif stat == b"GatesOpen":
                out.append((tick, "gates"))
            elif stat == b"DragonKnightActivated":
                if dragon is not None or len(dragons) != 1:
                    raise ValueError("Ambiguous active Dragon Knight")
                dragon = next(iter(dragons))
                out.append((tick, "dragon_on"))
        elif name == "SUnitBornEvent":
            tag = e["m_unitTagIndex"], e["m_unitTagRecycle"]
            t = e["m_unitTypeName"]
            if t == b"VehicleDragon":
                dragons.add(tag)
            elif t.startswith(b"MercDefender") and (
                e["m_controlPlayerId"],
                e["m_upkeepPlayerId"],
            ) == (
                15,
                15,
            ):
                slot = t.decode(), e["m_x"], e["m_y"]
                if slot not in slots or tag in live:
                    raise ValueError("Unexpected neutral defender slot/tag")
                live[tag] = (slots[slot], slot)
        elif name == "SUnitDiedEvent":
            tag = e["m_unitTagIndex"], e["m_unitTagRecycle"]
            if tag == dragon:
                out.append((tick, "dragon_off"))
                dragon = None
            dragons.discard(tag)
            if tag in live:
                cid, slot = live.pop(tag)
                out.append(
                    (tick, "death", cid, slot, teams.get(e.get("m_killerPlayerId")))
                )
    return out


def forecast(kinds, slots, signals, horizon):
    """Run WaveClock on predicted captures. The input has no capture, ownership or wave-outcome fields."""
    clock = WaveClock(kinds, slots)
    due = []
    captures = []
    no_team = 0
    same_tick_deaths = defaultdict(set)

    def advance(tick):
        while due and due[0][0] <= tick:
            t, cid, team = heappop(due)
            clock.event(t, "capture", cid)
            captures.append((t, cid, team))
        clock.advance(tick)

    for signal in signals:
        tick, kind, *args = signal
        if tick > horizon:
            break
        advance(tick)
        if kind == "death":
            cid, slot, team = args
            defending = (
                clock.camps[cid].state == "defending" and slot in clock.camps[cid].alive
            )
            clock.event(tick, "death", cid, slot)
            if defending:
                same_tick_deaths[tick, cid].add(team)
            if defending and clock.camps[cid].state == "awaiting_capture":
                if team not in (1, 2) or len(same_tick_deaths[tick, cid]) != 1:
                    no_team += 1
                else:
                    heappush(due, (tick + 25, cid, team))
        elif kind in ("gates", "dragon_on", "dragon_off"):
            clock.event(tick, kind)
        else:
            raise ValueError("Unsupported driver signal")
    advance(horizon)
    return captures, clock, no_team, len(due)


def score(events, projection, clock, slots):
    """Reveal capture stats and neutral births after forecasting has finished."""
    actual = []
    all_births = Counter()
    for e in events:
        if e.get("m_eventName") == b"JungleCampCapture":
            raw_team = number(e, "m_fixedData", "TeamID")
            if raw_team not in (4096, 8192):
                raise ValueError("Unexpected capture stat team")
            actual.append(
                (e["_gameloop"], number(e, "m_intData", "CampID"), raw_team // 4096)
            )
        elif (
            e["_event"].endswith("SUnitBornEvent")
            and e["m_unitTypeName"].startswith(b"MercDefender")
            and (e["m_controlPlayerId"], e["m_upkeepPlayerId"]) == (15, 15)
        ):
            s = e["m_unitTypeName"].decode(), e["m_x"], e["m_y"]
            if s not in slots:
                raise ValueError("Unexpected neutral defender target")
            all_births[e["_gameloop"], slots[s], s] += 1
    observed_groups = set((t, c) for t, c, s in all_births)
    first = clock.gates + 1922
    pred_groups = Counter((t, c) for t, c, initial in clock.waves if not initial)
    measured_groups = Counter({(t, c): 1 for t, c in observed_groups if t != first})
    predicted_births = Counter(
        (t, c, s) for t, c, initial in clock.waves for s, k in slots.items() if k == c
    )
    predicted_returned = Counter(
        {k: n for k, n in predicted_births.items() if k[0] != first}
    )
    observed_returned = Counter({k: n for k, n in all_births.items() if k[0] != first})
    cap_diffs = Counter()
    respawn_diffs = Counter()
    transfer = Counter()
    order_team = 0
    unpaired = 0
    for c in clock.camps:
        pred = [(t, team) for t, site, team in projection if site == c]
        obs = [(t, team) for t, site, team in actual if site == c]
        p_waves = sorted(t for t, site in pred_groups if site == c)
        o_waves = sorted(t for t, site in measured_groups if site == c)
        if (
            len(pred) != len(obs)
            or len(p_waves) != len(o_waves)
            or len(p_waves) > len(pred)
        ):
            # The multiset scores below still report false and missing predictions.
            # Abstain from ordinal timing attribution at this camp when generations cannot be paired.
            unpaired += 1
            continue
        for i, ((pred_t, pred_team), (obs_t, obs_team)) in enumerate(zip(pred, obs)):
            gap = obs_t - pred_t
            cap_diffs[gap] += 1
            order_team += pred_team == obs_team
            if i >= len(p_waves):
                transfer[
                    (
                        "late_capture_no_return_before_horizon"
                        if gap
                        else "exact_capture_no_return_before_horizon"
                    )
                ] += 1
            else:
                wave_gap = o_waves[i] - p_waves[i]
                respawn_diffs[wave_gap] += 1
                if gap == wave_gap == 0:
                    transfer["exact_capture_exact_return"] += 1
                elif gap and wave_gap == gap:
                    transfer["late_capture_error_propagates_to_return"] += 1
                elif gap and wave_gap == 0:
                    transfer["late_capture_error_absorbed_before_return"] += 1
                else:
                    transfer["different_error_at_return"] += 1
    return dict(
        capture_tuples=comparison(Counter(projection), Counter(actual)),
        capture_ordered_team_matches=order_team,
        camps_without_unambiguous_generation_pairing=unpaired,
        actual_minus_forecast_capture_loops=dict(sorted(cap_diffs.items())),
        later_wave_groups=comparison(pred_groups, measured_groups),
        all_individual_births=comparison(predicted_births, all_births),
        returned_individual_births=comparison(predicted_returned, observed_returned),
        actual_minus_forecast_return_loops=dict(sorted(respawn_diffs.items())),
        capture_to_return=dict(transfer),
    )


def run(path, digest, camps, slots):
    events, horizon, tracker = read_case(path, digest)
    kinds = {i: r[0] for i, r in camps.items()}
    drivers = driver_signals(events, slots)
    projected, clock, no_team, pending = forecast(kinds, slots, drivers, horizon)
    # Remove all award evidence and all owner-change records before regenerating the forecast.
    masked = [
        e
        for e in events
        if not e["_event"].endswith("SUnitOwnerChangeEvent")
        and e.get("m_eventName") != b"JungleCampCapture"
        and not e.get("m_unitTypeName", b"").startswith(b"MercLaner")
    ]
    if driver_signals(masked, slots) != drivers:
        raise ValueError("Masked outcomes affected the drivers")
    return dict(
        replay_sha256=digest,
        tracker_sha256=tracker,
        horizon=horizon,
        neutral_death_inputs=sum(s[1] == "death" for s in drivers),
        forecast_captures=len(projected),
        no_unique_killer_team=no_team,
        pending_capture_beyond_horizon=pending,
        masked_outcomes_leave_drivers_identical=True,
        state_diagnostics=dict(clock.faults),
        predicted_dragon_holds=clock.holds,
        **score(events, projected, clock, slots)
    )


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--map", type=Path, required=True)
    cli.add_argument("--replays", type=Path, required=True, nargs="+")
    args = cli.parse_args()
    camps, slots = map_slots(args.map)
    refs = {sha256(p.read_bytes()).hexdigest(): p for p in args.replays}
    if len(refs) != len(args.replays) or not set(refs) <= {SOURCE, *CONTROLS}:
        raise ValueError("Unexpected or duplicate case")
    print(
        json.dumps(
            dict(
                format="death-driven-legacy-camp-baseline-v1",
                map_sha256=MAP,
                delay_loops=25,
                capture_stats_or_beacon_owners_are_inputs=False,
                cases=[
                    run(refs[d], d, camps, slots)
                    for d in (SOURCE, *CONTROLS)
                    if d in refs
                ],
            ),
            indent=2,
        )
    )
