"""NodeSet -> the template's normative node tables.

The Word node tables are *derived from the model*, never transcribed from prose, so the
document and the NodeSet cannot drift apart — and so the result parses in the OPC
Foundation's Word-versus-NodeSet validator.

Table shapes follow OPC 20020 clause 3.4.1:
  Table 2  type definition        Attribute/Value rows, a References block, ConformanceUnits
  Table 4  additional References  SourceBrowsePath / Reference Type / Is Forward / TargetBrowsePath
  Table 5  additional subcomponents
  Table 6  Attribute values for child Nodes
"""

import xml.etree.ElementTree as ET

from . import contract

UANS = '{http://opcfoundation.org/UA/2011/03/UANodeSet.xsd}'

# Base-namespace Nodes this family of models refers to. Keeping an explicit table is
# deliberate: guessing a BrowseName from a NodeId is how a wrong DataType reaches print.
STANDARD_NODES = {
    'i=1': 'Boolean', 'i=2': 'SByte', 'i=3': 'Byte', 'i=4': 'Int16', 'i=5': 'UInt16',
    'i=6': 'Int32', 'i=7': 'UInt32', 'i=8': 'Int64', 'i=9': 'UInt64', 'i=10': 'Float',
    'i=11': 'Double', 'i=12': 'String', 'i=13': 'DateTime', 'i=14': 'Guid',
    'i=15': 'ByteString', 'i=17': 'NodeId', 'i=20': 'QualifiedName',
    'i=21': 'LocalizedText', 'i=22': 'Structure', 'i=24': 'BaseDataType',
    'i=29': 'Enumeration', 'i=540': 'RelativePath', 'i=887': 'EUInformation',
    'i=35': 'Organizes', 'i=37': 'HasModellingRule', 'i=40': 'HasTypeDefinition',
    'i=45': 'HasSubtype', 'i=46': 'HasProperty', 'i=47': 'HasComponent',
    'i=17603': 'HasInterface', 'i=17604': 'HasAddIn',
    'i=58': 'BaseObjectType', 'i=61': 'FolderType', 'i=62': 'BaseVariableType',
    'i=63': 'BaseDataVariableType', 'i=68': 'PropertyType',
    'i=17602': 'BaseInterfaceType', 'i=11575': 'FileType',
    'i=31': 'References', 'i=32': 'NonHierarchicalReferences',
    'i=33': 'HierarchicalReferences', 'i=44': 'Aggregates',
    'i=78': 'Mandatory', 'i=80': 'Optional', 'i=11508': 'OptionalPlaceholder',
    'i=11510': 'MandatoryPlaceholder', 'i=2253': 'Server',
}

# The RequiredModel's types, referred to by NodeId from this model.
REQUIRED_MODEL_NODES = {
    'ns=1;i=63000': 'RegistryType',
    'ns=1;i=63001': 'GroupType',
    'ns=1;i=63002': 'ResourceType',
}

NODE_CLASS = {
    'UAObjectType': 'ObjectType',
    'UAVariableType': 'VariableType',
    'UADataType': 'DataType',
    'UAReferenceType': 'ReferenceType',
    'UAObject': 'Object',
    'UAVariable': 'Variable',
    'UAMethod': 'Method',
}


class Node:
    __slots__ = ('node_id', 'tag', 'browse_name', 'ns_index', 'name', 'display',
                 'description', 'categories', 'parent', 'refs', 'attrs', 'abstract',
                 'definition', 'inverse_name', 'symmetric', 'value')

    def __init__(self):
        self.refs = []
        self.categories = []
        self.attrs = {}
        self.abstract = False
        self.definition = None
        self.description = ''
        self.parent = None
        self.inverse_name = None
        self.symmetric = False
        self.value = None


