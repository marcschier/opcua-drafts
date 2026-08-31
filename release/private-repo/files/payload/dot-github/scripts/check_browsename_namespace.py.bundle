#!/usr/bin/env python3
"""Check that standard OPC UA BrowseNames are not qualified into a model namespace.

    python .github/scripts/check_browsename_namespace.py

`InputArguments`, `OutputArguments`, `Default Binary` and the rest below are defined by
the core OPC UA specifications and live in **namespace 0**. A NodeSet that qualifies one
of them into its own namespace — `BrowseName="1:InputArguments"` — is not merely untidy:
a stack resolving a Method's signature looks for the child Property named
`InputArguments` *in namespace 0*, does not find it, concludes the Method takes no
arguments, and rejects every real call with `Bad_TooManyArguments`. The Method is
uncallable and browsing cannot discover its signature either.

That defect shipped in three models at once, because the generators apply the model's
namespace prefix to every BrowseName unless told otherwise, so it is a default rather
than a typo and it reappears with the next Method someone adds. This check is
deliberately **generator-agnostic**: it reads the committed NodeSets, so it also covers
hand-authored files and any model added later.

The list below is the guarded set, not the whole of namespace 0. It holds the standard
BrowseNames a companion model actually emits as children of its own nodes — the ones a
model is therefore in a position to get wrong. Add to it rather than widening the check
to all of namespace 0, which would flag legitimate model-defined names that happen to
collide with an unrelated core node.
"""

import os
import re
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

NS = '{http://opcfoundation.org/UA/2011/03/UANodeSet.xsd}'

# Standard BrowseNames a companion model emits beneath its own nodes. Each lives in
# namespace 0, so each must be written unprefixed.
STANDARD_NAMES = {
    # Method signatures — OPC 10000-3 §6.6, the case that makes a Method uncallable.
    'InputArguments',
    'OutputArguments',
    # DataTypeEncodings — OPC 10000-3 §8.49. Tooling that resolves an encoding by
    # BrowseName cannot find a prefixed one.
    'Default Binary',
    'Default XML',
    'Default JSON',
    # Enumeration and OptionSet metadata — OPC 10000-3 §8.40, §8.44.
    'EnumStrings',
    'EnumValues',
    'OptionSetValues',
    # Well-known Properties of type and instance nodes — OPC 10000-3, OPC 10000-5.
    'NodeVersion',
    'Icon',
    'NamingRule',
    'InstanceDeclaration',
}

SKIP_DIRS = {'.git', 'node_modules', '__pycache__', 'ref',
             # Vendored as a submodule: a separate repository with its own copy of this
             # check and its own CI. Scanning it here would report findings this repo
             # cannot fix and would go red on a submodule bump.
             'spec-drafts'}

# A prefixed BrowseName: "<index>:<name>". An unprefixed one is already namespace 0.
PREFIXED_RE = re.compile(r'^(\d+):(.+)$')


def nodesets():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in sorted(filenames):
            if fn.endswith('.NodeSet2.xml'):
                yield os.path.join(dirpath, fn)


def findings(path):
    """Yield (line-ish node id, browse name) for each guarded name that is prefixed."""
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        return [(None, f'XML parse error: {exc}')]
    out = []
    for node in root:
        if not node.tag.startswith(NS):
            continue
        bn = node.get('BrowseName')
        if not bn:
            continue
        m = PREFIXED_RE.match(bn)
        if not m:
            continue
        index, name = m.group(1), m.group(2)
        if index == '0':
            # Explicitly namespace 0 already; unusual spelling but correct.
            continue
        if name in STANDARD_NAMES:
            out.append((node.get('NodeId'), bn))
    return out


def main():
    total_files = 0
    total_bad = 0
    for path in nodesets():
        total_files += 1
        bad = findings(path)
        if not bad:
            continue
        rel = os.path.relpath(path, ROOT).replace('\\', '/')
        for nid, bn in bad:
            total_bad += 1
            if nid is None:
                print(f'{rel}: {bn}')
            else:
                print(f'{rel}: {nid} BrowseName="{bn}" — '
                      f'"{bn.split(":", 1)[1]}" is a standard namespace-0 BrowseName '
                      f'and must be written without a namespace prefix')
    print(f'checked {total_files} NodeSet(s), {total_bad} misnamespaced BrowseName(s)')
    if total_bad:
        print('A standard BrowseName qualified into a model namespace is not cosmetic: '
              'a Method whose InputArguments sits in the model namespace is treated as '
              'taking no arguments and every call is rejected with Bad_TooManyArguments.')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
