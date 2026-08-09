# Proposal — binding a projected node to an existing type

**To:** the *OPC UA — WoT Binding* and *OPC UA — WoT Connectivity* drafts in `OPCF-Members/spec-drafts`.
**From:** the AAS companion specification work in this repository.
**Status:** proposed as `OPCF-Members/spec-drafts` PR #19, which carries the specification text for
the Binding and for WoT Connectivity. It adds **no vocabulary**.

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

| | with the type binding | published vocabulary only |
|---|---|---|
| nodes produced | 61 of 61 | 61 of 61 |
| NodeIds correct | 61 | 61 |
| BrowseNames correct | 61 | 61 |
| containment ReferenceTypes correct | 17 of 17 compared | 17 of 17 |
| TypeDefinitions correct | 61 | **0** |

Every other fact the vocabulary carries already arrives intact. The type binding is the whole of the
gap, which is why this is one rule and not a mechanism.

## The proposal

**A member of `@type` that names an ObjectType or VariableType, in the compact model name form of
§5.1.2, states that the projected node is an instance of that type.**

```jsonc
"@context": [ "https://www.w3.org/2022/wot/td/v1.1",
              { "uav": "http://opcfoundation.org/UA/WoT-Binding/",
                "i4aas": "http://opcfoundation.org/UA/I4AAS/" } ],
"@type": ["uav:object", "i4aas:AASSubmodelType"]
```

`uav:object` says the document projects to an Object; `i4aas:AASSubmodelType` says which Object.

`@type` is the JSON-LD member that says what a node **is**. §5.2 already annotates it with the
NodeClass term, it already carries more than one value, and in RDF it produces exactly the `rdf:type`
assertion a TypeDefinition expresses. A dedicated term would be a second way to say what `@type`
says.

**One form, not two.** Every other identity term in the Binding pairs a compact model name with an
ExpandedNodeId, because the name is a hint and the NodeId is definitive. That reasoning does not
apply to a type reference. A type is identified by its NamespaceUri-qualified BrowseName, which is
unique by construction; the prefix binds to the NamespaceUri in the `@context`; and the NodeId of a
type in a companion model is assigned by the Server that loaded it, so an author cannot know it and
a document that pinned it would be wrong on a different Server. A document **shall not** carry an
ExpandedNodeId alternative.

## Telling a type binding from an annotation

`@type` also carries ordinary semantic annotation — `saref:TemperatureSensor` on a Thing means what
it has always meant. A converter therefore cannot treat every member as a type binding.

Deciding by whether the lookup succeeds is the obvious rule and the wrong one: it turns a mistyped
type name into a silent `BaseObjectType`, which is the failure this proposal exists to prevent.

They are told apart by **namespace**:

- a member whose namespace the Server holds as an information model, or which the closure will
  materialize, is a **type binding**, and **shall** resolve;
- any other member is an **annotation**, and is retained as residue.

A namespace the Server holds is one the author is naming deliberately, so a name in it that does not
resolve is a mistake and is reported as one. A namespace the Server does not hold cannot have been
meant as a type in this AddressSpace. So `i4aas:AASSubmodlType` is reported, and
`saref:TemperatureSensor` is left alone.

## Resolution

A converter resolves a type binding against everything it has:

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

A rule about a member alone is not enough, because the projection is what has to change.

1. On projecting a document, a converter **shall** classify each member of `@type` by the namespace
   rule above, and **shall** resolve each type binding against the candidate space.
2. Where it resolves to an ObjectType and the document projects to an Object, or to a VariableType
   and the document projects to a Variable, the converter **shall** create the projected node with a
   `HasTypeDefinition` reference to it, and **shall not** generate a type of its own for that node.
3. Where a single `@type` carries more than one type binding, the document is invalid: a Node has
   exactly one `HasTypeDefinition`.
4. Where a binding resolves to more than one node, the document is invalid.
5. Where a binding does not resolve, the projection **shall** fail with `LoadState = Failed` and
   `Phase = Projection`. A converter **shall not** fall back to `BaseObjectType`: a silently mistyped
   node is worse than a reported failure.