class Model:
    """A parsed UANodeSet with the lookups the table builders need."""

    def __init__(self, path):
        tree = ET.parse(path)
        root = tree.getroot()
        self.namespace_uris = [u.text for u in root.findall(UANS + 'NamespaceUris/' + UANS + 'Uri')]
        model_el = root.find(UANS + 'Models/' + UANS + 'Model')
        self.model_uri = model_el.get('ModelUri')
        self.version = model_el.get('Version')
        self.publication_date = (model_el.get('PublicationDate') or '')[:10]
        self.required_models = [
            (m.get('ModelUri'), m.get('Version'), (m.get('PublicationDate') or '')[:10])
            for m in model_el.findall(UANS + 'RequiredModel')]
        self.aliases = {a.get('Alias'): (a.text or '').strip()
                        for a in root.findall(UANS + 'Aliases/' + UANS + 'Alias')}
        self._alias_to_id = dict(self.aliases)

        self.nodes = {}
        self.order = []
        for el in root:
            tag = el.tag.replace(UANS, '')
            if tag not in NODE_CLASS:
                continue
            n = Node()
            n.tag = tag
            n.node_id = el.get('NodeId')
            n.browse_name = el.get('BrowseName')
            if ':' in n.browse_name:
                idx, _, nm = n.browse_name.partition(':')
                n.ns_index, n.name = int(idx), nm
            else:
                n.ns_index, n.name = 0, n.browse_name
            n.abstract = el.get('IsAbstract') == 'true'
            n.parent = el.get('ParentNodeId')
            for k in ('DataType', 'ValueRank', 'ArrayDimensions'):
                if el.get(k) is not None:
                    n.attrs[k] = el.get(k)
            dn = el.find(UANS + 'DisplayName')
            n.display = dn.text if dn is not None else n.name
            de = el.find(UANS + 'Description')
            n.description = (de.text or '') if de is not None else ''
            inv = el.find(UANS + 'InverseName')
            n.inverse_name = inv.text if inv is not None else None
            n.symmetric = el.get('Symmetric') == 'true'
            n.value = el.find(UANS + 'Value')
            n.categories = [c.text for c in el.findall(UANS + 'Category')]
            defn = el.find(UANS + 'Definition')
            if defn is not None:
                n.definition = [
                    (f.get('Name'), f.get('Value'),
                     (f.findtext(UANS + 'Description') or '').strip())
                    for f in defn.findall(UANS + 'Field')]
            for r in el.findall(UANS + 'References/' + UANS + 'Reference'):
                n.refs.append((r.get('ReferenceType'),
                               (r.text or '').strip(),
                               r.get('IsForward') != 'false'))
            self.nodes[n.node_id] = n
            self.order.append(n.node_id)

        self.by_name = {}
        for n in self.nodes.values():
            self.by_name.setdefault(n.name, n)

    def names_of_class(self, tag):
        """BrowseNames of every Node of a NodeClass, in declaration order."""
        return [self.nodes[n].name for n in self.order if self.nodes[n].tag == tag]

    def method_named(self, name, *, owner=None):
        """A Method by BrowseName, disambiguated by its owning type where needed.

        The same Method name legitimately appears on several types (`AddAttribute` on
        every registry container), so a lookup by name alone would silently return
        whichever happened to be declared first.
        """
        owner_node = self.by_name.get(owner) if owner else None
        for nid in self.order:
            n = self.nodes[nid]
            if n.tag != 'UAMethod' or n.name != name:
                continue
            if owner_node is None:
                return n
            if n.parent == owner_node.node_id:
                return n
        return None

    # ------------------------------------------------------------------ lookups

    def resolve_id(self, value):
        """An alias or a NodeId string -> a NodeId string."""
        return self._alias_to_id.get(value, value)

    def browse_name_of(self, value, *, doc_ns_index):
        """A NodeId or alias -> the prefixed BrowseName the tables print.

        Per OPC 20020 3.4.2.2 a BrowseName from another namespace carries its index
        prefix; the document's own namespace is printed without one.
        """
        node_id = self.resolve_id(value)
        n = self.nodes.get(node_id)
        if n is not None:
            return n.name if n.ns_index == doc_ns_index else '%d:%s' % (n.ns_index, n.name)
        if node_id in STANDARD_NODES:
            return '0:' + STANDARD_NODES[node_id]
        if node_id in REQUIRED_MODEL_NODES:
            return '1:' + REQUIRED_MODEL_NODES[node_id]
        return node_id

    def plain_name_of(self, value):
        node_id = self.resolve_id(value)
        n = self.nodes.get(node_id)
        if n is not None:
            return n.name
        return STANDARD_NODES.get(node_id) or REQUIRED_MODEL_NODES.get(node_id) or node_id

    def supertype_of(self, node):
        for rt, target, forward in node.refs:
            if self.plain_name_of(rt) == 'HasSubtype' and not forward:
                return target
        return None

    def members_of(self, node):
        """Forward hierarchical references that declare a child Node, in declared order."""
        out = []
        for rt, target, forward in node.refs:
            if not forward:
                continue
            rt_name = self.plain_name_of(rt)
            if rt_name in ('HasSubtype', 'HasTypeDefinition', 'HasModellingRule'):
                continue
            child = self.nodes.get(self.resolve_id(target))
            if child is None:
                continue
            out.append((rt_name, child))
        return out

    def modelling_rule_of(self, node):
        for rt, target, forward in node.refs:
            if self.plain_name_of(rt) == 'HasModellingRule' and forward:
                return self.plain_name_of(target)
        return None

    def type_definition_of(self, node):
        for rt, target, forward in node.refs:
            if self.plain_name_of(rt) == 'HasTypeDefinition' and forward:
                return target
        return None

    def has_static_value(self, node):
        return self.modelling_rule_of(node) is None and node.tag == 'UAVariable'


