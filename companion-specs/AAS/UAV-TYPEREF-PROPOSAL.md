# Proposal — `uav:typeref`

**To:** the *OPC UA — WoT Binding* and *OPC UA — WoT Connectivity* drafts in `OPCF-Members/spec-drafts`.
**From:** the AAS companion specification work in this repository.
**Status:** proposal.

## The gap

A Thing Description projects to an Object. The Object's TypeDefinition comes from the Thing Model
the Thing Description instantiates, so a projection produces the type it generates and nothing else.
Nothing binds a projected Object to an ObjectType the Server has **already loaded** from a companion
model.

A companion specification that already defines its ObjectTypes — an AAS, a machine tool, a robot —
therefore cannot be projected from a Thing Description onto its own types. The projection produces a
parallel type that resembles the published one, so a Client written against the companion
specification does not recognise the result.

Measured over the AAS fixtures, with everything else in the vocabulary doing its job:

| | with the proposed term | published vocabulary only |
|---|---|---|
| nodes produced | 61 of 61 | 61 of 61 |
| NodeIds correct | 61 | 61 |
| BrowseNames correct | 61 | 61 |
| containment ReferenceTypes correct | 17 of 17 compared | 17 of 17 |
| TypeDefinitions correct | 61 | **0** |

Every other fact the vocabulary carries already arrives intact. The type binding is the whole of the
gap, which is why this is one term and not a mechanism.

## The options, and why this one

Four ways to close it were considered. The first three use only published vocabulary.

**1. A typed link, `rel: ua:HasTypeDefinition`.** §6.2 of the Binding already allows a
NamespaceUri-qualified ReferenceType compact model name directly in a link `rel`, so an author
reaches for:

```jsonc
"links": [ { "rel": "ua:HasTypeDefinition", "href": "i4aas:AASSubmodelType" } ]
```

This is the closest thing to a mechanism that already exists. It does not work today for two
reasons, both fixable in the drafts rather than in the vocabulary. `HasTypeDefinition` is
non-hierarchical and §6.2 frames `rel` as carrying references *between types*, so a converter is not
required to act on one at Thing level; and `href` is defined as a resource locator, so pointing it
at a model concept rather than at a document is outside what the Binding says `href` means.

If the working group prefers this shape, the change is to say normatively that a Thing-level link
with `rel: ua:HasTypeDefinition` binds the projected node's TypeDefinition, and to permit a compact
model name in that `href`. The rules below then apply unchanged, with the link in place of the term.
This option has the advantage of adding no vocabulary at all, and the disadvantage that a reader has
to know that one `rel` among many is not a reference between types.

**2. `uav:congruentType`.** It names the right node but means something else: it records that two
independently authored types are structurally congruent, for reconciling two models. A converter
retains it as residue. Overloading it would give one term two jobs. See *Reconciling `congruentType`*.

**3. A Thing Model per ObjectType, instantiated by the Thing Description.** This works with the
vocabulary exactly as published and needs no change. It produces a type *congruent with* the
published one rather than the published one, so a Server ends up with two type hierarchies for one
model and a Client must be told which it is talking to. It is the fallback, not the answer.

**4. A new term.** What follows.

## The term

**`uav:typeref`** (string) — the NamespaceUri-qualified BrowseName, in the compact model name form
of §5.1.2, of an ObjectType or VariableType. It states that the node this document projects to is an
instance of that type.

```jsonc
"@context": [ "https://www.w3.org/2022/wot/td/v1.1",
              { "uav": "http://opcfoundation.org/UA/WoT-Binding/",
                "i4aas": "http://opcfoundation.org/UA/I4AAS/" } ],
"@type": ["uav:object"],
"uav:typeref": "i4aas:AASSubmodelType"
```

**One form, not two.** Every other identity term in the Binding pairs a compact model name with an
ExpandedNodeId, because the name is a hint and the NodeId is definitive. That reasoning does not
apply to a type reference. A type is identified by its NamespaceUri-qualified BrowseName, which is
unique by construction; the prefix binds to the NamespaceUri in the `@context`; and the NodeId of a
type in a companion model is assigned by the Server that loaded it, so an author cannot know it and
a document that pinned it would be wrong on a different Server. `uav:typeref` therefore carries the
compact form only, and a document **shall not** carry an ExpandedNodeId alternative to it.

