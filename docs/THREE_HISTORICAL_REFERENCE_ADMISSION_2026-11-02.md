# Exact admission for three historical Dragon Shire controls

The read-only historical reference gate now accepts three separately named
41810 controls from the earlier local acquisition. Previously selecting the
public41810 profile rejected these different files at its fingerprint guard.
The new choices are41810-local3,41810-local4 and41810-local5. Each requires its
own exact whole-file length/SHA256, observed event counts/hashes, lobby member
length/hash, mod count and section boundaries. Build41810 alone admits nothing.

The command structure remains:

```text
python scripts/check_historical_references.py --profile 41810-local3 --replay PRIVATE_LOCAL_COPY --report NEW_REPORT.json
```

Use the existing pinned upstream environment. The private inputs are not in the
repository. The command writes sanitized evidence only, refuses an existing
report, and does not write a replay or transformed member.

## Separate member and MapInfo policy

legacy_mapinfo_framing.py adds exactly three measured member digests and their
five-record span lists. All source MapInfo record bits equal the original at
the same spans, but their surrounding whole lobby members have distinct hashes.
The previous four entries remain byte-for-byte unchanged. Admission now totals
seven member hashes and38record spans; MAX_RECORDS remains7. Nonempty permission
lists remain unsupported. The codec algorithm and source/schema guards did not
change.

The gate's MapInfo policy is explicit per profile. The public41810 control keeps
its seven records,1816native comparisons and original converted-member hash.
Each new control has five records,160named root comparisons,1191comparisons
across all native fields and its own converted-member hash. Added bytes are
three per record: only the empty permission count expands from seven to31bits.
Every field value/bound, non-count token and outside bit must remain exact, and
the inverse must recover the entire original member. The nearby42273 control
remains unadmitted and never invokes the framing converter.

## Fresh validation

All three new references freshly reconstruct header, details, initData and all
game/message/tracker streams byte-identically. The unchanged core helper also
compares semantic values with the pinned official decoder. Across these files
that covers331482game events,419message events and18900tracker events. Message
and player values were used only in RAM for codec checks; none are emitted.

Each lobby passes same-profile full-source reconstruction and a RAM-only
MapInfo proof. Across the three controls,15records pass480named root comparisons
and3573native-field comparisons. Each transformed RAM member gains15bytes; each
inverse equals the complete input member. No transformed payload was saved.

The exact CLI entry point passed on all five actual references: the two old
public controls and three new private ones. The two public result dictionaries
equal those returned by the previous gate implementation, with all old profile
values preserved. A wraps-only spy observed zero converter calls for actual
42273 and one for each admitted41810 profile; no admission/return value was
overridden. Three real same-build fixture/profile swaps were rejected before
schema loading.

Thirty-one focused unit tests passed with zero errors, failures or skips,
including six new tests for the pre-import fingerprint guard and cross-profile
MapInfo source/count/hash refusals. An independent reviewer repeated the31tests
and checked the exact profile data, unchanged old profile/admission values,
codec AST and privacy/closed-routing conditions, with no actionable findings.
The existing offline workflow discovers root test modules; no private replay
was uploaded or added to hosted CI, and no hosted run is claimed here.

For the combined local check, an isolated copy of the existing pinned upstream
package adds its separately cached, byte-verified official42273 schema. The
earlier partial LF package was missing that filename. Existing dependency files
were preserved; no package acquisition, source rewriting or runtime fallback
was needed. Both41810 and42273 schema bodies match the allowed canonical pin.

## Limits and next conversion boundary

See observations/three-historical-reference-admission-2026-11-02.json and its
validation receipt for exact pins and the per-profile results. These gates
formalize the new historical controls; they do not convert TEN_GREYMANE or R8.
The lobby suffix remains semantically opaque despite exact byte reconstruction.
Current-format complete lobby decoding, effective catalog/rule equivalence,
missing player fields, ability126/351implementation identity and deterministic
98348playback remain separate gaps. No values were guessed or copied from a
donor. No game, Computer Use, target-native execution or emulation occurred.
Full upgrade and current-client playback remain false.
