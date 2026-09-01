#!/usr/bin/env python3
"""Check that every section reference in a specification resolves to a real clause.

    python .github/scripts/check_section_refs.py

Restructuring a specification renumbers its clauses, and a stale `§5.15` is invisible
to a spell-checker, a link checker and a reader who does not happen to follow it. This
walks every markdown document, collects the clause numbers its headings declare, and
reports any `§` reference that names a clause the document does not have.

References that name another document explicitly (`Part 1 §7.11`, `Bindings spec §7.4.2`)
are resolved against that document when it can be located, and references qualified by
another standard (`OPC 10000-3 …§4.10.3`, `Schema Registry §7`) are skipped.
SpecificationPublisher headings are numbered from their `{#sec-...}` hierarchy, and annex
letters are read from `{#anx-a ...}` anchors.

Qualifiers are matched in a **bounded window** around the reference. A document name
elsewhere in the same sentence must not mask a genuine stale self-reference, which is
exactly the defect this exists to catch. The cost is that a reference whose qualifier sits
far away cannot be classified, so only the trees in `STRICT_PREFIXES` fail the check;
elsewhere findings are printed as advisory notes.
"""

import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

HEADING_RE = re.compile(r'^#{2,6}\s+(?:Annex\s+([A-Z])\b|([0-9]+(?:\.[0-9]+)*|[A-Z](?:\.[0-9]+)+))\s')
REF_RE = re.compile(r'(?P<qualifier>.{0,44})§\s*(?P<number>[0-9]+(?:\.[0-9]+)*|[A-Z](?:\.[0-9]+)*)')

# A clause range — "§7.10–7.10.2" — whose second endpoint carries no § of its own.
RANGE_AFTER = re.compile(r'^\s*[\u2013\u2014-]\s*([0-9]+(?:\.[0-9]+)*)')

# A bare annex citation: "see Annex D", "(Annex F)". Renumbering moves these too, and
# nothing else checks them.
ANNEX_REF_RE = re.compile(r'\bAnnex\s+([A-Z])\b')
FENCE_RE = re.compile(r'^```')

# A reference qualified by another standard is that standard's clause, not ours. These
# are matched in a short window immediately around the reference: a document name
# elsewhere in the same sentence must not mask a genuine self-reference.
WINDOW = 70
LINK_WINDOW = 130

EXTERNAL_BEFORE = re.compile(
    r'(OPC\s*1\d{4}|OPC\s*\d{5}|IEC\s*\d+|AOUSD|RFC\s*\d+|W3C'
    r'|Regulation\s*\(EU\)|EU AI Act|Machinery Regulation'
    r'|Core Specification|core spec'
    r'|\bthat specification\b'
    r'|\bbase\s*$'
    r'|\*[^*]*OPC UA[^*]*\*'
    r'|`[^`]*\.md`'
    r')', re.IGNORECASE)

# The qualifier sometimes follows the reference: "(§4.2 of the base)", "§8 of that
# specification".
EXTERNAL_AFTER = re.compile(
    r'^[^.]{0,40}?\bof (?:the base|that specification|\[|\*)', re.IGNORECASE)

# A markdown link to another document just before the reference names that document.
LINK_BEFORE = re.compile(r'\[[^\]]*\]\([^)]*\)[^§]{0,20}$')

# "Schema Registry §7", "WoT Connectivity §7.3", "Avro Part 14 §8.1".
NAMED_SPEC_BEFORE = re.compile(
    r'(?<!\bPart )[A-Z][A-Za-z]+(?: [A-Z][A-Za-z0-9]+)+(?:\s+\d+)?[\s,(]*$')

# A chained list — "Schema Registry §7, §8" — carries the qualifier of its first member.
CHAINED_BEFORE = re.compile(r'§\s*[0-9A-Z](?:\.[0-9]+)*\s*(?:,|and|/)\s*$')

# "Part 14 Arrow mapping §7.2.8" names another standard's clause. "Part 1"/"Part 2" name
# this repository's own documents and are resolved before this rule is reached.
PART_NEAR = re.compile(r'\bPart\s+\d{1,3}\b[^§]{0,40}$')

# A bibliography entry — a list item that opens with a markdown link — cites another
# document throughout, however far the clause number sits from the link.
BIBLIOGRAPHY_LINE = re.compile(r'^\s*[-*]\s*\[')

# Documents that are cited by name from their siblings.
NAMED_DOCUMENTS = {
    'part 1': 'metaverse-specs/openusd-binding/OPC-UA-OpenUSD-Bindings.md',
    'bindings spec': 'metaverse-specs/openusd-binding/OPC-UA-OpenUSD-Bindings.md',
    'part 2': 'metaverse-specs/openusd-scene/OPC-UA-OpenUSD-Scene-Materialization.md',
}

SKIP_DIRS = {'.git', 'node_modules', '__pycache__'}

