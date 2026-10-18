"""Research-only bounded attribute/header projection; never writes a replay/header.

Profiles and optional-empty value requirements are restricted to the observed
controls. Unknown nonempty value requirement flags are rejected.
"""
from dataclasses import dataclass
from battlelobby_attribute_layer import _Reader,decode_layer,width,LayerError,MAX_TOTAL_VALUES
from depot_s2mh_wire import Choice
import copy

@dataclass(repr=False)
class AttributeProjection:
    attributes:list
    starts:list
    ends:list
    attribute_visual_indices:list
    value_visual_indices:list
    full_end_bit:int

def project(raw:bytes,profile:str)->AttributeProjection:
    layer=decode_layer(raw,profile)
    positions={};position=0;w=width(profile)
    for token in layer.tokens:
        if token.kind=='blob':
            position+=(-position)%8;positions[token.path]=position;position+=len(token.value)*8
        else:
            positions[token.path]=position
            position+=token.fixed_width if token.kind=='fixed' else w+(token.kind=='count')
    reader=_Reader(raw);reader.position=positions['/attributes/0/namespace']
    attribute_indices=[];value_indices=[]
    def localization():
        if not reader.bits(1):return None
        color=reader.bits(32) if reader.bits(1) else None
        return {0:color,1:reader.bits(6),2:reader.bits(16)}
    def picture():
        if not reader.bits(1):return None
        return {0:reader.bits(6),1:reader.bits(16),2:reader.bits(16),3:reader.bits(16),4:reader.bits(16)}
    def visual(indices):
        value={0:localization(),1:localization(),2:picture()}
        indices.extend(x[2] for x in (value[0],value[1]) if x is not None and x[2])
        return value
    attributes=[];starts=[];ends=[];total=0
    for i in range(len(layer.attributes)):
        if reader.position!=positions[f'/attributes/{i}/namespace']:raise LayerError('Independent attribute start differs')
        starts.append(reader.position)
        instance={0:reader.bits(32),1:reader.bits(32)}
        count=reader.bits(w+1);total+=count
        if not 1<=count or total>MAX_TOTAL_VALUES:raise LayerError('Attribute value budget exceeded')
        values=[]
        for _ in range(count):
            value_name=reader.bits(32).to_bytes(4,'big')
            value_visual=visual(value_indices)
            if reader.bits(3):raise LayerError('Nonempty value requirement bits outside observed projection')
            values.append({0:value_name,1:value_visual,2:[]})
        attr_visual=visual(attribute_indices)
        requirements=[]
        for _ in range(reader.bits(5)):
            link={0:reader.bits(5),1:{0:reader.bits(32),1:reader.bits(32)}}
            vals=[reader.bits(32).to_bytes(4,'big') for _ in range(reader.bits(w+1))]
            requirements.append({0:link,1:vals})
        meta={k:reader.bits(5) for k in (4,5,6)}
        meta[7]=reader.bits(32)
        tag=reader.bits(8)
        def default():return {0:reader.bits(w),1:reader.bits(1)}
        if tag==0:defaults=default()
        elif tag==1:defaults=[default() for _ in range(reader.bits(5))]
        else:raise LayerError('Unsupported attribute default choice')
        meta[8]=Choice(tag,defaults);meta[9]=reader.bits(9)
        item={0:instance,1:values,2:attr_visual,3:requirements,**meta}
        attributes.append(item);ends.append(reader.position)
        if i+1<len(layer.attributes) and reader.position!=positions[f'/attributes/{i+1}/namespace']:raise LayerError('Independent attribute end differs')
    expected=dict(layer.boundaries)['attribute_definitions_end']
    if reader.position!=expected:raise LayerError('Independent definitions boundary differs')
    return AttributeProjection(attributes,starts,ends,attribute_indices,value_indices,reader.position)

def localization_indices(value):
    """Only structurally known header attribute localization-key paths."""
    indices=[]
    for item in value:
        visuals=[item[2]]+[v[1] for v in item[1]]
        for visual in visuals:
            for key in (visual[0],visual[1]):
                if key is not None and key[2]:indices.append(key[2])
    return indices

def localize_package(attributes,global_table_index:int):
    """Undo observed global locale-table concatenation, guarded by controls."""
    if type(global_table_index) is not int or not 0<=global_table_index<64:raise LayerError('Invalid package table index')
    output=copy.deepcopy(attributes)
    for item in output:
        for visual in [item[2]]+[x[1] for x in item[1]]:
            for key in (visual[0],visual[1]):
                if key is not None:
                    if key[1]!=global_table_index:raise LayerError('Unexpected cross-package localization key')
                    key[1]=0
    return output
