# Proposal — `uav:typeDefinition`

**To:** the *OPC UA — WoT Binding* and *OPC UA — WoT Connectivity* drafts.
**From:** the AAS companion specification work in this repository.
**Status:** proposal, not adopted.

## The gap

A Thing Description projects to an Object. The Object's TypeDefinition comes from the Thing Model
the Thing Description instantiates, so a projection produces the type it generates and nothing else.
There is no term that binds a projected Object to an ObjectType the Server has **already loaded**
from a companion model.

`uav:congruentType` does not close this. It records that a type is structurally congruent with
another, for reconciling two models that describe the same type. It is retained as residue by a
converter and does not produce a `HasTypeDefinition` reference.

## Why it matters

A companion specification that already defines its ObjectTypes — an AAS, a machine tool, a robot —
cannot be projected from a Thing Description onto its own types. The projection produces a parallel
type that resembles the published one, so a Client written against the companion specification does
not recognise the result and the Server cannot claim conformance to it.

Measured over the AAS fixtures, with everything else in the vocabulary doing its job:

| | with the proposed term | published vocabulary only |
|---|---|---|
| nodes produced | 61 of 61 | 61 of 61 |
| NodeIds correct | 61 | 61 |
| BrowseNames correct | 61 | 61 |
| ReferenceTypes correct | 61 | 61 |
| TypeDefinitions correct | 61 | **0** |

Every other fact the vocabulary carries already arrives intact. The type binding is the whole of the
gap, which is why the proposal is one term rather than a mechanism.

## The term

**`uav:typeDefinition`** (string) — the ExpandedNodeId, per §5.1.1, of an ObjectType or VariableType
that the Server has already loaded. It states that the node this document projects to is an instance
of that type.

```jsonc
"@type": ["uav:object"],
"uav:typeDefinition": "nsu=http://opcfoundation.org/UA/I4AAS/;i=1013",
"uav:congruentTypeName": "i4aas:AASSubmodelType"
```

It is instance identity of a *type node*, so a compact model name is a hint and not a substitute; an
author **should** also supply `uav:congruentTypeName` for readability, and the two **shall** resolve
to the same node when both are present.

## Converter behaviour

A vocabulary entry alone is not enough, because the projection is what has to change.

1. On projecting a document that carries `uav:typeDefinition`, a converter **shall** resolve the
   ExpandedNodeId in the loaded AddressSpace.
2. Where it resolves to an ObjectType and the document projects to an Object, or to a VariableType
   and the document projects to a Variable, the converter **shall** create the projected node with a
   `HasTypeDefinition` reference to it, and **shall not** generate a type of its own for that node.
3. Where it does not resolve, the projection **shall** fail with `LoadState = Failed` and
   `Phase = Projection`. A converter **shall not** fall back to `BaseObjectType`, because a silently
   mistyped node is worse than a reported failure.
4. Where it resolves to a node of the wrong NodeClass, the document is invalid.
5. Where the document also instantiates a Thing Model, the two **shall** resolve to the same type
   node; otherwise the document is invalid.
6. The instance declarations the resolved type mandates **shall not** be duplicated by members the
   document also declares. A member of the document whose BrowseName matches a mandatory instance
   declaration of the type **shall** populate that declaration rather than adding a sibling.

Rule 6 is the one an implementer is most likely to miss, and it is the difference between a
conforming instance of the type and a node that carries each mandatory member twice.

## Conformance

A converter implementing rules 1 to 6 **may** declare the conformance unit `WoT-ExistingTypeBinding`.
A registry **should** report, per document, whether the type was bound or generated, so an operator
can tell which of the two they have.

## Effect on the existing text

- *WoT Binding* §5.2, the type-annotation table: add the row.
- *WoT Binding* §6.4, type identity and naming: state the relationship to `uav:congruentType`, which
  keeps its present meaning.
- *WoT Binding* §7, validation rules: add the domain, range and conflict rules above.
- *WoT Connectivity* §7.2, projection mapping: add rules 1 to 6.

No existing term changes meaning, and a document that does not use the term projects exactly as it
does today.