# A changelog records the numbering of the release it describes, and a generated model
# reference is not prose; neither is a place to chase a renumbering.
SKIP_FILES = (
    'CHANGELOG.md',
    'model-reference.md',
    'research.md',
    'OPC-UA-Robot-Intent-Research.md',
)

# Trees where an unresolved reference fails the check. Elsewhere findings are printed
# as advisory notes: a reference whose qualifier sits far from it ("No change to
# OPC 10000-6 §7.2 is required. … Reverse connect (§7.1.3) …") cannot be classified from
# a bounded window, and widening the window is what makes the check miss real defects.
# Opting a tree in is a deliberate act by whoever has verified its references. The private
# repository's spec roots differ from the public draft repository, so set the
# SECTION_REF_STRICT_PREFIXES repository variable to a space-separated list of roots that
# should fail the check. If unset, every unresolved reference is advisory.
_env_strict = os.environ.get('SECTION_REF_STRICT_PREFIXES', '').split()


ATTRIBUTE_ANCHOR_RE = re.compile(r'(?m)^#{2,6}\s+.*\{#(?:sec|anx)-')
ATTRIBUTE_HEADING_RE = re.compile(
    r'^(?P<marks>#{2,6})\s+.*\{#(?P<anchor>(?:sec|anx)-[^\s}]+)[^}]*\}\s*$',
    re.IGNORECASE)


def derives_its_numbers(text):
    """True if this document is written in the OPC UA specification template's dialect.

    A heading carries an anchor rather than a literal number because the renderer derives
    the number. This checker applies the same heading-level sequence so numeric references
    can still be validated before rendering.
    """
    return bool(ATTRIBUTE_ANCHOR_RE.search(text))

STRICT_PREFIXES = tuple(p.strip().rstrip('/').replace('\\', '/') + '/'
                        for p in _env_strict if p.strip())


def clause_numbers(text):
    """Every clause number a document declares, including annex letters."""
    numbers = set()
    section_counters = [0] * 5
    annex_counters = [0] * 5
    annex = None
    annex_level = None
    in_fence = False
    for line in text.splitlines():
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = HEADING_RE.match(line)
        if m:
            numbers.add(m.group(1) or m.group(2))
            continue
        m = ATTRIBUTE_HEADING_RE.match(line)
        if not m:
            continue
        level = len(m.group('marks'))
        anchor = m.group('anchor').lower()
        if anchor.startswith('anx-'):
            suffix = anchor[4:]
            if len(suffix) == 1 and suffix.isalpha():
                annex = suffix.upper()
                annex_level = level
                annex_counters = [0] * 5
                numbers.add(annex)
            continue
        if annex is not None:
            depth = level - annex_level
            if depth <= 0:
                continue
            annex_counters[depth - 1] += 1
            for index in range(depth, len(annex_counters)):
                annex_counters[index] = 0
            numbers.add(annex + '.' + '.'.join(
                str(value) for value in annex_counters[:depth]))
            continue
        depth = level - 2
        if (depth == 0 and section_counters[0] == 1
                and anchor != 'sec-scope'):
            # SpecificationPublisher inserts clauses 2 (Normative references) and
            # 3 (Terms, definitions, symbols and abbreviated terms) from manifest
            # metadata between Scope and the next authored top-level clause.
            section_counters[0] = 4
        else:
            section_counters[depth] += 1
        for index in range(depth + 1, len(section_counters)):
            section_counters[index] = 0
        numbers.add('.'.join(str(value) for value in section_counters[:depth + 1]))
    return numbers


def annex_letters(text):
    """The annex letters a document declares."""
    out = set()
    for line in text.splitlines():
        if not line.startswith('#'):
            continue
        m = re.match(r'^#{2,6}\s+Annex\s+([A-Z])\b', line)
        if m:
            out.add(m.group(1))
            continue
        m = re.search(r'\{#anx-([a-z])(?:\s|})', line, re.IGNORECASE)
        if m:
            out.add(m.group(1).upper())
    return out


def annex_references(text):
    """Bare `Annex X` citations, excluding the headings that declare them."""
    in_fence = False
    for lineno, line in enumerate(text.splitlines(), 1):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence or line.startswith('#'):
            continue
        for m in ANNEX_REF_RE.finditer(line):
            before = line[:m.start()]
            if EXTERNAL_BEFORE.search(before[-WINDOW:]) or BIBLIOGRAPHY_LINE.match(line):
                continue
            yield lineno, before.strip().lower(), m.group(1)


