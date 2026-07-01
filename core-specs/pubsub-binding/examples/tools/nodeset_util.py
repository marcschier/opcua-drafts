#!/usr/bin/env python3
"""Minimal multi-NodeSet reader + type-instance-declaration walker.

Loads a set of UANodeSet2 files, normalises every NodeId to a (namespaceUri, id)
key, and walks the instance declarations of an ObjectType (following HasComponent/
HasProperty/HasAddIn into typed sub-objects and inherited members) to enumerate the
bindable Variables/Methods with their type-level RelativePath, BrowseName, DataType,
TypeDefinition and ModellingRule.

Used by build_bindings.py and the analysis helpers. Pure stdlib.
"""
import os
import xml.etree.ElementTree as ET

NS = "{http://opcfoundation.org/UA/2011/03/UANodeSet.xsd}"
UA = "http://opcfoundation.org/UA/"

# Base reference-type / modelling-rule identifiers (namespace 0)
HAS_COMPONENT = (UA, 47)
HAS_PROPERTY = (UA, 46)
HAS_SUBTYPE = (UA, 45)
HAS_TYPEDEF = (UA, 40)
HAS_MODELLINGRULE = (UA, 37)
ORGANIZES = (UA, 35)
HAS_INTERFACE = (UA, 17603)
HAS_ADDIN = (UA, 17604)
MR = {(UA, 78): "Mandatory", (UA, 80): "Optional",
      (UA, 11508): "MandatoryPlaceholder", (UA, 11510): "OptionalPlaceholder",
      (UA, 83): "ExposesItsArray"}
HIERARCHICAL_INTO = {HAS_COMPONENT, HAS_PROPERTY, HAS_ADDIN, ORGANIZES}


def _parse_nodeid(s, file_ns):
    """'ns=2;i=1052' | 'i=58' -> (uri, int)."""
    idx = 0
    ident = s
    if s.startswith("ns="):
        semi = s.index(";")
        idx = int(s[3:semi])
        ident = s[semi + 1:]
    if not ident.startswith("i="):
        # string/guid identifiers are not used for the structural nodes we walk
        return (file_ns[idx] if idx < len(file_ns) else str(idx), ident)
    return (file_ns[idx] if idx < len(file_ns) else str(idx), int(ident[2:]))


class Node:
    __slots__ = ("key", "cls", "bn_ns", "bn_name", "datatype", "valuerank",
                 "parent", "refs", "file_ns")

    def __init__(self):
        self.refs = []            # list of (reftype_key, target_key, forward)
        self.datatype = None
        self.valuerank = None
        self.parent = None
        self.file_ns = None