# --------------------------------------------------------------------------- tables


def data_type_cell(model, node, *, doc_ns_index):
    """The DataType column, with the array notation of OPC 20020 3.4.1.1."""
    dt = node.attrs.get('DataType')
    if dt is None:
        return ''
    name = model.browse_name_of(dt, doc_ns_index=doc_ns_index)
    rank = node.attrs.get('ValueRank')
    dims = node.attrs.get('ArrayDimensions')
    if rank in (None, '-1'):
        return name
    if rank == '0':
        return name + '{OneOrMoreDimensions}'
    if rank == '-2':
        return name + '{Any}'
    if rank == '-3':
        return name + '{ScalarOrOneDimension}'
    count = int(rank)
    dim_values = (dims or '').split(',') if dims else []
    parts = []
    for d in range(count):
        v = dim_values[d].strip() if d < len(dim_values) else ''
        parts.append('[%s]' % v if v and v != '0' else '[]')
    return name + ''.join(parts)


def other_cell(model, node):
    """The Other column: modelling rule short name, plus access qualifiers."""
    parts = []
    rule = model.modelling_rule_of(node)
    if rule:
        parts.append(contract.modelling_rule_short(rule))
    return ', '.join(parts)


def type_table(model, type_name, *, doc_ns_index):
    """Build the Table 2 structure for one type.

    Returns a dict with `attributes`, `members`, `subtype_of` and `conformance_units`;
    the OOXML writer turns that into the exact template markup.
    """
    node = model.by_name.get(type_name)
    if node is None:
        raise KeyError('type not in NodeSet: %s' % type_name)

    attributes = [('BrowseName', '%d:%s' % (node.ns_index, node.name))]
    if node.tag in ('UAObjectType', 'UAVariableType', 'UADataType', 'UAReferenceType'):
        attributes.append(('IsAbstract', 'True' if node.abstract else 'False'))
    if node.tag == 'UAVariableType':
        attributes.append(('ValueRank', node.attrs.get('ValueRank', '-1')))
        attributes.append(('DataType', model.browse_name_of(
            node.attrs.get('DataType', 'i=24'), doc_ns_index=doc_ns_index)))
    if node.tag == 'UAReferenceType':
        if node.inverse_name:
            attributes.append(('InverseName', node.inverse_name))
        attributes.append(('Symmetric', 'True' if node.symmetric else 'False'))

    supertype = model.supertype_of(node)
    subtype_of = model.browse_name_of(supertype, doc_ns_index=doc_ns_index) if supertype else None

    members = []
    for rt_name, child in model.members_of(node):
        if rt_name in contract.SUPPRESSED_REFERENCE_TYPES:
            continue
        td = model.type_definition_of(child)
        members.append({
            'referenceType': '0:' + rt_name if rt_name in STANDARD_NODES.values() else rt_name,
            'nodeClass': NODE_CLASS[child.tag],
            'browseName': child.name,
            'dataType': data_type_cell(model, child, doc_ns_index=doc_ns_index),
            'typeDefinition': (model.browse_name_of(td, doc_ns_index=doc_ns_index)
                               if td else ''),
            'other': other_cell(model, child),
            'description': child.description,
        })

    return {
        'browseName': node.name,
        'nodeClass': NODE_CLASS[node.tag],
        'attributes': attributes,
        'subtypeOf': subtype_of,
        'members': members,
        'conformanceUnits': list(node.categories),
        'description': node.description,
        'definition': node.definition,
    }