def references(text):
    in_fence = False
    for lineno, line in enumerate(text.splitlines(), 1):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        skipped_here = False
        bibliography = bool(BIBLIOGRAPHY_LINE.match(line))
        for m in REF_RE.finditer(line):
            qualifier = m.group('qualifier') or ''
            before = line[:m.start('number')]
            head = before.rstrip().rstrip('\u00a7').rstrip()
            after = line[m.end('number'):]
            if _names_sibling(qualifier):
                yield lineno, qualifier.strip().lower(), m.group('number')
                continue
            if (bibliography
                    or EXTERNAL_BEFORE.search(head[-WINDOW:])
                    or EXTERNAL_AFTER.match(after)
                    or LINK_BEFORE.search(head[-LINK_WINDOW:])
                    or NAMED_SPEC_BEFORE.search(head[-WINDOW:])
                    or PART_NEAR.search(head[-WINDOW:])
                    or (skipped_here and CHAINED_BEFORE.search(head))):
                skipped_here = True
                continue
            skipped_here = False
            yield lineno, qualifier.strip().lower(), m.group('number')
            # "§7.10–7.10.2": the second endpoint carries no § and would otherwise
            # never be checked, which is how "§7.10–5.14" survived a renumbering.
            rng = RANGE_AFTER.match(after)
            if rng:
                yield lineno, qualifier.strip().lower(), rng.group(1)


def _names_sibling(qualifier):
    low = qualifier.lower()
    return any(low.rstrip().endswith(name) for name in NAMED_DOCUMENTS)


def markdown_files():
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [
            d for d in dirs
            if d not in SKIP_DIRS and not os.path.exists(os.path.join(base, d, '.git'))
        ]
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

    def sibling_specs(path, text=''):
        """The specification documents a bare `§` in this file could reasonably mean.

        A README or an addendum has no clauses of its own, and a multi-part
        specification splits its clauses across sibling files, so a reference is
        resolved against every specification document beside it, one level up, and any
        document this file cites by relative path.
        """
        found = []
        folder = os.path.dirname(path)
        for candidate_dir in (folder, os.path.dirname(folder)):
            if not os.path.isdir(candidate_dir):
                continue
            for name in sorted(os.listdir(candidate_dir)):
                if name != 'spec.md' and (
                        not name.startswith('OPC-UA-') or not name.endswith('.md')):
                    continue
                candidate = os.path.join(candidate_dir, name)
                if candidate != path and len(numbers_for(candidate)) > 3:
                    found.append(candidate)
        for rel in set(re.findall(
                r'[\w./-]*(?:OPC-UA-[\w.-]+|spec)\.md', text)):
            for base in (folder, ROOT):
                candidate = os.path.normpath(os.path.join(base, rel))
                if (os.path.exists(candidate) and candidate != path
                        and candidate not in found
                        and len(numbers_for(candidate)) > 3):
                    found.append(candidate)
                    break
        return found

    def annexes_for(path):
        if ('annex', path) not in cache:
            with open(path, encoding='utf-8') as f:
                cache[('annex', path)] = annex_letters(f.read())
        return cache[('annex', path)]

    problems = 0
    notes = 0
    checked = 0
    for path in sorted(markdown_files()):
        with open(path, encoding='utf-8') as f:
            text = f.read()
        own = numbers_for(path)
        siblings = sibling_specs(path, text)
        if len(own) <= 3 and not siblings:
            continue
        checked += 1
        rel = os.path.relpath(path, ROOT).replace('\\', '/')
        strict = rel.startswith(STRICT_PREFIXES) and not derives_its_numbers(text)

        def resolve(qualifier):
            targets = [path] + siblings
            for name, target_rel in NAMED_DOCUMENTS.items():
                if qualifier.endswith(name):
                    candidate = os.path.join(ROOT, target_rel)
                    if os.path.exists(candidate):
                        return [candidate]
            return targets

        def report(lineno, what, where):
            print('%s%s:%d: %s does not resolve to %s'
                  % ('' if strict else 'note: ', rel, lineno, what, where))

        for lineno, qualifier, number in references(text):
            targets = resolve(qualifier)
            if any(number in numbers_for(t) for t in targets):
                continue
            tgt = os.path.relpath(targets[0], ROOT).replace('\\', '/')
            report(lineno, '\u00a7%s' % number,
                   'a clause of %s' % ('this document' if targets[0] == path else tgt))
            problems, notes = (problems + 1, notes) if strict else (problems, notes + 1)

        for lineno, qualifier, letter in annex_references(text):
            targets = resolve(qualifier)
            if any(letter in annexes_for(t) for t in targets):
                continue
            tgt = os.path.relpath(targets[0], ROOT).replace('\\', '/')
            report(lineno, 'Annex %s' % letter,
                   'an annex of %s' % ('this document' if targets[0] == path else tgt))
            problems, notes = (problems + 1, notes) if strict else (problems, notes + 1)

    print('checked %d document(s), %d unresolved reference(s), %d advisory note(s)'
          % (checked, problems, notes))
    return 1 if problems else 0


if __name__ == '__main__':
    raise SystemExit(main())
