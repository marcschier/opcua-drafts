"""AddressSpace figures checked against the UANodeSet they claim to draw.

A figure in the OPC UA graphical notation is a claim about the model: that a Node exists,
that it has a given NodeClass, that a Reference of a given type runs between two Nodes.
Prose drifts from a model quietly, and a picture drifts even more quietly, because nothing
about a diagram looks wrong until a reader tries to implement it.

So every AddressSpace figure opts in with a directive above its fence:

    <!-- model-figure: root=WoTAssetConnectionManagementType require=mandatory
         external=Objects,BaseObjectType -->

and this module re-derives the answer from the NodeSet. It never reads the specification's
own tables or annexes: checking a figure against prose that the same author wrote proves
only that the author was consistent, not that either matches the model.

`external` is deliberately explicit. Nodes from a required model are not in this NodeSet
and cannot be verified here, so the author has to name them; otherwise a typo in a Node
name would be silently accepted as "probably from the base namespace".
"""

import html
import os
import re

from . import mermaid_pptx
from . import nodeset_tables
from .nodeset_tables import NODE_CLASS, Model

DIRECTIVE_RE = re.compile(r'<!--\s*model-figure:(?P<body>.*?)-->', re.S)
FENCE_RE = re.compile(r'^\s*```mermaid\s*$')
FENCE_END_RE = re.compile(r'^\s*```\s*$')

MANDATORY_RULE = 'i=78'
PLACEHOLDER_RULES = {'i=11508', 'i=11510'}

# A declared `:::class` and the NodeClass it asserts.
CLASS_TO_NODECLASS = {
    'object': 'Object',
    'variable': 'Variable',
    'method': 'Method',
    'objecttype': 'ObjectType',
    'variabletype': 'VariableType',
    'referencetype': 'ReferenceType',
    'datatype': 'DataType',
    # An EventType is an ObjectType in the NodeSet; the class only says how to draw it.
    'eventtype': 'ObjectType',
}
# Classes that style rather than assert a NodeClass.
MODIFIER_CLASSES = {'abstract', 'placeholder', 'view'}


class Figure:
    def __init__(self, directive, source, line):
        self.directive = directive
        self.source = source
        self.line = line

    @property
    def root(self):
        return self.directive.get('root')

    @property
    def externals(self):
        raw = self.directive.get('external', '')
        return {_bare(p) for p in raw.replace(';', ',').split(',') if p.strip()}

    @property
    def require(self):
        return self.directive.get('require', 'none')


def _bare(name):
    """A BrowseName as the model stores it: entities decoded, no namespace index.

    Only a numeric prefix is stripped. A NodeId such as `ns=2;i=1` also contains a colon,
    and treating that as a namespace prefix turned the root reference into a name that
    matched nothing. The angle brackets of a placeholder are **kept**: `<WoTAssetName>` is
    the BrowseName the NodeSet actually carries, not decoration around one.
    """
    name = html.unescape((name or '').strip())
    head, sep, tail = name.partition(':')
    if sep and head.isdigit():
        name = tail
    return name.strip()


def _is_placeholder_label(label):
    label = html.unescape((label or '').strip())
    return label.startswith('<') and label.endswith('>')


def extract_figures(md_path):
    """Every mermaid block preceded by a model-figure directive."""
    with open(md_path, encoding='utf-8') as fh:
        lines = fh.read().splitlines()
    figures = []
    pending = None
    i = 0
    while i < len(lines):
        line = lines[i]
        m = DIRECTIVE_RE.search(line)
        if m:
            pending = _parse_directive(m.group('body'))
            i += 1
            continue
        if FENCE_RE.match(line):
            start = i + 1
            j = start
            while j < len(lines) and not FENCE_END_RE.match(lines[j]):
                j += 1
            if pending is not None:
                figures.append(Figure(pending, '\n'.join(lines[start:j]), start))
                pending = None
            i = j + 1
            continue
        if line.strip() and pending is not None and not line.strip().startswith('<!--'):
            # A directive must sit immediately above its diagram. Letting prose come
            # between them would attach a figure's claims to the wrong picture.
            raise ValueError('model-figure directive at line %d is not followed by a '
                             'mermaid block' % i)
        i += 1
    return figures


