# Historical reference gates

41810 matches TEN_GREYMANE's build; 42273 is separate.
Sources: [41810 ZIP](https://upload2.inven.co.kr/upload/2016/04/12/bbs/c13569754257.zip),
[page 2520](https://www.inven.co.kr/board/hos/4200/2520);
[42273 replay](https://upload2.inven.co.kr/upload/2016/04/20/bbs/r13421174119.stormreplay),
[page 2558](https://www.inven.co.kr/board/hos/4200/2558).

| Build | Game / message / tracker events | Mods | Metadata / handle end bits |
| --- | --- | ---: | --- |
| 41810 | 134617 / 160 / 4405 | 7 | 227810 / 230056 |
| 42273 | 50614 / 281 / 3370 | 5 | 215673 / 217280 |

`python scripts/check_historical_references.py --replay INPUT --report NEW.json`
defaults to 41810; `--profile 42273` selects the nearby control. Exact fixture
size/SHA checks precede project-root insertion and decoder imports. Existing
reports, input aliases and missing parents are refused.

Schemas at commit `9af3ea7150f1a8acb53464c92519a9bbcc7a3594`
accept only exact 25890-byte LF SHA-256
`879d228d9d8acd21d63563538dd15841aaf49259ee0bb468b8a46b6a4ef866fd`
or deterministic 26364-byte CRLF SHA-256
`a970f10719f29787c7ea25359a908a1f8d99e7f9a721ec91cd8c1dcb38fd112c`.
Reports retain raw/canonical hashes; dependencies are unchanged.

41810 alone runs admitted MapInfo framing in RAM: 7 records, +21 bytes,
224 root/1816 total field comparisons, exact current 32-field values/bounds,
non-count/outside bits, whole inverse and inverse API. 42273 stays unadmitted
without a conversion attempt. No payload is saved.

Actual staged tests passed both controls, root discovery with dependency-only
paths in a virtual published-path model, output guards and cached ZIP CRC/SHA
checks. Both one-byte corruptions failed before parsing/root insertion; V2 is preserved.
Staged CI caps downloads, refuses redirects and uploads sanitized reports; CI is unrun. Legacy source reconstruction retains an opaque
suffix; it is not complete semantic/EOF validation. Observed event and member
framing checks do not prove a replay upgrade or playback, or supply missing values.