6. Where a binding resolves to a node of the wrong NodeClass, the document is invalid.
7. Where the document also instantiates a Thing Model, the two **shall** resolve to the same type
   node; otherwise the document is invalid.
8. The instance declarations the resolved type mandates **shall not** be duplicated by members the
   document also declares. A member of the document whose BrowseName matches a mandatory instance
   declaration of the type **shall** populate that declaration rather than adding a sibling.

Rule 8 is the one an implementer is most likely to miss, and it is the difference between a
conforming instance of the type and a node carrying each mandatory member twice.

## The alternatives, and why not

**1. A dedicated term, `uav:typeref`.** This was proposed first. It is unambiguous without a
namespace rule, and it fails loudly on a name that does not resolve without needing one. It was
withdrawn because it adds vocabulary to say what `@type` already says, and because the namespace rule
recovers the strictness at no cost. Measured on the same fixtures, the two forms produce **identical**
node sets — 61 of 61 either way — so the choice is decided on form, not on result.
`tools/jsonld/wot_bridge.py --form term` still emits it, so the comparison can be repeated.

**2. A typed link, `rel: ua:HasTypeDefinition`.** §6.2 already allows a NamespaceUri-qualified
ReferenceType compact model name in a link `rel`:

```jsonc
"links": [ { "rel": "ua:HasTypeDefinition", "href": "i4aas:AASSubmodelType" } ]
```

It does not work today for two reasons, both fixable in the drafts. `HasTypeDefinition` is
non-hierarchical and §6.2 frames `rel` as carrying references *between types*, so a converter is not
required to act on one at Thing level; and `href` is defined as a resource locator, so pointing it at
a model concept rather than a document is outside what the Binding says `href` means. It also puts a
fact about what a node *is* in the links array rather than in `@type`, where a reader looks for it.

**3. `uav:congruentType`.** It names the right node but means something else: it records that two
independently authored types are structurally congruent, for reconciling two models. A converter
retains it as residue. Overloading it would give one term two jobs. See below.

**4. A Thing Model per ObjectType, instantiated by the Thing Description.** This works with the
vocabulary exactly as published and needs no change. It produces a type *congruent with* the
published one rather than the published one, so a Server ends up with two type hierarchies for one
model and a Client must be told which it is talking to. It is the fallback, not the answer.

## Reconciling `congruentType`

`uav:congruentType` and `uav:congruentTypeName` keep their meaning, and a document **may** carry them
alongside a type binding: one says *this is an instance of that type*, the other says *this type and
that type are the same shape*. They answer different questions.

If the working group concludes that congruence carries no weight in the NodeSet materialization —
that a converter reads it, retains it and never acts on it — then it is documentation rather than
model and should be renamed to say so, or folded into `uav:metadata`. The name is the difficulty
either way: "congruent" states a relation between two types without saying what a consumer does
about it, and it is the term reached for first when looking for the facility this proposal adds.

## Conformance

A converter implementing rules 1 to 8 **may** declare the conformance unit `WoT-ExistingTypeBinding`.
A registry **should** report, per document, whether the type was bound or generated, so an operator
can tell which of the two they have.

## Effect on the existing text

- *WoT Binding* §5.2.1: the rule, the namespace test and the converter behaviour. **New.**
- *WoT Binding* §6.4, type identity and naming: state the relationship to `uav:congruentType`.
- *WoT Binding* §7, validation rules: the domain and range row for a type name in `@type`.
- *WoT Connectivity* §7.2, projection mapping: rules 1 to 8.
- *WoT Connectivity* §7.4, dependency graph: the candidate space includes the closure's own types.

No term is added and no existing term changes meaning. A document whose `@type` carries only
node-class terms projects exactly as it does today, and a document carrying a semantic annotation in
a namespace the Server does not hold is unaffected — which is every such document written so far.

## Worked example

`companion-specs/AAS/examples/wot/` holds one Thing Description per fixture of the AAS conformance
corpus, generated by `companion-specs/AAS/tools/jsonld/wot_bridge.py`. Each names its ObjectType in
`@type` and projects to the AddressSpace clause 5.6 of the AAS specification defines; Annex F of that
document states the correspondence and the tool checks it.