def _parse_directive(body):
    out = {}
    for token in body.replace('\n', ' ').split():
        if '=' not in token:
            raise ValueError('model-figure directive token %r is not key=value' % token)
        k, _, v = token.partition('=')
        out[k.strip()] = v.strip()
    if 'root' not in out:
        raise ValueError('model-figure directive has no root=')
    return out


def _ref_type_name(model, raw):
    """A reference type as a name, whether the NodeSet wrote an alias or a NodeId."""
    if raw in model.aliases:
        return raw
    for alias, nid in model.aliases.items():
        if nid == raw:
            return alias
    node = model.nodes.get(raw)
    if node is not None:
        return node.name
    return raw


def _modelling_rule(model, node):
    for ref_type, target, forward in node.refs:
        if forward and _ref_type_name(model, ref_type) == 'HasModellingRule':
            return target
    return None


def _edge_reference(edge):
    """The ReferenceType an edge asserts."""
    if edge.label:
        return edge.label.strip()
    if edge.thick:
        return 'HasTypeDefinition'
    return 'HasComponent'


def _has_reference(model, src, dst, ref_name):
    """Whether the model really carries this reference, in this direction."""
    for ref_type, target, forward in src.refs:
        if _ref_type_name(model, ref_type) != ref_name:
            continue
        if forward and target == dst.node_id:
            return True
    for ref_type, target, forward in dst.refs:
        if _ref_type_name(model, ref_type) != ref_name:
            continue
        if not forward and target == src.node_id:
            return True
    return False


def _external_reference(model, node, ref_name, other_label, node_is_source):
    """Check an edge with one end in a required model, from the end that is in this one.

    An `external=` Node is never resolved, so an edge touching one used to be skipped
    altogether — and every figure anchors its types on a base-namespace supertype, so the
    unchecked edges were the majority. A NodeSet cannot confirm what it does not contain,
    but it does carry its own half of the reference: the inverse `HasSubtype` sits on the
    subtype and the inverse `HasComponent` on the child, both naming a NodeId outside this
    model. That is enough to verify the ReferenceType and its direction, which is what the
    figure actually asserts.

    Where the far NodeId is a well-known base-namespace Node, its BrowseName is checked
    too. Where it is not, the reference is accepted on type and direction alone rather
    than guessed at — returning None to say so.
    """
    for ref_type, target, forward in node.refs:
        if _ref_type_name(model, ref_type) != ref_name:
            continue
        if forward != node_is_source or target in model.nodes:
            continue
        known = nodeset_tables.STANDARD_NODES.get(target)
        if known is None or known == _bare(other_label):
            return True
    return False


def check_figure(model, fig):
    """Errors this figure makes about the model. Empty means it is accurate."""
    errors = []
    where = 'figure at line %d (root=%s)' % (fig.line, fig.root)
    try:
        graph = mermaid_pptx.parse(fig.source)
    except ValueError as exc:
        return ['%s: %s' % (where, exc)]

    resolved, errors = _resolve(model, fig, graph, where)
    errors.extend(_check_node_claims(model, fig, graph, resolved, where))

    if fig.require == 'mandatory':
        errors.extend(_check_mandatory(model, fig, resolved, where))
    elif fig.require not in ('none', ''):
        errors.append('%s: unknown require=%s' % (where, fig.require))
    return errors


