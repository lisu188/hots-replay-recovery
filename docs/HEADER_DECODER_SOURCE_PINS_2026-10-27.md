# Exact decoder source variants - 2026-10-27

The upstream decoder pin now supports both the canonical LF Git blob and the exact known CRLF checkout. The earlier LF correction in `7dc5f98` remains intact. This follow-up preserves local Windows compatibility and records which physical decoder source was used by the three-header integration audit.

The original regression run at `820aefa` failed in the numeric879 header step on all three hosted jobs. Its retained tracebacks identify the decoder source pin, rather than a replay decode, as the failure. The pinned Blizzard revision `9af3ea7150f1a8acb53464c92519a9bbcc7a3594` stores `heroprotocol/decoders.py` as 9,199 LF bytes with SHA-256 `17bfb926af0f7f79e18f6299dbae50fc2821c53b229235d4f9c857c7ef3e96b1`. The previously authenticated local CRLF file has 9,512 bytes and SHA-256 `c5e4e7c588ebc2ef722ab9fd9def2e67e309c45d451639cfdee3126b0f616a42`.

The bounded pin reader accepts those two complete byte identities only for this decoder. Other dependencies retain their single exact pins. It does not normalize a file before authentication, rewrite the dependency cache, or accept mixed endings or modified Python. The integration report separates the actual physical decoder pin from its canonical LF pin.

Two regression tests cover both accepted sources and reject an appended comment, truncation, mixed endings and an oversized input. All 19 header tests pass separately against fresh LF and CRLF package copies made from the pinned upstream Git blobs. In each environment, the real original41810, partial R8 and current98348 headers pass source inversion and six independent official checks of a controlled in-memory edit. Neither those edits nor this pin correction define a build-retarget policy. Hosted results for a later commit must be checked separately.

The [observation](../observations/header-decoder-source-pins-2026-10-27.json) records this validation. No replay bytes, header schema, wire policy, synchronization data or game installation changed. Full historical conversion and playback remain unproved.
