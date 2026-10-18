# Exact EU HeroesData header reproduction

`recover_current_eu_heroesdata_header.py` reproduces one content-addressed object:
`f644ce88b9d1a1c15af40be380be285f3d2ffcaf901dc9c15da367e763ee75c0.s2mh`.
It accepts explicit local inputs and uses no machine-specific cache path,
precomputed observation/profile report, network, client, SDK or replay writer.
It revalidates the complete observed reference core with pinned Blizzard schema
96477, its actual98348 build/base/data/root, EU participant regions, the actual
battlelobby package169992/version65663 and exact advertised EU target handle.
The source headers and schema have fixed SHA256 requirements.

## Inputs and modules

Provide these private inputs:

| Input | SHA256 |
|---|---|
| EU HeroesData65662 header | `f115def2b9adbc67cfdd8bb4255cff1a8b44a8c921e98f56eebe20708660a7c9` |
| EU HeroesData65661 singleton witness | `29f66c9eca1844826ad55f63eb8fd32a2d6e74ddb7931a8e835fb951f58e184d` |
| Verified public EU replay used locally | `a3c97e9a669e73e4c2b19a8f6c5e2de0315cbc5725be82cf1e887ed6319a01c4` |

The first two headers are bounded at512KiB each; the replay is bounded at3MiB.
The CLI accepts another reference only if the complete explicit context and
narrow recipe gates also pass. The fixed full target SHA remains the acceptance
criterion. No region, package version, catalog mapping or missing field is taken
from a saved CI report.

The project modules must be importable, together with:

- `lossless_wire.py`
- `battlelobby_header_attributes.py`
- `project_attribute_nodes.py`
- `registry_header_candidates.py`

The root registry helper contains only the bounded pure functions, extracted
without AST changes from the historical research producers. No cache loader is
imported. The required canonical Blizzard schema96477 has SHA256
`e95b728028399e7ffcfd32dff5e0c5fa3077d3827837755ccf40da2efcedbc84`.

Create the output directory before running. Then use your actual input paths:

```text
python recover_current_eu_heroesdata_header.py \
  --source-header INPUT-65662.s2mh \
  --prior-header INPUT-65661.s2mh \
  --reference-replay INPUT-current-EU.StormReplay \
  --output PRIVATE/f644ce88b9d1a1c15af40be380be285f3d2ffcaf901dc9c15da367e763ee75c0.s2mh \
  --report result.json
```

The example uses POSIX line continuation; on PowerShell, put the command on one
line or use PowerShell's continuation syntax. Add the repository, helper folders
and installed pinned heroprotocol package to `PYTHONPATH` as appropriate.

## Acceptance and evidence

Exactly two registry insertion vectors are assembled in RAM. The recipe applies
the14observed attribute definitions,12observed locale handles, version65663,
an experimental+9shift of99strictly checked field7indices, and the nine
historically witnessed registry singletons. All other65662fields and wire types
remain unchanged. These hypotheses are accepted for this object only after its
complete bytes match the independently advertised target SHA256.

Mismatching bodies are never written or emitted. A matching body also needs a
complete independent `depot_s2mh_wire` decode and generic-value agreement before
exclusive output creation. Existing output or report paths are refused.
The report contains hashes and structural metadata, without raw localized text,
account identifiers, ownership masks, messages or score values.

Exit0 means the exact header was recovered and written. Exit2 records an inspected
hash miss without a header write. Exit1 means invalid input or an I/O failure.
Artifact and report writes are not a multi-file atomic transaction; an accepted
header can remain if a later report write fails. Such a file still needs its
own digest verification. This does not alter the no-mismatch-write rule.

The fresh portable local run reproduced the negative candidate
`de56b149b10ed06cc13a00ef601e86b59cfb0b2533ea4cb6ec47a784251f1d88`
and exact positive target,222049bytes, using the second registry gap1502.
`portable-reproduction.json` records that run separately from the original
machine-bound experiment, whose executed source remains unchanged.

Run the focused synthetic filesystem guards with:

```text
python -m unittest test_recover_current_eu_heroesdata_header test_registry_header_candidates -v
```

The eight tests cover mismatch/no-file, exact digest plus complete wire, existing
output preservation, trailing-wire refusal, malformed expected digest, size
bounds and existing-report preflight. They use a tiny synthetic generic header;
they are not substitutes for actual input reproduction.

The exact old65661/65662EUdepot URLs currently return404 in the parent's fresh
availability check. Therefore a hosted CI job cannot presently acquire these
exact private inputs from those URLs. Keep raw headers/replays out of Git;
run synthetic guards in CI and retain the explicitly local full reproduction
receipt. Do not report hosted full reproduction unless those exact input bytes
are independently supplied and verified.

Recovering this static header does not modify TEN_GREYMANE, prove account
entitlement semantics, recover a Dragon Shire regional package tuple, or prove
deterministic replay playback.