def _resolve(model, fig, graph, where):
    """Map figure nodes onto model Nodes by walking the edges from the root.

    Resolution cannot go by BrowseName alone: this model has 46 names borne by more than
    one Node — `CreateAsset` exists on the type *and* on the well-known instance, and so
    do most members. Picking the first match would check an edge against the wrong Node
    and report success, which is worse than not checking it. So a child is resolved as
    the Node its already-resolved parent actually references, which is also what makes
    the edge assertion meaningful.
    """
    errors = []
    resolved = {}
    externals = fig.externals

    root_node = _lookup_unique(model, fig.root)
    if isinstance(root_node, str):
        return {}, ['%s: %s' % (where, root_node)]
    root_ids = [nid for nid in graph.order
                if _bare(graph.nodes[nid].label) == root_node.name]
    if not root_ids:
        return {}, ['%s: the root %s does not appear in the figure'
                    % (where, root_node.name)]
    resolved[root_ids[0]] = root_node

    # Alternate two passes until neither makes progress. The graph walk resolves a child
    # through the parent that references it; the name pass picks up a node that no
    # resolved neighbour reaches — typically one hanging off an `external=` Node, such as
    # a type whose only drawn relation is HasSubtype from a base-namespace supertype.
    # Running the name pass only once, after the walk, left every node *below* such a type
    # unresolvable, and they were then reported as missing references that plainly exist.
    progress = True
    while progress:
        progress = _walk_edges(model, graph, resolved, externals, errors, where)
        progress = _name_pass(model, graph, resolved, externals) or progress

    for nid in graph.order:
        label = graph.nodes[nid].label
        if nid in resolved or _bare(label) in externals:
            continue
        # If the node hangs off one that did resolve, the honest diagnosis is that the
        # asserted reference does not exist — not that the BrowseName is ambiguous. The
        # global fallback would report the ambiguity and send the author to fix the wrong
        # thing.
        via = [(e, resolved[e.src] if e.src in resolved else resolved[e.dst])
               for e in graph.edges
               if (e.src == nid and e.dst in resolved) or (e.dst == nid and e.src in resolved)]
        if via:
            for e, other in via:
                errors.append('%s: no %s reference between %s and %r in the model'
                              % (where, _edge_reference(e), other.name, label))
            continue
        # Neither pass could place it and nothing resolved touches it.
        found = _lookup_unique(model, label)
        errors.append('%s: %s' % (where, found if isinstance(found, str)
                                  else '%r could not be placed in the model' % label))

    # Every edge whose endpoints both resolved must be a real reference.
    for e in graph.edges:
        src, dst = resolved.get(e.src), resolved.get(e.dst)
        ref = _edge_reference(e)
        if src is not None and dst is not None:
            if not _has_reference(model, src, dst, ref):
                errors.append('%s: no %s reference from %s to %s in the model'
                              % (where, ref, src.name, dst.name))
            continue
        # One end is in a required model. Check the half this NodeSet does carry.
        for near, far, near_is_source in ((src, e.dst, True), (dst, e.src, False)):
            if near is None:
                continue
            far_label = graph.nodes[far].label
            if _bare(far_label) not in externals:
                continue
            if not _external_reference(model, near, ref, far_label, near_is_source):
                errors.append('%s: no %s reference between %s and the external Node %r '
                              'in the model' % (where, ref, near.name, far_label))
    return resolved, errors


def _walk_edges(model, graph, resolved, externals, errors, where):
    """Resolve each unresolved node through a neighbour that is already resolved."""
    progress = False
    for e in graph.edges:
        ref = _edge_reference(e)
        for a, b, forward in ((e.src, e.dst, True), (e.dst, e.src, False)):
            if a not in resolved or b in resolved:
                continue
            label = graph.nodes[b].label
            if _bare(label) in externals:
                continue
            cands = _related(model, resolved[a], ref, _bare(label), forward)
            if len(cands) == 1:
                resolved[b] = cands[0]
                progress = True
            elif len(cands) > 1:
                errors.append('%s: %r is reached by more than one %s reference from '
                              '%s; the figure cannot say which Node it means'
                              % (where, label, ref, resolved[a].name))
                resolved[b] = cands[0]
                progress = True
    return progress


