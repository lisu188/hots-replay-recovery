# Derived historical MapInfo count-width constraint

This read-only experiment tests one alteration of the authenticated current
98348 selected native graph. In a private in-memory copy, it changes only
`Permission::HandleList` type1828 from a 31-bit count/max2147483647 to a 7-bit
count/max127. It does not change or bypass the production reader's schema pin.
The generic scalar engine is called directly with the explicitly derived graph.

The inputs are the hash-pinned original41810, R8 and one public39445 control.
They contain five, five and six historical MapInfo records respectively.
Their unchanged `legacy-10`/`historical-fixed` metadata baseline fully reencodes
the source member. No tail profile is patched or needed for this experiment.

For all16 records, the derived graph covers all32 current-named root fields,
matches the historical record end and handle pair, and reconstructs every
consumed physical bit using a separate bit writer. Existing how-to-play and
patch-note section boundaries match where present. All derived permission
counts are zero; the last two fields occupy one plus seven bits. Original and
R8 derived wire-token sequences are identical in order, including private values
which remain in RAM and are not included in the report.

The unmodified current graph is retained as a negative control. Thirteen
records decode into bytes beyond their historical end. Each file's last record
fails at the current 31-bit permission count; its implied payload would exceed
the whole remaining member. Success from a standalone current decoder therefore
does not establish a correct historical record boundary.

These results constrain a layout hypothesis. They do not authenticate historical
native field names, permission semantics, the older ClientInfo schema or an
old-to-current transformation. In particular, the production historical profiles
remain frozen, and the separate39445 unchanged full-tail failure is unaffected.

The reproduction source contains local research paths, requires the existing
private inputs and pinned selected graph, and writes only a new bounded JSON
report. It checks every source replay SHA256 before and after analysis, loads
the archive into RAM once per run, and performs no PE read, network operation,
client launch, replay/header write or conversion. The first setup attempt
assumed five records for39445 and stopped; the observed six-record admission
was then corrected without changing the tested layout hypothesis.

Run the frozen source from the task workspace with the existing Python311:

```powershell
python work/legacy-mapinfo-hypothesis/probe_legacy_mapinfo.py
```

The report output must not already exist. Source hashes identify the exact
research engine, selected schema and independent physical writer used. Raw
replays, headers, game binaries, player data and the generic historical schema
file are not part of this publication set.
