#!/usr/bin/env python3
"""Check that every section reference in a specification resolves to a real clause.

    python .github/scripts/check_section_refs.py

Restructuring a specification renumbers its clauses, and a stale `§5.15` is invisible
to a spell-checker, a link checker and a reader who does not happen to follow it. This
walks every markdown document, collects the clause numbers its headings declare, and
reports any `§` reference that names a clause the document does not have.

References that name another document explicitly (`Part 1 §7.11`, `Bindings spec §7.4.2`)
are resolved against that document when it can be located, and skipped otherwise.
"""

import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

HEADING_RE = re.compile(r'^#{2,6}\s+(?:Annex\s+([A-Z])\b|([0-9A-Z](?:\.[0-9]+)*))\s')
REF_RE = re.compile(r'(?P<qualifier>.{0,44})§\s*(?P<number>[0-9A-Z](?:\.[0-9]+)*)')
FENCE_RE = re.compile(r'^```')

# A reference qualified by another standard is that standard's clause, not ours.
EXTERNAL_QUALIFIERS = re.compile(
    r'(OPC\s*1\d{4}|OPC\s*\d{5}|IEC\s*\d+|Part\s*\d+\b(?!\s*§?\s*$)|xRegistry|AOUSD'
    r'|Core Specification|core spec|RFC\s*\d+|W3C)', re.IGNORECASE)

# Documents that are cited by name from their siblings.
NAMED_DOCUMENTS = {
    'part 1': 'metaverse-specs/openusd-binding/OPC-UA-OpenUSD-Bindings.md',
    'bindings spec': 'metaverse-specs/openusd-binding/OPC-UA-OpenUSD-Bindings.md',
    'part 2': 'metaverse-specs/openusd-scene/OPC-UA-OpenUSD-Scene-Materialization.md',
}

SKIP_DIRS = {'.git', 'node_modules', '__pycache__'}

# A changelog records the numbering of the release it describes, and a generated model
# reference is not prose; neither is a place to chase a renumbering.
SKIP_FILES = ('CHANGELOG.md', 'model-reference.md')


def clause_numbers(text):
    """Every clause number a document declares, including annex letters."""
    numbers = set()
    in_fence = False
    for line in text.splitlines():
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = HEADING_RE.match(line)
        if not m:
            continue
        numbers.add(m.group(1) or m.group(2))
    return numbers


def references(text):
    in_fence = False
    for lineno, line in enumerate(text.splitlines(), 1):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for m in REF_RE.finditer(line):
            qualifier = m.group('qualifier') or ''
            before = line[:m.start('number')]
            if EXTERNAL_QUALIFIERS.search(before) and not _names_sibling(qualifier):
                continue
            yield lineno, qualifier.strip().lower(), m.group('number')


def _names_sibling(qualifier):
    low = qualifier.lower()
    return any(low.rstrip().endswith(name) for name in NAMED_DOCUMENTS)


def markdown_files():
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            if name.endswith('.md') and name not in SKIP_FILES:
                yield os.path.join(base, name)


def main():
    cache = {}

    def numbers_for(path):
        if path not in cache:
            with open(path, encoding='utf-8') as f:
                cache[path] = clause_numbers(f.read())
        return cache[path]

    def owning_spec(path):
        """A README or addendum has no clauses of its own; its `§` means its spec."""
        folder = os.path.dirname(path)
        for candidate_dir in (folder, os.path.dirname(folder)):
            for name in sorted(os.listdir(candidate_dir)):
                if not name.startswith('OPC-UA-') or not name.endswith('.md'):
                    continue
                candidate = os.path.join(candidate_dir, name)
                if candidate != path and len(numbers_for(candidate)) > 3:
                    return candidate
        return None

    problems = 0
    checked = 0
    for path in sorted(markdown_files()):
        with open(path, encoding='utf-8') as f:
            text = f.read()
        own = numbers_for(path)
        default_target = path if len(own) > 3 else owning_spec(path)
        if default_target is None:
            continue
        checked += 1
        for lineno, qualifier, number in references(text):
            targets = [default_target]
            if default_target != path:
                targets.insert(0, path)
            spec = owning_spec(path)
            if spec and spec not in targets:
                targets.append(spec)
            for name, rel in NAMED_DOCUMENTS.items():
                if qualifier.endswith(name):
                    candidate = os.path.join(ROOT, rel)
                    if os.path.exists(candidate):
                        targets = [candidate]
                    break
            if any(number in numbers_for(t) for t in targets if t):
                continue
            rel = os.path.relpath(path, ROOT).replace('\\', '/')
            tgt = os.path.relpath(targets[0], ROOT).replace('\\', '/')
            where = 'this document' if targets[0] == path else tgt
            print('%s:%d: \u00a7%s does not resolve to a clause of %s'
                  % (rel, lineno, number, where))
            problems += 1

    print('checked %d document(s), %d unresolved reference(s)' % (checked, problems))
    return 1 if problems else 0


if __name__ == '__main__':
    raise SystemExit(main())
