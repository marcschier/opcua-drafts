"""Emit OPC 20020 node-definition tables as template-dialect markdown.

The tables the specification publisher checks are *authored* — it has no directive that
generates one, so every type a model declares needs a table in the prose bound to it with
`defines=`. Our documents never had those tables: they carried a generated Annex A instead,
which has different columns and lists inherited members, so it cannot be lifted.

The tables therefore come from where they always came from, the UANodeSet, through the same
`opcdocx.nodeset_tables.type_table` that builds the committed Word documents now under
Foundation review. Emitting them once turns a generated artifact into authored prose, which is
what the template's model asks for; from then on the tables are edited by hand and the build
reports where they and the model disagree.

Usage:
    python emit_node_tables.py <NodeSet2.xml> --doc-ns-index N [--type X]
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

from opcdocx import nodeset_tables as nt

COLUMNS = 6
REFERENCE_HEADERS = [
    '**References**', '**Node Class**', '**BrowseName**',
    '**DataType**', '**TypeDefinition**', '**Other**',
]

# Where the base OPC UA types a companion specification usually derives from are defined.
# A namespace maps to one document only for a companion namespace; namespace 0 is spread
# across the core parts, so a blanket map for it names the wrong part -- which is what the
# Word writer does today, printing "defined in OPC 10000-5" for every supertype including
# DeviceType, which is OPC 10000-100.
NS0_DEFINING_PART = {
    'BaseObjectType': 'OPC 10000-5',
    'BaseVariableType': 'OPC 10000-5',
    'BaseDataVariableType': 'OPC 10000-5',
    'PropertyType': 'OPC 10000-5',
    'FolderType': 'OPC 10000-5',
    'BaseEventType': 'OPC 10000-5',
    'BaseObjectState': 'OPC 10000-5',
    'FileType': 'OPC 10000-5',
    'FileDirectoryType': 'OPC 10000-5',
    'ServerType': 'OPC 10000-5',
    'ServerCapabilitiesType': 'OPC 10000-5',
    'NamespaceMetadataType': 'OPC 10000-5',
    'BaseInterfaceType': 'OPC 10000-5',
    'AuditEventType': 'OPC 10000-5',
    'AuditSessionEventType': 'OPC 10000-5',
    'AuditUpdateMethodEventType': 'OPC 10000-5',
    'HasComponent': 'OPC 10000-5',
    'NonHierarchicalReferences': 'OPC 10000-5',
    'HierarchicalReferences': 'OPC 10000-5',
    'References': 'OPC 10000-5',
    'Aggregates': 'OPC 10000-5',
    'Boolean': 'OPC 10000-3',
    'String': 'OPC 10000-3',
    'Double': 'OPC 10000-3',
    'Float': 'OPC 10000-3',
    'Int32': 'OPC 10000-3',
    'UInt32': 'OPC 10000-3',
    'DateTime': 'OPC 10000-3',
    'ByteString': 'OPC 10000-3',
    'BaseDataType': 'OPC 10000-3',
    'Enumeration': 'OPC 10000-3',
    'Structure': 'OPC 10000-3',
    'Union': 'OPC 10000-3',
    'OptionSet': 'OPC 10000-3',
    'StateMachineType': 'OPC 10000-16',
    'FiniteStateMachineType': 'OPC 10000-16',
    'StateType': 'OPC 10000-16',
    'InitialStateType': 'OPC 10000-16',
    'TransitionType': 'OPC 10000-16',
    'ConditionType': 'OPC 10000-9',
    'AlarmConditionType': 'OPC 10000-9',
    'OffNormalAlarmType': 'OPC 10000-9',
    'DiscreteAlarmType': 'OPC 10000-9',
    'AnalogUnitType': 'OPC 10000-8',
    'AnalogItemType': 'OPC 10000-8',
    'DataItemType': 'OPC 10000-8',
}


def anchor(text: str) -> str:
    """A heading/table anchor slug: lowercase, non-alphanumerics collapsed to a dash."""
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', text.lower())).strip('-')


def row(cells: list[str]) -> str:
    """One markdown row padded to the table's column count.

    A cell spanning the rest of its row is written as one cell followed by empties, which is
    how the converter reads a span back -- markdown has no colspan.
    """
    padded = list(cells) + [''] * (COLUMNS - len(cells))
    return '| ' + ' | '.join(padded) + ' |'


def separator() -> str:
    return '| ' + ' | '.join(['---'] * COLUMNS) + ' |'


def escape(text: str) -> str:
    """Keep a cell on one line and stop a stray pipe ending it early."""
    if not text:
        return ''
    return text.replace('|', r'\|').replace('\r\n', ' ').replace('\n', ' ').strip()


def subtype_phrase(supertype: str, defined_in, doc_ns_index: int, unnamed: list,
                   own: set | None = None) -> str:
    """`Subtype of the X defined in OPC N`, naming the document that actually defines X.

    A supertype has to name the specification that defines it, because the reader cannot
    otherwise look it up. Namespace 0 is not one document -- FiniteStateMachineType is
    OPC 10000-16 and OffNormalAlarmType is OPC 10000-9 -- so it is resolved per type and
    anything unrecognised is reported rather than attributed to a part at random.

    A name with no prefix is this document's own when the model declares it. That is not the
    same as namespace 0: a specification that adds to the base namespace has a document index
    of 0 and prints its own types unprefixed, and so does one whose supertype happens to be
    printed without an index.
    """
    cell = escape(supertype)
    prefix, _, plain = cell.rpartition(':')
    if prefix == str(doc_ns_index):
        return cell
    if not prefix and own and plain in own:
        return cell
    document = NS0_DEFINING_PART.get(plain) if prefix in ('', '0') else defined_in.get(prefix)
    if not document:
        unnamed.append(cell)
        return cell
    return '%s defined in %s' % (cell, document)


def definition_table(model, type_name: str, *, doc_ns_index: int,
                     defined_in=None, unnamed=None) -> str:
    """The definition table for one type: attributes, references and conformance units.

    Three tables under one caption, separated by blank lines and sharing one number -- the
    `table-wrap` the STS carries. They must not be given captions of their own.

    `defined_in` maps a namespace prefix to the document that defines it, so a supertype
    borrowed from another specification names it the way the template does.
    """
    spec = nt.type_table(model, type_name, doc_ns_index=doc_ns_index)
    slug = anchor(type_name)

    out = [
        '*Table - %s Definition* {#tbl-%s-definition defines=%s}' % (type_name, slug, type_name),
        '',
        row(['**Attribute**', '**Value**']),
        separator(),
    ]
    for name, value in spec['attributes']:
        out.append(row([escape(name), escape(value)]))

    out += ['', row(REFERENCE_HEADERS), separator()]
    if spec['subtypeOf']:
        out.append(row(['Subtype of the %s' % subtype_phrase(
            spec['subtypeOf'], defined_in or {}, doc_ns_index,
            unnamed if unnamed is not None else [], set(model.by_name))]))
    for member in spec['members']:
        out.append(row([
            escape(member['referenceType']),
            escape(member['nodeClass']),
            escape(member['browseName']),
            escape(member['dataType']),
            escape(member['typeDefinition']),
            escape(member['other']),
        ]))

    if spec['conformanceUnits']:
        out += ['', row(['**Conformance Units**']), separator()]
        for unit in spec['conformanceUnits']:
            out.append(row([escape(unit)]))

    return '\n'.join(out)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('nodeset', type=pathlib.Path)
    ap.add_argument('--doc-ns-index', type=int, required=True)
    ap.add_argument('--type', action='append', dest='types')
    ap.add_argument('--config', type=pathlib.Path,
                    help='a word-drafts/tools/specs/<spec>.json, read for requiredModelNodes: '
                         'a NodeSet names its required models but not the BrowseNames inside '
                         'them, so without this map a borrowed type prints as a bare NodeId')
    ap.add_argument('--defined-in', action='append', default=[],
                    metavar='PREFIX=DOCUMENT',
                    help='namespace prefix to the document defining it, e.g. 2=OPC 10000-100')
    args = ap.parse_args(argv)

    defined_in = dict(pair.split('=', 1) for pair in args.defined_in)
    required = None
    if args.config:
        required = json.loads(args.config.read_text(encoding='utf-8')).get('requiredModelNodes')

    model = nt.Model(str(args.nodeset), required)
    names = args.types or list(nt.object_types(model, doc_ns_index=args.doc_ns_index))

    unresolved = []
    unnamed = []
    for name in names:
        table = definition_table(model, name, doc_ns_index=args.doc_ns_index,
                                 defined_in=defined_in, unnamed=unnamed)
        unresolved += re.findall(r'\bns=\d+;[isgb]=[^\s|]+', table)
        print(table)
        print()

    problems = 0
    if unresolved:
        # A bare NodeId in print means a borrowed type nothing named. Report it rather than
        # emitting it quietly: the reader cannot look it up and no later check would catch it.
        print('unresolved NodeIds, add them to requiredModelNodes: %s'
              % ', '.join(sorted(set(unresolved))), file=sys.stderr)
        problems += 1
    if unnamed:
        print('supertypes with no defining document, add --defined-in or extend '
              'NS0_DEFINING_PART: %s' % ', '.join(sorted(set(unnamed))), file=sys.stderr)
        problems += 1
    return 1 if problems else 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
