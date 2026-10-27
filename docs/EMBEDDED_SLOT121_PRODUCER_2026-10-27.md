# Embedded slot121 producer and selector13 - 2026-10-27

The selected compiled dispatch path now connects the initialized embedded registry to the slot121 callback and identifies the source pointer in its argument. A parsed selector of decimal13 selects this path. This replaces the previous unresolved sender frontier with a conditional static producer route; actual historical field values and runtime execution remain unverified.

Addresses and offsets are hexadecimal; indices, selector values, and byte/instruction counts are decimal. The [observation](../observations/embedded-slot121-producer-2026-10-27.json) records code, table and decoder-output pins. Selected executable code comes from the retained analyst-derived 98348 static patch. The primary table word was independently read from the SHA-256-verified original PE.

## Receiver identity

The previously inspected initializer places table `28E6CE8` at the object later published through global `3B7C6B0`. Its original-PE slot0 word points to `1D84540`. That twelve-byte thunk adds `D0` to RCX and tail-jumps to `1E65070`. Thus, conditional on invocation through that initialized stable object, the delegate receives embedded base `B=G+D0`.

The delegate examines the byte at its incoming RDX descriptor. Byte value 3 selects the call at `1E650CD` to `1E5CF60`, preserving RCX and passing its original R8 object as RDX. The latter function saves B in R15 at `1E5CF87`. Its selected notification branch computes `RCX=R15+3D0` at `1E5D280`, which is exactly `G+4A0`, the storage previously authenticated as physical slot121.

This identifies the relevant container in the compiled path. It does not show a live virtual call, a successful network read, or stable contents across concurrent or aliased writes. The five index22 calls documented earlier still use the separate `QWORD[G+A0]` access path and do not provide this receiver proof.

## Selector and argument

At `1E5D0A6`, the function loads the leading DWORD from parsed object P. An unsigned comparison admits values 0 through 21; the out-of-range branch goes to `1E5D396`. The indexed load at `1E5D0B9` reads the 22-entry DWORD table at `[1E5D3D8,1E5D430)`, adds the image base, and jumps to the result. Every recovered table entry names an instruction start in the selected decoded range. Exactly entry 13 targets `1E5D26C`.

That branch and its shared tail construct argument A at `RBP-79`:

| Argument offset | Selected store | Instruction RVA |
| --- | --- | --- |
| `+0` | QWORD address `0x1428F2A78` | `1E5D381`, from `1E5D279` |
| `+8` | QWORD zero | `1E5D275`, from `1E5D26C` |
| `+10` | DWORD `0x79`, decimal121 | `1E5D26E` |
| `+18` | QWORD `P+4` | `1E5D389`, from `1E5D385` |

At `1E5D391`, `2DDC10` receives RCX=`B+3D0` and RDX=A. The previously authenticated callback forwarding and `CD1660` thunk carry A to `CD6D30` when the same valid registered node remains selected and stable. The load at `CD6D83` then obtains `P+4` from A+18 before the selector2 setter call at `CD6D95`. This connects the source pointer to the parsed object's payload, without recovering the payload's historical contents.

Selector 13 is a branch ordinal in this compiled parsed-object switch. The stored value 121 is a callback argument tag and matches the physical slot calculation on this route. Neither number has been assigned a catalog identity, schema type name or historical enum meaning.

## Parsing frontier and scope

Before parsing, the selected code initializes the initially allocated object's leading DWORD to -1 and stores its pointer in the holder at `RBP-11`. P denotes the pointer reloaded from this holder after the virtual parser call through slot `+108` at `1E5D09B`; replacement of the holder pointer by the parser is not excluded. That parser's receiver comes from `1E5AA40`. The input object is queried through virtual offsets `+18`, `+20` and `+10`. These are observed call boundaries; the virtual parser target, protocol type and field semantics are the next source task.

The new witnesses cover 1,154 bytes and 257 instructions. Another 410 bytes and 87 instructions from the previously retained delegate were rechecked against the same freshly hashed patch. A separate 88-byte switch table is interpreted as data. The selected code ends at the RET at `1E5D3D5`; a linear attempt covering the entire runtime-function record encountered table bytes after that return and was not accepted as an instruction proof. The bounded decode uses trailing context to verify that the selected endpoint is an instruction boundary. No complete-function or whole-CFG claim follows from the runtime-function range.

The original PE and static patch SHA-256 pins were refreshed, the primary table word and all 22 switch targets were checked, and instruction-byte columns matched the guarded source. No new database, game process, Computer Use, codec change or replay was produced. This milestone supplies no missing historical values, resource identity/ownership, catalog equivalence or deterministic playback proof. The full replay upgrade remains incomplete.