def _name_pass(model, graph, resolved, externals):
    """Resolve nodes no resolved neighbour reaches, where the BrowseName is unambiguous.

    Errors are deliberately not raised here. A node that stays unresolved is reported once,
    after both passes have stopped, so that the message names the reference the figure got
    wrong rather than the name lookup that came after it.
    """
    progress = False
    for nid in graph.order:
        label = graph.nodes[nid].label
        if nid in resolved or _bare(label) in externals:
            continue
        found = _lookup_unique(model, label)
        if not isinstance(found, str):
            resolved[nid] = found
            progress = True
    return progress


def _related(model, node, ref_name, other_name, forward):
    """Candidates for the other end of a reference, by the same rule the edge check uses.

    A NodeSet may write a reference on either end: `HasTypeDefinition` sits on the
    instance and `HasSubtype` on the child, so neither "scan the source's forward refs"
    nor "scan the target's inverse refs" finds both. Resolution and checking therefore
    share one definition of existence, or a figure could resolve and then fail its own
    edge check on a reference that is plainly there.
    """
    out = []
    for cand in model.nodes.values():
        if cand.name != other_name:
            continue
        ok = (_has_reference(model, node, cand, ref_name) if forward
              else _has_reference(model, cand, node, ref_name))
        if ok:
            out.append(cand)
    return out


def _lookup_unique(model, name):
    """A Node by BrowseName or NodeId; a message when that is not unambiguous."""
    raw = (name or '').strip()
    if raw in model.nodes:
        return model.nodes[raw]
    bare = _bare(raw)
    matches = [n for n in model.nodes.values() if n.name == bare]
    if not matches:
        return ('%r is not a Node in the model and is not declared external=' % name)
    if len(matches) > 1:
        return ('%r names %d Nodes in the model; give the NodeId instead of the '
                'BrowseName' % (name, len(matches)))
    return matches[0]


def _check_node_claims(model, fig, graph, resolved, where):
    errors = []
    for nid in graph.order:
        n = graph.nodes[nid]
        node = resolved.get(nid)
        if node is None:
            continue

        declared = [c for c in n.cls if c not in MODIFIER_CLASSES]
        if not declared:
            errors.append('%s: %r declares no NodeClass' % (where, n.label))
        else:
            want = CLASS_TO_NODECLASS.get(declared[0])
            actual = NODE_CLASS.get(node.tag)
            if want != actual:
                errors.append('%s: %r is drawn as %s but the model declares %s'
                              % (where, n.label, declared[0], actual))

        if node.abstract != ('abstract' in n.cls):
            errors.append('%s: %r %s marked abstract but the model says IsAbstract=%s'
                          % (where, n.label,
                             'is' if 'abstract' in n.cls else 'is not',
                             str(node.abstract).lower()))

        rule = _modelling_rule(model, node)
        is_ph = rule in PLACEHOLDER_RULES
        if is_ph != _is_placeholder_label(n.label):
            errors.append('%s: %r %s written as a <placeholder> but its ModellingRule '
                          'is %s' % (where, n.label,
                                     'is' if _is_placeholder_label(n.label) else 'is not',
                                     rule or 'none'))
    return errors


def _check_mandatory(model, fig, resolved, where):
    root = _lookup_unique(model, fig.root)
    if isinstance(root, str):
        return ['%s: %s' % (where, root)]
    drawn = {n.node_id for n in resolved.values()}
    missing = []
    for ref_type, target, forward in root.refs:
        if not forward:
            continue
        child = model.nodes.get(target)
        if child is None:
            continue
        if _modelling_rule(model, child) != MANDATORY_RULE:
            continue
        if child.node_id not in drawn:
            missing.append(child.name)
    return ['%s: Mandatory member %s is missing from the figure' % (where, name)
            for name in sorted(missing)]


def check_markdown(md_path, nodeset_path):
    """Every model figure in one document, against one NodeSet."""
    if not os.path.exists(md_path) or not os.path.exists(nodeset_path):
        return ['model figures: %s or %s not found' % (md_path, nodeset_path)]
    model = Model(nodeset_path)
    errors = []
    for fig in extract_figures(md_path):
        errors.extend(check_figure(model, fig))
    return errors