class NodeSetDB:
    def __init__(self):
        self.nodes = {}           # key -> Node
        self.uris = set([UA])

    def load(self, path):
        root = ET.parse(path).getroot()
        file_ns = [UA]
        for u in root.iter(NS + "Uri"):
            file_ns.append(u.text)
            self.uris.add(u.text)
        aliases = {}
        for al in root.iter(NS + "Alias"):
            aliases[al.get("Alias")] = al.text

        def resolve(ref):
            return _parse_nodeid(aliases.get(ref, ref), file_ns)

        for el in root:
            tag = el.tag.replace(NS, "")
            if not tag.startswith("UA"):
                continue
            nid = el.get("NodeId")
            if nid is None:
                continue
            n = Node()
            n.key = _parse_nodeid(nid, file_ns)
            n.cls = tag
            n.file_ns = file_ns
            bn = el.get("BrowseName", "")
            if ":" in bn:
                i, name = bn.split(":", 1)
                n.bn_ns = file_ns[int(i)] if int(i) < len(file_ns) else UA
                n.bn_name = name
            else:
                n.bn_ns, n.bn_name = UA, bn
            n.datatype = el.get("DataType")
            if n.datatype:
                n.datatype = resolve(n.datatype)
            n.valuerank = el.get("ValueRank")
            p = el.get("ParentNodeId")
            n.parent = _parse_nodeid(p, file_ns) if p else None
            refs = el.find(NS + "References")
            if refs is not None:
                for r in refs:
                    rt = resolve(r.get("ReferenceType"))
                    tgt = resolve(r.text)
                    fwd = r.get("IsForward", "true") != "false"
                    n.refs.append((rt, tgt, fwd))
            # last definition wins is fine; nodes are unique per key across files
            self.nodes[n.key] = n
        return self

    # -- helpers ------------------------------------------------------------
    def get(self, key):
        return self.nodes.get(key)

    def modelling_rule(self, key):
        n = self.get(key)
        if not n:
            return None
        for rt, tgt, fwd in n.refs:
            if rt == HAS_MODELLINGRULE and fwd:
                return MR.get(tgt)
        return None

    def type_definition(self, key):
        n = self.get(key)
        if not n:
            return None
        for rt, tgt, fwd in n.refs:
            if rt == HAS_TYPEDEF and fwd:
                return tgt
        return None

    def supertype(self, key):
        n = self.get(key)
        if not n:
            return None
        for rt, tgt, fwd in n.refs:
            if rt == HAS_SUBTYPE and not fwd:
                return tgt
        return None

    def _forward_children(self, key):
        n = self.get(key)
        if not n:
            return
        for rt, tgt, fwd in n.refs:
            if fwd and rt in HIERARCHICAL_INTO:
                yield rt, tgt

    def instance_declarations(self, type_key, include_inherited=True):
        """Direct instance declarations of a type, optionally incl. inherited,
        de-duplicated by BrowseName (subtype overrides supertype)."""
        seen = {}
        chain = []
        k = type_key
        depth = 0
        while k and depth < 20:
            chain.append(k)
            if not include_inherited:
                break
            k = self.supertype(k)
            depth += 1
        # walk from most-derived to base so derived wins
        for tk in chain:
            for rt, tgt in self._forward_children(tk):
                child = self.get(tgt)
                if not child:
                    continue
                bnkey = (child.bn_ns, child.bn_name)
                if bnkey not in seen:
                    seen[bnkey] = (tgt, tk)
        return seen  # {(bn_ns,bn_name): (child_key, declaring_type_key)}

    def _decl_children(self, key, is_type):
        """Instance-declaration children under key, keyed by (bn_ns, bn_name).
        For a type: its (inherited) instance declarations. For an instance node:
        the merge of its TypeDefinition's declarations and its own inline forward
        children (the inline ones override)."""
        result = {}
        if is_type:
            for bnk, (ckey, _dtk) in self.instance_declarations(key).items():
                result[bnk] = ckey
        else:
            td = self.type_definition(key)
            if td:
                for bnk, (ckey, _dtk) in self.instance_declarations(td).items():
                    result[bnk] = ckey
            for _rt, tgt in self._forward_children(key):
                c = self.get(tgt)
                if c:
                    result[(c.bn_ns, c.bn_name)] = tgt
        return result

    def walk(self, key, max_depth=8, is_type=True, _path=(), _pk=frozenset()):
        """Yield dicts for every Variable/Method instance declaration reachable
        from a type (or instance) key, with RelativePath segments + metadata."""
        if max_depth < 0 or key in _pk:
            return
        _pk = _pk | {key}
        for (bn_ns, bn_name), ckey in self._decl_children(key, is_type).items():
            child = self.get(ckey)
            if not child:
                continue
            seg = {"ns": bn_ns, "name": bn_name}
            path = _path + (seg,)
            rec = {
                "cls": child.cls, "bn_ns": bn_ns, "bn_name": bn_name,
                "path": path, "datatype": child.datatype, "valuerank": child.valuerank,
                "modelling_rule": self.modelling_rule(ckey),
                "typedef": self.type_definition(ckey), "key": ckey,
            }
            if child.cls in ("UAVariable", "UAMethod"):
                yield rec
            if child.cls in ("UAObject", "UAVariable"):
                yield from self.walk(ckey, max_depth - 1, False, path, _pk)


def rel_path(path, ns_prefix):
    """Render RelativePath text using ns_prefix: uri -> short index string."""
    out = ""
    for seg in path:
        pfx = ns_prefix.get(seg["ns"], "?")
        out += f"/{pfx}:{seg['name']}"
    return out


if __name__ == "__main__":
    import sys
    db = NodeSetDB()
    for p in sys.argv[2:]:
        db.load(p)
    root = None
    for k, n in db.nodes.items():
        if n.cls == "UAObjectType" and n.bn_name == sys.argv[1]:
            root = k
    print("root:", root)
    if root:
        for rec in db.walk(root, max_depth=5):
            if rec["cls"] == "UAVariable":
                dt = rec["datatype"][1] if rec["datatype"] else "?"
                print(f'{rec["modelling_rule"] or "-":20} '
                      f'{"/".join(s["name"] for s in rec["path"]):55} dt={dt}')
