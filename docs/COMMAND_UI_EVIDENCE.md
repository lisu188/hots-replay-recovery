# Can the player's click identify the missing initial command?

TEN has 13,984 numeric command sequences whose first target update immediately precedes a same-user, same-loop state-2 manager record and whose user and sequence have no recorded issue anywhere. The complete game member contains 2,756 unit-click events, 158 selection changes and 313 dialog-control events. Each auxiliary event was re-encoded against its physical bytes with its original enclosing loop delta.

| Most recent prior event from the same user | Same loop | Same or previous four loops |
| --- | ---: | ---: |
| Unit click | 0 | 40 |
| Selection change | 1 | 4 |
| Dialog control | 8 | 42 |

Of the 40 clicked tags, 15 match a first unit update, one differs from a first unit update and 24 precede a point update. In 23 independent 41810 recordings a click matched the first unit update of one sequence that also had a uniquely recorded later issue. Its issue selected the clicked unit. The same relationship failed in **34 of 34** issue-backed retail controls where the click matched the first unit update, including one case in three new public recordings. The actual retail issue targeted a different unit in 22 examples and carried no unit target in 12. Nine of the 34 clicks even preceded the actual issue in physical order. Retail comparisons use a unique earlier issue with descriptor bit 19 set. They do not reproduce the historical state-2 producer. The project emits zero new issues from these associations.

Of 1,100 recorded same-sequence later issues from the historical recordings (39 TEN and 1,061 independent), none contained an explicit ability, other-unit tag or unit-group tag. In 427,330 qualifying 98348 sequences, 4,138 actual issues carried an explicit ability. None populated other-unit, unit-group or vector. The target counts split into 377,535 established and 49,795 new public control sequences. These three absent optional fields constrain an empirical candidate descriptor. The absent issue bytes of an individual TEN sequence remain unknown.

The installed client set inspected for this study starts at 92264 and the workspace search found no historical 41810 executable. The Blizzard 41810 grammar gives unit-click a unit tag and selection its own delta. It provides no command sequence link in either event. A Blizzard maintainer identifies the command ability link as an index relative to that build's ability data. [Official protocol source](https://github.com/Blizzard/heroprotocol/blob/master/heroprotocol/versions/protocol41810.py), [maintainer's explanation](https://github.com/Blizzard/heroprotocol/issues/27).

Run `python command_ui_evidence.py SOURCE PRIVATE_REFERENCE_MANIFEST NEW_PUBLIC_FIXTURE_DIRECTORY` with the recovery repository, its Blizzard heroprotocol checkout and MPQ dependency on the Python import path. The JSON receipt records only aggregate counts and archive hashes. The three additional download hashes are pinned in the script and identify the 98348 public fixtures in the Heroes.StormReplayParser repository. [Public fixture tree](https://github.com/HeroesToolChest/Heroes.StormReplayParser/tree/92b0286fd3c12fc713a8b4e9983f1182da48c4cb)
