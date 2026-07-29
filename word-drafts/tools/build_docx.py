#!/usr/bin/env python3
"""Build an OPC Foundation companion-specification Word document from a markdown draft.

    python word-drafts/tools/build_docx.py word-drafts/tools/specs/openusd-binding.json

The template is cloned and its body edited in place, bottom-up so earlier indices stay
valid. Regions the build does not own — the cover, the legal front matter, clause 3.4
"Conventions for Node descriptions", the OPC UA introduction with its five embedded
figures, the Annex A skeleton and the back matter — are kept verbatim from the template
and only have their placeholder tokens substituted.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from opcdocx import contract, docmodel as dm, md_parse, mermaid_pptx, nodeset_tables, ole_embed
from opcdocx import oxml
from opcdocx.oxml import BookmarkAllocator, paragraph, run, toc_field
from opcdocx.package import Package, substitute_tokens
from opcdocx.writer import Writer

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
TEMPLATE = os.path.join(
    REPO, 'templates', 'OPC 20020 - UA Companion Specification Template v1.01.19.docx')


# --------------------------------------------------------------------------- helpers


def clause_id(number):
    return 'c' + str(number).replace('.', '-')


def clause_level(number):
    return str(number).count('.') + 1


def is_annex_number(number):
    return str(number)[0].isalpha()


class Build:
    def __init__(self, config_path):
        with open(config_path, encoding='utf-8') as f:
            self.cfg = json.load(f)
        self.identity = self.cfg['identity']
        src = self.cfg['source']
        with open(os.path.join(REPO, src['markdown']), encoding='utf-8') as f:
            self.md_text = f.read()
        self.sections, self.section_order = md_parse.split_sections(self.md_text)
        self.model = nodeset_tables.Model(os.path.join(REPO, src['nodeset']))
        self.doc_ns_index = self.identity['namespaceIndexInDocument']

        self.by_number = {str(e['number']): e for e in self.cfg['clauseMap']}
        self.xref_map = self.cfg['xrefMap']
        self.doc = dm.DocModel()
        self.figure_specs = list(self.cfg.get('figures', []))
        # Types already given a clause by the clause map, so `_gen_types` does not
        # emit them a second time.
        self.emitted_types = set()

    # ------------------------------------------------------------------ xrefs

    def resolve_xref(self, number):
        """A section reference in the markdown -> (docmodel id, printed number).

        A restructured document already carries the final numbers, so those resolve
        directly; the clause map is only consulted for a document still written against
        the previous numbering.
        """
        if number in self.by_number:
            return clause_id(number), number
        target = self.xref_map.get(number)
        if target is None:
            return None
        label = target
        if target.startswith('Annex '):
            target = target.split()[1]
        if target not in self.by_number:
            return None
        return clause_id(target), label

    def parser(self):
        return md_parse.BlockParser(xref_resolver=self.resolve_xref)

    # ------------------------------------------------------------------ docmodel

    def build_docmodel(self):
        region = None
        parser = self.parser()
        for entry in self.cfg['clauseMap']:
            number = str(entry['number'])
            if entry.get('region'):
                region = entry['region']
            if region is None:
                raise ValueError('clause %s has no region' % number)

            blocks = []
            cid = clause_id(number)
            emit_heading = entry.get('emitHeading', True)
            if not emit_heading:
                pass
            elif entry.get('annex'):
                blocks.append(dm.annex(cid, entry['title'],
                                       normative=entry.get('normative', False)))
            elif is_annex_number(number):
                blocks.append(dm.annex_clause(cid, entry['title'],
                                              level=clause_level(number) - 1))
            else:
                blocks.append(dm.clause(cid, entry['title'], level=clause_level(number)))

            if entry.get('from') and not entry.get('generated'):
                blocks.extend(self.section_blocks(entry, parser))
            if entry.get('generated'):
                blocks.extend(self.generated_blocks(entry['generated'], entry))
            if entry.get('nodetable'):
                blocks.extend(self.node_table_blocks(entry))
            if entry.get('append') and not self._restructured(entry):
                blocks.extend(self.appended_blocks(entry['append'], parser))

            self.doc.add(region, *blocks)
        self.assign_ids()
        return self.doc

    def _heading_key(self, entry):
        """The heading text this clause has once the markdown is restructured."""
        number = str(entry['number'])
        if entry.get('annex'):
            kind = 'normative' if entry.get('normative') else 'informative'
            return 'Annex %s (%s) \u2014 %s' % (number, kind, entry['title'])
        return '%s %s' % (number, entry['title'])

    def _restructured(self, entry):
        return self._heading_key(entry) in self.sections

    def _section_for(self, entry):
        """Locate a clause's markdown section, before or after restructuring.

        The same clause map drives the restructure, so the build works against either
        form: the original headings the map was written against, and the restructured
        headings the map produces. That is what lets the markdown and the document be
        regenerated from one another without a manual step in between.
        """
        key = self._heading_key(entry)
        if key in self.sections:
            return self.sections[key]
        if entry.get('from') and entry['from'] in self.sections:
            return self.sections[entry['from']]
        return None

    def section_blocks(self, entry, parser):
        section = self._section_for(entry)
        if section is None:
            raise KeyError('markdown section not found for clause %s (%r)'
                           % (entry['number'], entry.get('from')))
        blocks = parser.parse(section.lines, context=section.key)
        if entry.get('nodetable'):
            # The generated node table is authoritative; the compact markdown member
            # table would be a second source of truth for the same facts.
            blocks = [b for b in blocks if b['t'] != 'table']
        return [b for b in blocks if not self._is_repo_internal(b)]

    def _is_repo_internal(self, block):
        """Drop paragraphs that talk about the repository rather than the model."""
        if block['t'] not in ('para', 'list'):
            return False
        text = dm.plain_text(block['runs']) if block['t'] == 'para' else ' '.join(
            dm.plain_text(i) for i in block['items'])
        for needle in self.cfg.get('dropParagraphsContaining', []):
            if needle in text:
                return True
        return False

    def appended_blocks(self, spec, parser):
        """Content merged in from another markdown section, optionally a single bullet."""
        key, _, anchor = spec.partition('#')
        section = self.sections.get(key)
        if section is None:
            # A `5.11#alarm` style selector names a bullet inside a section whose
            # heading text carries its old number.
            section = self._section_starting_with(key)
        blocks = parser.parse(section.lines, context=key)
        if anchor:
            blocks = [b for b in blocks if _mentions(b, anchor)]
        return blocks

    def _section_starting_with(self, prefix):
        for key in self.section_order:
            if key.startswith(prefix):
                return self.sections[key]
        raise KeyError('markdown section not found: %r' % prefix)

    def node_table_blocks(self, entry):
        name = entry['nodetable']
        node = self.model.by_name.get(name)
        if node is None:
            raise KeyError('%s is not in the NodeSet' % name)
        self.emitted_types.add(name)
        caption = '%s definition' % name
        blocks = [dm.nodetable(clause_id(entry['number']) + '-tab', caption, name)]
        blocks.extend(self._method_clauses(str(entry['number']), name))
        return blocks

    def assign_ids(self):
        """Give every table and figure a stable id and a caption in template style."""
        counters = {}
        fig_index = 0
        current_title = 'Table'
        for region, block in self.doc.iter_blocks():
            if block['t'] in ('clause', 'annex', 'annex-clause'):
                current_title = block['title']
                counters[current_title] = 0
            elif block['t'] == 'table' and not block.get('id'):
                counters[current_title] = counters.get(current_title, 0) + 1
                n = counters[current_title]
                block['id'] = '%s-tab%d' % (_slug(current_title), n)
                if not block.get('caption'):
                    block['caption'] = (current_title if n == 1
                                        else '%s (%d)' % (current_title, n))
            elif block['t'] == 'figure' and not block.get('id'):
                spec = (self.figure_specs[fig_index]
                        if fig_index < len(self.figure_specs) else None)
                fig_index += 1
                block['id'] = spec['id'] if spec else 'fig%d' % fig_index
                block['caption'] = spec['caption'] if spec else current_title

    # ------------------------------------------------------------------ generated

    def generated_blocks(self, kind, entry):
        return getattr(self, '_gen_' + kind.replace('-', '_'))(entry)

    def _gen_normative_references(self, entry):
        out = [dm.text_para(
            'The following referenced documents are indispensable for the application '
            'of this document. For dated references, only the edition cited applies. '
            'For undated references, the latest edition of the referenced document '
            '(including any amendments and errata) applies.'),
            dm.note([dm.t('The OPC UA core specifications are regularly published as '
                          'IEC 62541.')])]
        for ref in self.cfg['normativeReferences']:
            out.append(dm.text_para('%s, %s' % (ref['label'], ref['title']),
                                    'ReferenceDocuments', bookmark=ref['id']))
            if ref.get('url'):
                out.append(dm.text_para(ref['url'], 'ReferenceDocuments'))
        return out

    def _gen_terms_overview(self, entry):
        title = self.identity['title']
        return [dm.text_para(
            'It is assumed that basic concepts of OPC UA information modelling and of '
            '%s are understood in this document. This document uses these concepts to '
            'describe the %s Information Model. For the purposes of this document, the '
            'terms and definitions given in OPC 10000-1, OPC 10000-3, OPC 10000-4, '
            'OPC 10000-5 and OPC 10000-7, as well as the following, apply.'
            % (title, title)),
            dm.text_para('OPC UA terms and terms defined in this document are '
                         'italicized in the document.')]

    def _gen_terms(self, entry):
        """The markdown term table becomes the template's TERM entry structure."""
        section = self._section_for(entry)
        if section is None:
            raise KeyError('terms section not found')
        parser = self.parser()
        blocks = parser.parse(section.lines, context=section.key)
        out = []
        for b in blocks:
            if b['t'] != 'table':
                continue
            for r in b['rows']:
                if len(r) < 2:
                    continue
                name = dm.plain_text(r[0]).strip()
                if not name:
                    continue
                out.append(dm.term(name, r[1]))
        if not out:
            raise ValueError('no terms parsed from %r' % entry['from'])
        return out

    def _gen_abbreviations(self, entry):
        return [dm.para([dm.t(abbr), dm.tab(), dm.t(expansion)], 'PARAGRAPHCompressed')
                for abbr, expansion in self.cfg['abbreviations']]

    def _gen_intro_openusd(self, entry):
        return [dm.text_para(
            'OpenUSD (Universal Scene Description) is an open, extensible framework for '
            'describing, composing, simulating and collaborating on three-dimensional '
            'scenes. Its scene graph is assembled from layers that compose into a single '
            'stage, so several authors and tools contribute to one scene without '
            'rewriting it. A stage is a hierarchy of prims, each carrying typed '
            'attributes and relationships, addressed by a canonical prim path.'),
            dm.text_para(
                'OpenUSD is governed by the Alliance for OpenUSD (AOUSD), which publishes '
                'the OpenUSD Core Specification. The Core Specification covers paths, '
                'composition, layers and identity; the domain schemas that describe '
                'geometry, materials, lighting, skeletons and physics are versioned '
                'separately with the OpenUSD software releases.'),
            dm.text_para(
                'Industrial visualization pairs OpenUSD with live process data. This '
                'document defines how an OPC UA Server declares that pairing as part of '
                'its own address space, so that any conforming connector can apply it '
                'without prior knowledge of the domain model.')]

    def _gen_datatypes(self, entry):
        return self._gen_types(dict(entry, nodeClass='UADataType'))

    def _gen_types(self, entry):
        """One subclause per Node of a NodeClass: description, then its tables.

        Types the clause map names explicitly keep their authored prose; the rest are
        emitted from the model. Without this a model with 23 ObjectTypes would need 23
        near-identical config entries, and `check_node_tables` fails the build for any
        type the document forgets.
        """
        node_class = entry['nodeClass']
        out = []
        section = self._section_for(entry)
        if section is not None:
            intro = [b for b in self.parser().parse(section.lines, context=section.key)
                     if b['t'] == 'para']
            out.extend(intro[:1])
        n = entry.get('numberFrom', 1) - 1
        for name in self.model.names_of_class(node_class):
            if name in self.emitted_types:
                continue
            self.emitted_types.add(name)
            n += 1
            number = '%s.%d' % (entry['number'], n)
            node = self.model.by_name[name]
            out.append(dm.clause(clause_id(number), name, level=clause_level(number)))
            if node.description:
                out.append(dm.text_para(node.description))
            if node.definition and node_class == 'UADataType':
                out.append({'t': 'enumtable', 'id': clause_id(number) + '-items',
                            'browseName': name})
            out.append(dm.nodetable(clause_id(number) + '-def',
                                    '%s definition' % name, name))
            out.extend(self._method_clauses(number, name))
        return out

    def _method_clauses(self, type_number, type_name):
        """A subclause per Method the type owns, as OPC 20020 8.1.3 places them."""
        out = []
        for k, method in enumerate(nodeset_tables.methods_of(self.model, type_name), 1):
            number = '%s.%d' % (type_number, k)
            out.append(dm.clause(clause_id(number), method,
                                 level=clause_level(number)))
            out.append({'t': 'methodtable', 'id': clause_id(number) + '-m',
                        'browseName': method, 'owner': type_name})
        return out

    def _gen_type_stub(self, entry):
        node = self.model.by_name[entry['nodetable']]
        return [dm.text_para(node.description)] if node.description else []

    def _gen_namespace_metadata(self, entry):
        ident = self.identity
        rows = [
            [[dm.t('NamespaceUri')], [dm.t('String')], [dm.t(ident['namespaceUri'])]],
            [[dm.t('NamespaceVersion')], [dm.t('String')], [dm.t(self.model.version)]],
            [[dm.t('NamespacePublicationDate')], [dm.t('DateTime')],
             [dm.t(self.model.publication_date)]],
            [[dm.t('IsNamespaceSubset')], [dm.t('Boolean')], [dm.t('False')]],
            [[dm.t('StaticNodeIdTypes')], [dm.t('IdType[]')], [dm.t('0 (Numeric)')]],
            [[dm.t('StaticNumericNodeIdRange')], [dm.t('NumericRange[]')],
             [dm.t('1001:9999')]],
            [[dm.t('StaticStringNodeIdPattern')], [dm.t('String')], [dm.t('--')]],
        ]
        return [
            dm.text_para(
                'The namespace metadata provide standardized information about the '
                'elements of this namespace, which an aggregating Server relies on. All '
                'Nodes defined by this document are static: they are identical in every '
                'Server, including the Value Attribute.'),
            dm.text_para(
                'The information is provided as an Object of type NamespaceMetadataType, '
                'a component of the Namespaces Object of the Server Object. The '
                'NamespaceMetadataType ObjectType and its Properties are defined in '
                'OPC 10000-5. The same version information is carried by the '
                'ModelTableEntry of the UANodeSet XML file.'),
            dm.table(None, 'NamespaceMetadata Object for this document',
                     [[dm.t('Property')], [dm.t('DataType')], [dm.t('Value')]], rows,
                     widths=[2800, 2000, 4126]),
            dm.text_para(
                'The IsNamespaceSubset Property is False because the UANodeSet XML file '
                'contains the complete namespace. A Server exposing only a subset sets '
                'it to True.'),
        ]

    def _gen_namespace_handling(self, entry):
        ident = self.identity
        server_rows = [
            [[dm.t('http://opcfoundation.org/UA/')],
             [dm.t('Namespace for NodeIds and BrowseNames defined in the OPC UA '
                   'specification (OPC 10000-3, OPC 10000-5).')]],
            [[dm.t('Local Server URI')],
             [dm.t('Namespace for Nodes defined in the local Server. This namespace '
                   'shall have index 1.')]],
            [[dm.t('http://opcfoundation.org/UA/xRegistry/')],
             [dm.t('Namespace of the RequiredModel that carries the abstract registry '
                   'base types this document extends.')]],
            [[dm.t(ident['namespaceUri'])],
             [dm.t('Namespace for NodeIds and BrowseNames defined in this document.')]],
            [[dm.t('Vendor specific types')],
             [dm.t('A Server may provide vendor-specific types derived from the types '
                   'defined in this document, in one or more additional namespaces.')]],
        ]
        doc_rows = [
            [[dm.t('http://opcfoundation.org/UA/')], [dm.t('0')],
             [dm.t('0:EngineeringUnits')]],
            [[dm.t('http://opcfoundation.org/UA/xRegistry/')], [dm.t('1')],
             [dm.t('1:ResourceType')]],
        ]
        return [
            dm.text_para(
                'Namespaces are used by OPC UA to create unique identifiers across '
                'different naming authorities. The NodeId and BrowseName Attributes are '
                'identifiers. A Node in the AddressSpace is unambiguously identified by '
                'its NodeId; a BrowseName is not unique and is used to build a browse '
                'path or to name a standard Property.'),
            dm.table(None, 'Namespaces used in an OpenUSD Server',
                     [[dm.t('NamespaceURI')], [dm.t('Description')]], server_rows,
                     widths=[3400, 5526]),
            dm.text_para(
                'The following table lists the namespaces and their indexes used for '
                'BrowseNames in this document. The default namespace of this document is '
                'not listed, because every BrowseName without a prefix uses it.'),
            dm.table(None, 'Namespaces used in this document',
                     [[dm.t('NamespaceURI')], [dm.t('Namespace Index')], [dm.t('Example')]],
                     doc_rows, widths=[3800, 1600, 3526]),
        ]


def _mentions(block, anchor):
    text = json.dumps(block).lower()
    return anchor.lower() in text


def _slug(text):
    return ''.join(ch.lower() if ch.isalnum() else '-' for ch in text).strip('-')


# --------------------------------------------------------------------------- surgery


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('config')
    ap.add_argument('--template', default=TEMPLATE)
    args = ap.parse_args(argv)

    build = Build(args.config)
    doc = build.build_docmodel()

    out_docmodel = os.path.join(REPO, build.cfg['output']['docmodel'])
    with open(out_docmodel, 'w', encoding='utf-8', newline='\n') as f:
        f.write(doc.to_json())

    from render_docx import render
    out_docx = os.path.join(REPO, build.cfg['output']['docx'])
    render(build, doc, args.template, out_docx)
    print('wrote %s' % os.path.relpath(out_docx, REPO))
    print('wrote %s' % os.path.relpath(out_docmodel, REPO))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
