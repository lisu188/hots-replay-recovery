"""Inspect immutable public replay fixtures for build, queue and physical loop-zero evidence."""

import argparse
from contextlib import closing
from hashlib import sha256
from itertools import groupby, takewhile
import json
from pathlib import Path

from encoders import encode_tracker_events
from mpq_reader import MPQArchive
from protocol_loader import load_protocol


CASES = [
    ("heroesreplay-fixture", "55ac72260033a80d14580a147194bb372444907cde939e6ab54316dd19ec2916", "https://raw.githubusercontent.com/HeroesReplay/HeroesReplay/57d9ddec37245ac3068b7a39b5bf795806735d99/src/HeroesReplay.Tests/Assets/hour-long-replay-provided-by-mgatner.StormReplay"),
    ("reader-fixture", "8761d8bf33dd2a238b76bd73e3c24f35eaefff93462bde002f1793f63d68552e", "https://raw.githubusercontent.com/Arthrose/HotsReplayReader/3e94e39d3c170b593ce881f3f4f86f30656b303f/tools/2025-10-09%2021.52.51%20Hanamura%20Temple.StormReplay"),
    ("dragon-shire-parser", "7a27e561c11c569ecb802799f9b158785145a5b36f3a7460c3be7fe0400692c2", "https://raw.githubusercontent.com/astefanski1/storm-parser/28e7e2430037c184b4a982537086824eb831af65/tests/replays/2025-08-17%2019.40.18%20Dragon%20Shire.StormReplay"),
    ("silver-city", "29aee1cf058ac729f9a73012cb2bc99e0f952e89d78e7f92aaea4eddb093d326", "https://raw.githubusercontent.com/matella/storm-codex/a325597a57698387afcf34f86607f3a61fa773ba/crates/storm-replay-viewer/tests/data/silver-city-aram.StormReplay"),
]
PARSER_URL = "https://raw.githubusercontent.com/HeroesToolChest/Heroes.StormReplayParser/92b0286fd3c12fc713a8b4e9983f1182da48c4cb/Tests/Heroes.StormReplayParser.Tests/Replays/"
CASES += [(name, digest, PARSER_URL+name+".StormR") for name,digest in (
    ("CustomBattlefieldofEternity2_98348","7fb7b9bcd16df2c19d64f720731b3a937b5931a83582e67c45347368a563fb60"),
    ("CustomInfernalShrines3_98348","f4e315a3b7044401359e73969172a442a96e7529432f64c183b9f09e7387f04c"),
    ("SilverCity2_98348","96f31eb4ca6c71ba094646442e95090c65226be63301dfd40e6e9fcea728a14c"),
)]


def inspect(path, expected, url):
    data=path.read_bytes()
    if sha256(data).hexdigest()!=expected:
        raise ValueError("Downloaded archive differs from the pinned public fixture")
    with closing(MPQArchive(path)) as archive:
        h=load_protocol(96477).decode_replay_header(archive.header["user_data_header"]["content"])
        build=h["m_version"]["m_baseBuild"]
        if (h["m_version"]["m_build"],h["m_dataBuildNum"])!=(build,build):
            raise ValueError("Physical build fields disagree")
        schema=96477 if build==98348 else build
        p=load_protocol(schema)
        title=p.decode_replay_details(archive.read_file("replay.details"))["m_title"].decode()
        init=p.decode_replay_initdata(archive.read_file("replay.initData"))["m_syncLobbyState"]["m_gameDescription"]["m_gameOptions"]
        raw=archive.read_file("replay.tracker.events")
    opening=list(takewhile(lambda e:e["_gameloop"]==0,p.decode_replay_tracker_events(raw)))
    n,rem=divmod(sum(r["_bits"] for r in opening),8)
    if not n or rem or encode_tracker_events(opening,p)!=raw[:n]:
        raise ValueError("Loop-zero re-encoding differs from physical frame boundaries")
    return dict(source_url=url,archive_bytes=len(data),archive_sha256=expected,build=build,decoded_schema=schema,map=title,
                amm=init["m_amm"],amm_id=init["m_ammId"],loop_zero_frames=len(opening),loop_zero_bytes=n,
                loop_zero_sha256=sha256(raw[:n]).hexdigest(),
                loop_zero_runs=[[kind,sum(1 for _ in rs)] for kind,rs in groupby(opening,key=lambda e:e["_eventid"])],
                exact_target_qm=build==98348 and init["m_amm"] is True and init["m_ammId"]==50001)


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("folder",type=Path)
    folder=cli.parse_args().folder
    rows=[inspect(folder/(name+".private.StormReplay"),digest,url) for name,digest,url in CASES]
    print(json.dumps(dict(physical_fixtures=rows,verified_target_quick_matches=sum(r["exact_target_qm"] for r in rows)),indent=2))
