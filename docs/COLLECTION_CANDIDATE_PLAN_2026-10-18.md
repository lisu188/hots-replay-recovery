# Exact-name collection candidate planning

`plan_collection_candidates.py` compares the existing catalog-only collection observation with the exact SHA256-pinned static declaration projection for live build `2.57.0.98348`. It reads the two JSON inputs and writes one new report. It does not accept a replay, ownership matrix, player identity, raw XML or network input.

From the repository root, with Python 3.11 or later:

```powershell
python plan_collection_candidates.py --licenses observations/collection-license-current-98348.json --collection-observation observations/collection-identities-2026-10-18.json --output NEW_COLLECTION_CANDIDATES.json
python -m unittest discover -s . -p test_plan_collection_candidates.py -v
```

The actual fixture test locates `observations/` beside the test file. `COLLECTION_PLAN_FIXTURES` can instead point to a repository checkout containing those pinned observations. The CLI always requires static projection SHA256 `c8f03ddbc859feb5c2dc1836761201b5e6fea4632ce0325817abdd7299c8aa22`; it has no hash override. The Python `expected_sha256` argument exists for hash-bound synthetic fixtures in tests, which do not establish current-build provenance.

The planner verifies the collection observation's byte count, SHA256 and case summaries against the static projection, rejects unsupported schemas and numeric bounds, and recomputes the stored direct comparison from declarations. It selects only exact legacy-name matches among `CReward*` records and observed literal `License` values. `ProductId` collisions, shared License values and duplicate declarations are reported separately. They establish no aliases or effective identity mapping. Parent, default and duplicate-record blockers remain unresolved even if one literal candidate exists. Field-level reasons are reported separately from record-level reasons.

The actual current inputs reproduce 263 legacy names and 5,418 current keys: 56 names have one observed literal candidate, including 54 without recorded reward-record reasons and two with unresolved parent inheritance (`Horse` → `10182`, `Vulture` → `18535`). Another 207 names remain unresolved: 201 have no exact reward record and six have no observed literal License. These counts express candidate coverage only. They do not authorize collection conversion, resolve catalog inheritance/order or prove ownership or replay playback.

The focused suite contains 13 tests, including the actual pinned projection, wrong-build/unbound inputs, duplicate JSON keys, malformed paths/schema, unsigned numeric bounds, namespace collisions, ambiguous candidates, default/indexed exclusions, duplicate identity blockers and refusal to overwrite output. Synthetic XML fixtures are generated only inside temporary test directories.
