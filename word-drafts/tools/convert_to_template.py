"""Convert a specification from this repository's dialect to the OPC UA template's.

Two halves, because they fail differently.

`manifest` is a schema translation. Every field the template's `manifest.json` wants -- the
identity, the normative references, the abbreviations, the namespace table -- is already in
`word-drafts/tools/specs/<spec>.json` in a different shape, so this half is a rename and a
reshape and it either succeeds or names the field it could not find.

`prose` is a rewrite of the markdown, and it is where guessing would do damage. It does only
what is mechanical and reversible: strip the number from a heading and give it the anchor its
text implies, move an `<a id="...">` onto the heading that follows it, repoint the links that
cited either, and delete a `reference.opcfoundation.org` link while keeping its text, because
`OPC030` forbids the link and the generated clauses carry the address. Everything else -- a
table that needs a caption, a clause that has to become a directive, a figure to extract -- is
reported with its line number and left alone, because a person has to decide what it means.

Usage:
    python convert_to_template.py manifest <spec> --doc-number "OPC 99006-1" --out <path>
    python convert_to_template.py prose <markdown> [--write]
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent

# A numbered heading in our dialect: `## 4.3 Namespaces`, `### 6.1 [GeneratorSetType](#type-X)`.
NUMBERED_HEADING = re.compile(r'^(#{1,6})\s+(\d+(?:\.\d+)*)\s+(.*?)\s*$')
PLAIN_HEADING = re.compile(r'^(#{1,6})\s+(.*?)\s*$')
HTML_ANCHOR = re.compile(r'^\s*<a\s+id="([^"]+)"\s*>\s*</a>\s*$')
REFERENCE_LINK = re.compile(r'\[([^\]]+)\]\(https?://reference\.opcfoundation\.org/[^)]*\)')
INLINE_LINK = re.compile(r'\[([^\]]*)\]\(#([^)]+)\)')
MERMAID_FENCE = re.compile(r'^```mermaid\s*$')
ATTR_ID_RE = re.compile(r'\{#([A-Za-z0-9][A-Za-z0-9_.:-]*)')
TABLE_ROW = re.compile(r'^\s*\|')
SECTION_REF = re.compile(r'§\s*[\d.]+')


def anchor(text: str) -> str:
    """A heading anchor: lower case, non-alphanumerics collapsed to a single dash."""
    text = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', text)   # links become their text
    text = re.sub(r'[`*_~]', '', text)
    text = re.sub(r'[^a-z0-9]+', '-', text.lower())
    return text.strip('-')


# --------------------------------------------------------------------------- manifest

LICENCE = {
    'spdxId': 'LicenseRef-OPC-Specification-1.15',
    'copyright': 'Copyright (c) 2026, OPC Federation AISBL',
    'url': 'https://opcfoundation.org/license/specifications/1.15/',
}


def build_manifest(cfg: dict, doc_number: str, model_dir: str = 'model') -> tuple[dict, list[str]]:
    """Reshape a Word build config into a template manifest, reporting what is not there."""
    findings = []
    ident = cfg.get('identity') or {}

    def need(key):
        value = ident.get(key)
        if not value:
            findings.append('identity.%s is not in the Word config; fill it in by hand' % key)
        return value or ''

    # Our configs carry the cover title in upper case (`OPC UA FOR SCHEMA REGISTRY`) beside a
    # properly cased short one (`Schema Registry`). Case-folding the former turns `OPC UA` into
    # `Opc Ua`, so the title is composed from the short one instead, and a config that does not
    # follow the pattern is reported rather than guessed at.
    main_title = ident.get('mainTitle') or ''
    short = need('title')
    if re.match(r'^OPC UA FOR ', main_title):
        title = 'OPC UA for %s' % short
        # The cover title may say more than the short one -- "OPC UA FOR APACHE ARROW ENCODING"
        # beside "Arrow Encoding" -- and composing from the short one would quietly drop a word.
        # Case-folding the cover title instead would turn "OPC UA" into "Opc Ua", so neither is
        # safe on its own; where they disagree, say so and let a person choose.
        covered = set(re.findall(r'[A-Za-z0-9]+', main_title[len('OPC UA FOR '):].lower()))
        if covered - set(re.findall(r'[A-Za-z0-9]+', short.lower())):
            findings.append('identity.mainTitle is %r but identity.title is %r; the manifest '
                            'title is composed from the latter, so check it reads as intended'
                            % (main_title, short))
    elif main_title:
        title = main_title
        findings.append('identity.mainTitle is %r, which does not begin "OPC UA FOR"; check the '
                        'capitalisation of identity.title in the manifest' % main_title)
    else:
        title = short

    manifest = {
        'schemaVersion': 1,
        'sourceOfTruth': 'markdown',
        'identity': {
            'docNumber': doc_number,
            'partName': need('partName'),
            'title': title,
            'shortTitle': short,
            'shortName': need('shortName'),
            # `otherOrganization` names a partner on a joint work; the template's single
            # `organization` field is printed as the Author and written into the STS as the
            # copyright holder, so a joint work names both.
            'organization': ('OPC Foundation and the %s' % ident['otherOrganization']
                             if ident.get('otherOrganization') else 'OPC Foundation'),
            'capabilityIdentifier': ident.get('capabilityIdentifier', ''),
            'namespaceUri': need('namespaceUri'),
            'version': need('version'),
            'publicationDate': need('publicationDate'),
            'releaseType': ident.get('releaseType', 'Draft'),
            'gitHubTag': '',
            'mantisUrl': 'https://mantis.opcfoundation.org',
            'license': dict(LICENCE),
        },
    }

    nodeset = (cfg.get('source') or {}).get('nodeset')
    if nodeset:
        manifest['model'] = {
            'nodeset': '%s/%s' % (model_dir.rstrip('/'), os.path.basename(nodeset)),
            'generated': True,
        }
    else:
        findings.append('no nodeset in the Word config, so the model block is omitted and the '
                        'build will report "model: none" - correct for a specification that '
                        'defines none, a finding for one that does')

    manifest['markdown'] = {'main': 'spec.md', 'figures': 'figures'}
    for key in sorted((cfg.get('additionalMarkdown') or {})):
        manifest['markdown'][key] = '%s.md' % key

    manifest['figureGenerators'] = {
        '.drawio.svg': '',
        '.pptx': {'win': 'tools/office-to-svg.ps1', 'default': 'tools/office-to-svg.sh'},
    }
    flat = doc_number.replace(' ', '-')
    manifest['output'] = {
        'sts': 'artifacts/%s.xml' % flat,
        'documentationCsv': 'artifacts/%s-documentation.csv' % flat,
    }

    # `id` becomes the anchor a `[](#ref-<id>)` citation names, and the template writes it in
    # lower case; ours are mixed (`UAPart1`), so they are folded here rather than in the prose.
    manifest['normativeReferences'] = [
        {'id': r['id'].lower(), 'label': r['label'], 'title': r['title'], 'url': r.get('url', '')}
        for r in (cfg.get('normativeReferences') or [])
    ]
    if not manifest['normativeReferences']:
        findings.append('no normativeReferences in the Word config; clause 2 would be empty')

    manifest['terms'] = []
    findings.append('terms are not carried by the Word config: take them from the document\'s '
                    'own Terms clause, which this conversion deletes')
    manifest['abbreviations'] = [list(a) for a in (cfg.get('abbreviations') or [])]

    index = ident.get('namespaceIndexInDocument')
    if index is None:
        findings.append('identity.namespaceIndexInDocument is not set, so the namespace table '
                        'cannot be built; write namespaces by hand')
    else:
        manifest['namespaces'] = {
            'documentNamespaceIndex': index,
            'table': [{
                'uri': 'http://opcfoundation.org/UA/',
                'index': 0,
                'definedBy': 'uapart5',
                'description': 'Namespace for *NodeIds* and *BrowseNames* defined in the OPC UA '
                               'specification. This namespace shall have namespace index 0.',
            }],
        }
        if index != 0:
            manifest['namespaces']['table'].append({
                'uri': ident.get('namespaceUri', ''),
                'index': index,
                'description': 'Namespace for *NodeIds* and *BrowseNames* defined in this model.',
            })
        findings.append('the namespace table holds only namespace 0 and this document\'s own; '
                        'add every namespace the model or its dependencies reach, or the build '
                        'reports an unknown namespace')

    return manifest, findings


# --------------------------------------------------------------------------- prose

def strip_front_matter(lines: list[str]) -> tuple[list[str], list[str]]:
    """Drop the title and the banner above the first clause.

    A document in this repository opens with an H1 and a status banner naming the release, the
    namespace and the publication date. All of that is identity, and identity is in
    `manifest.json`: the tool builds the cover from it. Left in the markdown the H1 becomes
    clause 1, and the build then reports that clause 1 is not Scope -- correctly, because the
    title is sitting in front of it.
    """
    for i, line in enumerate(lines):
        if re.match(r'^##\s', line):
            if i == 0:
                return lines, []
            return lines[i:], ['%d line(s) of title and banner removed from the top; the '
                               'cover is built from manifest.json -> identity, so check that '
                               'nothing normative was in them' % i]
    return lines, ['no ## clause found, so nothing was treated as front matter']


def strip_generated(lines: list[str], has_model: bool = True) -> tuple[list[str], list[str], dict]:
    """Remove the clauses the publisher writes, and ask for them where they belong.

    A specification with no model has no generated annex, so its Annex A is one somebody wrote
    and is kept. That is why `has_model` is asked for rather than assumed: the two cases look
    identical in the markdown and only the manifest can tell them apart.

    Clause 2 and clause 3 are generated from `manifest.json`, and the Annex A our documents
    carry was generated into the markdown by the model generator. Leaving any of them in place
    publishes the clause twice and leaves the copy that can drift from the model.

    The annex is where the old anchors live -- `<a id="type-SomeType">` -- so removing it is
    also what makes the `#type-...` citations in the prose dangle, which is a finding rather
    than damage: the clause that documents a type is where that citation should point, and only
    a person can say which one that is.
    """
    findings = []
    out = []
    skipping = None
    redirect = {}
    for line in lines:
        heading = re.match(r'^(#{1,6})\s+(.*?)(\s*\{#([^}\s]+)[^}]*\})?\s*$', line)
        if heading:
            level = len(heading.group(1))
            slug = heading.group(4) or ''
            if skipping is not None and level <= skipping[0]:
                skipping = None
            if skipping is None:
                if slug == 'sec-normative-references':
                    skipping = (level, None)
                    findings.append('clause 2 removed; it is generated from '
                                    'manifest.json -> normativeReferences')
                    continue
                if re.match(r'^sec-terms\b', slug) or slug == 'sec-terms-and-abbreviations':
                    skipping = (level, None)
                    findings.append('clause 3 removed; terms and abbreviations are generated '
                                    'from manifest.json, and a {clause} kind: terms directive '
                                    'switches the Terms subclause on')
                    continue
                if slug == 'anx-a' and has_model:
                    skipping = (level, 'anx-a')
                    findings.append('the generated Annex A removed and replaced by a directive; '
                                    'every #type-... citation in the prose pointed into it and '
                                    'now needs repointing at the clause documenting that type')
                    out += ['## Information model reference {#anx-a annex=normative}', '',
                            '```{clause}', 'kind: annex-a', '```', '']
                    continue
                if slug.startswith('anx-'):
                    findings.append('%s is an annex this document wrote, so it is kept; only '
                                    'Annex A is generated from the model' % slug)
        if skipping is None:
            out.append(line)
        else:
            # Remember every anchor going away, so a citation of one can be sent to whatever
            # replaces it -- Annex A is replaced by the directive, and a heading inside it is
            # therefore the directive too. A clause with no replacement maps to nothing and
            # its citations are reported.
            for gone in ATTR_ID_RE.findall(line):
                redirect[gone] = skipping[1]
    return out, findings, redirect


def extract_terms(lines: list[str]) -> tuple[list[dict], list[str]]:
    """Read the Terms clause's table into the manifest's `terms` list before it is deleted.

    Clause 3 is generated from `manifest.json`, so the conversion deletes the authored one --
    and with it every definition the working group wrote, unless they are carried across. Our
    documents state them as a two-column table under a "Terms" heading, which is enough to
    read: the first column is the term, the second its definition.

    A term is written lower case, because that is how ISO renders one and how the generated
    clause prints it; the `<a id="term-...">` some of them carry is dropped, because the
    generated clause anchors them itself.
    """
    findings = []
    terms = []
    inside = False
    for line in lines:
        heading = re.match(r'^(#{1,6})\s+(.*)$', line)
        if heading:
            if inside:
                break
            inside = bool(re.search(r'\bterms?\b', heading.group(2), re.I))
            continue
        if not inside or not line.startswith('|'):
            continue
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) < 2 or set(cells[0]) <= set('- :') or cells[0].lower() == 'term':
            continue
        term = re.sub(r'<a\s+id="[^"]*"\s*>\s*</a>', '', cells[0]).strip()
        term = re.sub(r'[`*]', '', term).strip()
        definition = re.sub(r'<a\s+id="[^"]*"\s*>\s*</a>', '', cells[1]).strip()
        if term and definition:
            terms.append({'term': term[:1].lower() + term[1:], 'definition': definition})
    if terms:
        findings.append('%d term(s) carried from the Terms clause into manifest.json; check '
                        'the wording, because a definition written for a table is not always a '
                        'noun phrase' % len(terms))
    return terms, findings


def tidy(lines: list[str]) -> list[str]:
    """Normalise the whitespace the conversion disturbs.

    Deleting a clause or a banner leaves the blank lines that surrounded it, and inserting a
    table between two clauses can leave none. Neither is a judgement call -- markdownlint
    states the rule (`MD012`, `MD022`, `MD009`) and the fix is the same every time -- so it is
    done here rather than left as a finding for a person to apply mechanically.
    """
    out = []
    in_fence = False
    for line in lines:
        if line.startswith('```') or line.startswith('~~~'):
            in_fence = not in_fence
            out.append(line)
            continue
        if in_fence:
            out.append(line)
            continue
        line = line.rstrip()
        if not line and out and not out[-1]:
            continue                      # one blank line is enough
        if re.match(r'^#{1,6}\s', line) and out and out[-1]:
            out.append('')                # a heading opens on its own
        out.append(line)
        if re.match(r'^#{1,6}\s', line):
            out.append('')
    while out and not out[0]:
        out.pop(0)
    while out and not out[-1]:
        out.pop()
    # A heading followed by a blank we just added, then the blank that was already there.
    squeezed = []
    for line in out:
        if not line and squeezed and not squeezed[-1]:
            continue
        squeezed.append(line)
    return squeezed


def convert_prose(lines: list[str], has_model: bool = True) -> tuple[list[str], list[str]]:
    """Rewrite what is mechanical; report what needs a decision."""
    findings = []
    out = []
    renames = {}          # old anchor -> new anchor
    pending_html = None   # an <a id> waiting for the heading it labels
    in_fence = False
    seen = set()

    for number, line in enumerate(lines, 1):
        if line.startswith('```'):
            in_fence = not in_fence
            if MERMAID_FENCE.match(line):
                findings.append('%d: mermaid fence - extract it to figures/<name>.mmd and cite '
                                'it with a {figure} directive; note that the Word writer cannot '
                                'embed one, so a .drawio.svg or .pptx is the safer source'
                                % number)
            out.append(line)
            continue
        if in_fence:
            out.append(line)
            continue

        html = HTML_ANCHOR.match(line)
        if html:
            pending_html = html.group(1)
            continue      # the anchor moves onto the heading below it

        heading = NUMBERED_HEADING.match(line) or PLAIN_HEADING.match(line)
        if heading:
            hashes = heading.group(1)
            text = heading.group(3) if heading.re is NUMBERED_HEADING else heading.group(2)
            if '{#' in text:
                out.append(line)
                pending_html = None
                continue
            slug = anchor(text)
            annex = re.match(r'^annex-([a-z])\b-*(.*)$', slug)
            if annex:
                # Keep the letter in the anchor so a later pass can tell Annex A -- which our
                # documents generate from the model -- from an annex somebody wrote. The label
                # is derived by the renderer, so the heading text drops "Annex X —".
                new = 'anx-%s' % annex.group(1)
                text = re.sub(r'^\s*Annex\s+[A-Za-z]\s*[-\u2013\u2014:]*\s*', '', text.strip())
                # An annex that calls itself informative is informative. Getting this wrong
                # changes what the document requires, so it is read from the title rather than
                # assumed, and a title that says nothing is normative -- which is what an
                # annex of a companion specification is unless it says otherwise.
                kind = 'informative' if re.search(r'\(informative\)', text, re.I) else 'normative'
                attrs = ' annex=%s' % kind
            else:
                new = 'sec-%s' % slug
                attrs = ''
            while new in seen:
                new += '-x'
            seen.add(new)
            if pending_html:
                renames[pending_html] = new
                pending_html = None
            # Register the slug GitHub would have given this heading, because that is what the
            # old in-document links used. Both forms occur -- a numbered heading was cited by
            # its slug and an unnumbered one by the slug of its whole title -- so the original
            # text is what has to be slugged, before the annex label is taken off it.
            renames.setdefault(anchor(heading.group(3) if heading.re is NUMBERED_HEADING
                                      else heading.group(2)), new)
            out.append('%s %s {#%s%s}' % (hashes, text.strip(), new, attrs))
            continue

        pending_html = None if line.strip() else pending_html
        out.append(line)

    # Drop the clauses the publisher writes for itself, *before* the citations are repointed.
    # The generated Annex A is where the old `<a id="type-...">` anchors lived, so a rename
    # onto one of its headings would point at something this pass is about to delete. Pruning
    # the map to the anchors that survive leaves those citations as `#type-...`, which is what
    # lets a later pass repoint them at the clause that documents the type.
    out, stripped, redirect = strip_generated(out, has_model)
    surviving = set()
    for line in out:
        surviving |= set(ATTR_ID_RE.findall(line))
    # A rename onto a heading that has gone follows it to its replacement, if it has one --
    # except a `type-...` citation, which is deliberately left alone so the pass that places
    # the node tables can send it to the clause that documents that type. Sending it to the
    # annex directive instead would be worse than leaving it dangling: it would resolve, and
    # it would resolve to the wrong place.
    renames = {old: (new if old.startswith('type-') else redirect.get(new, new))
               for old, new in renames.items()
               if new in surviving or (redirect.get(new) and not old.startswith('type-'))}
    renames.update({gone: to for gone, to in redirect.items()
                    if to and not gone.startswith('type-')})
    seen &= surviving

    # Second pass: repoint the citations, and strip the links OPC030 forbids.
    result = []
    for number, line in enumerate(out, 1):
        before = line
        line = REFERENCE_LINK.sub(r'\1', line)
        if line != before:
            findings.append('%d: reference.opcfoundation.org link removed (OPC030); the '
                            'designation links itself from the normative references' % number)
        line = INLINE_LINK.sub(
            lambda m: '[%s](#%s)' % (m.group(1), renames.get(m.group(2), m.group(2))), line)
        # A citation of a term defined in the clause this conversion deleted becomes the term
        # marker instead of a link. `*Term*` is what AUTHORING.md asks for -- it feeds the term
        # index -- and the generated Terms clause is where the definition now lives, so a link
        # to a particular anchor is both broken and unnecessary.
        def term_marker(m):
            if m.group(2).startswith('term-') and m.group(2) not in surviving:
                return '*%s*' % re.sub(r'[`*]', '', m.group(1))
            return m.group(0)
        before_terms = line
        line = INLINE_LINK.sub(term_marker, line)
        if line != before_terms:
            findings.append('%d: a citation of a term became the term marker *...*, because '
                            'the Terms clause it pointed into is now generated' % number)
        for stale in INLINE_LINK.finditer(line):
            target = stale.group(2)
            if target not in seen and target not in renames.values():
                findings.append('%d: link to #%s has no anchor in this file; it may be in an '
                                'included part, or it may be stale' % (number, target))
        if SECTION_REF.search(line):
            findings.append('%d: a section reference by number - the template derives numbers, '
                            'so write [](#sec-...) and let the renderer fill it in' % number)
        if TABLE_ROW.match(line) and not TABLE_ROW.match(out[number - 2] if number > 1 else ''):
            findings.append('%d: a table starts here with no caption above it; every table '
                            'needs *Table - X* {#tbl-x}, and one documenting a type needs '
                            'defines=' % number)
        result.append(line)

    # Last: drop the title and the banner above the first clause.
    result, front = strip_front_matter(result)
    return tidy(result), findings + stripped + front


# --------------------------------------------------------------------------- entry

def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='verb', required=True)

    m = sub.add_parser('manifest', help='a Word build config -> a template manifest.json')
    m.add_argument('spec', help='the name of a word-drafts/tools/specs/<spec>.json')
    m.add_argument('--doc-number', required=True, help='e.g. "OPC 99006-1"')
    m.add_argument('--out', type=pathlib.Path)

    p = sub.add_parser('prose', help='rewrite one markdown file into the template dialect')
    p.add_argument('markdown', type=pathlib.Path)
    p.add_argument('--write', action='store_true', help='edit in place instead of reporting')

    args = ap.parse_args(argv)

    if args.verb == 'manifest':
        path = HERE / 'specs' / ('%s.json' % args.spec)
        if not path.exists():
            print('no such Word config: %s' % path, file=sys.stderr)
            return 2
        cfg = json.loads(path.read_text(encoding='utf-8'))
        model_dir = 'model'
        if args.out:
            try:
                spec_dir = args.out.resolve().parent.relative_to((REPO / 'source').resolve())
                model_dir = (pathlib.Path('model') / spec_dir).as_posix()
            except ValueError:
                pass
        manifest, findings = build_manifest(cfg, args.doc_number, model_dir)
        text = json.dumps(manifest, indent=2, ensure_ascii=False) + '\n'
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(text, encoding='utf-8', newline='\n')
            print('wrote %s' % args.out)
        else:
            print(text)
    else:
        lines = args.markdown.read_text(encoding='utf-8').splitlines()
        converted, findings = convert_prose(lines)
        if args.write:
            args.markdown.write_text('\n'.join(converted) + '\n',
                                     encoding='utf-8', newline='\n')
            print('rewrote %s (%d lines)' % (args.markdown, len(converted)))
        else:
            print('would rewrite %s (%d lines); pass --write to apply'
                  % (args.markdown, len(converted)))

    if findings:
        print('\n%d finding(s) for a person to resolve:' % len(findings), file=sys.stderr)
        for f in findings:
            print('  %s' % f, file=sys.stderr)
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
