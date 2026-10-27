# GetReplayInfo callback, readers and reply - 2026-10-27

The selected compiled path now connects `Response.GetReplayInfo` to its path-consuming callback, replay-reader calls, and success/failure `Request.GetReplayInfoResponse` messages. This narrows the file-inspection route while keeping it separate from the recorded bootstrap and full playback.

Addresses and offsets are hexadecimal; type IDs, selectors and counts are decimal. The [observation](../observations/getreplayinfo-reader-and-reply-2026-10-27.json) pins the witnesses. Executable code comes from the retained analyst-derived 98348 static patch. Original-PE and embedded-BSN SHA-256 pins were refreshed. No game process or runtime capture was used.

## Callback and path

The response choice's selector 14 branch starts at `1E5D28C`. On the selected initialized-object route, it forms callback receiver `(G+D0)+3E8=G+4B8`, physical slot 124, and argument tag 124. The argument carries a scanned C-string pointer derived from P+14 at offset+18 and its count at+20. Handler `CD3FE0` reads that pointer and the low DWORD of the count at `CD4050/CD4057`.

The retained registration range initializes descriptor function `CD3FE0` at global `3771390` with shown signed adjustment 0 at `3771398`. It uses the global-derived slot at `CDBB16/CDBB29` and stores thunk `CD1800` in the flagged node at `CDBB3A`. With the same valid stable node and zero adjustment, the owner+10 registration key becomes the owner receiver; the argument pointer remains in RDX. Lazy-init skip paths, other descriptor writers and concurrent mutation remain outside that conditional proof.

## Reader gates and response

The selected handler prefix calls `134E680`, cached-header wrapper `134DC00`, `134D9D0`, required setup reader `134DD30`, metadata wrapper `134D950`, and `134DF60`, followed by cleanup `134BF90`. Their exact callsites are recorded in the observation. The established setup and metadata member bindings remain those in [the recorded-bootstrap gate study](NATIVE_RECORDED_BOOTSTRAP_GATES_2026-10-25.md), including distinct native775 setup and online5917/local5962 battlelobby roots.

At `CD449F/CD44A1`, nonzero EAX from `134DD30` branches to failure label `CD4DB4`. A zero accumulated BL also branches there at `CD44A7/CD44A9`. The selected success path writes inner selector 0 at `CD4521`. The later metadata read at `CD455A` branches on a nonzero result to `CD46D9`, rather than directly to that earlier failure label. This is a local branch distinction; it does not authenticate every callee effect, successful complete decoding, or playback.

The request object is at RBP+180. Its outer selector 14 is written at `CD402E`. The selected success branch calls `1D81F60` at `CD4CBE`; the failure branch writes inner selector 1 at `CD4DDE` and calls it at `CD4DEA`. Both pass the local object's address in R9 and byte 2 in DL, conditional on normal returns and no intervening alias mutation invalidating the shown values.

The data-only metadata readers agree on the selected request/response declarations. `Response` type 6060 names selector 14 `GetReplayInfo`, whose payload 6077 contains `m_replayPath`. `Request` type 5973 has 18 event choices; selector 14 names `GetReplayInfoResponse`. Its success branch is a USER wrapper for `Battlenet::S2Game::Replay::LobbyInfo` type 6027, containing `m_slotList`, `m_replayTitle`, `m_date`, `m_eventList`, `m_headerCacheHandleList` and `m_mapInfoList`. Failure is NULL. These declarations provide no historical ClientInfo defaults or payload values.

## Sender and input bridge

`1D81F60` configures a local wrapper with registry `0x143B7F140` and type 5973, initially retaining its incoming R9 payload pointer at wrapper+30. After an opaque wrapper virtual call at+40, it passes the wrapper address to slot+28 of the object at saved-owner+918. That call also receives zero-extended entry DL and the saved entry R8. No asynchronous-copy, lifetime or execution guarantee is inferred from this forwarding boundary.

The previously unresolved read bridge `1A78CC0` is a five-byte tail jump to `1A78210`. The selected body dispatches the result of `1A6D8B0` through 16 branches after subtracting 1 and checking an unsigned upper bound 15. All 16 entries of the 64-byte table at `[1A78668,1A786A8)` point to selected instruction starts. The table and preceding padding are excluded from instruction counts. Type-specific callees and the external input descriptor remain unresolved; this is not a complete wire-reader implementation.

The five new witnesses cover 5,159 bytes and 1,107 instructions. Another 1,222 instructions from the retained registration and response sender were rechecked. The consumer witness is a prefix ending in a conditional branch at `CD4E8E`; cleanup continues beyond its selected end `CD4E90`. Runtime-function adjacency does not prove a complete function or CFG. Native byte columns and endpoints were checked with trailing decoder context. Failed linear/table and terminal-classification attempts remain local and are not accepted witnesses.

No new database, Computer Use, game launch, codec change or replay was produced. Preview metadata, recorded bootstrap, full historical conversion and deterministic playback remain separate evidence scopes. Next qualify the relevant reader component contracts or trace the actual replay-start producer, without promoting this preview reply into gameplay or migration acceptance. The full replay upgrade remains incomplete.
