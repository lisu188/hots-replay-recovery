# Current ClientInfo source transfer — 2026-10-25

The covered current ClientInfo copy paths forward player level, boost and the conditional InfoHero voice/staff flags from source bytes. Independent reviews now cover existing-record assignment at `6B9A50` and SharedPlayerInfo transfer at `6BADE0`, alongside the prior append-path proof. These findings identify where the current values come from during copying. Historical per-player values and a valid old-to-current migration rule remain unresolved.

This extends [the client-list copy paths](NATIVE_CLIENT_LIST_COPY_2026-10-25.md), following the [backing-list address proof](NATIVE_CLIENT_LIST_BACKING_2026-10-25.md). The [structured observation](../observations/native-clientinfo-source-transfer-2026-10-25.json) records reviewed witness/profile hashes and exact address facts. All addresses and displacements below are hexadecimal RVAs or native record offsets.

## Five declarations and their conditions

The pinned current profile names two ClientInfo fields and three fields conditional on SharedPlayerInfo tag1, InfoHero:

| Field | Declared wire width | Native record offset | Observed native transfer |
| --- | --- | --- | --- |
| `m_playerLevel` | 32 bits | `+0x358` | Source DWORD, both covered record paths |
| `m_hasActiveBoost` | 1 bit | `+0x35C` | Source byte, both covered record paths |
| `m_isLobbyVoiceSilenced` | 1 bit | `+0x2C1` | Source byte, InfoHero tag1 |
| `m_isTeamVoiceSilenced` | 1 bit | `+0x2C2` | Source byte, InfoHero tag1 |
| `m_isBlizzardStaff` | 1 bit | `+0x2C3` | Source byte, InfoHero tag1 |

The tally is 33 common ClientInfo bits plus three conditional InfoHero bits. **36 is an omitted-declaration sum, not a universal append-36-bits recipe.** The old observed branch0 has not been authenticated as current InfoS2 or InfoHero. Native byte copying also does not prove Boolean normalization, accepted wire values or absent-field handling.

Transfer claims require valid initialized readable source and writable destination storage, valid ranges and nonoverflowing index arithmetic. Preceding helpers must return normally and preserve the receivers under the ordinary ABI. Relevant source bytes and list headers must stay stable until read; helper/global aliases, callbacks and concurrent writes must not invalidate that condition. Distinct variant storage must be disjoint or satisfy an equally strong noninterference condition. Arbitrary partial-overlap snapshot copying is unproved.

## Existing and appended records

The list helper passes existing records to `6B9A50` from `6B5BF7`. It uses record base `list+8+i*0x360`, with a stride of 864 bytes. Its header operations are QWORD-width, while retained DFE7D0 consumers load the count through DWORD operations. That width difference remains explicit.

The existing-record function has 115 decoded instructions covering 625 bytes through RET. Its optional-field branches rejoin a common tail: `6B9C9A/6B9CA0` load/store the level DWORD, and `6B9CA6/6B9CAD` load/store the boost byte. The earlier append path has corresponding direct transfers at `6B5EE5/6B5EEC` and `6B5EF3/6B5EFB`. These are source transfers under the stated conditions. Other assignment helpers remain unexpanded, so no unconditional entry-snapshot or complete deep-copy guarantee follows.

Both paths call `6BADE0` on the corresponding record `+0x2BC` variants. Append initializes the destination tag to `0xFFFFFFFF` before `6B5E49`; existing assignment calls at `6B9C14` without that preceding sentinel store.

## Variant behavior and native tag limits

The joined variant listing contains 147 bytes and 44 instructions, with seven conditional branches, two RETs and no calls. Equal variant pointers return before any variant-memory access; this does not establish whole-record self-assignment behavior through the other helpers.

For distinct pointers, an existing destination tag0 or1 is invalidated before reading the source tag. Source tag1 constructs InfoHero and forwards bytes `+4..+8`. The three requested flags are variant `+5/+6/+7`, which become record `+0x2C1/+0x2C2/+0x2C3`. A nonzero copied presence byte `+8` also causes a QWORD payload transfer at `+0x0C`; absent payload is not copied or cleared on that path. PartyAddress is a current-schema aggregate. This eight-byte native transfer establishes no wire-u64, identity or lifetime rule.

Source tag0 constructs the other branch, copying presence `+4`, conditional DWORD `+8` and byte `+0x0C`. Other source tags return without constructing a recognized source payload. A previously valid destination has already become `0xFFFFFFFF`; another prior tag remains. The current schema declares only tags0/1, but the native body is not a reject-all-unknown-tags validator and does not normalize every input to a valid branch.

The code came from the existing analyst-derived, statically transformed 98348 text patch, not runtime capture or unaltered PE text. Three new hidden IDA batches completed with exit0 in empty databases; decoded game code was not executed. Noncovering/fragmented metadata and external-callee limits remain recorded. No codec or replay changed, no historical values or defaults were recovered, and native playback, synchronization compatibility and full conversion remain unproved. No new exact-head CI result is claimed.
