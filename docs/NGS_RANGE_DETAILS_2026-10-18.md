# Bounded partial NGS replay screening

This helper screens a saved public NGS replay key without downloading its full
object. It supplies the file-like read/seek interface used by pinned
`mpyq==0.2.5`, with listfile loading disabled. Only the header, legacy hash/block
tables, `replay.details`, and optionally `replay.tracker.events` are read.
The returned details/tracker bytes contain private match data and must remain
in memory. Published observations contain build/root, map, selected hero names,
target unit-type counts and acquisition receipts only.

This is an NGS-specific metadata helper, not a general MPQ validator or downloader.
It does not create a replay, infer catalog mappings, verify full-object SHA256,
establish whole-parser acceptance, or launch the client.

## Dependencies and API

Install `mpyq==0.2.5` in the normal Python environment. The helper does not alter
`sys.path` or depend on a task `work/` layout. It verifies both version and the
exact installed source SHA256 before any request:

`526d3e3ae1f5254d8bc32e0248b0763ec5998f350846876c38794373983bed78`.

```python
from ngs_range_details import SharedBudget, screen, read_member

budget = SharedBudget(max_requests=400, max_bytes=4 * 1024 * 1024)
source, archive, details_bytes = screen(observed_public_ngs_url, budget=budget)
# Decode build/root and details privately with the pinned official protocol.
# Only after the exact build/root and selected hero gate succeeds:
tracker_bytes = read_member(archive, "replay.tracker.events",
                            output_bound=2 * 1024 * 1024)
```

The caller must obtain keys from an observed public source. The adapter accepts
only HTTPS object URLs under `s3.amazonaws.com/ngs-replay-storage/`; it refuses
credentials, queries, fragments and unsupported encoded keys. It never tries
another region, bucket, redirect target or full-object fallback.

## Enforced bounds

- Every response must be `206`, with the exact requested `Content-Range`, a
  consistent object size and a strong ETag. Every request after bootstrap sends
  `If-Match`, and the returned ETag must remain identical.
- A `200`, redirect, `412`, invalid range, changed ETag/size or encoded HTTP body
  is refused before its body is consumed. The response is closed.
- An object is at most 5 MiB; each logical read is at most 64 KiB. Per object,
  at most 24 requests and 128 KiB of response body bytes are allowed. A shared
  budget across objects cannot exceed 400 requests or 4 MiB of response body
  bytes. These counters do not represent HTTP/TLS wire overhead.
- Reads with no explicit size are rejected. Cached ranges consume no new
  requests. Failed attempts count against the request budget.
- Details output is capped at 64 KiB and tracker output at 2 MiB, with bounded
  zlib/bzip2 decompression, exact sector sizes and trailing-data rejection.
  Unsupported flags, encryption and CRC profiles are refused.
- Compressed non-single-unit members ending exactly on a sector boundary are
  explicitly refused before member I/O. The inherited mpyq `floor+1` formula
  has not been promoted into general support for that boundary. The tests
  cover explicit 512-byte and 1024-byte refusals.

The archive view supports the observed legacy table layouts used by MPQ
format values 0, 1 and 3. In particular, it does not validate all extended
format-3 fields. The recorded control equality covers every header field read
by mpyq and the complete user header, not every physical extended-header byte.

## Validation and actual observations

`test_ngs_range_details.py` has 15 focused tests, including full-200 refusal
before body reads, redirects, range/ETag/size mismatches, shared and per-object
budgets, bounded decompression, exact-sector refusal and an optional authentic
control. Run:

```text
python -B -m unittest -v test_ngs_range_details
```

Set `NGS_RANGE_CONTROL` to the already-downloaded Sky Temple control to enable
the authentic offline case. Its full SHA256 is checked against
`afcf49a656068f343173fc79afff2d2ebf15066f531cb192382cdba9d1ea3272`.
The test uses a local synthetic Range transport, compares header/details to
unchanged mpyq, and also compares the complete decoded tracker bytes. It makes
no network request. Without that fixture, only this authentic case is skipped.

The saved live control proof used 6 exact `206` requests and 1,821 response body
bytes for the 1,357,323-byte Sky Temple object. Header/details equality passed.
The details member SHA256 is
`570d27e3f489fa49c99a4792ea0b062040515785a267ef035bbfb948874146d9`.

The actual bounded search screened 40 previously undownloaded keys from an
85-key saved public projection: 243 requests, 205,526 response body bytes,
all exact executable/base/data build 98348 and root
`c3b3c8bc82e3a5a62e550fdde9a40c28`. It found two Nova rosters. One complete
tracker stream reported `HeroNova: 1` and `NovaHoloClone: 116`. The one Abathur
tracker inspected contained no Monstrosity type. This is not a full replay
validation or a claim that all uninspected tracker streams lack Monstrosity.

The live receipts were captured with the scratch prototype before portability
changes and the explicit sector-boundary refusal were added. The final portable
code has 15 passing offline tests with the authentic control enabled. No further
network requests were made to relabel the historical receipts as a new run.

Evidence files:

- `ngs-range-details-control-proof.json`: live known-control comparison.
- `partial-roster-tracker-screening-40.json`: URLs, build gates, ETags, exact
  requested ranges, counts and partial-only limitations; no raw members.
- `ngs-range-portable-validation.json`: final portable source hashes and checks.

The selected full replay must be acquired and hashed separately before it can
enter the existing complete reference-inspection pipeline.