## Resolution

A converter resolves `uav:typeref` against everything it has:

1. the **loaded AddressSpace**, by NamespaceUri-qualified BrowseName; and
2. the **types the registry will materialize in this refresh** — the Thing Models of the closure,
   whose projected types are known once the closure is planned (*WoT Connectivity* §7.4).

Both are searched because a document may name a type from a companion model the Server loaded, or a
type another document in the same closure defines, and an author should not have to know which.

That candidate space is the one a Server already builds. A converter that synthesises a type without
first looking for an existing one of that name produces a duplicate of something it is already
holding. The AAS case is the demonstration: the Server has `AASSubmodelType` loaded, the document
says `i4aas:AASSubmodelType`, and the projection today invents a second type of the same name in a
different namespace.

## Converter behaviour

A vocabulary entry alone is not enough, because the projection is what has to change.

1. On projecting a document that carries `uav:typeref`, a converter **shall** resolve the compact
   model name against the candidate space above.
2. Where it resolves to an ObjectType and the document projects to an Object, or to a VariableType
   and the document projects to a Variable, the converter **shall** create the projected node with a
   `HasTypeDefinition` reference to it, and **shall not** generate a type of its own for that node.
3. Where it resolves to more than one node, the document is invalid.
4. Where it does not resolve, the projection **shall** fail with `LoadState = Failed` and
   `Phase = Projection`. A converter **shall not** fall back to `BaseObjectType`: a silently
   mistyped node is worse than a reported failure.
5. Where it resolves to a node of the wrong NodeClass, the document is invalid.
6. Where the document also instantiates a Thing Model, the two **shall** resolve to the same type
   node; otherwise the document is invalid.
7. The instance declarations the resolved type mandates **shall not** be duplicated by members the
   document also declares. A member of the document whose BrowseName matches a mandatory instance
   declaration of the type **shall** populate that declaration rather than adding a sibling.

Rule 7 is the one an implementer is most likely to miss, and it is the difference between a
conforming instance of the type and a node carrying each mandatory member twice.

## Reconciling `congruentType`

`uav:congruentType` and `uav:congruentTypeName` keep their meaning, and a document **may** carry them
alongside `uav:typeref`: one says *this is an instance of that type*, the other says *this type and
that type are the same shape*. They answer different questions.

If the working group concludes that congruence carries no weight in the NodeSet materialization —
that a converter reads it, retains it and never acts on it — then it is documentation rather than
model and should be renamed to say so, or folded into `uav:metadata`. The name is the difficulty
either way: "congruent" states a relation between two types without saying what a consumer does
about it, and it is the term reached for first when looking for the facility this proposal adds.

## Conformance

A converter implementing rules 1 to 7 **may** declare the conformance unit `WoT-ExistingTypeBinding`.
A registry **should** report, per document, whether the type was bound or generated, so an operator
can tell which of the two they have.

## Effect on the existing text

- *WoT Binding* §5.2, the type-annotation table: add the row.
- *WoT Binding* §6.2, links and references: state whether option 1 is also adopted.
- *WoT Binding* §6.4, type identity and naming: state the relationship to `uav:congruentType`.
- *WoT Binding* §7, validation rules: add the domain, range and conflict rules above.
- *WoT Connectivity* §7.2, projection mapping: add rules 1 to 7.
- *WoT Connectivity* §7.4, dependency graph: the candidate space includes the closure's own types.

No existing term changes meaning, and a document that does not carry `uav:typeref` projects exactly
as it does today. The vocabulary preserved from the published OPC 10101 v1.00 is untouched; only the
terms this revision adds are affected, and the revision is still in review.

## Worked example

`companion-specs/AAS/examples/wot/` holds one Thing Description per fixture of the AAS conformance
corpus, generated by `companion-specs/AAS/tools/jsonld/wot_bridge.py`. Each carries `uav:typeref`
and projects to the AddressSpace clause 5.6 of the AAS specification defines; Annex F of that
document states the correspondence and the tool checks it.
