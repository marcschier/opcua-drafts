#!/usr/bin/env python3
"""Restructure a markdown draft into the OPC 20020 clause skeleton.

    python word-drafts/tools/restructure_markdown.py word-drafts/tools/specs/openusd-binding.json

The Word build and this script read the *same* clause map, so the document and its
markdown source cannot drift into different structures. Section references are rewritten
through the same map, in every document that cites this one.
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from opcdocx import md_parse, nodeset_tables

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

SECTION_REF_RE = re.compile(r'§\s*(\d+(?:\.\d+)*)')

# A reference qualified by another document belongs to that document, and applying this
# document's clause map to it corrupts it — that is how a `Part 2 §8` citation became
# `Part 2 Annex E`. Anything naming another standard or Part is left alone.
FOREIGN_QUALIFIER = re.compile(
    r'(?:OPC\s*\d{4,5}|IEC\s*\d+|xRegistry|AOUSD|RFC\s*\d+|W3C'
    r'|Part\s*\d+|\bthe base\b|\bbase (?:spec|specification|model)\b'
    r'|\*[^*]*OPC UA[^*]*\*)[^§]{0,60}$', re.IGNORECASE)


def heading_prefix(number):
    """`7.11.3` -> '####' (the document title owns level 1)."""
    return '#' * (str(number).count('.') + 2)


def is_annex(number):
    return str(number)[0].isalpha()


def rewrite_refs(text, xref_map, annex_map=None):
    """Rewrite every section reference through the clause map, longest key first."""
    keys = sorted(xref_map, key=len, reverse=True)
    pattern = re.compile(
        r'§\s*(' + '|'.join(re.escape(k) for k in keys) + r')(?!\.?\d)'
        # A range endpoint carries no § of its own and would otherwise be left behind,
        # producing a range whose end is below its start.
        r'(?P<range>\s*[\u2013\u2014-]\s*(?:' + '|'.join(re.escape(k) for k in keys)
        + r')(?!\.?\d))?')

    def repl(m):
        if FOREIGN_QUALIFIER.search(m.string[:m.start()]):
            return m.group(0)
        out = _mapped(xref_map, m.group(1))
        tail = m.group('range')
        if tail:
            end = tail.lstrip(' \u2013\u2014-')
            dash = tail[:len(tail) - len(end)]
            out += dash + _mapped(xref_map, end.strip())
        return out

    text = pattern.sub(repl, text)
    if annex_map:
        text = _rewrite_annexes(text, annex_map)
    return text


def _mapped(xref_map, old):
    new = xref_map.get(old)
    if new is None:
        return '\u00a7' + old
    return new if new.startswith('Annex ') else '\u00a7' + new


def _rewrite_annexes(text, annex_map):
    """Renumber bare `Annex X` citations, leaving the headings that declare them."""
    pattern = re.compile(r'\bAnnex\s+([A-Z])\b')

    def repl(m):
        line_start = text.rfind('\n', 0, m.start()) + 1
        if text[line_start:line_start + 1] == '#':
            return m.group(0)
        if FOREIGN_QUALIFIER.search(text[line_start:m.start()]):
            return m.group(0)
        return 'Annex ' + annex_map.get(m.group(1), m.group(1))

    out = []
    pos = 0
    for m in pattern.finditer(text):
        out.append(text[pos:m.start()])
        out.append(repl(m))
        pos = m.end()
    out.append(text[pos:])
    return ''.join(out)


def restructure(cfg):
    src = os.path.join(REPO, cfg['source']['markdown'])
    with open(src, encoding='utf-8') as f:
        text = f.read()
    sections, order = md_parse.split_sections(text)
    model = nodeset_tables.Model(os.path.join(REPO, cfg['source']['nodeset']))
    _EMITTED_TYPES.clear()
    for entry in cfg['clauseMap']:
        if entry.get('nodetable'):
            _EMITTED_TYPES.add(entry['nodetable'])

    ident = cfg['identity']
    out = []
    title_key = next((k for k in order
                      if k != '__preamble__' and sections[k].level == 1), None)
    banner_lines = (sections[title_key].lines if title_key else
                    sections['__preamble__'].lines)
    out.extend(_new_preamble(ident, banner_lines))

    used = {'__preamble__'}
    if title_key:
        used.add(title_key)
    for entry in cfg['clauseMap']:
        number = str(entry['number'])
        title = entry['title']
        if not entry.get('emitHeading', True):
            pass
        elif is_annex(number) and '.' not in number:
            out.append('')
            out.append('---')
            out.append('')
            kind = 'normative' if entry.get('normative') else 'informative'
            out.append('## Annex %s (%s) — %s' % (number, kind, title))
        elif is_annex(number):
            out.append('')
            out.append('%s %s %s' % (heading_prefix(number), number, title))
        else:
            if '.' not in number:
                out.append('')
                out.append('---')
                out.append('')
            else:
                out.append('')
            out.append('%s %s %s' % (heading_prefix(number), number, title))
        out.append('')

        body = []
        if entry.get('from'):
            body.extend(_body(sections, entry['from']))
            used.add(entry['from'])
        if entry.get('generated') == 'types':
            # The authored prose introduces the clause; the per-type subclauses follow.
            body.extend(_generated_markdown('types', cfg, entry, model))
        elif not entry.get('from') and entry.get('generated'):
            body.extend(_generated_markdown(entry['generated'], cfg, entry, model))
        elif not entry.get('from') and entry.get('slice'):
            body.extend(_slice_markdown(entry['slice']))
        if entry.get('append'):
            key, _, anchor = entry['append'].partition('#')
            section = _lookup(sections, order, key)
            used.add(section.key)
            extra = _select(section.lines, anchor) if anchor else section.lines
            if extra:
                body.append('')
                body.extend(extra)
        out.extend(_strip(body))

    out.append('')
    body_text = '\n'.join(out).rstrip() + '\n'
    body_text = rewrite_refs(body_text, cfg['xrefMap'], cfg.get('annexMap'))
    body_text = re.sub(r'\n{3,}', '\n\n', body_text)

    missing = [k for k in order
               if k != '__preamble__' and k not in used
               and not any(k.startswith(d) for d in cfg.get('dropped', []))]
    return body_text, missing


def _assert_no_old_numbers(text, cfg):
    """Deliberately not used as a gate.

    Checking the rewritten text against the map's own keys is unsound: a clause that
    moves to 8.1 collides with 8.1 as an *old* key, so a correctly-rewritten reference
    is indistinguishable from a missed one. The meaningful property — does a reference
    resolve to a clause that exists? — is checked by
    `.github/scripts/check_section_refs.py`, which is the gate.

    Kept as a diagnostic for tracking down a suspected miss.
    """
    keys = {k for k, v in cfg['xrefMap'].items() if v != k}
    survivors = []
    in_fence = False
    for lineno, line in enumerate(text.split('\n'), 1):
        if line.startswith('```'):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for m in re.finditer(r'§\s*(\d+(?:\.\d+)*)', line):
            if m.group(1) in keys and not FOREIGN_QUALIFIER.search(line[:m.start()]):
                survivors.append('  line %d: \u00a7%s in %r'
                                 % (lineno, m.group(1), line[:90]))
    return survivors


def _lookup(sections, order, key):
    if key in sections:
        return sections[key]
    for k in order:
        if k.startswith(key):
            return sections[k]
    raise KeyError('markdown section not found: %r' % key)


def _select(lines, anchor):
    """Pick the bullet of a section that names `anchor`."""
    out = []
    for line in lines:
        if line.strip().startswith('-') and anchor.lower() in line.lower():
            out.append(line)
    return out


def _body(sections, key):
    return list(sections[key].lines)


def _strip(lines):
    lines = list(lines)
    while lines and (not lines[0].strip() or lines[0].strip() == '---'):
        lines.pop(0)
    while lines and (not lines[-1].strip() or lines[-1].strip() == '---'):
        lines.pop()
    return lines


def _new_preamble(ident, banner_lines):
    keep = []
    for line in banner_lines:
        if line.strip().startswith('>'):
            keep.append(line)
    return [
        '# OPC UA for %s — %s: %s' % (ident['title'], ident['partNumber'],
                                      ident['partName']),
        '',
        '**Release %s — %s**' % (ident['version'], ident['releaseType']),
        '**Namespace:** `%s`' % ident['namespaceUri'],
        '**Publication date:** %s' % ident['publicationDate'],
        '',
    ] + keep


def _slice_markdown(kind):
    """Clauses whose text the Word build takes verbatim from the OPC 20020 template.

    The markdown states the intent and defers, so a reader of either form sees the same
    clause structure without this repository restating boilerplate it does not own.
    """
    if kind == 'conventions':
        return [
            'Node definitions in this document follow the table conventions of the OPC '
            'Foundation companion specification template: an Attribute/Value block, a '
            'References block giving the ReferenceType, NodeClass, BrowseName, DataType '
            'and TypeDefinition of each child Node, and the ConformanceUnits that '
            'require the Node in the AddressSpace. The Word rendering of this document '
            'carries that clause verbatim from the template.',
            '',
            'A BrowseName defined outside this document is prefixed with its namespace '
            'index; a BrowseName without a prefix belongs to this document\u2019s '
            'namespace. Placeholder InstanceDeclarations are enclosed in angle brackets.',
        ]
    if kind == 'opcua-intro':
        return [
            'The Word rendering of this document carries the standard OPC UA '
            'introduction from the OPC Foundation companion specification template, '
            'including its five figures. See OPC 10000-1 for the overview and '
            'OPC 10000-3 and OPC 10000-5 for the address space and information model.',
        ]
    if kind == 'annex-a':
        return []
    return []


def _types_markdown(cfg, entry, model):
    """Mirror the Word build's generated type subclauses.

    Both forms must declare the same clause numbers, or a reference that resolves in
    one fails in the other — which is the drift the shared clause map exists to prevent.
    """
    if model is None or entry is None:
        return []
    lines = []
    n = entry.get('numberFrom', 1) - 1
    for name in model.names_of_class(entry['nodeClass'], entry.get('select')):
        if name in _EMITTED_TYPES:
            continue
        _EMITTED_TYPES.add(name)
        n += 1
        number = '%s.%d' % (entry['number'], n)
        node = model.by_name[name]
        lines.append('')
        lines.append('%s %s `%s`' % (heading_prefix(number), number, name))
        lines.append('')
        if node.description:
            lines.append(node.description)
    return lines


_EMITTED_TYPES = set()


def _generated_markdown(kind, cfg, entry=None, model=None):
    ident = cfg['identity']
    if kind == 'types':
        return _types_markdown(cfg, entry, model)
    if kind == 'terms-overview':
        return [
            'It is assumed that basic concepts of OPC UA information modelling and of '
            '%s are understood in this document. For the purposes of this document, the '
            'terms and definitions given in OPC 10000-1, OPC 10000-3, OPC 10000-4, '
            'OPC 10000-5 and OPC 10000-7, as well as the following, apply.'
            % ident['title'],
            '',
            'OPC UA terms and terms defined in this document are italicized in the '
            'document.',
        ]
    if kind == 'abbreviations':
        rows = ['| Abbreviation | Term |', '|---|---|']
        rows += ['| %s | %s |' % (a, b) for a, b in cfg['abbreviations']]
        return rows
    if kind == 'intro-openusd':
        return [
            'OpenUSD (Universal Scene Description) is an open, extensible framework for '
            'describing, composing, simulating and collaborating on three-dimensional '
            'scenes. Its scene graph is assembled from layers that compose into a single '
            'stage, so several authors and tools contribute to one scene without '
            'rewriting it. A stage is a hierarchy of prims, each carrying typed '
            'attributes and relationships, addressed by a canonical prim path.',
            '',
            'OpenUSD is governed by the Alliance for OpenUSD (AOUSD), which publishes the '
            'OpenUSD Core Specification. The Core Specification covers paths, '
            'composition, layers and identity; the domain schemas that describe geometry, '
            'materials, lighting, skeletons and physics are versioned separately with the '
            'OpenUSD software releases.',
        ]
    if kind == 'namespace-metadata':
        return [
            'The namespace metadata provide standardized information about the elements '
            'of this namespace, which an aggregating Server relies on. All Nodes defined '
            'by this document are static.',
            '',
            '| Property | DataType | Value |',
            '|---|---|---|',
            '| NamespaceUri | String | `%s` |' % ident['namespaceUri'],
            '| NamespaceVersion | String | %s |' % ident['version'],
            '| NamespacePublicationDate | DateTime | %s |' % ident['publicationDate'],
            '| IsNamespaceSubset | Boolean | False |',
            '| StaticNodeIdTypes | IdType[] | 0 (Numeric) |',
            '| StaticNumericNodeIdRange | NumericRange[] | 1001:9999 |',
            '| StaticStringNodeIdPattern | String | -- |',
        ]
    if kind == 'namespace-handling':
        return [
            'Namespaces are used by OPC UA to create unique identifiers across different '
            'naming authorities. The following namespaces are used for BrowseNames in '
            'this document; the default namespace is not listed, because every BrowseName '
            'without a prefix uses it.',
            '',
            '| NamespaceURI | Namespace index | Example |',
            '|---|---|---|',
            '| `http://opcfoundation.org/UA/` | 0 | `0:EngineeringUnits` |',
            '| `http://opcfoundation.org/UA/xRegistry/` | 1 | `1:ResourceType` |',
        ]
    if kind == 'normative-references':
        rows = []
        for ref in cfg['normativeReferences']:
            if ref.get('url'):
                rows.append('- [%s](%s) — %s' % (ref['label'], ref['url'], ref['title']))
            else:
                rows.append('- %s — %s' % (ref['label'], ref['title']))
        return ['The following referenced documents are indispensable for the '
                'application of this document. For dated references, only the edition '
                'cited applies. For undated references, the latest edition of the '
                'referenced document (including any amendments and errata) applies.',
                ''] + rows
    if kind == 'terms':
        return []
    if kind == 'datatypes':
        return ['The DataTypes defined by this document are enumerations. Each is '
                'formally defined in the NodeSet and listed in Annex A.']
    if kind == 'type-stub':
        return []
    return []


# --------------------------------------------------------------------------- siblings


def rewrite_siblings(cfg, paths):
    """Rewrite `Part 1 §x.y` style references in the documents that cite this one."""
    changed = []
    unanchored = set(cfg.get('unanchoredSiblings') or [])
    xref = cfg['xrefMap']
    annex_map = cfg.get('annexMap') or {}
    keys = sorted(xref, key=len, reverse=True)
    # How sibling documents name this one. A reference is only rewritten when it is
    # anchored on one of these, so this document's clause map is never applied to a
    # reference that belongs elsewhere.
    anchors = cfg.get('citedAs') or [cfg['identity']['partNumber']]
    anchor_alt = '|'.join(re.escape(a) for a in anchors)
    pattern = re.compile(
        r'(?P<anchor>(?:' + anchor_alt + r')[^.\n]{0,60}?)§\s*(?P<num>'
        + '|'.join(re.escape(k) for k in keys) + r')(?!\.?\d)'
        r'(?P<range>\s*[\u2013\u2014-]\s*(?:' + '|'.join(re.escape(k) for k in keys)
        + r')(?!\.?\d))?')
    annex_pattern = re.compile(
        r'(?P<anchor>(?:' + anchor_alt + r')[^.\n]{0,60}?)Annex\s+(?P<letter>[A-Z])\b')

    def repl(m):
        out = m.group('anchor') + _mapped(xref, m.group('num'))
        tail = m.group('range')
        if tail:
            end = tail.lstrip(' \u2013\u2014-')
            out += tail[:len(tail) - len(end)] + _mapped(xref, end.strip())
        return out

    def annex_repl(m):
        return m.group('anchor') + 'Annex ' + annex_map.get(m.group('letter'),
                                                            m.group('letter'))

    for rel in paths:
        full = os.path.join(REPO, rel)
        if not os.path.exists(full):
            continue
        with open(full, encoding='utf-8') as f:
            text = f.read()
        new_text = pattern.sub(repl, text)
        if annex_map:
            new_text = annex_pattern.sub(annex_repl, new_text)
        if rel in unanchored:
            # A README beside the specification cites it without naming it, so every
            # bare reference in the file means this document.
            new_text = rewrite_refs(new_text, xref, annex_map)
        if new_text != text:
            with open(full, 'w', encoding='utf-8', newline='\n') as f:
                f.write(new_text)
            changed.append(rel)
    return changed


DEFAULT_SIBLINGS = [
    'metaverse-specs/openusd-scene/OPC-UA-OpenUSD-Scene-Materialization.md',
    'metaverse-specs/openusd-binding/OPC-UA-OpenUSD-Bindings.md',
    'metaverse-specs/openusd-binding/README.md',
    'metaverse-specs/openusd-scene/README.md',
    'metaverse-specs/openusd-binding/pumps/OPC-UA-Pumps-OpenUSD-Bindings-Addendum.md',
    'metaverse-specs/openusd-binding/robotics/OPC-UA-Robotics-OpenUSD-Bindings-Addendum.md',
    'metaverse-specs/extras/openusd-binding/examples/pumps/E2E-GUIDE.md',
    'metaverse-specs/extras/openusd-binding/examples/robotics/E2E-GUIDE.md',
    'metaverse-specs/extras/openusd-artifacts/README.md',
    'metaverse-specs/README.md',
]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('config')
    ap.add_argument('--check', action='store_true',
                    help='report what would change without writing')
    args = ap.parse_args(argv)

    with open(args.config, encoding='utf-8') as f:
        cfg = json.load(f)

    text, missing = restructure(cfg)
    target = os.path.join(REPO, cfg['source']['markdown'])
    if args.check:
        with open(target, encoding='utf-8') as f:
            current = f.read()
        print('would change' if current != text else 'unchanged')
    else:
        with open(target, 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
        print('rewrote %s' % cfg['source']['markdown'])
        changed = rewrite_siblings(cfg, cfg.get('siblingDocuments') or DEFAULT_SIBLINGS)
        for c in changed:
            print('updated references in %s' % c)
    if missing:
        print('WARNING: markdown sections not placed by the clause map:')
        for m in missing:
            print('  - %s' % m)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
