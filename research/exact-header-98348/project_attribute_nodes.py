"""Research-only patching of authenticated attribute wire templates in RAM.

No wire tags are inferred: every edited node keeps a compatible authenticated
template. New value records require an existing matching optional/type shape.
No header is assembled, saved or accepted by this module.
"""
from lossless_wire import clone,to_generic,encode,Node,WireError
from depot_s2mh_wire import Choice,BitArray

def _shape(value):
    if type(value) is dict:return ('dict',tuple((k,_shape(v)) for k,v in sorted(value.items())))
    if type(value) is list:return ('list',len(value),tuple(_shape(v) for v in value))
    if type(value) is Choice:return ('choice',value.tag,_shape(value.value))
    if type(value) is bytes:return ('bytes',len(value))
    if type(value) is BitArray:return ('bitarray',value.count,len(value.raw))
    return type(value).__name__

def _apply(node,value):
    if node.tag==5:
        if type(value) is not dict or set(value)!={k for k,_ in node.value}:raise WireError('Attribute struct keys differ from authenticated template')
        for k,child in node.value:_apply(child,value[k])
    elif node.tag==0:
        if type(value) is not list or len(node.value)!=len(value):raise WireError('Attribute nested array differs from authenticated template length')
        for child,new in zip(node.value,value):_apply(child,new)
    elif node.tag==4:
        if (node.value is None)!=(value is None):raise WireError('Attribute optional shape differs from authenticated template')
        if value is not None:_apply(node.value,value)
    elif node.tag==3:
        if type(value) is not Choice or node.value[0]!=value.tag:raise WireError('Attribute choice differs from authenticated template')
        _apply(node.value[1],value.value)
    elif node.tag==1:
        if type(value) is not BitArray or node.value[0]!=value.count:raise WireError('Attribute bitarray differs from authenticated template')
        node.value=(value.count,value.raw)
    elif node.tag in (2,7,8):
        if type(value) is not bytes or (node.tag in (7,8) and len(value)!=(4 if node.tag==7 else 8)):raise WireError('Attribute byte type differs from authenticated template')
        node.value=value
    elif node.tag in (6,9):
        if type(value) is not int:raise WireError('Attribute integer type differs from authenticated template')
        node.value=value
    else:raise WireError('Unsupported attribute wire node')

def project_nodes(template_array:Node,target_attributes:list)->Node:
    if template_array.tag!=0 or type(target_attributes) is not list or len(template_array.value)!=len(target_attributes):raise WireError('Attribute definition array differs from authenticated template')
    output=clone(template_array)
    for attr_node,target in zip(output.value,target_attributes):
        original=to_generic(attr_node)
        if original[0]!=target[0]:raise WireError('Attribute identity/order differs from authenticated template')
        values_node=attr_node.field(1)
        if values_node.tag!=0:raise WireError('Attribute values are not an authenticated wire array')
        old_by_value={}
        for x in values_node.value:old_by_value.setdefault(to_generic(x)[0],[]).append(x)
        shape_templates={}
        for old in values_node.value:shape_templates.setdefault(_shape(to_generic(old)),old)
        new_values=[]
        for index,new in enumerate(target[1]):
            positional=values_node.value[index] if index<len(values_node.value) else None
            old=positional if positional is not None and to_generic(positional)==new else next((x for x in old_by_value.get(new[0],[]) if _shape(to_generic(x))==_shape(new)),None)
            if old is None:old=shape_templates.get(_shape(new))
            if old is None:raise WireError('New value has no compatible authenticated wire template')
            child=clone(old);_apply(child,new);new_values.append(child)
        values_node.value=new_values
        for key,child in attr_node.value:
            if key!=1:_apply(child,target[key])
    if to_generic(output)!=target_attributes:raise WireError('Attribute generic postcondition differs')
    encode(output)
    return output
