# Reviewed collection projection pin refresh — 2026-11-15

The complete offline regression workflow at `2e07bf16cd8b61b4a9d3d6fbec7c9e5fe0b49111`
failed the actual collection-planner fixture on all three platforms because its
whole-file SHA-256 pin still described the October projection. The artifact had
already been refreshed by bot commit `b4967a2ae5bf28148a27c247be284c5eb36191e0`
on November 13, in run `43387752047`. That commit changed only the projection;
it did not refresh the consumer's pin. The later R5 publication-preservation
change did not cause this mismatch.

The review compared the complete artifact at historical commit
`9adb72853c01dd24101649709f341c2ccb3f95a6` with the artifact at current commit
`d708548c27a38c43fecf81d19a2f3e5db65249c1`. Both files have 9,580,143 bytes.
The old SHA-256 was
`c8f03ddbc859feb5c2dc1836761201b5e6fea4632ce0325817abdd7299c8aa22`;
the reviewed current SHA-256 is
`80c64713d4a9183d98e61e9b67f624ba230daa08d303dfb237b971733113eb7c`.

Exactly six JSON paths changed:

| Path | Reviewed difference |
| --- | --- |
| `/generation_provenance/github_run_id` | `39156204685` → `43387752047` |
| `/generation_provenance/official_manifest_sha256` | Recorded official-manifest digest changed. |
| `/generation_provenance/repository_commit` | `843a15858659acb75bf6b4e9fef45f28931f7faf` → `6adad9bf2a495db662e596e53b62d96b8ac4ca9c` |
| `/generation_provenance/workflow_url` | Changed from the October run URL to the November run URL. |
| `/source_files/109/sha256` | Digest of the 130-byte `mods/hdp.info` metadata file changed. |
| `/version_binding/metadata/0/sha256` | The same `hdp.info` digest changed in its version-binding descriptor. |

[The machine-readable review](../observations/collection-projection-pin-refresh-2026-11-15.json)
retains every old and new value, Git blob identity and comparison digest.
Replacing only those reviewed JSON literals makes the complete old file
byte-identical to the current file. The artifact itself was left unchanged.

All 5,575 XML source descriptors, 10,199 tracked declarations, 13,398 selected
fields, counts, collection identities and direct-comparison data are identical.
The projected `hdp.info` version remains `2.57.0.98348`, with `IsPtr=false` and
the same size and metadata shape. Its raw old and new contents were not
recovered; this review establishes the projected fields and hashes only.

Planning both hash-verified versions produces identical results except for the
input artifact digest: 56 single-license candidates and 207 unresolved names.
Every returned planning value, including all 263 candidate rows and eligibility
flags, has the same canonical SHA-256
`6e6f37fd954c656bb7719423a07804e8c0d32ff816892e9271ef5f4f602b7a60`.
Effective catalog order, inheritance, aliases, ownership and whole-collection
conversion remain unresolved.

The planner now pins the reviewed complete current artifact. Its exact SHA-256
check still runs before JSON parsing and binding. No normalization, provenance
exclusion or automatic pin refresh was introduced. Regression checks reject
unreviewed provenance, `hdp.info`, direct-license and whitespace changes under
the default pin, and retain the complete planning-result digest above.

Local focused validation completed 47 planner/collector tests: 46 passed and one
Windows synthetic-symlink case used its declared host-permission skip. All 14
planner tests passed. These checks did not launch a client or establish runtime
catalog semantics or replay playback.
