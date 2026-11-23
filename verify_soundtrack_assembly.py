"""Compare every ordinal and physical frame before and after TEN soundtrack insertion."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

from native_game_events import iter_game_events


PREVIOUS = '566e8866089d44c526dd4ae6e68f015c7dd280167a028aac06a5a708eb14c2f7'
PREVIOUS_LEDGER = '5e5057f2d2709b47f85c4d872cc2dd2243968255395457606206703417f95e77'
SOUND = '522bc5077b1ec41a874dcb5bd5918616a3b006d0456a860f4c25b642337bd1f9'
LABEL = 'intro_soundtrack_requires_stock_catalog_and_recorded_schedule'


def frames(data):
    for record in iter_game_events(data):
        if record.start_bit % 8 or record.aligned_end_bit % 8 or record.delta_tag > 2:
            raise ValueError('Expected the byte-aligned deltas used in these recordings')
        frame = data[record.start_bit//8:record.aligned_end_bit//8]
        yield record.event, frame, frame[record.delta_tag+1:]


def indexed(directory):
    data=(directory/'game-inputs.private.bin').read_bytes()
    ledger_data=(directory/'ordinals.private.json').read_bytes()
    ledger=json.loads(ledger_data)
    out={}
    loop=0
    for row, decoded in zip(ledger,frames(data),strict=True):
        ordinal,tick,kind,labels=row
        e,frame,body=decoded
        loop+=e.delta
        if (ordinal in out or tick!=loop or kind!=e.event_id or not labels):
            raise ValueError('Invalid native/ledger alignment')
        out[ordinal]=(row,e,frame,body)
    if list(out)!=sorted(out):
        raise ValueError('Chronology differs from physical source ordinals')
    return out,sha256(data).hexdigest(),sha256(ledger_data).hexdigest()


def verify(prior, updated, sparse, evidence):
    old,base_hash,base_ledger=indexed(prior)
    new,result_hash,result_ledger=indexed(updated)
    fragment=sparse.read_bytes()
    if (base_hash,base_ledger,sha256(fragment).hexdigest())!=(PREVIOUS,PREVIOUS_LEDGER,SOUND):
        raise ValueError('Unexpected reference artifact')
    info=json.loads(evidence.read_bytes())
    ordinals=info['ten_original_ordinals']
    extra=set(new)-set(old)
    if len(ordinals)!=46 or len(extra)!=len(ordinals) or extra!=set(ordinals) or not old.keys()<=new.keys():
        raise ValueError('Insertion changed the wrong ordinals')
    # Delta tag values 0, 1 and 2 occupy one, two and three whole bytes including the tag.
    # The bytes after them include the packed user, event ID, payload and physical padding.
    changed=[]
    for key,(row,e,raw,body) in old.items():
        fresh,other,actual,other_body=new[key]
        if fresh!=row or body!=other_body or (raw==actual)!=(e.delta==other.delta):
            raise ValueError(f'Unexplained physical change at original ordinal {key}')
        if e.delta!=other.delta:
            if other.delta>=e.delta:
                raise ValueError('Insertion increased a prior frame delta')
            changed.append(key)
    sparse_deltas=0
    for key,(ref,raw,body) in zip(ordinals,frames(fragment),strict=True):
        row,actual,wire,other_body=new[key]
        if (row[2:]!=[64,[LABEL]] or actual.payload!=(info['target_word'],) or ref.user_id!=actual.user_id
                or ref.payload!=actual.payload or ref.event_id!=64 or body!=other_body or (raw==wire)!=(actual.delta==ref.delta)):
            raise ValueError(f'New row differs from the independently checked fragment at {key}')
        sparse_deltas+=actual.delta!=ref.delta
    return dict(prior_inputs=len(old),added_inputs=len(extra),total_inputs=len(new),
                prior_frames_byte_identical=len(old)-len(changed),prior_frames_only_delta_changed=len(changed),
                prior_ordinals_with_new_delta=changed,added_frames_byte_identical_to_fragment=len(extra)-sparse_deltas,
                added_frames_only_delta_changed=sparse_deltas,prior_stream_sha256=base_hash,
                fragment_sha256=SOUND,combined_stream_sha256=result_hash,combined_ordinal_ledger_sha256=result_ledger)


if __name__=='__main__':
    cli=argparse.ArgumentParser(description=__doc__)
    for field in ('prior','updated','sparse','evidence'):
        cli.add_argument(field,type=Path)
    a=cli.parse_args()
    print(json.dumps(verify(a.prior,a.updated,a.sparse,a.evidence),indent=2))