# --------------------------------------------------------------------------- methods

# The Argument structure of OPC 10000-4, as encoded in a UANodeSet Value.
TYPES_NS = '{http://opcfoundation.org/UA/2008/02/Types.xsd}'


def _arguments(model, variable, *, doc_ns_index):
    """Decode an InputArguments / OutputArguments Value into argument descriptors."""
    if variable is None or variable.value is None:
        return []
    out = []
    for arg in variable.value.iter(TYPES_NS + 'Argument'):
        name = arg.findtext(TYPES_NS + 'Name') or ''
        dt = arg.find(TYPES_NS + 'DataType')
        identifier = dt.findtext(TYPES_NS + 'Identifier') if dt is not None else None
        rank = arg.findtext(TYPES_NS + 'ValueRank') or '-1'
        desc = ''
        d = arg.find(TYPES_NS + 'Description')
        if d is not None:
            desc = d.findtext(TYPES_NS + 'Text') or ''
        type_name = (model.browse_name_of(identifier, doc_ns_index=doc_ns_index)
                     if identifier else '')
        if rank not in ('-1', None):
            type_name += '[]'
        out.append({'name': name, 'dataType': type_name, 'description': desc})
    return out


def method_table(model, method_name, *, doc_ns_index, owner=None):
    """The signature, argument table and AddressSpace table of a Method.

    Follows OPC 20020 clause 8.1.3: a signature block, Table 20 (Method Arguments)
    and Table 21 (Method AddressSpace definition). Table 21 is omitted when the Method
    has no Properties beyond InputArguments and OutputArguments, as the template says.
    """
    node = model.method_named(method_name, owner=owner)
    if node is None:
        raise KeyError('Method not in NodeSet: %s' % method_name)

    inputs = outputs = None
    others = []
    for rt_name, child in model.members_of(node):
        if child.name == 'InputArguments':
            inputs = child
        elif child.name == 'OutputArguments':
            outputs = child
        else:
            others.append((rt_name, child))

    in_args = _arguments(model, inputs, doc_ns_index=doc_ns_index)
    out_args = _arguments(model, outputs, doc_ns_index=doc_ns_index)

    signature = ['%s (' % node.name]
    lines = (['[in]  %-14s %s,' % (a['dataType'], a['name']) for a in in_args]
             + ['[out] %-14s %s,' % (a['dataType'], a['name']) for a in out_args])
    if lines:
        lines[-1] = lines[-1].rstrip(',') + ');'
    else:
        signature[0] = '%s ();' % node.name
    signature.extend('    ' + ln for ln in lines)

    return {
        'browseName': node.name,
        'description': node.description,
        'signature': signature,
        'arguments': in_args + out_args,
        'hasExtraProperties': bool(others),
        'inputs': bool(in_args),
        'outputs': bool(out_args),
        'conformanceUnits': list(node.categories),
        'modellingRule': model.modelling_rule_of(node),
    }


def methods_of(model, type_name):
    """The Methods a type owns, in declaration order."""
    node = model.by_name.get(type_name)
    if node is None:
        return []
    return [child.name for rt, child in model.members_of(node)
            if child.tag == 'UAMethod']


def enum_table(model, type_name):
    """The `<someEnumeration> Items` table (Table 31 of the template)."""
    node = model.by_name.get(type_name)
    if node is None:
        raise KeyError('DataType not in NodeSet: %s' % type_name)
    if not node.definition:
        raise ValueError('%s has no Definition' % type_name)
    return {
        'browseName': node.name,
        'description': node.description,
        'fields': [{'name': f[0], 'value': f[1], 'description': f[2]}
                   for f in node.definition],
        'conformanceUnits': list(node.categories),
    }


def annex_node_table(model, *, doc_ns_index):
    """The generated Annex A node list: NodeId, BrowseName, NodeClass, Description."""
    rows = []
    for nid in model.order:
        n = model.nodes[nid]
        rows.append({
            'nodeId': nid,
            'browseName': n.name,
            'nodeClass': NODE_CLASS[n.tag],
            'description': n.description,
        })
    return rows


def object_types(model, *, doc_ns_index):
    return [model.nodes[n].name for n in model.order
            if model.nodes[n].tag == 'UAObjectType']


def data_types(model):
    return [model.nodes[n].name for n in model.order
            if model.nodes[n].tag == 'UADataType']
