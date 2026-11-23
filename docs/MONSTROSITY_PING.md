# Monstrosity ping in TEN_GREYMANE

The ping at loop 9030 refers to the second of six Monstrosities. Abathur targeted his own normal Locust at loop 8729. A different unit generation was born at the same loop, the Locust died at loop 8730 at the summon's position (106, 54), and the summon survived until loop 9257. The source game commands and tracker agree on the caster via the setup user mapping, the earlier named heroic talent purchase, the target's control and upkeep owners, and the transformed host generation. All six executions of source ability link 45, command index 0, resolve one-to-one to six births.

An independent game at build 97605 reproduces five such transformations using ability link 197. In all eleven cases the host dies one loop later at exactly the summon's tracker coordinates. One control snapshot taken by the command differs from that location by one map cell. [Cast and ping observations](../observations/monstrosity-casts-and-ping.json)

Build 98348's pinned AbathurData.xml links the targeted ability to its initial effect set, the unit creation effect and the exact produced unit type. The set accepts minions or Abathur Locusts. These records identify the summon that a compatible simulation must produce. The build-98348 numeric ability link and the allocated unit index and recycle value on the recovered map remain unresolved.

Reproduce with `python trace_monstrosity_ping.py --catalog AbathurData.xml --case REPLAY SHA256 BUILD`. Repeat the last option for each recording. The receipt identifies both full inputs and the installed catalog by SHA-256.
