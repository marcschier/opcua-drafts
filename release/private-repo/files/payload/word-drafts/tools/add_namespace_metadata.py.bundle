"""Insert the NamespaceMetadata declaration into a model generator.

OPC 10000-5 5.2.4 has a Server publish the version and publication date of every namespace it
hosts, as a `NamespaceMetadataType` Object under `Server/Namespaces`. None of these models
declared one, so a Client -- and the specification publisher, which states the same facts in
Annex A -- had no way to read them from the model.

The generators all share the same primitives (`add`, `ref`, `T`, `_mid`), so one block works in
every one of them. It goes in immediately after the `PUBDATE` constant, which is both where the
values it needs are defined and late enough that the Nodes are appended last -- so adding them
cannot renumber anything above, which is what makes the change safe to make to a published
model.

A specification that adds Nodes to the base OPC UA namespace rather than owning one is skipped:
the base namespace's metadata belongs to the base model, and a subset declaring it would be
claiming to own what it borrows.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

BASE_NAMESPACE = "http://opcfoundation.org/UA/"

BLOCK = '''

# OPC 10000-5 5.2.4: a Server publishes the version and publication date of every namespace it
# hosts as a NamespaceMetadataType Object under Server/Namespaces. Without one a Client -- and
# the specification publisher, which states the same facts in Annex A -- has no way to read them
# from the model, and has to take them from the file it happens to have been handed.
#
# These Nodes are appended last, so adding them cannot renumber anything above.
Server_Namespaces = "i=11715"
NamespaceMetadataType = "i=11616"


def namespace_metadata(uri, version, pubdate, is_subset=False):
    """Declare this model's namespace metadata, as OPC 10000-5 requires."""
    meta = _mid()
    # The BrowseName is the namespace URI in this model's own namespace; the Properties under
    # it are the base ones, so they keep their namespace-0 BrowseNames.
    add(meta, "UAObject", uri, "NamespaceMetadata", display=uri,
        desc="Metadata for this namespace, as OPC 10000-5 requires a Server to publish it.",
        parent=Server_Namespaces)
    ref(meta, HasTypeDefinition, NamespaceMetadataType)
    ref(meta, HasComponent, Server_Namespaces, forward=False)

    def _prop(name, datatype, xml_type, text):
        nid = _mid()
        add(nid, "UAVariable", name, f"NamespaceMetadata_{name}", parent=T(meta),
            attrs={"DataType": datatype, "ValueRank": "-1"})
        ref(nid, HasTypeDefinition, PropertyType)
        ref(nid, HasProperty, T(meta), forward=False)
        ref(meta, HasProperty, T(nid))
        NODES[nid].value = (
            f'<Value><uax:{xml_type}>{sx.escape(text)}</uax:{xml_type}></Value>')
        return nid

    _prop("NamespaceUri", "i=12", "String", uri)
    _prop("NamespaceVersion", "i=12", "String", version)
    _prop("NamespacePublicationDate", "i=13", "DateTime", pubdate)
    _prop("IsNamespaceSubset", "i=1", "Boolean", "true" if is_subset else "false")
    return meta


namespace_metadata(NAMESPACE, VERSION, PUBDATE)
'''

PUBDATE_RE = re.compile(r'(?m)^PUBDATE\s*=\s*"[^"]*"[^\n]*$')
NAMESPACE_RE = re.compile(r'(?m)^NAMESPACE\s*=\s*"([^"]+)"')


def patch(path: pathlib.Path, write: bool) -> str:
    text = path.read_text(encoding='utf-8')
    if 'def namespace_metadata(' in text:
        return 'already has it'
    ns = NAMESPACE_RE.search(text)
    if not ns:
        return 'no NAMESPACE constant'
    if ns.group(1) == BASE_NAMESPACE:
        return 'adds to the base namespace, so its metadata is not this model\'s to declare'
    m = PUBDATE_RE.search(text)
    if not m:
        return 'no PUBDATE constant to insert after'
    updated = text[:m.end()] + BLOCK + text[m.end():]
    if write:
        path.write_text(updated, encoding='utf-8', newline='\n')
    return 'inserted'


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('generators', nargs='+', type=pathlib.Path)
    ap.add_argument('--write', action='store_true')
    args = ap.parse_args(argv)
    for g in args.generators:
        print('%-64s %s' % (g.as_posix().split('/')[-3], patch(g, args.write)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
