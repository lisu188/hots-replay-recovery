# StartReplay parser and configured schema - 2026-10-27

The compiled slot121 path is now connected to the client's configured StartReplay metadata. The shown wrapper uses native type6060, `Battlenet::Event::S2GameEngine::Response`; its event choice maps selector13 to `StartReplay`, with payload type5951, `StartReplayRequest`. These names already existed in the retained namespace data. This milestone binds them to the previously authenticated sender path and identifies its virtual read method.

Addresses and offsets are hexadecimal; type IDs, selectors and counts are decimal. The [observation](../observations/startreplay-parser-and-schema-2026-10-27.json) records source, code, table and metadata-reader pins. Executable witnesses use the retained analyst-derived 98348 static text patch. The original PE supplies the selected table word, type-ID word and embedded BSN data. No runtime capture is involved.

## Wrapper and virtual read method

The wrapper W is at `RBP-49` in the selected sender. Its shown initialization places table `298CA10` at W+10 and registry address `0x143B7F140` at W+18. It loads the DWORD at `298BEF8` into R8D at `1E5CFC7`, then stores that configured type ID at W+20 at `1E5CFEF`. The original PE word is 6060. The prior store at `1E5CFCE` sets DWORD[W+8] to zero. That field's role remains unresolved, and the store supplies no historical payload default.

`1E5AA40..1E5AA45` is a five-byte helper returning W+10. On the shown stable-vtable path, the virtual call at `1E5D09B` selects table offset+108. The original PE word at `298CB18` points to `1A6E990`.

The selected `1A6E990..1A6E9EB` body checks `QWORD[QWORD[entry_R9]+38]`, returning AL=0 if it is null. Otherwise it builds a local call frame and calls `1A78CC0` at `1A6E9DC`, then sets AL according to whether the returned EAX is zero. Entry R9 is a separate external input descriptor; it has not been equated with configured BSN type6060. The helper algorithm and that descriptor's semantics remain unresolved.

After the virtual call, the sender immediately reloads the holder at `1E5D0A2` and its leading selector at `1E5D0A6`. There is no local test of the returned AL before that selector load. This does not establish a successful complete parse, initialized missing fields, or acceptance of malformed input. P continues to mean the pointer reloaded after the call; replacement of the holder pointer is not excluded.

## Configured metadata path

Two data-only metadata readers each validated all 8,330 embedded records. A focused comparison of 30 selected records agreed on framing, kinds, names, bounds, tags and child references. The path is:

| Type ID | Relationship |
| --- | --- |
| 6060 | `Response`, with field `m_event` pointing to 6061 |
| 6061 | USER wrapper for 6062 |
| 6062 | `Response::Event`, with 22 contiguous selectors 0 through 21 |
| 6076 | Selector 13 `StartReplay`, a USER wrapper for 5951 |
| 5951 | `Battlenet::Event::S2GameEngine::StartReplayRequest` |

The nine declared request fields are `StartRequest`, `m_clientId`, `m_clientInfoList`, `m_voiceSessionId`, `m_instanceHandle`, `m_clientLicensesList`, `m_replayPath`, optional `m_startGameTime`, and `m_turnIntervalMS`. The client list uses type 1702 with a declared count 0 through 16 and element ClientInfo type 1768. The path field uses native LocalPath type 354 with declared STRING count bounds 0 through 248. These are current schema declarations, not observed values or recovered native memory offsets.

The replay-start request reaches shared StartRequest type 5834 through its field wrapper 5952. The archive's current online battlelobby root 5917 reaches the same base through StartGameRequest type 5842 and its StartRequest field wrapper 5843. This verifies a shared current schema base while preserving the two distinct roots and their field framing. It supplies no missing historical player, entitlement or resource values.

## Scope and next source task

The three new witnesses cover 195 bytes and 49 instructions: the embedded-interface getter, the selected storage helper, and the virtual read method. Another 1,142 bytes and 255 instructions from the sender were rechecked against the freshly hashed static patch. The storage helper returns global address `3B7EDA0` and supplies literal EDX=`406C` to `304660` on its selected initialization branch; the callee remains opaque, so no element-layout or historical-default claim follows.

No new database, game launch, Computer Use, codec change or replay was produced. The configured current schema and compiled callback route do not prove an actual StartReplay input, complete decoding, a historical conversion or deterministic playback. Next resolve the input descriptor and `1A78CC0`, or follow the separately identified Request type 5973 path toward the upstream replay-load request producer. The full replay upgrade remains incomplete.
