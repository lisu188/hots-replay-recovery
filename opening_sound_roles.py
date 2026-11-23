"""Cross-check two symbolic opening sound orders without assigning a target TEN handle."""

import argparse
from collections import defaultdict
from contextlib import closing
import json
from pathlib import Path

from first_sync_game import game
from mpq_reader import MPQArchive
from predict_camp_captures import SOURCE
from sound_object_registry import minimum_allocations


COMMON = "common"
STOCK = "f557190f8aaab160789272ce086b8b69d6a8037b152de150332603dae3dc098f"


def role_order(build):
    players = list(range(1,11))
    return (players + [COMMON]) if build == 41810 else ([COMMON] + players)


def leave_one_out(first_ten, order):
    """Fit handle values from nine other players, then compare the complete withheld ten."""
    reproduced = 0
    complete = None
    for held in range(1,11):
        values = {}
        conflict = False
        for player, words in first_ten.items():
            if player == held:
                continue
            for role,word in zip((r for r in order if r!=player),words,strict=True):
                if role in values and values[role] != word:
                    conflict = True
                values[role] = word
        if conflict or len(values)!=11 or len(set(values.values()))!=11:
            continue
        predicted = [values[r] for r in order if r!=held]
        if predicted == first_ten[held]:
            reproduced += 1
            complete = values
    return reproduced,complete


def audit(path, digest, build):
    p,raw = game(path,digest,build)
    with closing(MPQArchive(path)) as a:
        details=p.decode_replay_details(a.read_file("replay.details"))
        game_map=details["m_cacheHandles"][-1][8:].hex()
        setup={}
        for row in p.decode_replay_tracker_events(a.read_file("replay.tracker.events")):
            if row["_gameloop"]>0:
                break
            if row["_eventid"]==9 and row["m_userId"] is not None:
                user,player=row["m_userId"],row["m_playerId"]
                if user in setup or player in setup.values():
                    raise ValueError("Duplicate setup mapping")
                setup[user]=player
    if set(setup.values())!=set(range(1,11)):
        raise ValueError("Unexpected player setup")
    groups=defaultdict(list)
    ordinals=defaultdict(list)
    first=None
    for ordinal,row in enumerate(p.decode_replay_game_events(raw)):
        tick=row["_gameloop"]
        if first and tick>first[1]+100:
            break
        if row["_eventid"]!=46:
            continue
        user,word=row["_userid"]["m_userId"],row["m_sound"]
        if not first:
            first=(ordinal,tick,user,setup[user],word)
        groups[setup[user]].append(word)
        if len(groups[setup[user]]) <= 10:
            ordinals[setup[user]].append(ordinal)
    first_ten={player:words[:10] for player,words in groups.items()}
    enough=len(first_ten)==10 and all(len(v)==10 for v in first_ten.values())
    hits,values=leave_one_out(first_ten,role_order(build)) if enough else (0,None)
    reverse,_=leave_one_out(first_ten,role_order(98348 if build==41810 else 41810)) if enough else (0,None)
    row=dict(sha256=digest,build=build,stock_dragon=game_map==STOCK,first_ordinal=first[0],first_loop=first[1],
             first_reporting_user=first[2],first_reporting_player=first[3],first_word=first[4],
             reporting_players=len(groups),fully_reproduced_held_out_users=hits,
             reversed_order_held_out_users=reverse,closed_ten_user_round=hits==10,
             first_report_word_same_for_all_ten=enough and len({words[0] for words in first_ten.values()})==1)
    if hits==10:
        row["common_word"]=values[COMMON]
        if build==98348:
            row["minimum_ordinary_registry_allocations_through_observed_round"]=minimum_allocations(values.values())
            row["late_handles_predicted_from_player6_alone"]=sum(
                values[6]+player-6 == values[player] for player in range(7,11))
        row["late_five_player_words_generation_one_consecutive"]=(
            all(values[player]>>16==1 for player in range(6,11)) and
            [values[player]-values[6] for player in range(6,11)]==list(range(5)))
        if digest==SOURCE:
            row["source_common_first_ordinal"]=min(indices[-1] for indices in ordinals.values())
            row["first_source_word_role"]=next(r for r in values if values[r]==first[4])
            row["symbolic_reordering_by_reporting_player"]={}
            for player, words in first_ten.items():
                by_role={role:ordinals[player][i] for i,word in enumerate(words)
                         for role,value in values.items() if word==value}
                if len(by_role)!=10:
                    raise ValueError("TEN role has no unique source ordinal")
                row["symbolic_reordering_by_reporting_player"][player]=[
                    by_role[role] for role in role_order(98348) if role!=player]
    return row


def summarize(cases):
    rows=[audit(path,digest,build) for path,digest,build in cases]
    if len({r["sha256"] for r in rows}) != len(rows):
        raise ValueError("Duplicate recording")
    groups={}
    for build in (41810,98348):
        matches=[r for r in rows if r["build"]==build]
        closed=[r for r in matches if r["closed_ten_user_round"]]
        groups[build]=dict(recordings=len(matches),closed_rounds=len(closed),
            closed_stock_dragon=sum(r["stock_dragon"] for r in closed),
            closed_held_out_users=sum(r["fully_reproduced_held_out_users"] for r in closed),
            all_reversed_order_successes=sum(r["reversed_order_held_out_users"] for r in matches),
            all_ten_first_reports_share_word=sum(r["first_report_word_same_for_all_ten"] for r in matches),
            closed_last_five_g1_consecutive=sum(r["late_five_player_words_generation_one_consecutive"] for r in closed))
        if build==98348:
            groups[build]["late_handles_predicted_from_player6_alone"]=sum(
                r["late_handles_predicted_from_player6_alone"] for r in closed)
    return dict(builds=groups,target_ten_numeric_handle=None,cases=sorted(rows,key=lambda r:(r["build"],r["sha256"])))


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--case",action="append",nargs=3,required=True,metavar=("BUILD","SHA256","PATH"))
    args=cli.parse_args()
    print(json.dumps(summarize([(Path(p),h,int(b)) for b,h,p in args.case]),indent=2))
