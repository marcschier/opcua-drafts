"""Convert one specification onto the OPC UA template, as far as a machine safely can.

The steps a conversion always needs, in one place: the manifest from the Word build config,
the prose rewritten into the template's dialect, the NodeSets moved to `model/`, a
`profiles.json` carrying the Conformance Units the NodeSet already names, and a definition
table for every type the model declares.

The one interesting step is placing those tables. The publisher has no directive that
generates a node table -- a table is authored and bound to its type with `defines=` -- and our
documents mostly have a clause per type already, titled with the type's name. So a table is
attached to the clause that names its type, which is where a reader looks for it, and a type
with no such clause gets one of its own at the end and is **reported**, because appending a
type to a document silently is how a specification grows a clause nobody wrote.

Usage:
    python convert_spec.py <spec> --doc-number "OPC 99006-1" --group core-specs --name xregistry
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))

import convert_to_template as ctt          # noqa: E402
import emit_node_tables as ent             # noqa: E402
from opcdocx import nodeset_tables as nt   # noqa: E402

HEADING = re.compile(r'^(#{2,6})\s+(.*?)(\s*\{#[^}]*\})?\s*$')


def type_named_by(text: str, names: set[str]) -> str | None:
    """The type a clause heading is about, if its title names exactly one.

    A heading may name a type plainly (`AlternatorType`), in code (`` `EngineType` ``) or as a
    link left over from the old dialect. Two names in one heading is not a match: the clause
    documents both and a table bound to one of them would be filed under the wrong heading.
    """
    words = set(re.findall(r'[A-Za-z_][A-Za-z0-9_]*', text))
    hits = words & names
    return next(iter(hits)) if len(hits) == 1 else None


def profiles_from(model, path: pathlib.Path) -> list[str]:
    """Write the Conformance Units the NodeSet already names, so nothing is invented."""
    units = sorted({c for n in model.nodes.values() for c in (n.categories or ())})
    if not units:
        return ['the NodeSet names no Category, so no profiles.json is written; a companion '
                'specification is expected to define Conformance Units']
    payload = {
        'conformanceUnits': [
            {'name': u, 'group': model.model_uri.rstrip('/').rsplit('/', 1)[-1],
             'category': 'Server',
             'description': ''}
            for u in units
        ],
        'profiles': [],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n',
                    encoding='utf-8', newline='\n')
    return ['profiles.json lists the %d Conformance Unit(s) the NodeSet names, with empty '
            'descriptions and no Profiles: write the descriptions, and the Facets that require '
            'them, by hand' % len(units)]


def attach_tables(lines: list[str], model, doc_ns_index: int, defined_in: dict):
    """Put each type's definition table under the clause that names it; report the rest.

    Returns the rewritten lines, the findings, and a map from the old `type-<Name>` anchor --
    which pointed into the generated Annex A this conversion deletes -- to the clause that now
    documents that type. Repointing those citations is the whole reason to know where each
    table went: a reader following `#type-EngineType` should land on the clause about the
    engine, not on a annex that no longer exists.
    """
    findings = []
    declared = (list(nt.object_types(model, doc_ns_index=doc_ns_index))
                + list(nt.data_types(model))
                + [n.name for n in model.nodes.values()
                   if n.tag in ('UAReferenceType', 'UAVariableType')])
    names = set(declared)
    placed = {}
    unnamed = []
    renames = {}

    # Where each clause ends, so a table goes after its prose rather than before it.
    starts = [i for i, l in enumerate(lines) if HEADING.match(l)]
    for pos in starts:
        m = HEADING.match(lines[pos])
        name = type_named_by(m.group(2), names - set(placed))
        if name:
            placed[name] = pos
            attrs = m.group(3) or ''
            slug = re.search(r'\{#([^}\s]+)', attrs)
            if slug:
                renames['type-%s' % name] = slug.group(1)

    # Insert from the bottom so the earlier indices stay valid.
    out = list(lines)
    for name in sorted(placed, key=lambda n: -placed[n]):
        pos = placed[name]
        end = pos + 1
        while end < len(out) and not HEADING.match(out[end]):
            end += 1
        table = ent.definition_table(model, name, doc_ns_index=doc_ns_index,
                                     defined_in=defined_in, unnamed=unnamed)
        out[end:end] = ['', table, '']

    missing = [n for n in declared if n not in placed]
    if missing:
        tail = ['', '## Information model {#sec-information-model}', '',
                'The types below are declared by the model. Each clause was generated because no '
                'clause of this document named its type; fold them into the prose where they '
                'belong.', '']
        for name in missing:
            node = model.by_name.get(name)
            tail.append('### %s {#sec-%s}' % (name, ent.anchor(name)))
            tail.append('')
            renames['type-%s' % name] = 'sec-%s' % ent.anchor(name)
            if node is not None and (node.description or '').strip():
                tail.append(node.description.strip())
                tail.append('')
            tail.append(ent.definition_table(model, name, doc_ns_index=doc_ns_index,
                                             defined_in=defined_in, unnamed=unnamed))
            tail.append('')
        out += tail
        findings.append('%d type(s) had no clause naming them and were appended under an '
                        '"Information model" clause: %s' % (len(missing), ', '.join(missing)))
    if unnamed:
        findings.append('supertype(s) with no defining document, so the table cannot say where '
                        'to look them up: %s' % ', '.join(sorted(set(unnamed))))
    findings.append('%d of %d type(s) placed under a clause that names them'
                    % (len(placed), len(declared)))
    return out, findings, renames


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('spec', help='name of a word-drafts/tools/specs/<spec>.json, or --config')
    ap.add_argument('--config', type=pathlib.Path,
                    help='a build config elsewhere, for a specification that never had a Word '
                         'rendering and so has no file in specs/')
    ap.add_argument('--doc-number', required=True)
    ap.add_argument('--group', required=True, help='e.g. core-specs')
    ap.add_argument('--name', required=True, help='the directory under source/<group>/')
    ap.add_argument('--defined-in', action='append', default=[], metavar='PREFIX=DOCUMENT')
    args = ap.parse_args(argv)

    cfg_path = args.config or (HERE / 'specs' / ('%s.json' % args.spec))
    cfg = json.loads(cfg_path.read_text(encoding='utf-8'))
    dest = REPO / 'source' / args.group / args.name
    dest.mkdir(parents=True, exist_ok=True)
    findings = []

    manifest, f = ctt.build_manifest(cfg, args.doc_number)
    findings += f

    # The prose.
    src = REPO / (cfg['source']['markdown'])
    raw = src.read_text(encoding='utf-8').splitlines()

    # Read the Terms clause before the conversion deletes it: clause 3 is generated from the
    # manifest, so a definition not carried across is a definition lost.
    terms, f = ctt.extract_terms(raw)
    if terms:
        manifest['terms'] = terms
        findings = [x for x in findings if 'terms are not carried' not in x]
    findings += f

    lines, f = ctt.convert_prose(raw, has_model=bool((cfg.get('source') or {}).get('nodeset')))
    findings += ['prose: %s' % x for x in f]

    # The model, and the tables that document it.
    nodeset = (cfg.get('source') or {}).get('nodeset')
    model = None
    if nodeset:
        model = nt.Model(str(REPO / nodeset), cfg.get('requiredModelNodes'))
        index = (cfg['identity'] or {}).get('namespaceIndexInDocument', 1)
        defined_in = dict(p.split('=', 1) for p in args.defined_in)
        lines, f, renames = attach_tables(lines, model, index, defined_in)
        findings += ['tables: %s' % x for x in f]
        # The citations that pointed into the annex now point at the clause documenting the
        # type. A `#type-...` left over is one whose type the model does not declare, which is
        # a finding: the document cites something that is not in the model.
        stale = set()
        rewritten = []
        for line in lines:
            def repoint(m):
                target = m.group(2)
                if target.startswith('type-'):
                    if target in renames:
                        return '[%s](#%s)' % (m.group(1), renames[target])
                    stale.add(target)
                return m.group(0)
            rewritten.append(ctt.INLINE_LINK.sub(repoint, line))
        lines = rewritten
        findings += ['tables: %d citation target(s) repointed from the deleted Annex A'
                     % len(renames)]
        if stale:
            findings += ['tables: %d citation(s) name a type the model does not declare: %s'
                         % (len(stale), ', '.join(sorted(stale)))]
        findings += profiles_from(model, dest / 'profiles.json')
        manifest['profiles'] = 'profiles.json'

    (dest / 'spec.md').write_text('\n'.join(ctt.tidy(lines)) + '\n',
                                  encoding='utf-8', newline='\n')

    for key, rel in (cfg.get('additionalMarkdown') or {}).items():
        part = REPO / rel
        body, f = ctt.convert_prose(part.read_text(encoding='utf-8').splitlines(), has_model=False)
        (dest / ('%s.md' % key)).write_text('\n'.join(ctt.tidy(body)) + '\n',
                                            encoding='utf-8', newline='\n')
        findings += ['%s.md: written from %s; add a ```{include %s} directive where it belongs'
                     % (key, rel, key)]

    (dest / 'manifest.json').write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + '\n',
        encoding='utf-8', newline='\n')

    print('wrote %s' % dest.relative_to(REPO))
    print('%d finding(s):' % len(findings), file=sys.stderr)
    for x in findings:
        print('  %s' % x, file=sys.stderr)
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
