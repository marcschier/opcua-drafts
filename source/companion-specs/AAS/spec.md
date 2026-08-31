## Scope {#sec-scope}

This companion specification defines an OPC UA information model for the Asset Administration Shell
(AAS). It covers two things a Server does with shells, and a Server may implement either or both:

- **The metamodel.** An AAS, its submodels and its submodel elements are projected onto the
  AddressSpace as typed nodes, so a Client reads a value, writes one, or invokes an operation
  through ordinary OPC UA Services.
- **The registry.** A catalogue of shells is projected onto the AddressSpace as folders of files, so
  a Client discovers which shells exist, retrieves a submodel as a document, reads an earlier
  revision, or follows a shell served by another Server.

The metamodel mapping is **lossless in both directions**: an AAS materialized into the AddressSpace
and read back reproduces the original, and an AddressSpace subtree serialized and materialized again
reproduces itself. Clause 6.1 defines the rules this requires and clause 6.4 defines how it is tested.
Losslessness is not decoration — it is what allows an AAS to be compiled into a Server by a source
generator, because a mapping in which any choice is left to the implementer cannot be generated.

The same mapping is reached from a **W3C Thing Description**. A Thing Description carrying the AAS
vocabulary materializes the AddressSpace this document defines, and an AddressSpace subtree is
expressible as a Thing Description again, so an AAS authored as a WoT document and an AAS
materialized from a package are the same nodes. [Annex F](#anx-f) states the correspondence, the
terms it uses and the one rule it requires, and `examples/wot/` holds a Thing Description for each
fixture of the conformance corpus.

OPC 30270 v1.00 maps the AAS v1.x metamodel in a separate namespace. Clause 4.3 defines its
relationship to this specification.

---

## General information to Asset Administration Shell and OPC UA {#sec-general-information-to-asset-administration-shell-and-opc-ua}

### Introduction to Asset Administration Shell {#sec-introduction-to-asset-administration-shell}

An AAS is the standardized digital representation of an asset. It carries the asset's identity and
references the submodels that describe it — a nameplate, technical data, a carbon footprint, a bill
of material. Submodels are identified in their own right and are not owned by the shell that
references them, so one submodel may be referenced by several shells.

Three kinds of thing carry a globally unique identifier: shells, submodels and concept descriptions.
Everything else is named only within its parent, by a short name, and is addressed by the path of
short names that leads to it.

### Introduction to OPC Unified Architecture {#sec-introduction-to-opc-unified-architecture}

The Word rendering of this document carries the standard OPC UA introduction from the OPC Foundation companion specification template, including its five figures. See OPC 10000-1 for the overview and OPC 10000-3 and OPC 10000-5 for the address space and information model.

### Relationship to OPC 30270 v1.00 {#sec-relationship-to-opc-30270-v1-00}

OPC 30270 v1.00 models the AAS v1.x metamodel in
`http://opcfoundation.org/UA/I4AAS/`. This specification models the incompatible AAS V3 metamodel
in `http://opcfoundation.org/UA/I4AAS/v3/`. A model version does not change NodeId identity, so the
two models use distinct namespace URIs and a Server may load both without rebinding a published
NodeId.

AAS V3 has `AssetInformation` and `SpecificAssetId` in place of the v1.x `Asset` and `View`
shapes, carries identifiers as bare strings, and distinguishes `SubmodelElementList` from
`SubmodelElementCollection`. This specification also carries the information required for a
lossless round trip and defines the AAS registry as an xRegistry domain model. Annex C gives an
informative concept correspondence for migration tooling.

### AddressSpace figures {#sec-addressspace-figures}

The AddressSpace figures in this document use the OPC UA graphical notation of OPC 10000-3. A Node
of an instance NodeClass — Object, Variable or View — is a plain rectangle, a Method is a rounded
rectangle, and a type — ObjectType, VariableType, ReferenceType or DataType — is a rectangle standing
on a shadow. An abstract type is set in *italics*, and a Node whose BrowseName is a placeholder is
written in angle brackets. A `HasTypeDefinition` reference carries a solid arrowhead; a
`HasComponent` reference is the plain unlabelled arrow; every other ReferenceType is drawn with its
BrowseName on the arrow. A figure shows the part of the model its clause describes, never the whole
of it.

```{figure}
id: fig-aas-notation
caption: Graphical notation used by the AddressSpace figures
source: figures/AAS-Fig1-Notation.png
```

Every figure that draws part of this specification's information model is re-derived from the
NodeSet by `tools/validate_local.py`: each Node must exist with the NodeClass and abstractness the
figure claims, and each edge must be a real Reference of that type in that direction.

---

## Use cases {#sec-use-cases}

### Registry discovery {#sec-registry-discovery}

Given an asset key such as a serial number or manufacturer part identifier, a Client needs to find
which shells describe that asset without browsing the whole collection. `LookupShellsByAssetLink`
(clause 6.5.5) answers that question directly, using the registry's indexed asset links rather than
a traversal of every shell group.

### Digital Product Passport {#sec-digital-product-passport}

A Digital Product Passport is public in part and restricted in part. The registry serves that shape
with the disclosure tiers and authorization advertisement of clause 6.5.7, and with the version
history of clause 6.5.4. That history lets a record be retrieved as it stood on a date, which
regulation requires and the AAS metamodel alone cannot supply.

### Lossless Server generation from an AAS {#sec-lossless-server-generation-from-an-aas}

The mapping leaves no choice to the implementer (clause 6.1.6). An AAS can therefore be compiled by
a source generator into a loadable NodeSet, and a Server that loads that NodeSet serves the AAS. This
is a consequence of losslessness: a mapping with implementation-defined choices could not be
compiled deterministically.

### Federation {#sec-federation}

A shell may be described by one registry and hosted by another. It is reached through an
`ExternalReference` or `ResourceUrl`, while identity remains the AAS identifier attributes and the
identifier derived from them, never an endpoint (clause 6.5.6). A Client can therefore follow the
serving location without changing the entity it has resolved.

### Authoring an AAS as a Thing Description {#sec-authoring-an-aas-as-a-thing-description}

A WoT Thing Description carrying the AAS vocabulary materializes the same AddressSpace (Annex F).
An AAS authored as linked data and an AAS materialized from an AASX package are therefore the same
nodes, not parallel representations that a Consumer must reconcile.

---

## Asset Administration Shell information model overview {#sec-asset-administration-shell-information-model-overview}

### Mapping rules {#sec-mapping-rules}

#### General {#sec-general}

An AAS `Environment` materializes as an `AASEnvironmentType` folder holding the shells, submodels
and concept descriptions it contains. Submodels are held by the environment, not nested inside
shells, because a submodel is not owned by the shell that references it; a shell carries references
to its submodels, and those references are the link.

`AASEnvironmentType` is a `FolderType` and **not** a subtype of the xRegistry `RegistryType`. An
environment holds the metamodel objects of one serialization — the unit an AASX package carries and
a source generator compiles — and its membership is whatever that serialization contained. A
registry holds documents about shells, versioned and federatable, and its membership is what the
Server catalogues. A Server may serve one, the other, or both over the same shells. Making
`AASEnvironmentType` a `RegistryType` would require every Server that materializes an AAS to
implement the registry half.

Where both halves are present, clause 6.5.2 defines the link between a catalogued shell and its
materialized node tree, and clause 6.5.10 requires the registry to serve the materialized environment
as retrievable AAS and AASX documents.

Every metamodel field has exactly one representation in the AddressSpace. [Annex B](#anx-b) lists
them all, field by field. A field with no entry in that annex is a defect in this specification, not
a field an implementation may drop.

#### Canonical value representation {#sec-canonical-value-representation}

AAS types values with an xsd type. Clause 6.3.1 assigns each of the thirty values of `DataTypeDefXsd`
one OPC UA DataType, and no DataType is assigned to two of them. Where a built-in DataType denotes
the xsd type on its own it is used; where two xsd types would otherwise share one built-in,
clause 6.3.1 defines a subtype for one of them.

A value materializes as one `Value` Variable, whose DataType is the one clause 6.3.1 assigns to its
declared xsd type. The declared type is read from that DataType.

`ValueType` is a Mandatory Variable. The metamodel makes `Property.valueType` mandatory and
`Property.value` optional, and the same holds for `Range`, so a Property that declares `xs:decimal`
and carries no value is conformant AAS; clause 6.1.5 gives an absent field no node, leaving no value
node to carry the declaration. Where both are present a Server **shall** keep them consistent: the
`Value` node's DataType **shall** be the one clause 6.3.1 assigns to `ValueType`.

**A value is compared in the xsd value space, not the lexical space.** XML Schema defines a
datatype's *value space* and its *lexical space* separately, defines identity on the value space,
and designates a *canonical lexical representation* for each type. AAS carries a value as a string
in the lexical space and defines no equality on it: no normalization, no canonical form, and no
requirement that a lexical form survive a round trip. The ValueOnly serialization of AAS Part 2
renders a value as a native JSON number or boolean and back, so `"1"` declared `xs:boolean` returns
as `"true"`.

A Server therefore:

- **shall** materialize a value into the DataType of clause 6.3.1, and
- **shall** serialize it back as the XSD canonical lexical representation of that type.

The canonical lexical representation is the one defined by XSD 1.1 Part 2: Datatypes. For
`xs:decimal`, the `decimalCanonicalMap` omits the fractional part where the value is integral:
`"1"` therefore serializes as `"1"`, not as the XSD 1.0 form `"1.0"`. The same XSD 1.1
canonical mapping governs the exponent form serialized for `xs:float` and `xs:double`.

A Property authored as `"1.500000"` with `ValueType` `xs:decimal` therefore serializes as `"1.5"`,
and one authored `"+42"` with `xs:int` serializes as `"42"`. The documents are equivalent under
clause 6.4, not identical. An implementation that requires the authored lexical form to survive
verbatim expresses that in the metamodel, with a qualifier or an IEC 61360 `valueFormat`.

`AASValueString` is used only where a Structure field carries a value whose declared type is given
by a sibling field of the same Structure (clause 6.3.2). It is never the DataType of a Variable.

#### NodeId and BrowseName assignment {#sec-nodeid-and-browsename-assignment}

Assignment is deterministic: two implementations materializing the same AAS produce the same nodes.

**NodeId.** Instance nodes use String identifiers in the Server's own namespace. The identifier is
a node-kind discriminator followed by decimal length prefixes and reversibly escaped source
components:

| Node | String identifier |
|---|---|
| Asset Administration Shell | `i4aas3:A:<n>:E(<id>)` |
| Submodel | `i4aas3:S:<n>:E(<id>)` |
| Concept Description | `i4aas3:C:<n>:E(<id>)` |
| Submodel Element | `i4aas3:E:<n>:<m>:E(<owner-id>)E(<idShortPath>)` |

`E` is applied independently to every raw identifier and path component. It scans the source
Unicode scalar values without normalization. A literal `%`, every C0 control from U+0000 through
U+001F, and every C1 control from U+007F through U+009F is encoded as its UTF-8 bytes, with each
byte written as `%HH` using uppercase hexadecimal digits. Every other scalar value is copied
unchanged. Decoding accepts only this canonical form: a raw C0 or C1 control, a malformed escape,
or an escape whose decoded value would not be escaped by `E` is invalid. This also makes a literal
percent unambiguous: `%` encodes as `%25`.

`<n>` and `<m>` are the numbers of Unicode code points in the *encoded* components that follow,
written with ASCII decimal digits and without leading zeroes. For an identifiable, `<n>` is the
length of `E(<id>)`. For an element, `<n>` is the length of `E(<owner-id>)` and `<m>` is the length of
`E(<idShortPath>)`; those lengths split the concatenated payload before either component is
decoded, without relying on a delimiter that a source string may contain. `A`, `S`, `C` and `E`
distinguish the four node kinds.

The `idShortPath` is the metamodel's own path convention: short names joined by `.`, with `[n]` for
a member of a list. The encoding is reversible and collision-free: for example, a shell whose
identifier is `a#b` encodes as `i4aas3:A:3:a#b`, while element path `b` beneath owner `a` encodes as
`i4aas3:E:1:1:ab`. An identifier containing LF between `a` and `b` encodes as
`i4aas3:S:5:a%0Ab`; NUL in the same position encodes as `i4aas3:S:5:a%00b`; U+0085 by itself
encodes as `i4aas3:S:6:%C2%85`; and the three source characters `%0A` encode as
`i4aas3:S:5:%250A`, not as a line feed.

An `OperationVariable` wrapper is not a node. Its `value` element has the path
`<operation-path>.<role>[<index>]`, where `<role>` is exactly `inputVariables`,
`outputVariables` or `inoutputVariables` and `<index>` is its zero-based position in that role.
For example, the first input value of `AnOperation` has path
`AnOperation.inputVariables[0]`. The value element's own `idShort` remains its BrowseName and
`IdShort` Property; the role and index, rather than that short name, identify its containment
position.

OPC UA limits a String NodeId identifier to 4096 characters. Before creating any nodes for one
identifiable, a materializer **shall** derive every identifier in its subtree. If any derived
identifier, after escaping and adding its discriminator and length prefixes, exceeds that limit, it
**shall** reject that identifiable without exposing a partial subtree and **shall** report the
overlength path in its diagnostic. It **shall not** truncate, replace or hash the source strings,
because those operations would not implement the reversible encoding above.

**BrowseName.** A Referable that has a non-empty `idShort` uses that exact short name in the
Server's namespace. The three top-level Identifiables permit `idShort` to be absent. In that case
the BrowseName is `<kind>_<digest>`, where `<kind>` is exactly `AssetAdministrationShell`,
`Submodel` or `ConceptDescription`, and `<digest>` is the lowercase hexadecimal SHA-256 digest of
the exact, non-normalized UTF-8 bytes of `id`. The raw identifier is not included in the
BrowseName.

Before allocating derived BrowseNames, a materializer **shall** reserve every BrowseName supplied
by an `idShort` among the environment's top-level children. Identifiers that produce one derived
base name are processed in ascending lexicographic order of their UTF-8 bytes. The first available
name is used: the unsuffixed base where it is free, otherwise the base followed by `_n`, where `n`
is the smallest non-negative ASCII decimal integer that makes the name unused. This rule handles both
a SHA-256 collision and a collision with an authored `idShort` without making source array order
significant. Duplicate identifiers within one identifiable kind would produce the same NodeId and
**shall** be rejected.

An element inside a `SubmodelElementList` has no short name — the metamodel does not give it one —
so its BrowseName is its index rendered as a decimal string. Order is carried by the `Index`
Property, not by the BrowseName, because a BrowseName is a name and not a position.

**DisplayName.** The short name where one exists; otherwise the index for a list member or the
derived BrowseName for a top-level Identifiable.

#### Ordering {#sec-ordering}

`SubmodelElementList.orderRelevant` says whether the order of a list's members carries meaning; when
it is false the metamodel states that the list represents a set or a bag. OPC UA can say this in the
type system rather than in a Property, and it does:

- Where `orderRelevant` is **true** — including where it is absent, since its default is true — a
  `SubmodelElementList` **shall** reference its members with `HasOrderedComponent` (`i=49`), the
  subtype of `HasComponent` whose semantic is that the order of the references is meaningful.
- Where `orderRelevant` is **false**, it **shall** reference them with `HasComponent`.
- Every other parent/child relationship between Submodel Elements **shall** use `HasComponent`.

The ReferenceType carries `orderRelevant`; there is no `OrderRelevant` Property.
`AASSubmodelElementListType.<Element>` is declared with `HasComponent`; an ordered instance uses
the `HasOrderedComponent` subtype for that declaration.

`Index` carries the position. The Browse Service is not required to return references in any
particular order, and a NodeSet is a set of references rather than a sequence, so the order of a
Browse result is not a reliable source for it. `Index` is Optional on a list member and RECOMMENDED
wherever `HasOrderedComponent` is used; an implementation claiming `AAS-LosslessRoundTrip` **shall**
materialize it there. Where a Server materializes `Index`, the values **shall** be the positions
`0 … n-1` without gaps or repeats, and a serializer emits members in `Index` order.

Where the members are referenced with `HasComponent`, a serializer **may** emit them in any order,
and clause 6.4 compares the collection as a bag.

The three `Operation` variable roles are separately ordered arrays. Their value elements are direct
`HasComponent` children, not `HasOrderedComponent` children. Each value element **shall** carry
`Index` equal to its zero-based position within its role. The array position is authoritative; the
`Index` Property and the role/index in the NodeId of clause 6.1.3 **shall** agree with it. Indices
start again at zero for each role.

#### Absent versus empty {#sec-absent-versus-empty}

An optional field that is absent and one present but empty are distinct in the metamodel:

- An **absent** optional field has **no node**.
- A field **present but empty** has a node whose value is an empty array, or an Object with no
  children.

A Server **shall not** materialize a node for an absent field, and **shall not** omit one for a
present-but-empty field. A serializer distinguishes the two by the presence of the node, never by
its value.

The rule presupposes that the field has a node of its own, and five do not. `submodelElements`,
`SubmodelElementCollection.value`, `SubmodelElementList.value`, `Entity.statements` and
`AnnotatedRelationshipElement.annotations` materialize as components of the parent node rather than
as a node holding a collection (Annex B), so an absent one and a present-but-empty one both leave
the parent with no children of that kind and no marker distinguishes them. For these five fields
only, the distinction is therefore **not** preserved: a serializer **shall** emit the field as
absent where the parent has no corresponding children, and clause 6.4 compares them accordingly.

Collapsing the distinction is deliberate rather than an oversight. Preserving it would require a
marker node on every collection-bearing element, which would appear in every AddressSpace to record
a difference the metamodel draws but nothing observable depends on, and clause 6.4 would still have
to special-case it. Every other optional field keeps the distinction, because every other optional
field has a node.

#### Instance materialization {#sec-instance-materialization}

Materializing an `Environment` is mechanical:

1. Create an `AASEnvironmentType` folder.
2. For each shell, submodel and concept description, create a node of the corresponding type, with
   the NodeId of clause 6.1.3 and the BrowseName of clause 6.1.3, organized by the environment folder.
3. For each element within a submodel, recursively create a node of the type corresponding to its
   metamodel class, referenced by its parent with `HasComponent`.
4. For each field present on the element, create the member node named in Annex B, with the value
   the metamodel carries. Omit members for absent fields, per clause 6.1.5.
5. For a value-bearing element, set `ValueType`, and set `Value` with the DataType clause 6.3.1
   assigns to it, per clause 6.1.2.
6. Reference the members of a `SubmodelElementList` with `HasOrderedComponent` where its
   `orderRelevant` is true and `HasComponent` where it is false, and set each member's `Index` to
   its position, per clause 6.1.4.

No step in that sequence is implementation-defined. A generator that implements it compiles an AAS
into a loadable NodeSet, and a Server that loads the NodeSet serves the AAS.

### AAS metamodel ObjectTypes {#sec-aas-metamodel-objecttypes}

The companion namespace is `http://opcfoundation.org/UA/I4AAS/v3/`, model version 3.00-draft4.
Draft numeric NodeIds use the `1001+` block; final NodeIds are assigned by the OPC Foundation. The
normative node reference is [Annex A](#anx-a); this clause describes intent.

#### Abstract bases {#sec-abstract-bases}

The abstract bases mirror the metamodel's own hierarchy, so that an element carries the members its
metamodel class gives it and no others: `AASReferableType` for everything with a short name,
`AASIdentifiableType` for the three classes with a globally unique identifier, and
`AASHasSemanticsType`, `AASHasKindType`, `AASHasDataSpecificationType` and `AASQualifiableType` for
the orthogonal aspects.

`AASReferableType` carries a Mandatory `ModelType`, the metamodel class name. It is redundant with
the ObjectType, and it is carried anyway: a serialization produced from the AddressSpace must be
byte-identical to the one that produced it, and the metamodel's serialization includes this
discriminator.

`AASIdentifiableType` carries the `Id` — up to 2048 characters of arbitrary text, which is why
identity lives in a Property and in the encoded String NodeId rather than in the BrowseName
(clause 6.1.3).

<!-- model-figure: root=ns=2;i=1001 require=mandatory external=BaseObjectType  graph=figures/fig-aas-referable.mmd -->

```{figure}
id: fig-aas-referable
caption: AASReferableType and the identity it gives every element
source: figures/AAS-Fig2-ReferableType.png
```

<!-- model-figure: root=ns=2;i=1003 require=mandatory external=BaseObjectType  graph=figures/fig-aas-aspect-bases.mmd -->

```{figure}
id: fig-aas-aspect-bases
caption: The orthogonal aspect bases
source: figures/AAS-Fig3-AspectBases.png
```

#### Environment, shell and asset information {#sec-environment-shell-and-asset-information}

`AASEnvironmentType` is the container and the root a generator materializes into. Shells, submodels
and concept descriptions are all held by it directly: a submodel is not owned by the shell that
references it, and one submodel may be referenced by several shells, so nesting them inside shells
would misrepresent the model.

`AASType` is a shell. It holds `AssetInformation`, references to its submodels, and the derivation
link from an instance to its type.

<!-- model-figure: root=ns=2;i=1010 require=mandatory external=FolderType  graph=figures/fig-aas-environment.mmd -->

```{figure}
id: fig-aas-environment
caption: AASEnvironmentType, the container a generator materializes
source: figures/AAS-Fig4-Environment.png
```

<!-- model-figure: root=ns=2;i=1011 require=mandatory  graph=figures/fig-aas-shell.mmd -->

```{figure}
id: fig-aas-shell
caption: AASType and the asset identity it carries
source: figures/AAS-Fig5-Shell.png
```

#### Submodel and concept description {#sec-submodel-and-concept-description}

`AASSubmodelType` is a submodel, holding its elements. `AASConceptDescriptionType` is the definition
a semantic identifier resolves to — what makes two submodels from different vendors comparable.

<!-- model-figure: root=ns=2;i=1013 require=mandatory  graph=figures/fig-aas-submodel-concept.mmd -->

```{figure}
id: fig-aas-submodel-concept
caption: AASSubmodelType and AASConceptDescriptionType
source: figures/AAS-Fig6-SubmodelConcept.png
```

#### Submodel elements {#sec-submodel-elements}

The element types cover the metamodel's element set. Every one of them subtypes
`AASSubmodelElementType`, which carries the semantics, qualifiers and data specifications an element
may have, and the `Index` that gives a list member its position (clause 6.1.4).

<!-- model-figure: root=ns=2;i=1020 require=mandatory  graph=figures/fig-aas-elements.mmd -->

```{figure}
id: fig-aas-elements
caption: The submodel element hierarchy
source: figures/AAS-Fig7-ElementHierarchy.png
```

Three element types deserve note, and they are the three the losslessness rules bear on.

**`AASPropertyType`** carries a value once, in a `Value` node whose DataType is the one clause 6.3.1
assigns to the declared `ValueType` (clause 6.1.2). `ValueType` is Mandatory because the metamodel
makes it mandatory while making the value itself optional. **`AASRangeType`** carries its bounds the
same way, and an absent bound means unbounded rather than zero.

<!-- model-figure: root=ns=2;i=1021 require=mandatory  graph=figures/fig-aas-value-type.mmd -->

```{figure}
id: fig-aas-value-type
caption: A value and the type it is declared as
source: figures/AAS-Fig8-ValueType.png
```

**`AASSubmodelElementListType`** declares its member placeholder with `HasComponent`. An instance
specializes that reference to `HasOrderedComponent` where the list's order is relevant and retains
`HasComponent` where it is not; its members carry `Index` where the position has to be recoverable.
`AASSubmodelElementCollectionType` is unordered and its members are identified by their own short
names.

<!-- model-figure: root=ns=2;i=1031 require=mandatory  graph=figures/fig-aas-collections.mmd -->

```{figure}
id: fig-aas-collections
caption: Ordered and unordered collections
source: figures/AAS-Fig9-Collections.png
```

**`AASEntityType`** is a component of a composition; a self-managed entity carries the identifier of
its own shell, so a bill of material is traversable across organizations.
**`AASOperationType`** carries its variables as references to the element nodes that hold them,
rather than duplicating those elements, so an operation's variables round-trip as the elements they
are.

For every `OperationVariable` in a present role array, a materializer **shall** create the wrapper's
mandatory `value` as one direct `HasComponent` child of the `AASOperationType` node. It **shall not**
create a node for the wrapper itself. The corresponding `InputVariables`, `OutputVariables` or
`InoutputVariables` array entry **shall** be one `AASOperationVariableDataType` whose
`ValueNodeId` is the local NodeId of that child. A child **shall** occur in exactly one role entry.
The child uses its concrete AAS ObjectType and its own `idShort` as BrowseName; its NodeId and
`Index` follow clauses 6.1.3 and 6.1.4. An absent role has no corresponding Property instance, while a
present empty role has a Property whose value is an empty array.

<!-- model-figure: root=ns=2;i=1032 require=mandatory  graph=figures/fig-aas-composition.mmd -->

```{figure}
id: fig-aas-composition
caption: Composition, operations and events
source: figures/AAS-Fig10-Composition.png
```

#### Invoking an operation {#sec-invoking-an-operation}

An `Operation` submodel element is invocable. `AASOperationType` carries the Method `Invoke`, whose
arguments correspond positionally to the element's `InputVariables`, `OutputVariables` and
`InoutputVariables`.

| Argument | Direction | Corresponds to |
|---|---|---|
| `InputValues` | in | `inputArguments` of the AAS API request, in the order of `InputVariables` |
| `InoutputValues` | in | `inoutputArguments` of the request, in the order of `InoutputVariables` |
| `ClientTimeout` | in | `clientTimeoutDuration`; zero selects the Server's default |
| `OutputValues` | out | `outputArguments` of the result, in the order of `OutputVariables` |
| `InoutputResults` | out | `inoutputArguments` of the result |
| `Success` | out | `success` |
| `Diagnostic` | out | the message of a failed execution |

A Server **shall** return `Bad_InvalidArgument` where the number of values does not match the number
of variables the element declares.

`Success` reports the outcome of the operation, not of the Call. An operation that runs and reports
failure returns `Good` with `Success` false; a Call that could not be made at all returns a bad
StatusCode. Conflating the two would leave a Client unable to distinguish an unreachable Server from
a rejected workpiece.

Positional correspondence, rather than a name-keyed structure, is what the metamodel supports:
`InputVariables` is an ordered array and clause 6.1.4 already preserves that order, so the *n*-th value
belongs to the *n*-th variable in both directions.

The AAS API of IDTA-01002 Part 2 also defines an asynchronous form, `InvokeOperationAsync` with
`GetOperationAsyncResult`. This specification defines no counterpart: an OPC UA Method Call is
synchronous, and a Server whose operations outlive a Call implements the Program interface of
OPC 10000-10 on the element rather than a second Method here. Annex G records the correspondence.

### AAS DataTypes {#sec-aas-datatypes}

#### The xsd type mapping {#sec-the-xsd-type-mapping}

Each of the thirty values of `AASDataTypeDefXsdDataType` is assigned one OPC UA DataType, and no
DataType is assigned to two of them. A serializer reads the declared xsd type from the DataType of
the value node.

Where a built-in DataType denotes the xsd type on its own, it is used. Where two xsd types would
otherwise share one built-in, a subtype is defined in this namespace, as OPC UA does in deriving
`DecimalString`, `DurationString`, `DateString` and `TimeString` from `String`. Ten such subtypes
are defined.

| `ValueType` | OPC UA DataType | Note |
|---|---|---|
| `xs:boolean` | `Boolean` (`i=1`) | |
| `xs:byte` | `SByte` (`i=2`) | xsd `byte` is signed |
| `xs:unsignedByte` | `Byte` (`i=3`) | |
| `xs:short` | `Int16` (`i=4`) | |
| `xs:unsignedShort` | `UInt16` (`i=5`) | |
| `xs:int` | `Int32` (`i=6`) | |
| `xs:unsignedInt` | `UInt32` (`i=7`) | |
| `xs:long` | `Int64` (`i=8`) | |
| `xs:unsignedLong` | `UInt64` (`i=9`) | |
| `xs:float` | `Float` (`i=10`) | |
| `xs:double` | `Double` (`i=11`) | |
| `xs:decimal` | `Decimal` (`i=50`) | arbitrary precision, and its `Scale` preserves the authored number of decimal places |
| `xs:integer` | `Integer` (`i=27`) | |
| `xs:nonNegativeInteger` | `UInteger` (`i=28`) | |
| `xs:positiveInteger` | `AASPositiveInteger` | subtype of `UInteger`, so it does not collide with `xs:nonNegativeInteger` |
| `xs:nonPositiveInteger` | `AASNonPositiveInteger` | subtype of `Integer` |
| `xs:negativeInteger` | `AASNegativeInteger` | subtype of `AASNonPositiveInteger`, mirroring the xsd restriction hierarchy |
| `xs:string` | `String` (`i=12`) | |
| `xs:anyURI` | `AASAnyUri` | subtype of `String`, so it does not collide with `xs:string` |
| `xs:dateTime` | `DateTime` (`i=13`) | |
| `xs:date` | `DateString` (`i=12881`) | a date is a day, not an instant |
| `xs:time` | `TimeString` (`i=12880`) | a time-of-day has no day |
| `xs:duration` | `DurationString` (`i=12879`) | the ISO 8601 duration form; **not** `Duration` (`i=290`), which is a count of milliseconds |
| `xs:gYear` | `AASGYear` | a Gregorian period; OPC UA has no DataType denoting one |
| `xs:gYearMonth` | `AASGYearMonth` | |
| `xs:gMonth` | `AASGMonth` | |
| `xs:gMonthDay` | `AASGMonthDay` | |
| `xs:gDay` | `AASGDay` | |
| `xs:base64Binary` | `ByteString` (`i=15`) | |
| `xs:hexBinary` | `AASHexBinary` | subtype of `ByteString`; the octets are identical to a `xs:base64Binary` value's and only the written form differs |

Four rows are qualified further.

`xs:duration` is assigned `DurationString`, not `Duration` (`i=290`). `Duration` is a `Double`
counting milliseconds; `xs:duration` has year and month components that are not a fixed number of
milliseconds, as `P1M` is not thirty days. `DurationString` holds the ISO 8601 form, which is the
lexical space of `xs:duration`.

`xs:date` and `xs:time` are assigned `DateString` and `TimeString`, not `DateTime`. A `DateTime` is
an instant; a date is a day in some timezone and a time is a time-of-day with no day. Assigning
either `DateTime` would require a value for the missing component.

The five partial-date types have no OPC UA DataType, built-in or derived, that denotes a period.
Each is assigned its own `String` subtype.

Two assignments have a range narrower than the xsd type. `Integer` and `UInteger` are the abstract
unions of OPC UA's concrete integer types, so their range is that of `Int64` and `UInt64`, whereas
`xs:integer` is unbounded; and `DateTime` begins in 1601, whereas `xs:dateTime` does not. A value
outside the representable range **shall** be rejected rather than truncated, as in clause 6.3.3.

#### AASValueString {#sec-aasvaluestring}

`AASValueString` is a subtype of `String` (`i=12`). It carries the xsd lexical form of a value whose
declared type is given by a sibling field of the same Structure.

A Structure field has one static DataType and cannot vary with a declared type.
`AASQualifierDataType` and `AASExtensionDataType` pair a value with a `ValueType` field.
`AASDataSpecificationIec61360DataType` pairs its value with a `DataType` field. In each case the
value field is lexical and the sibling field states how to read it. Where a Variable carries a
value, clause 6.3.1 assigns the DataType of its declared xsd type instead.

A Server **shall not** use `AASValueString` as the DataType of a Variable.

*Table - AASValueString Definition* {#tbl-aasvaluestring-definition defines=AASValueString}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASValueString |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:String defined in OPC 10000-3 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AAS-ValueFidelity |  |  |  |  |  |

#### Enumerations {#sec-enumerations}

The enumerations are closed. `AASKeyTypesDataType`, `AASDataTypeDefXsdDataType` and the rest
enumerate exactly the metamodel's values; a value outside the enumeration cannot round-trip, so an
implementation rejects it rather than dropping it silently.

#### Structures {#sec-structures}

The structures carry the metamodel's value classes: references and their ordered keys,
language-tagged strings, specific asset identifiers, administrative information, qualifiers,
extensions, data specifications and their IEC 61360 content. `AASQualifierDataType` and
`AASExtensionDataType` pair a value with `ValueType`;
`AASDataSpecificationIec61360DataType` pairs it with `DataType`. Each carries the value as
`AASValueString` for the reason given in clause 6.3.2.

`AASReferenceDataType` carries its `Keys` as an ordered array. The order is part of the reference's
meaning — it is the path — so it is preserved exactly.

IEC 61360 permitted values are structured rather than flattened into strings.
`AASValueReferencePairDataType` has Mandatory `Value` and `ValueId` fields.
`AASValueListDataType` has a Mandatory, non-empty `ValueReferencePairs` array of those pairs.
`AASLevelTypeDataType` has the four Mandatory Boolean fields `Min`, `Nom`, `Typ` and `Max`.
`AASDataSpecificationIec61360DataType.ValueList` and `.LevelType` are Optional, so their absence
remains distinct from a present structured value.

### Round-trip conformance {#sec-round-trip-conformance}

An implementation claiming the `AAS-LosslessRoundTrip` conformance unit **shall** satisfy both
directions.

**Materialize and serialize.** For any conformant AAS environment, materializing it per clause 6.1.6
and serializing the result **shall** produce an environment **equivalent** to the original.

**Serialize and materialize.** For any AddressSpace subtree produced by clause 6.1.6, serializing it
and materializing the result **shall** produce a subtree with the same nodes, NodeIds, BrowseNames,
References and values.

Two environments are equivalent when, after canonical ordering of JSON object members:

- every field present in one is present in the other, and absent in one is absent in the other;
- every value is the same element of the xsd value space of its declared `valueType`, compared per
  XSD 1.1 Part 2: Datatypes. `"1.500000"` and `"1.5"` are equivalent as `xs:decimal`; `"1"` and
  `"true"` are equivalent as `xs:boolean`; `"1.5"` and `"2.5"` are not;
- every array to which the metamodel gives an order is compared in order: the keys of a reference, a
  multi-language value, an operation's variables, and a `SubmodelElementList` whose `orderRelevant`
  is true;
- a `SubmodelElementList` whose `orderRelevant` is false is compared as a bag: same members, same
  multiplicities, order disregarded;
- the five container fields of clause 6.1.5 that materialize as parent components rather than as a
  node of their own — `submodelElements`, `SubmodelElementCollection.value`,
  `SubmodelElementList.value`, `Entity.statements` and
  `AnnotatedRelationshipElement.annotations` — are compared with absent and present-but-empty
  treated alike, since the mapping does not distinguish them.

No further tolerance applies. A field that cannot be represented is a defect in this specification;
Annex B is the list against which that is checked.

A test corpus accompanies this document under `tools/fixtures/`, and `tools/roundtrip_check.py`
runs both directions over it. The corpus covers every element type, nested and ordered lists,
elements without short names, multi-language values, non-canonical lexical forms of the xsd types,
the absent-versus-empty distinction, qualifiers, extensions, data specifications and multi-key
references.

The same tool carries a **negative control**. It breaks one normative rule at a time — corrupting a
value rather than re-writing it, canonicalizing an `xs:decimal` through a fixed working precision so
that digits are lost, restoring an ordered list in Browse order rather than by `Index`, conflating an
absent field with an empty one — and asserts that the comparison reports each. It also asserts that
re-writing a value into its canonical lexical form is **not** reported.

### The AAS Registry {#sec-the-aas-registry}

#### The registry is folders of files {#sec-the-registry-is-folders-of-files}

The registry half projects a catalogue of shells onto the AddressSpace using the abstract
*OPC UA — xRegistry* base model: a registry and its groups are `FolderType` folders, and a resource
document *is* a `FileType` file, read with the File Transfer Methods of OPC 10000-20.

It answers different questions from the metamodel half:

| | Metamodel clauses | Registry clauses |
|---|---|---|
| Unit | one shell's metamodel, in nodes | a catalogue of shells, as folders and files |
| Granularity | per element | per document |
| Access | Read, Write, Call | Open, Read, Close |
| Answers | what is this value now | which shells exist, at what versions, where else served |

A Server may implement either half or both. Where both are present the same shell appears twice, and
`AASShellGroupType.ShellNode` links the catalogue entry to the live node tree.

#### Registry types {#sec-registry-types}

`AASRegistryType` is the registry root, exposed as a well-known `AASRegistry` Object under the
`Server` Object so that any Client reaching the standard Server object discovers it. Its group
folders hold shells, submodel template families, concept dictionaries and package stores; its
Methods answer the discovery question and provide a document fast path.

The UANodeSet representation of the concrete `LookupShellsByAssetLink`, `GetSubmodel` and
`Materialize` Methods on the well-known `AASRegistry` Object **shall** set the
`MethodDeclarationId` XML attribute to the NodeId of the same-named Method declaration on
`AASRegistryType`.

`AASShellGroupType` holds the submodel documents of one shell. It is a `GroupType`, and therefore a
folder of resource files, whereas `AASType` is the shell's metamodel object tree. They are separate
types because they are separate things, and three consequences follow that a single type could not
give:

- **Either half can exist without the other.** A registry that catalogues a shell served by another
  Server has no metamodel tree to attach to, and a Server that materializes an AAS from a package
  need not catalogue it. Conflating the two would make each imply the other.
- **A group is a folder of files; a shell is an object.** The base `GroupType` gives the catalogue
  entry its xRegistry attributes, its creation Methods and its file members. `AASType` gives the
  shell its `AssetInformation` and its submodel references. Neither set belongs on the other.
- **They have different lifetimes.** A catalogued shell has versions, and the current version of its
  submodel document need not be what the metamodel tree currently holds — that is the whole point of
  clause 6.5.4.

Where a Server implements both halves, `AASShellGroupType.ShellNode` points at the `AASType` node
for the same shell, and both carry the same identifiers, so a Client can move between the catalogue
and the live tree without re-resolving anything.

`AASSubmodelFileType` is one submodel document. `AASConceptDescriptionFileType` and
`AASPackageFileType` are the corresponding resources for concept definitions and packages. Every
package carries the strong integrity metadata defined in clause 6.5.4.

<!-- model-figure: root=ns=2;i=1100 require=mandatory external=RegistryType,GroupType,ResourceType,Server  graph=figures/fig-aas-registry.mmd -->

```{figure}
id: fig-aas-registry
caption: The registry root, shells and their submodel documents
source: figures/AAS-Fig11-Registry.png
```

The other three group types follow the same shape: a group folder holding resource files, each
naming the source identity its identifier is derived from.

<!-- model-figure: root=ns=2;i=1103 require=mandatory external=GroupType,ResourceType  graph=figures/fig-aas-registry-stores.mmd -->

```{figure}
id: fig-aas-registry-stores
caption: Templates, concept dictionaries and package stores, each with its source identity
source: figures/AAS-Fig12-RegistryStores.png
```

#### Identifiers {#sec-identifiers}

Base clause 6.9 requires every group and resource type to name exactly one **source identity** and to
expose it verbatim as a Mandatory Property, and derives the identifier from it by the symbolic
construction defined there. This clause names them:

| Type | Source identity |
|---|---|
| `AASShellGroupType` | `AasIdentifier` |
| `AASSubmodelFileType` | `SubmodelIdentifier` |
| `AASSubmodelTemplateGroupType` | `TemplateNamespace` |
| `AASConceptDictionaryGroupType` | `DictionaryIdentifier` |
| `AASConceptDescriptionFileType` | `ConceptIdentifier` |
| `AASPackageStoreGroupType` | `StoreIdentifier` |
| `AASPackageFileType` | `PackageIdentifier` |

These are the same source identities the xRegistry AAS model names, and the construction is the same
one. The same shell therefore receives the same identifier whether it is served over OPC UA or over
HTTP, so the two bindings address one registry.

An identifier is never derived from a document. A resource is a stable umbrella over its versions,
so its identifier is invariant while its document changes; a content digest is version-level
metadata and identifies bytes, not entities.

#### Versioning and the lifecycle record {#sec-versioning-and-the-lifecycle-record}

The AAS metamodel records a single current revision. `AdministrativeInformation` carries a version
label and a revision label, and nothing retains what a submodel previously said or distinguishes a
correction from a new observation.

The registry supplies what the metamodel does not: each version of an `AASSubmodelFileType` is one
revision, ordered in time, and a Client asking for a submodel as it stood at a given moment reads
the newest version not later than that moment. This is not a convenience. Where a regulation
requires a record retrievable as of a date, or an auditable and tamper-evident history of changes to
controlled data, a Server implementing only the metamodel half has nothing to answer from.

The AAS version labels are carried unchanged in `Administration`; they are not reflected into the
registry's version identifiers, which follow the base model's own rules.

**Package integrity.** Every Version of an `AASPackageFileType` **shall** instantiate `Digest` and
`DigestAlg`, and both Properties **shall** be immutable within that Version. `Digest` **shall** be
the lowercase hexadecimal digest of the exact package blob bytes returned by `FileType.Read` and
**shall not** contain an algorithm prefix. `DigestAlg` is case-sensitive and **shall** be exactly
`Sha256`, `Sha384` or `Sha512`; every other algorithm or casing **shall** be rejected. An OCI
descriptor algorithm of `sha256`, `sha384` or `sha512` **shall** map respectively to `Sha256`,
`Sha384` or `Sha512`.

Before publishing these Properties or making the package available for reading or materialization,
the Server **shall** verify the exact returned blob against them. Before parsing, materializing or
otherwise using a retrieved package, a Consumer **shall** independently recompute `Digest` over
the exact returned bytes using `DigestAlg` and compare it with the published value.

An OCI-backed package Version **shall** instantiate immutable `ManifestDigest` as the exact digest
of the OCI manifest bytes, including a lower-case algorithm prefix and lower-case hexadecimal
value, for example `sha256:<lowercase-hex>`. `ManifestDigest` verifies only those exact manifest
bytes and **shall not** be treated as verification of the returned package blob. Before publishing
or using the Version, respectively, the Server and Consumer **shall** perform all of these checks:

1. recompute and compare `ManifestDigest` over the exact manifest bytes;
2. parse the verified manifest and require exactly one package-layer descriptor;
3. require that descriptor's algorithm and encoded digest, after the mapping above, equal
   `DigestAlg` and `Digest`; and
4. retrieve the package blob and independently recompute and compare `Digest` using `DigestAlg`.

`ManifestDigest` **shall** be the sole authority for OCI Version identity, and `VersionId` **shall** be the always-hashed symbolic identifier of its exact value. A raw OCI tag **may** locate a current manifest only as a mutable Resource-level alias and **shall never** be a `VersionId`. The tag **shall** match `[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}` and **shall** be preserved byte-for-byte, including case and a leading underscore. Moving a tag to a previously unseen manifest **shall** create and retain a distinct immutable Version and **shall not** mutate or replace the old Version. The xRegistry base `ResourceType` declares the `Attestations` attribute, and `AASAttestationDataType` is the AAS payload type for that attribute. An `AASPackageFileType` Version **shall not** instantiate `Subject` or `Attestations`: the prohibition is on the package Version, not on use of the DataType. An attestation or other OCI referrer **shall** be represented as a separate immutable Resource and **shall not** become a Version of the package Resource it refers to. Adding, removing or discovering a referrer **shall not** change that package Resource's Version collection, default Version, document, attributes, `Epoch` or `ModifiedAt`.

#### Discovery and resolution {#sec-discovery-and-resolution}

`LookupShellsByAssetLink` answers the discovery question — given an asset key such as a serial
number or a manufacturer part identifier, which shells describe it — without the Client browsing the
whole collection. `GetSubmodel` returns a document and enough metadata to parse it, for a Client that
holds an identifier rather than a node.

`GetSubmodel` **shall** first resolve the selected `AASSubmodelFileType` and then apply, for the
calling Session, the exact effective `RolePermissions`, `UserRolePermissions`, disclosure tier,
authorization policy and access decision that direct `FileType.Open` and `FileType.Read` apply to
that target. Permission to Call the registry Method **shall not** authorize the target resource.
Where target access is denied, the Method **shall** return `Bad_UserAccessDenied`, or
`Bad_NotFound` where the Server's policy conceals the target's existence. Before successful target
authorization it **shall not** return document bytes, `Format`, `ContentType`, size, digest or other
target metadata, and **shall** use the same externally observable failure behavior, including
response timing, for a concealed unauthorized target and a nonexistent target.

A Server **should** bound the results returned for an unauthenticated collection query. A registry
serving regulated product data is subject to requirements to prevent bulk extraction of its
contents, and an unbounded collection endpoint is exactly such an extraction surface.

#### Federation {#sec-federation-x}

Federation follows the base model. A shell or submodel this registry describes but does not host
carries an `ExternalReference` — an `ExpandedNodeId` whose `ServerUri` identifies the hosting
endpoint and whose `NamespaceUri` and identifier identify the entity — or a `ResourceUrl` for a
registry served over a different protocol.

The identity rule is absolute: identity is carried by the AAS identifier attributes and the
identifier derived from them, never by an endpoint. A Server exposing a local proxy for a remote
entity **shall** retain the remote entity's identifier attributes and **shall not** treat its own
endpoint as part of that entity's identity. The external authority identifies the serving endpoint,
not the entity.

Every resolution of `ExternalReference.ServerUri` or `ResourceUrl` is an egress operation over
untrusted registry metadata. A resolver **shall** apply the fail-closed federation policy of the
AAS xRegistry binding before opening a connection: configured scheme, host and port allowlists;
DNS resolution and connected-address checks that reject loopback, link-local, private,
unique-local, unspecified, multicast, reserved and cloud-metadata destinations unless explicitly
trusted; revalidation on every redirect and after connection to prevent DNS rebinding; finite
redirect, time, response and decompressed-size bounds; and no ambient cookies, credentials,
authorization headers or proxy credentials. A credential configured for one peer **shall not** be
sent to another peer or redirect target.

For an OPC UA peer, the resolver **shall** validate the endpoint certificate against its configured
trust list and **shall** require the certificate ApplicationUri, the Server ApplicationUri returned
by discovery and the configured federation-peer identity to agree. A policy, DNS, redirect,
credential, certificate, identity or resource-bound failure **shall** terminate resolution without
returning or caching any bytes obtained from the rejected destination.

Because the construction of clause 6.5.3 is deterministic, the same shell has the same identifier in
every registry that describes it, and a Client moving between registries re-resolves nothing.

#### Information disclosure tiers {#sec-information-disclosure-tiers}

Some assets carry data that cannot be shown to everyone: a product passport is public in part and
restricted in part, and a supplier's technical data is commercially sensitive.

An **information disclosure tier** is the class of caller an entity's content may be released to.
This specification defines two, `Public` and `Controlled`, carried by the `DisclosureTier` Property.
They classify the *information*, not the caller and not the transport: a tier says what kind of
release this entity's content is, and leaves who may obtain it to the authorization the entity
advertises. A regulation that names finer classes maps them onto these two by deciding, for each,
whether the content is readable without authentication.

Note that a disclosure tier is metadata about content, and is therefore itself disclosed. A Server
that must not reveal even the existence of controlled content omits those entries entirely rather
than marking them; see the mitigations below.

This specification expresses two of the three things tiering requires, and does not express the
third.

**Segmentation** is expressible: a registry serves public content as stored documents and represents
controlled content as entries carrying a `ResourceUrl` or an `ExternalReference` instead of bytes.

**Advertisement** is expressible: `DisclosureTier` records whether an entity is readable without
authentication, and `Authorization` describes the authorization options a Consumer may use — a type,
a mechanism, and the authority and resource URIs that say where authorization is obtained and what
for. `Authorization` is authorization configuration only and **shall not** carry credentials, keys
or tokens, which are supplied out of band.

**Enforcement at element granularity is not expressible.** Where a regulation requires access rights
to be enforced between two elements *within* one document, this model cannot express it: a registry
resource document is opaque bytes, and a decision that falls inside a document cannot be taken by a
model that addresses documents.

OPC UA's own access control does not close that gap. It operates on nodes, and the boundary in
question is inside a file. Two mitigations are conformant: a registry **may** publish tier-specific
resources whose documents are already the redacted projection appropriate to a tier, so that every
document is wholly one tier; and a registry **may** omit controlled entries entirely from responses
to unauthenticated Clients, since advertising that a controlled submodel exists is itself a
disclosure.

A registry that serves public data **shall not** require authentication to read it.

The same disclosure decision applies through every access path. In particular, the
`GetSubmodel` convenience Method is subject to the target-resource authorization and
existence-concealment rule of clause 6.5.5; its Method-level Call permission is never a substitute for
the target's disclosure and file-access controls.

#### The xRegistry API over OPC UA {#sec-the-xregistry-api-over-opc-ua}

The registry subtree is simultaneously an xRegistry API server: the operations are realized natively
by OPC UA Services over the same nodes, as defined by the base model and its API binding. Annex D
gives the correspondence to the HTTP binding for readers who know that one.

#### Updateable registry {#sec-updateable-registry}

Clauses 6.5.1 to 6.5.8 describe a registry that catalogues documents. A Server **may** additionally make
the registry **updateable**: a Client writes a document into the registry, and the AddressSpace of
clause 6.1 changes to match. This clause defines that profile. It is optional, it is declared by the
`AAS-UpdateableRegistry` conformance unit, and a Server that implements clauses 6.5.1 to 6.5.8 without
it is fully conformant.

**The documents are canonical; the nodes are derived.** A Server implementing this profile **shall**
be able to rebuild the entire materialized subtree from the stored documents and this specification
alone, with no additional state. A Client **shall not** assume that a materialized node survives a
change to the document it came from, except as the generation rules below allow.

**Materialization is generational, and a switch is atomic.** A Server **shall not** let a Client
observe a half-built subtree. It **prepares** the new nodes as a shadow generation beside the active
one, with the document's `LoadState` set to `Loading`; it validates them; and only then does it
**switch**, making them visible, setting `LoadState` to `Active` and incrementing
`MaterializationGeneration`. Nodes in a shadow generation are not browsable and raise no events.

**A superseded generation is retired under one documented policy.** After a switch the previous
generation becomes `Superseded`. A Server **shall** apply exactly one of two policies, deterministic
for a given call and documented by the implementation:

- **Graceful.** The superseded generation enters `Retiring`. Existing MonitoredItems, continuation
  points and in-flight requests continue to be served from it until they drain or are migrated; new
  requests use the active generation. Its nodes are removed only once the retained work has drained.
- **Immediate.** The superseded generation is retired without waiting. The Server **shall**
  invalidate every affected MonitoredItem: a data-change item reports `BadNodeIdUnknown`, an event
  item stops producing events, and subsequent monitored-item operations on either return
  `BadNodeIdUnknown`.

Graceful retirement preserves subscriptions across an update; immediate retirement applies where a
Server cannot hold two generations at once. A Server **shall** apply one of these two and **shall
not** apply a third behaviour.

**A failed document does not destroy anything.** Validation failure **shall** leave the stored
document in place, set its `LoadState` to `Failed` and record the reason. The generation that was
active **shall** keep serving, unchanged. `DesiredVersionId` records the version an operator wants
materialized and `ActiveVersionId` the version actually serving; they diverge transiently during a
switch and persistently when the desired version does not validate. That divergence is observable on
purpose, because an operator needs to see that the update they requested is not the one being
served. A Server **shall not** silently activate a version that failed validation.

**A shell is materialized whole or not at all.** A shell's document, its submodel documents and the
concept descriptions its `SemanticId`s resolve to form a closure. A Server **shall** materialize a
closure into one shadow generation and commit it as a unit: a closure with an unresolved or invalid
member **shall not** be partially activated, and no node of it becomes visible. A dependency is
resolved against the registry itself first and, failing that, through a configured federation
provider (clause 6.5.6). A Server **shall not** dereference an arbitrary URL found inside a document
while materializing it — an `ExternalReference` is federation metadata, not permission to fetch.

**Re-materializing an unchanged document changes nothing.** A document whose digest is unchanged
since it was last materialized **shall** be reported `Unchanged` and **shall not** be
re-materialized, unless `Force` is set. Re-running an unchanged call **shall** produce the same nodes
with the same NodeIds and **shall not** increment `MaterializationGeneration`. A Server **should**
compute the digest over canonical document bytes, so that reformatting a document that means the
same thing does not churn the AddressSpace.

**A committed switch is announced.** A switch changes the AddressSpace graph, so the Server
**shall** emit `GeneralModelChangeEventType` for the committed additions, removals and reference
changes, and **shall** stamp the affected nodes' `NodeVersion` so a Client can correlate a node with
the `MaterializationGeneration` that produced it. Events are emitted for committed changes only,
never for shadow-generation work.

**Deleting a document retires its nodes first.** Deleting a registry resource **shall** retire its
materialized generation before removing the stored document, under the same closure rules: a Server
**shall** refuse the deletion while another materialized document depends on it, unless the caller
asks for the dependents to be retired too, in which case those dependents are retired first and
reported.

`AutoMaterialize` states whether a stored-document change re-materializes without being asked. The
`Materialize` Method re-materializes a selection on demand whether or not `AutoMaterialize` is set,
and returns one `AASMaterializationResultDataType` per document it considered — so a caller learns
which documents were skipped, which were rebuilt and which failed, rather than only whether the call
returned good.

<!-- model-figure: root=ns=2;i=1100 require=none external=RegistryType,ResourceType  graph=figures/fig-aas-updateable-registry.mmd -->

```{figure}
id: fig-aas-updateable-registry
caption: The updateable registry profile
source: figures/AAS-Fig13-UpdateableRegistry.png
```

The states a document passes through are those of `AASLoadStateDataType`, and the transitions are
the rules above rather than an implementation's choice:

```{figure}
id: fig-aas-materialization-lifecycle
caption: Materialization lifecycle of one stored document
source: figures/AAS-Fig14-MaterializationLifecycle.png
```

**Implementer notes.** This subclause is informative.

- *NodeId stability.* The NodeIds of clause 6.1.3 are the escaped, length-prefixed encodings of the
  AAS identifier and `idShortPath`, not values allocated by the Server. Two generations of the same
  document therefore contain the *same* NodeIds. A shadow generation must be held in a separate
  node table until the switch, not merged into the live one, or the preparation itself becomes
  visible.
- *Retirement and NodeId reuse together.* Under graceful retirement two generations exist at once
  with overlapping NodeIds. A Session that resolved a NodeId before the switch must continue to
  reach the generation it started with; resolving NodeId to node per Session-and-generation rather
  than globally is the straightforward way to get this right.
- *Digest before parse.* Compute the digest and compare it before parsing. A registry of any size
  spends nearly all of a periodic re-materialization discovering that nothing changed.
- *The closure is not the document.* A submodel document that validates on its own can still fail a
  closure because a concept description it references is missing. Report the failure against the
  document the operator wrote, naming the unresolved member — reporting it against the missing
  document tells the operator nothing they can act on.

The *OPC UA — WoT Connectivity* draft, currently under OPC Foundation review, defines the same
canonical-document-and-derived-projection discipline for a registry of Thing Descriptions. The rules
above are stated here in full rather than incorporated by reference.

#### Environment documents {#sec-environment-documents}

This clause applies to a Server that implements both halves — that is, one claiming `AAS-Registry`
together with `AAS-InstanceMaterialization`. Such a Server **shall** claim `AAS-EnvironmentExport`
and satisfy this clause.

For each `AASEnvironmentType` folder it materializes, the registry **shall** hold at least one
`AASEnvironmentFileType` resource whose file content is a serialization of that environment. The
`Format` attribute states which serialization; a Server **shall** offer at least the AAS JSON
environment document (`aas/3.0+json`) and the AASX package (`aasx/3.0`), and **may** offer the AAS
XML environment document (`aas/3.0+xml`). `EnvironmentNode` identifies the folder the document
serializes. The document is retrieved with the File Transfer Methods of clause 6.5.1, like any other
registry resource.

**The document covers the whole environment.** A serialization **shall** contain every shell,
submodel, concept description and submodel element materialized under that folder, serialized per
clauses 6.1 and 6.4. A Server **shall not** offer a document that covers part of an environment under
this type; a partial export is a submodel document (clause 6.5.2) or a package (clause 6.5.2), not an
environment document.

**The document is filtered to the caller's permissions.** The content served to a Session **shall**
contain only what that Session is permitted to read. A node the Session could not Browse or Read
**shall** be absent from the document, together with everything beneath it. Filtering **shall** be
applied at the point of retrieval, not at the point the document was written, so a Session never
obtains content through a document that the AddressSpace would have withheld from it.

Filtering interacts with three earlier rules, and the interaction is resolved in favour of the
permission check:

- **Absent versus empty (clause 6.1.5) is not re-derived from filtering.** A field removed by
  filtering **shall** be omitted as though absent. A Consumer **shall not** infer from a filtered
  document that a field was absent in the environment.
- **A filtered document is not lossless.** Clause 6.4 applies to an unfiltered serialization. A Server
  **shall** set `Filtered` on the resource to indicate that the content served to this Session omits
  content, and **shall not** publish a `Digest` for a document whose bytes depend on the caller.
- **Disclosure tiers (clause 6.5.7) apply to the document itself.** `DisclosureTier` and
  `Authorization` on the resource describe the document; they do not substitute for the per-node
  permission check above.

A Server **may** materialize the document on demand rather than storing it, provided the result is
identical to a stored document filtered the same way.

<!-- model-figure: root=ns=2;i=1100 require=none external=RegistryType,ResourceType  graph=figures/fig-aas-environment-document.mmd -->

```{figure}
id: fig-aas-environment-document
caption: The materialized environment served as a retrievable document
source: figures/AAS-Fig15-EnvironmentDocument.png
```

---

## OPC UA ObjectTypes {#sec-opc-ua-objecttypes}

### `AASReferableType` {#sec-aasreferabletype}

Abstract base of everything in the metamodel that can be referred to by a short name. Carries the identifying and descriptive attributes every element has.

*Table - AASReferableType Definition* {#tbl-aasreferabletype-definition defines=AASReferableType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASReferableType |  |  |  |  |
| IsAbstract | True |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:BaseObjectType defined in OPC 10000-5 |  |  |  |  |  |
| 0:HasProperty | Variable | 2:IdShort | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:Category | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:DisplayNameSet | 2:AASLangStringDataType[] | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:DescriptionSet | 2:AASLangStringDataType[] | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:Extensions | 2:AASExtensionDataType[] | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:ModelType | 0:String | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AAS-Metamodel |  |  |  |  |  |

### `AASIdentifiableType` {#sec-aasidentifiabletype}

Abstract base of the metamodel elements that carry a globally unique identifier: shells, submodels and concept descriptions.

*Table - AASIdentifiableType Definition* {#tbl-aasidentifiabletype-definition defines=AASIdentifiableType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASIdentifiableType |  |  |  |  |
| IsAbstract | True |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 2:AASReferableType defined in [](#sec-aasreferabletype) |  |  |  |  |  |
| 0:HasProperty | Variable | 2:Id | 0:String | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:Administration | 2:AASAdministrativeInformationDataType | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AAS-Metamodel |  |  |  |  |  |

### `AASHasSemanticsType` {#sec-aashassemanticstype}

Abstract base of the elements that declare what concept they are an occurrence of.

*Table - AASHasSemanticsType Definition* {#tbl-aashassemanticstype-definition defines=AASHasSemanticsType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASHasSemanticsType |  |  |  |  |
| IsAbstract | True |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:BaseObjectType defined in OPC 10000-5 |  |  |  |  |  |
| 0:HasProperty | Variable | 2:SemanticId | 2:AASReferenceDataType | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:SupplementalSemanticIds | 2:AASReferenceDataType[] | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AAS-Metamodel |  |  |  |  |  |

### `AASHasKindType` {#sec-aashaskindtype}

Abstract base of the elements that distinguish a template from an instance.

*Table - AASHasKindType Definition* {#tbl-aashaskindtype-definition defines=AASHasKindType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASHasKindType |  |  |  |  |
| IsAbstract | True |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:BaseObjectType defined in OPC 10000-5 |  |  |  |  |  |
| 0:HasProperty | Variable | 2:Kind | 2:AASModellingKindDataType | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AAS-Metamodel |  |  |  |  |  |

### `AASHasDataSpecificationType` {#sec-aashasdataspecificationtype}

Abstract base of the elements that carry data specifications.

*Table - AASHasDataSpecificationType Definition* {#tbl-aashasdataspecificationtype-definition defines=AASHasDataSpecificationType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASHasDataSpecificationType |  |  |  |  |
| IsAbstract | True |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:BaseObjectType defined in OPC 10000-5 |  |  |  |  |  |
| 0:HasProperty | Variable | 2:EmbeddedDataSpecifications | 2:AASEmbeddedDataSpecificationDataType[] | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AAS-Metamodel |  |  |  |  |  |

### `AASQualifiableType` {#sec-aasqualifiabletype}

Abstract base of the elements that can be qualified.

*Table - AASQualifiableType Definition* {#tbl-aasqualifiabletype-definition defines=AASQualifiableType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASQualifiableType |  |  |  |  |
| IsAbstract | True |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:BaseObjectType defined in OPC 10000-5 |  |  |  |  |  |
| 0:HasProperty | Variable | 2:Qualifiers | 2:AASQualifierDataType[] | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AAS-Metamodel |  |  |  |  |  |

### `AASEnvironmentType` {#sec-aasenvironmenttype}

The container of shells, submodels and concept descriptions - the unit an AAS serialization carries and the root a source generator materializes into a Server.

*Table - AASEnvironmentType Definition* {#tbl-aasenvironmenttype-definition defines=AASEnvironmentType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASEnvironmentType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:FolderType defined in OPC 10000-5 |  |  |  |  |  |
| 0:Organizes | Object | 2:<AssetAdministrationShell> |  | 2:AASType | OP |
| 0:Organizes | Object | 2:<Submodel> |  | 2:AASSubmodelType | OP |
| 0:Organizes | Object | 2:<ConceptDescription> |  | 2:AASConceptDescriptionType | OP |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AAS-Metamodel |  |  |  |  |  |
| AAS-InstanceMaterialization |  |  |  |  |  |

### `AASType` {#sec-aastype}

An Asset Administration Shell: the digital representation of one asset, carrying the asset's identity and references to the submodels that describe it.

*Table - AASType Definition* {#tbl-aastype-definition defines=AASType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 2:AASIdentifiableType defined in [](#sec-aasidentifiabletype) |  |  |  |  |  |
| 0:HasComponent | Object | 2:AssetInformation |  | 2:AASAssetInformationType | M |
| 0:HasProperty | Variable | 2:SubmodelReferences | 2:AASReferenceDataType[] | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:DerivedFrom | 2:AASReferenceDataType | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:EmbeddedDataSpecifications | 2:AASEmbeddedDataSpecificationDataType[] | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AAS-Metamodel |  |  |  |  |  |
| AAS-InstanceMaterialization |  |  |  |  |  |

### `AASAssetInformationType` {#sec-aasassetinformationtype}

The identity of the asset a shell represents, as distinct from the identity of the shell itself.

*Table - AASAssetInformationType Definition* {#tbl-aasassetinformationtype-definition defines=AASAssetInformationType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASAssetInformationType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:BaseObjectType defined in OPC 10000-5 |  |  |  |  |  |
| 0:HasProperty | Variable | 2:AssetKind | 2:AASAssetKindDataType | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:GlobalAssetId | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:AssetType | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:SpecificAssetIds | 2:AASSpecificAssetIdDataType[] | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:DefaultThumbnail | 2:AASResourceDataType | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AAS-Metamodel |  |  |  |  |  |

### `AASSubmodelType` {#sec-aassubmodeltype}

One coherent aspect of an asset, identified in its own right and typed by its SemanticId: a nameplate, technical data, a carbon footprint, a bill of material.

*Table - AASSubmodelType Definition* {#tbl-aassubmodeltype-definition defines=AASSubmodelType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASSubmodelType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 2:AASIdentifiableType defined in [](#sec-aasidentifiabletype) |  |  |  |  |  |
| 0:HasProperty | Variable | 2:Kind | 2:AASModellingKindDataType | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:SemanticId | 2:AASReferenceDataType | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:SupplementalSemanticIds | 2:AASReferenceDataType[] | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:Qualifiers | 2:AASQualifierDataType[] | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:EmbeddedDataSpecifications | 2:AASEmbeddedDataSpecificationDataType[] | 0:PropertyType | O |
| 0:HasComponent | Object | 2:<SubmodelElement> |  | 2:AASSubmodelElementType | OP |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AAS-Metamodel |  |  |  |  |  |
| AAS-InstanceMaterialization |  |  |  |  |  |

### `AASConceptDescriptionType` {#sec-aasconceptdescriptiontype}

The definition a SemanticId resolves to - what makes two submodels from different vendors comparable.

*Table - AASConceptDescriptionType Definition* {#tbl-aasconceptdescriptiontype-definition defines=AASConceptDescriptionType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASConceptDescriptionType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 2:AASIdentifiableType defined in [](#sec-aasidentifiabletype) |  |  |  |  |  |
| 0:HasProperty | Variable | 2:IsCaseOf | 2:AASReferenceDataType[] | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:EmbeddedDataSpecifications | 2:AASEmbeddedDataSpecificationDataType[] | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AAS-Metamodel |  |  |  |  |  |

### `AASSubmodelElementType` {#sec-aassubmodelelementtype}

Abstract base of every element that can appear inside a submodel.

*Table - AASSubmodelElementType Definition* {#tbl-aassubmodelelementtype-definition defines=AASSubmodelElementType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASSubmodelElementType |  |  |  |  |
| IsAbstract | True |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 2:AASReferableType defined in [](#sec-aasreferabletype) |  |  |  |  |  |
| 0:HasProperty | Variable | 2:SemanticId | 2:AASReferenceDataType | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:SupplementalSemanticIds | 2:AASReferenceDataType[] | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:Qualifiers | 2:AASQualifierDataType[] | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:EmbeddedDataSpecifications | 2:AASEmbeddedDataSpecificationDataType[] | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:Index | 0:UInt32 | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AAS-SubmodelElements |  |  |  |  |  |

### `AASPropertyType` {#sec-aaspropertytype}

A single typed value. The value node carries the OPC UA DataType clause 6.3.1 assigns to the declared xsd type, from which the declared type is read.

*Table - AASPropertyType Definition* {#tbl-aaspropertytype-definition defines=AASPropertyType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASPropertyType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 2:AASSubmodelElementType defined in [](#sec-aassubmodelelementtype) |  |  |  |  |  |
| 0:HasProperty | Variable | 2:ValueType | 2:AASDataTypeDefXsdDataType | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:Value | 0:BaseDataType | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:ValueId | 2:AASReferenceDataType | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AAS-SubmodelElements |  |  |  |  |  |
| AAS-ValueFidelity |  |  |  |  |  |

### `AASMultiLanguagePropertyType` {#sec-aasmultilanguagepropertytype}

A value expressed in one or more languages. The array order is preserved, because the metamodel's serialization is ordered and a round trip that reordered it would not reproduce its input.

*Table - AASMultiLanguagePropertyType Definition* {#tbl-aasmultilanguagepropertytype-definition defines=AASMultiLanguagePropertyType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASMultiLanguagePropertyType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 2:AASSubmodelElementType defined in [](#sec-aassubmodelelementtype) |  |  |  |  |  |
| 0:HasProperty | Variable | 2:Value | 2:AASLangStringDataType[] | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:ValueId | 2:AASReferenceDataType | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AAS-SubmodelElements |  |  |  |  |  |
| AAS-ValueFidelity |  |  |  |  |  |

### `AASRangeType` {#sec-aasrangetype}

A closed or half-open interval of a single typed value.

*Table - AASRangeType Definition* {#tbl-aasrangetype-definition defines=AASRangeType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASRangeType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 2:AASSubmodelElementType defined in [](#sec-aassubmodelelementtype) |  |  |  |  |  |
| 0:HasProperty | Variable | 2:ValueType | 2:AASDataTypeDefXsdDataType | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:Min | 0:BaseDataType | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:Max | 0:BaseDataType | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AAS-SubmodelElements |  |  |  |  |  |
| AAS-ValueFidelity |  |  |  |  |  |

### `AASBlobType` {#sec-aasblobtype}

Binary content carried inline.

*Table - AASBlobType Definition* {#tbl-aasblobtype-definition defines=AASBlobType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASBlobType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 2:AASSubmodelElementType defined in [](#sec-aassubmodelelementtype) |  |  |  |  |  |
| 0:HasProperty | Variable | 2:Value | 0:ByteString | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:ContentType | 0:String | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AAS-SubmodelElements |  |  |  |  |  |
| AAS-ValueFidelity |  |  |  |  |  |

### `AASFileType` {#sec-aasfiletype}

A pointer to content held outside the element.

*Table - AASFileType Definition* {#tbl-aasfiletype-definition defines=AASFileType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASFileType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 2:AASSubmodelElementType defined in [](#sec-aassubmodelelementtype) |  |  |  |  |  |
| 0:HasProperty | Variable | 2:Value | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:ContentType | 0:String | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AAS-SubmodelElements |  |  |  |  |  |
| AAS-ValueFidelity |  |  |  |  |  |

### `AASReferenceElementType` {#sec-aasreferenceelementtype}

An element whose value is a reference.

*Table - AASReferenceElementType Definition* {#tbl-aasreferenceelementtype-definition defines=AASReferenceElementType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASReferenceElementType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 2:AASSubmodelElementType defined in [](#sec-aassubmodelelementtype) |  |  |  |  |  |
| 0:HasProperty | Variable | 2:Value | 2:AASReferenceDataType | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AAS-SubmodelElements |  |  |  |  |  |

### `AASRelationshipElementType` {#sec-aasrelationshipelementtype}

A directed relationship between two referenced things.

*Table - AASRelationshipElementType Definition* {#tbl-aasrelationshipelementtype-definition defines=AASRelationshipElementType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASRelationshipElementType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 2:AASSubmodelElementType defined in [](#sec-aassubmodelelementtype) |  |  |  |  |  |
| 0:HasProperty | Variable | 2:First | 2:AASReferenceDataType | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:Second | 2:AASReferenceDataType | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AAS-SubmodelElements |  |  |  |  |  |

### `AASAnnotatedRelationshipElementType` {#sec-aasannotatedrelationshipelementtype}

A relationship carrying data elements that annotate it, such as a quantity or a position.

*Table - AASAnnotatedRelationshipElementType Definition* {#tbl-aasannotatedrelationshipelementtype-definition defines=AASAnnotatedRelationshipElementType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASAnnotatedRelationshipElementType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 2:AASRelationshipElementType defined in [](#sec-aasrelationshipelementtype) |  |  |  |  |  |
| 0:HasComponent | Object | 2:<Annotation> |  | 2:AASSubmodelElementType | OP |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AAS-SubmodelElements |  |  |  |  |  |

### `AASSubmodelElementCollectionType` {#sec-aassubmodelelementcollectiontype}

An unordered set of elements, each identified by its own IdShort.

*Table - AASSubmodelElementCollectionType Definition* {#tbl-aassubmodelelementcollectiontype-definition defines=AASSubmodelElementCollectionType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASSubmodelElementCollectionType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 2:AASSubmodelElementType defined in [](#sec-aassubmodelelementtype) |  |  |  |  |  |
| 0:HasComponent | Object | 2:<SubmodelElement> |  | 2:AASSubmodelElementType | OP |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AAS-SubmodelElements |  |  |  |  |  |
| AAS-LosslessRoundTrip |  |  |  |  |  |

### `AASSubmodelElementListType` {#sec-aassubmodelelementlisttype}

A list of elements. Its members have no IdShort, so they are named by index. Whether the order carries meaning is stated by the ReferenceType on each instance, not by a Property: HasOrderedComponent where it does, HasComponent where the list is a set or a bag. The declaration uses HasComponent, the base of both legal instance forms.

*Table - AASSubmodelElementListType Definition* {#tbl-aassubmodelelementlisttype-definition defines=AASSubmodelElementListType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASSubmodelElementListType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 2:AASSubmodelElementType defined in [](#sec-aassubmodelelementtype) |  |  |  |  |  |
| 0:HasProperty | Variable | 2:TypeValueListElement | 2:AASSubmodelElementsDataType | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:SemanticIdListElement | 2:AASReferenceDataType | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:ValueTypeListElement | 2:AASDataTypeDefXsdDataType | 0:PropertyType | O |
| 0:HasComponent | Object | 2:<Element> |  | 2:AASSubmodelElementType | OP |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AAS-SubmodelElements |  |  |  |  |  |
| AAS-LosslessRoundTrip |  |  |  |  |  |

### `AASEntityType` {#sec-aasentitytype}

A component of a composition. A self-managed entity carries the identifier of its own shell, so a bill of material is traversable across organizations.

*Table - AASEntityType Definition* {#tbl-aasentitytype-definition defines=AASEntityType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASEntityType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 2:AASSubmodelElementType defined in [](#sec-aassubmodelelementtype) |  |  |  |  |  |
| 0:HasProperty | Variable | 2:EntityType | 2:AASEntityTypeDataType | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:GlobalAssetId | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:SpecificAssetIds | 2:AASSpecificAssetIdDataType[] | 0:PropertyType | O |
| 0:HasComponent | Object | 2:<Statement> |  | 2:AASSubmodelElementType | OP |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AAS-SubmodelElements |  |  |  |  |  |

### `AASBasicEventElementType` {#sec-aasbasiceventelementtype}

An event source or sink.

*Table - AASBasicEventElementType Definition* {#tbl-aasbasiceventelementtype-definition defines=AASBasicEventElementType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASBasicEventElementType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 2:AASSubmodelElementType defined in [](#sec-aassubmodelelementtype) |  |  |  |  |  |
| 0:HasProperty | Variable | 2:Observed | 2:AASReferenceDataType | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:Direction | 2:AASDirectionDataType | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:State | 2:AASStateOfEventDataType | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:MessageTopic | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:MessageBroker | 2:AASReferenceDataType | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:LastUpdate | 0:DateTime | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:MinInterval | 0:DurationString | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:MaxInterval | 0:DurationString | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AAS-SubmodelElements |  |  |  |  |  |

### `AASOperationType` {#sec-aasoperationtype}

An invocable operation.

*Table - AASOperationType Definition* {#tbl-aasoperationtype-definition defines=AASOperationType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASOperationType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 2:AASSubmodelElementType defined in [](#sec-aassubmodelelementtype) |  |  |  |  |  |
| 0:HasProperty | Variable | 2:InputVariables | 2:AASOperationVariableDataType[] | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:OutputVariables | 2:AASOperationVariableDataType[] | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:InoutputVariables | 2:AASOperationVariableDataType[] | 0:PropertyType | O |
| 0:HasComponent | Object | 2:<Variable> |  | 2:AASSubmodelElementType | OP |
| 0:HasComponent | Method | 2:Invoke |  |  | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AAS-SubmodelElements |  |  |  |  |  |

#### Invoke {#sec-aasoperationtype-invoke type=AASOperationType method=Invoke}

Invoke the operation and return its results. The Call counterpart of InvokeOperation in the AAS API of IDTA-01002 Part 2: a Client that has browsed to the Operation element calls this rather than reaching for the HTTP interface, and the two carry the same arguments in the same order.

**Signature**

```text
Invoke (
  [in]  0:BaseDataType[] InputValues,
  [in]  0:BaseDataType[] InoutputValues,
  [in]  0:Duration       ClientTimeout,
  [out] 0:BaseDataType[] OutputValues,
  [out] 0:BaseDataType[] InoutputResults,
  [out] 0:Boolean        Success,
  [out] 0:String         Diagnostic);
```

*Table - Invoke Method Arguments* {#tbl-invoke-method-arguments}

| **Argument** | **Description** |
| --- | --- |
| InputValues | Values for the operation's input variables, positionally matching InputVariables. |
| InoutputValues | Values for the operation's in-out variables, positionally matching InoutputVariables. |
| ClientTimeout | How long the caller will wait. Zero means the Server's default. Corresponds to clientTimeoutDuration of the AAS API request. |
| OutputValues | Results, positionally matching OutputVariables. |
| InoutputResults | The in-out variables after execution, positionally matching InoutputVariables. |
| Success | Whether the operation executed successfully. A false result is an executed operation that failed, not a failed Call. |
| Diagnostic | Why the operation failed, where it did. |

### `AASCapabilityType` {#sec-aascapabilitytype}

A declared capability of the asset. It carries no value of its own; the element's identity and semantics are the whole of its content.

*Table - AASCapabilityType Definition* {#tbl-aascapabilitytype-definition defines=AASCapabilityType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASCapabilityType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 2:AASSubmodelElementType defined in [](#sec-aassubmodelelementtype) |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AAS-SubmodelElements |  |  |  |  |  |

### `AASRegistryType` {#sec-aasregistrytype}

The AAS Registry root - an xRegistry RegistryType, and therefore a FolderType - whose group folders hold shells, submodel templates, concept dictionaries and packages. Exposed as a well-known object under the Server object, so any Client that reaches the standard Server object discovers it.

*Table - AASRegistryType Definition* {#tbl-aasregistrytype-definition defines=AASRegistryType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASRegistryType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 1:RegistryType defined in OPC 99004-1 |  |  |  |  |  |
| 0:Organizes | Object | 2:<ShellGroup> |  | 2:AASShellGroupType | OP |
| 0:Organizes | Object | 2:<SubmodelTemplateGroup> |  | 2:AASSubmodelTemplateGroupType | OP |
| 0:Organizes | Object | 2:<ConceptDictionaryGroup> |  | 2:AASConceptDictionaryGroupType | OP |
| 0:Organizes | Object | 2:<PackageStoreGroup> |  | 2:AASPackageStoreGroupType | OP |
| 0:Organizes | Object | 2:<Environment> |  | 2:AASEnvironmentFileType | OP |
| 0:HasComponent | Method | 2:LookupShellsByAssetLink |  |  | O |
| 0:HasComponent | Method | 2:GetSubmodel |  |  | O |
| 0:HasProperty | Variable | 2:AutoMaterialize | 0:Boolean | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:MaterializationGeneration | 0:UInt32 | 0:PropertyType | O |
| 0:HasComponent | Method | 2:Materialize |  |  | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AAS-Registry |  |  |  |  |  |
| AAS-Discovery |  |  |  |  |  |
| AAS-UpdateableRegistry |  |  |  |  |  |
| AAS-EnvironmentExport |  |  |  |  |  |

#### LookupShellsByAssetLink {#sec-aasregistrytype-lookupshellsbyassetlink type=AASRegistryType method=LookupShellsByAssetLink}

Return the shells discoverable by an asset key. This is the discovery question - given a serial number or a part identifier, which shells describe it - answered without the caller browsing the whole collection.

**Signature**

```text
LookupShellsByAssetLink (
  [in]  0:String   Name,
  [in]  0:String   Value,
  [out] 0:NodeId[] Shells);
```

*Table - LookupShellsByAssetLink Method Arguments* {#tbl-lookupshellsbyassetlink-method-arguments}

| **Argument** | **Description** |
| --- | --- |
| Name | The key name, for example serialNumber. |
| Value | The key value. |
| Shells | The shell group nodes matching the key. |

#### GetSubmodel {#sec-aasregistrytype-getsubmodel type=AASRegistryType method=GetSubmodel}

Resolve the selected AASSubmodelFileType before returning its document and enforce the same Session-specific effective RolePermissions, UserRolePermissions, DisclosureTier, Authorization and FileType Open/Read decision as direct access to that target. Call permission on this Method does not authorize the target. Return Bad_UserAccessDenied, or Bad_NotFound where policy conceals existence, without exposing controlled bytes, Format, ContentType, other target metadata or a distinguishable timing path.

**Signature**

```text
GetSubmodel (
  [in]  0:String     SubmodelIdentifier,
  [out] 0:ByteString Document,
  [out] 0:String     Format,
  [out] 0:String     ContentType);
```

*Table - GetSubmodel Method Arguments* {#tbl-getsubmodel-method-arguments}

| **Argument** | **Description** |
| --- | --- |
| SubmodelIdentifier | The submodel's authored identifier. |
| Document | The submodel document bytes. |
| Format | xRegistry format string. |
| ContentType | Document media type. |

#### Materialize {#sec-aasregistrytype-materialize type=AASRegistryType method=Materialize}

Re-materialize the AddressSpace from the stored documents. Part of the updateable registry profile: the documents are canonical and the nodes are derived, so this is the operation that makes the derived side agree with the canonical one.

**Signature**

```text
Materialize (
  [in]  0:String[]                           Targets,
  [in]  0:Boolean                            Force,
  [out] 0:UInt32                             Generation,
  [out] 2:AASMaterializationResultDataType[] Results);
```

*Table - Materialize Method Arguments* {#tbl-materialize-method-arguments}

| **Argument** | **Description** |
| --- | --- |
| Targets | The documents to consider, as registry-relative paths. An empty array means every document. |
| Force | Re-materialize even a document whose digest is unchanged. |
| Generation | The generation in force after the call. |
| Results | One result per document considered. |

### `AASShellGroupType` {#sec-aasshellgrouptype}

An xRegistry GroupType holding the submodel documents of one shell. Its source identity is the shell's authored identifier, from which the GroupId is constructed. It is distinct from AASType, which models the same shell as a live node tree rather than as a catalogue entry.

*Table - AASShellGroupType Definition* {#tbl-aasshellgrouptype-definition defines=AASShellGroupType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASShellGroupType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 1:GroupType defined in OPC 99004-1 |  |  |  |  |  |
| 0:HasProperty | Variable | 2:AasIdentifier | 0:String | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:AssetKind | 2:AASAssetKindDataType | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:GlobalAssetId | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:AssetType | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:SpecificAssetIds | 2:AASSpecificAssetIdDataType[] | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:Administration | 2:AASAdministrativeInformationDataType | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:DerivedFrom | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:DisclosureTier | 2:AASDisclosureTierDataType | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:Authorization | 2:AASAuthorizationOptionDataType[] | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:EventEndpoint | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:ShellNode | 0:NodeId | 0:PropertyType | O |
| 0:Organizes | Object | 2:<Submodel> |  | 2:AASSubmodelFileType | OP |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AAS-Registry |  |  |  |  |  |
| AAS-RegistryIdentity |  |  |  |  |  |
| AAS-Discovery |  |  |  |  |  |
| AAS-DisclosureTiers |  |  |  |  |  |

### `AASSubmodelFileType` {#sec-aassubmodelfiletype}

An xRegistry ResourceType whose file content is one submodel document. Each version is one revision, which is what gives a shell the lifecycle history the metamodel does not itself provide.

*Table - AASSubmodelFileType Definition* {#tbl-aassubmodelfiletype-definition defines=AASSubmodelFileType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASSubmodelFileType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 1:ResourceType defined in OPC 99004-1 |  |  |  |  |  |
| 0:HasProperty | Variable | 2:SubmodelIdentifier | 0:String | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:SemanticId | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:SupplementalSemanticIds | 0:String[] | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:Kind | 2:AASModellingKindDataType | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:Template | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:Digest | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:DigestAlg | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:IsDefault | 0:Boolean | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:Ancestor | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:DisclosureTier | 2:AASDisclosureTierDataType | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:Authorization | 2:AASAuthorizationOptionDataType[] | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:SubmodelNode | 0:NodeId | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:LoadState | 2:AASLoadStateDataType | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:DesiredVersionId | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:ActiveVersionId | 0:String | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AAS-Registry |  |  |  |  |  |
| AAS-RegistryIdentity |  |  |  |  |  |
| AAS-RegistryVersioning |  |  |  |  |  |
| AAS-DisclosureTiers |  |  |  |  |  |
| AAS-UpdateableRegistry |  |  |  |  |  |

### `AASSubmodelTemplateGroupType` {#sec-aassubmodeltemplategrouptype}

An xRegistry GroupType holding one publisher's family of submodel templates. Templates are held in a group of their own so that a Consumer lists templates and instances separately.

*Table - AASSubmodelTemplateGroupType Definition* {#tbl-aassubmodeltemplategrouptype-definition defines=AASSubmodelTemplateGroupType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASSubmodelTemplateGroupType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 1:GroupType defined in OPC 99004-1 |  |  |  |  |  |
| 0:HasProperty | Variable | 2:TemplateNamespace | 0:String | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:Publisher | 0:String | 0:PropertyType | O |
| 0:Organizes | Object | 2:<Submodel> |  | 2:AASSubmodelFileType | OP |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AAS-Registry |  |  |  |  |  |
| AAS-RegistryIdentity |  |  |  |  |  |

### `AASConceptDictionaryGroupType` {#sec-aasconceptdictionarygrouptype}

An xRegistry GroupType holding one dictionary of concept definitions - the definitions a SemanticId elsewhere in the registry resolves to.

*Table - AASConceptDictionaryGroupType Definition* {#tbl-aasconceptdictionarygrouptype-definition defines=AASConceptDictionaryGroupType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASConceptDictionaryGroupType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 1:GroupType defined in OPC 99004-1 |  |  |  |  |  |
| 0:HasProperty | Variable | 2:DictionaryIdentifier | 0:String | 0:PropertyType | M |
| 0:Organizes | Object | 2:<ConceptDescription> |  | 2:AASConceptDescriptionFileType | OP |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AAS-Registry |  |  |  |  |  |
| AAS-RegistryIdentity |  |  |  |  |  |

### `AASConceptDescriptionFileType` {#sec-aasconceptdescriptionfiletype}

An xRegistry ResourceType whose file content is one concept description document.

*Table - AASConceptDescriptionFileType Definition* {#tbl-aasconceptdescriptionfiletype-definition defines=AASConceptDescriptionFileType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASConceptDescriptionFileType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 1:ResourceType defined in OPC 99004-1 |  |  |  |  |  |
| 0:HasProperty | Variable | 2:ConceptIdentifier | 0:String | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:IsCaseOf | 0:String[] | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:ConceptNode | 0:NodeId | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:LoadState | 2:AASLoadStateDataType | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:DesiredVersionId | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:ActiveVersionId | 0:String | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AAS-Registry |  |  |  |  |  |
| AAS-RegistryIdentity |  |  |  |  |  |
| AAS-UpdateableRegistry |  |  |  |  |  |

### `AASPackageStoreGroupType` {#sec-aaspackagestoregrouptype}

An xRegistry GroupType holding packages - one store, or one namespace within one.

*Table - AASPackageStoreGroupType Definition* {#tbl-aaspackagestoregrouptype-definition defines=AASPackageStoreGroupType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASPackageStoreGroupType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 1:GroupType defined in OPC 99004-1 |  |  |  |  |  |
| 0:HasProperty | Variable | 2:StoreIdentifier | 0:String | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:RegistryUrl | 0:String | 0:PropertyType | O |
| 0:Organizes | Object | 2:<Package> |  | 2:AASPackageFileType | OP |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AAS-Packages |  |  |  |  |  |
| AAS-RegistryIdentity |  |  |  |  |  |

### `AASPackageFileType` {#sec-aaspackagefiletype}

An xRegistry ResourceType whose file content is one package. Every package carries mandatory strong integrity metadata for the exact returned blob; an OCI-backed version also carries the immutable manifest digest that is its version identity. Mutable tags are Resource-level discovery aliases, never Version identity, and OCI referrers are separate Resources rather than package Versions and cannot affect the package default Version.

*Table - AASPackageFileType Definition* {#tbl-aaspackagefiletype-definition defines=AASPackageFileType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASPackageFileType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 1:ResourceType defined in OPC 99004-1 |  |  |  |  |  |
| 0:HasProperty | Variable | 2:PackageIdentifier | 0:String | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:ArtifactType | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:Digest | 0:String | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:DigestAlg | 0:String | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:AasIdentifiers | 0:String[] | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:ManifestDigest | 0:String | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AAS-Packages |  |  |  |  |  |
| AAS-RegistryIdentity |  |  |  |  |  |
| AAS-PackageIntegrity |  |  |  |  |  |

### `AASEnvironmentFileType` {#sec-aasenvironmentfiletype}

An xRegistry ResourceType whose file content is one serialization of a materialized environment: an AAS JSON or XML environment document, or an AASX package. It is the retrievable form of an AASEnvironmentType folder, and its content is filtered to what the calling Session is permitted to read.

---

*Table - AASEnvironmentFileType Definition* {#tbl-aasenvironmentfiletype-definition defines=AASEnvironmentFileType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASEnvironmentFileType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 1:ResourceType defined in OPC 99004-1 |  |  |  |  |  |
| 0:HasProperty | Variable | 2:EnvironmentIdentifier | 0:String | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:Format | 0:String | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:EnvironmentNode | 0:NodeId | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:Digest | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:DigestAlg | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:Filtered | 0:Boolean | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:DisclosureTier | 2:AASDisclosureTierDataType | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:Authorization | 2:AASAuthorizationOptionDataType[] | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AAS-EnvironmentExport |  |  |  |  |  |
| AAS-RegistryIdentity |  |  |  |  |  |

## OPC UA DataTypes {#sec-opc-ua-datatypes}

The DataTypes defined by this document are enumerations. Each is formally defined in the NodeSet and listed in Annex A.

---

## Instances {#sec-instances}

### `AASRegistry` {#sec-aasregistry}

Server-wide AAS Registry, a well-known component of the Server object.

---

## Profiles and conformance units {#sec-profiles-and-conformance-units}

```{clause}
kind: profiles
```

An implementation conforms to this specification if it implements at least one of the two halves and
declares the corresponding conformance units.

| Unit | Requires |
|---|---|
| `AAS-Metamodel` | Shells, submodels and concept descriptions as typed nodes. |
| `AAS-SubmodelElements` | The submodel element types. |
| `AAS-ValueFidelity` | The xsd type assignment of clauses 6.1.2 and 6.3.1. |
| `AAS-InstanceMaterialization` | Materialization per clause 6.1.6. |
| `AAS-LosslessRoundTrip` | Both directions of clause 6.4. |
| `AAS-Registry` | The registry root, groups and submodel documents. |
| `AAS-RegistryIdentity` | Source identities and derived identifiers per clause 6.5.3. |
| `AAS-RegistryVersioning` | Versions as the lifecycle record, clause 6.5.4. |
| `AAS-Discovery` | `LookupShellsByAssetLink` and `GetSubmodel`. |
| `AAS-OperationInvoke` | `AASOperationType.Invoke`, clause 6.2.5. |
| `AAS-Federation` | External references and the identity rule of clause 6.5.6. |
| `AAS-DisclosureTiers` | `DisclosureTier` and `Authorization`, clause 6.5.7. |
| `AAS-UpdateableRegistry` | Generational materialization from stored documents, clause 6.5.9. |
| `AAS-EnvironmentExport` | The materialized environment served as filtered AAS and AASX documents, clause 6.5.10. Required of a Server claiming both `AAS-Registry` and `AAS-InstanceMaterialization`. |
| `AAS-Packages` | Package stores and package resources; requires `AAS-PackageIntegrity`. |
| `AAS-PackageIntegrity` | Mandatory package-blob digest and algorithm, OCI manifest-to-blob binding, immutable identity and tag rules, referrer separation and verification requirements of clause 6.5.4. |

`AAS-Metamodel` and `AAS-SubmodelElements` together are the baseline for the metamodel half;
`AAS-Registry` and `AAS-RegistryIdentity` for the registry half. `AAS-ValueFidelity` is required by
`AAS-LosslessRoundTrip`, which is the unit that makes source generation possible. An implementation
claiming `AAS-Packages` **shall** also claim `AAS-PackageIntegrity`.

---

## Namespaces {#sec-namespaces}

### Namespace metadata {#sec-namespace-metadata}

The namespace metadata provide standardized information about the elements of this namespace, which an aggregating Server relies on. All Nodes defined by this document are static.

| Property | DataType | Value |
|---|---|---|
| NamespaceUri | String | `http://opcfoundation.org/UA/I4AAS/v3/` |
| NamespaceVersion | String | 3.00-draft4 |
| NamespacePublicationDate | DateTime | 2026-08-31 |
| IsNamespaceSubset | Boolean | False |
| StaticNodeIdTypes | IdType[] | 0 (Numeric) |
| StaticNumericNodeIdRange | NumericRange[] | 1001:9999 |
| StaticStringNodeIdPattern | String | -- |

### Handling of OPC UA namespaces {#sec-handling-of-opc-ua-namespaces}

Namespaces are used by OPC UA to create unique identifiers across different naming authorities. The following namespaces are used for BrowseNames in this document; the default namespace is not listed, because every BrowseName without a prefix uses it.

| NamespaceURI | Namespace index | Example |
|---|---|---|
| `http://opcfoundation.org/UA/` | 0 | `0:EngineeringUnits` |
| `http://opcfoundation.org/UA/xRegistry/` | 1 | `1:ResourceType` |

---

## Information model reference {#anx-a annex=normative}

```{clause}
kind: annex-a
```

## (normative) — Field coverage {#anx-b annex=normative}

This annex is normative. It is the losslessness argument in table form: every field of the AAS V3
metamodel, and where it lives in the AddressSpace. A field absent from this table is a defect.

### B.1 Referable and Identifiable {#sec-b-1-referable-and-identifiable}

| Metamodel field | Address space |
|---|---|
| `idShort` | `AASReferableType.IdShort`; absent for a list member, which is addressed by index |
| `category` | `AASReferableType.Category` |
| `displayName` | `AASReferableType.DisplayNameSet` |
| `description` | `AASReferableType.DescriptionSet` |
| `extensions` | `AASReferableType.Extensions` |
| `modelType` | `AASReferableType.ModelType`, Mandatory |
| `id` | `AASIdentifiableType.Id`, Mandatory, and input to the String NodeId encoding |
| `administration` | `AASIdentifiableType.Administration` |

### B.2 Shell and asset information {#sec-b-2-shell-and-asset-information}

| Metamodel field | Address space |
|---|---|
| `assetInformation` | `AASType.AssetInformation`, Mandatory |
| `submodels` | `AASType.SubmodelReferences` |
| `derivedFrom` | `AASType.DerivedFrom` |
| `embeddedDataSpecifications` | `AASType.EmbeddedDataSpecifications` |
| `assetKind` | `AASAssetInformationType.AssetKind`, Mandatory |
| `globalAssetId` | `AASAssetInformationType.GlobalAssetId` |
| `assetType` | `AASAssetInformationType.AssetType` |
| `specificAssetIds` | `AASAssetInformationType.SpecificAssetIds` |
| `defaultThumbnail` | `AASAssetInformationType.DefaultThumbnail` |

### B.3 Submodel and concept description {#sec-b-3-submodel-and-concept-description}

| Metamodel field | Address space |
|---|---|
| `kind` | `AASSubmodelType.Kind` |
| `semanticId` | `AASSubmodelType.SemanticId` |
| `supplementalSemanticIds` | `AASSubmodelType.SupplementalSemanticIds` |
| `qualifiers` | `AASSubmodelType.Qualifiers` |
| `embeddedDataSpecifications` | `AASSubmodelType.EmbeddedDataSpecifications` |
| `submodelElements` | `AASSubmodelType` components, one node per element |
| `isCaseOf` | `AASConceptDescriptionType.IsCaseOf` |
| `embeddedDataSpecifications` (concept) | `AASConceptDescriptionType.EmbeddedDataSpecifications` |

### B.4 Submodel elements {#sec-b-4-submodel-elements}

Every element carries the `AASReferableType` fields of B.1 and, from `AASSubmodelElementType`,
`SemanticId`, `SupplementalSemanticIds`, `Qualifiers`, `EmbeddedDataSpecifications` and — inside a
list — `Index`. Element-specific fields:

| Element and field | Address space |
|---|---|
| `Property.valueType` | `AASPropertyType.ValueType`, Mandatory |
| `Property.value` | `AASPropertyType.Value`, typed per clause 6.3.1 |
| `Property.valueId` | `AASPropertyType.ValueId` |
| `MultiLanguageProperty.value` | `AASMultiLanguagePropertyType.Value`, order preserved |
| `MultiLanguageProperty.valueId` | `AASMultiLanguagePropertyType.ValueId` |
| `Range.valueType` | `AASRangeType.ValueType`, Mandatory |
| `Range.min`, `Range.max` | `AASRangeType.Min`, `Max`, typed per clause 6.3.1; absent means unbounded |
| `Blob.value` | `AASBlobType.Value` |
| `Blob.contentType` | `AASBlobType.ContentType`, Mandatory |
| `File.value` | `AASFileType.Value` |
| `File.contentType` | `AASFileType.ContentType`, Mandatory |
| `ReferenceElement.value` | `AASReferenceElementType.Value` |
| `RelationshipElement.first`, `.second` | `AASRelationshipElementType.First`, `Second`, Mandatory |
| `AnnotatedRelationshipElement.annotations` | `AASAnnotatedRelationshipElementType` components |
| `SubmodelElementCollection.value` | `AASSubmodelElementCollectionType` components |
| `SubmodelElementList.orderRelevant` | the ReferenceType its members are referenced with: `HasOrderedComponent` when true, `HasComponent` when false (clause 6.1.4) |
| `SubmodelElementList.typeValueListElement` | `AASSubmodelElementListType.TypeValueListElement`, Mandatory |
| `SubmodelElementList.semanticIdListElement` | `AASSubmodelElementListType.SemanticIdListElement` |
| `SubmodelElementList.valueTypeListElement` | `AASSubmodelElementListType.ValueTypeListElement` |
| `SubmodelElementList.value` | `AASSubmodelElementListType` members, ordered by `Index` |
| `Entity.entityType` | `AASEntityType.EntityType`, Mandatory |
| `Entity.globalAssetId` | `AASEntityType.GlobalAssetId` |
| `Entity.specificAssetIds` | `AASEntityType.SpecificAssetIds` |
| `Entity.statements` | `AASEntityType` components |
| `BasicEventElement.observed` | `AASBasicEventElementType.Observed`, Mandatory |
| `BasicEventElement.direction` | `AASBasicEventElementType.Direction`, Mandatory |
| `BasicEventElement.state` | `AASBasicEventElementType.State`, Mandatory |
| `BasicEventElement.messageTopic` | `AASBasicEventElementType.MessageTopic` |
| `BasicEventElement.messageBroker` | `AASBasicEventElementType.MessageBroker` |
| `BasicEventElement.lastUpdate` | `AASBasicEventElementType.LastUpdate`, typed per clause 6.3.1 |
| `BasicEventElement.minInterval`, `.maxInterval` | `AASBasicEventElementType.MinInterval`, `MaxInterval`, typed per clause 6.3.1 |
| `Operation.inputVariables` | `AASOperationType.InputVariables`; each ordered `AASOperationVariableDataType.ValueNodeId` references one direct `<Variable>` child |
| `Operation.outputVariables` | `AASOperationType.OutputVariables`, with the same child contract |
| `Operation.inoutputVariables` | `AASOperationType.InoutputVariables`, with the same child contract |
| `Capability` | `AASCapabilityType`; the element has no own fields |

### B.5 Value classes {#sec-b-5-value-classes}

| Metamodel class and field | Address space |
|---|---|
| `Reference.type`, `.referredSemanticId`, `.keys` | `AASReferenceDataType`, keys ordered |
| `Key.type`, `.value` | `AASKeyDataType` |
| `LangString.language`, `.text` | `AASLangStringDataType` |
| `SpecificAssetId` fields | `AASSpecificAssetIdDataType` |
| `AdministrativeInformation` fields | `AASAdministrativeInformationDataType` |
| `Qualifier` fields | `AASQualifierDataType`, value as `AASValueString` |
| `Extension` fields | `AASExtensionDataType`, value as `AASValueString` |
| `Resource.path`, `.contentType` | `AASResourceDataType` |
| `EmbeddedDataSpecification` fields | `AASEmbeddedDataSpecificationDataType` |
| `DataSpecificationIec61360` fields | `AASDataSpecificationIec61360DataType` |

---

## (informative) — OPC 30270 v1.00 correspondence {#anx-c annex=informative}

This annex is informative.

| OPC 30270 v1.00 | This specification |
|---|---|
| `AASAssetType` | No direct counterpart. The asset's identity is `AASAssetInformationType`, a component of the shell. |
| `AASViewType` | No counterpart in the AAS V3 metamodel. |
| Identifier with a type discriminator | `AASIdentifiableType.Id`, a bare String |
| `AASSubmodelElementCollectionType` with ordering flags | Split into `AASSubmodelElementCollectionType`, unordered, and `AASSubmodelElementListType`, whose members are referenced with `HasOrderedComponent` and carry `Index` |
| One DataType shared by several xsd types | Clause 6.3.1: each of the thirty `DataTypeDefXsd` values is assigned its own OPC UA DataType |
| Data specification references | `EmbeddedDataSpecifications` |
| No catalogue | The registry half, clause 6.5 |

The two models have distinct namespace URIs. A Server may load both, and a Client identifies the
model by NamespaceUri rather than treating the model version as NodeId identity.

---

## (informative) — Correspondence to the xRegistry HTTP binding {#anx-d annex=informative}

This annex is informative. The registry half of this specification and the xRegistry AAS model
mirrored beside it describe one registry; this table maps the OPC UA realization onto the HTTP one.

| xRegistry over HTTP | This specification |
|---|---|
| `GET /shells` | Browse the registry's shell group folder |
| `GET /shells/<ID>` | Browse or Read the `AASShellGroupType` node |
| `GET /shells/<ID>/submodels/<SM>` | `Open`, `Read`, `Close` on the `AASSubmodelFileType` file |
| `GET …$details` | Read the resource node's Properties |
| `POST /shells` | `CreateGroup` on the registry root |
| `DELETE /shells/<ID>` | `Delete` on the group node |
| `?filter=specificassetids[*].value=…` | `LookupShellsByAssetLink` |
| `?filter=semanticid=…` | Browse the shell's submodels and Read `SemanticId` |
| Versions collection | The resource's version files |
| `<RESOURCE>url` | `ResourceUrl`, or `ExternalReference` as an `ExpandedNodeId` |

---

## (informative) — Federation resolution {#anx-e annex=informative}

This annex is informative and follows the base model's own resolution algorithm.

1. Read the entity's `ExternalReference`.
2. If its `ServerUri` is empty or identifies the local Server, resolve the target in the local
   AddressSpace.
3. Otherwise obtain the endpoint URL for `ServerUri`, open a secure channel and session to it,
   translate the `NamespaceUri` to the remote namespace index, and read the referenced entity there
   with the same Methods used locally.
4. Where only `ResourceUrl` is present, use it as the external locator and treat the remote bytes
   and metadata as the representation of the same entity identity carried by the identifier
   attributes.

Before step 3 or 4 opens a connection, apply the federation egress and peer-identity policy of
§6.5.6 to the initial target and to every resolution, redirect and connected address. The metadata is
an input to policy, never authorization to contact the target.

Because identifiers are stable across registries while the endpoint identifies only where an entity
is served, an entity federated from several registries keeps one identity and can be de-duplicated
by identifier even though it is reachable through several links.

---

## (informative) — Correspondence to a Thing Description projection {#anx-f annex=informative}

This annex is informative, and is pinned to the *OPC UA — WoT Connectivity* and *OPC UA — WoT
Binding* drafts as they stood at the date of this document. Both are under review by another body,
and a change there can invalidate what follows.

A Thing Description carrying the terms below, loaded through a WoT Connectivity registry,
materializes the nodes clause 6.1.6 defines. An author therefore writes an AAS once, as a WoT
document, and obtains both the Thing and the AddressSpace of this specification; and by clause 5A of
the JSON-LD mapping the same content exports as AAS JSON, XML and AASX through a registry.

`tools/jsonld/wot_bridge.py` emits the Thing Descriptions from an AAS environment, applies the
projection rules of this annex, and compares the result against the node set the reference
materializer produces from the same environment. Both sides of that comparison are implemented
alongside this document, so it establishes that the rules below are self-consistent and complete for
the reference fixtures. It is not a test of a WoT Connectivity implementation.

`examples/wot/` holds one generated projection bundle per fixture of the conformance corpus:
`absent-versus-empty`, `every-element-type`, `identifiable-without-idshort`,
`non-canonical-lexical-forms` and `ordering-and-nesting`. Every file in a bundle is one valid Thing
Description object.

### F.1 Scope of the claim {#sec-f-1-scope-of-the-claim}

The claim covers the **projection subgraph**: the nodes clause 6.1.6 materializes for the submodels
of one environment and their submodel elements, with their NodeIds, BrowseNames, TypeDefinitions
and the ReferenceType each is reached by.

Shells and concept descriptions are outside it. They project by the same rules, but the
correspondence has not been exercised for them and this annex does not claim it.

Also outside it are the nodes a registry adds on its own account — the document resource, its
versions, the reference from a document to its projection. Those exist because a registry is
present, not because an AAS is being mapped.

### F.2 Granularity {#sec-f-2-granularity}

The projection emits one Thing Description per projected OPC UA `Object`: one for the `Submodel`
and one for every submodel element Object below it. The TDs form one publication bundle.

This granularity follows the OPC UA WoT Binding term domains. `uav:object` is a Thing-level type,
`uav:variable` is a property-affordance type and `uav:method` is an action-affordance type. A
submodel element that maps to an OPC UA Object therefore cannot be represented as a member of the
TD `properties` map. Sibling TD links carry containment between the Objects.

The AAS RDF graph is distributed across the bundle. The union of the sibling TD datasets is the
same AAS graph that clause 1 of the JSON-LD mapping defines, with the ordering occurrences that
clause 3 requires. A blank-node identifier is scoped to its TD document when those datasets are
combined.

### F.3 Terms {#sec-f-3-terms}

| Fact of this specification | Term | Value |
|---|---|---|
| The AAS itself | the AAS vocabulary | `aas:Referable/idShort`, `aas:Property/value`, `aas:Submodel/submodelElements` and the rest, on the node they belong to |
| AAS subject | TD `id` | the AAS identifier itself where it is an ordinary absolute IRI; otherwise the reserved encoded subject of the JSON-LD mapping; `@id` is not also written |
| TD document identity | a `self` link | a sibling TD document IRI distinct from the AAS subject |
| NodeId, clause 6.1.3 | `uav:id` | an ExpandedNodeId naming its namespace by URI |
| BrowseName, clause 6.1.3 | `uav:browseName` | the portable QualifiedName form |
| TypeDefinition, clause 6.2, readably | a member of `@type` | the prefix-qualified BrowseName of the ObjectType, for example `i4aas:AASPropertyType` |
| TypeDefinition, clause 6.2, definitively | a link with `rel` `ua:HasTypeDefinition` | the ObjectType's portable ExpandedNodeId, for example `nsu=http://opcfoundation.org/UA/I4AAS/v3/;i=1021` |
| Protocol address | Thing-level `forms[].href` | an `opc.tcp` URL whose `id` query value decodes to `uav:id` |
| Child-to-parent containment | `uav:componentOf` and a `uav:componentOf` link | the parent ExpandedNodeId and parent sibling TD IRI |
| Parent-to-child containment | `uav:hasComponent` and a typed link | the child ExpandedNodeId and child sibling TD IRI |
| ReferenceType, clause 6.1.4 | typed link `rel`, `uav:refId` and optional `uav:refName` | `ua:HasOrderedComponent` with `i=49`, or `ua:HasComponent` with `i=47`; the reference name is the target BrowseName local name |
| Position, clause 6.1.4 | `uav:index` | the zero-based position |
| Modelling rule | `uav:modellingRule` | `Mandatory`, `Optional`, `MandatoryPlaceholder` or `OptionalPlaceholder` |
| Semantic identifier | `uav:semanticId` | the AAS `semanticId` as an IRI |

The AAS vocabulary is the first row because it is most of the document. A Thing Description that
carried only the `uav` terms would describe a tree of empty nodes: it would name what to create and
not what any of it is. The `uav` terms carry what the metamodel has no field for — a NodeId, a
BrowseName, an ObjectType, a ReferenceType, a modelling rule — and nothing else.

The type binding is §5.2.1 of *OPC UA — Web of Things Binding*. It admits two forms: the
prefix-qualified model name alongside the node-class term in `@type`, and a
`ua:HasTypeDefinition` link whose `href` is the ObjectType's portable ExpandedNodeId. A document
may carry either or both; the published examples carry both because the name is readable and the
link is definitive. A converter **shall** reject a document in which both resolve and disagree.
Every sibling TD root carries `Thing` and the `uav:object` node-class annotation. A projected Object
is never placed in `properties`. If a TD publishes actual OPC UA Variable or Method affordances,
each property carries `uav:variable` and each action carries `uav:method`.

Every projected Object carries one Thing-level `readallproperties` form. The form is the Object's
protocol address, not a property affordance. Its `href` has the WoT Binding form
`opc.tcp://<host>:<port>[/<resourcePath>]/?id=<ExpandedNodeId>`. URI decoding the `id` parameter
produces the TD root's `uav:id`. A percent escape that is part of the ExpandedNodeId is itself
percent-encoded in the URL.

The parent is the source of each typed containment link, so the link has no `anchor`. A
`uav:refName` on that link is the target BrowseName local name; the generated examples carry it.
Where a target TD declares the BrowseName, a publication can instead omit the duplicate
`uav:refName`. An Operation role index is not a BrowseName and is never used as one.

The `@type` form is resolved in the local model context defined by the WoT Binding. The link form
uses `nsu=<NamespaceUri>;i=<id>`, not the session-local `ns=<index>` form: these ObjectType NodeIds
are published in `Opc.Ua.I4AAS.NodeIds.csv`, so the link means the same on every Server that loads
this model. `@type` may also carry semantic annotations; only a model name that resolves in the
local context is a type binding. A TD carries at most one such name and one
`ua:HasTypeDefinition` link because an OPC UA Node has one `HasTypeDefinition`.

The context contains the published W3C TD 1.1 context, relative references to the bundled AAS and
OPC UA WoT Binding contexts, and an inline `id: "@id"` alias plus the `i4aas` prefix bound to
`http://opcfoundation.org/UA/I4AAS/v3/`.

### F.4 A worked Thing Description {#sec-f-4-a-worked-thing-description}

The `ordering-and-nesting` fixture contains a `SubmodelElementList` whose order is relevant, holding
`SubmodelElementCollection` members. It projects as a bundle. The following abridged root TD contains no Object-valued property
affordance:

```jsonc
{
  "@context": [
    "https://www.w3.org/2022/wot/td/v1.1",
    "../../aas.context.jsonld",
    "../../tools/jsonld/vendor/opc-ua-wot-binding.context.jsonld",
    { "id": "@id", "i4aas": "http://opcfoundation.org/UA/I4AAS/v3/" }
  ],
  "@type": ["Thing", "uav:object", "aas:Submodel", "i4aas:AASSubmodelType"],
  "id": "https://fabrikam.com/ids/sm/ordering",
  "title": "Ordering",
  "uav:id": "nsu=https://example.com/aas/instances/;s=i4aas3:S:36:https://fabrikam.com/ids/sm/ordering",
  "uav:browseName": "nsu=https://example.com/aas/instances/;Ordering",
  "uav:hasComponent": [
    "nsu=https://example.com/aas/instances/;s=i4aas3:E:36:22:https://fabrikam.com/ids/sm/orderingCollectionsInsideAList"
  ],
  "aas:Submodel/submodelElements": [
    {
      "@id": "https://w3id.org/aas-jsonld/node/v1/aHR0cHM6Ly9mYWJyaWthbS5jb20vaWRzL3NtL29yZGVyaW5n/Q29sbGVjdGlvbnNJbnNpZGVBTGlzdA"
    }
  ],
  "forms": [{
    "href": "opc.tcp://example.com:4840/?id=nsu=https://example.com/aas/instances/;s=i4aas3:S:36:https://fabrikam.com/ids/sm/ordering",
    "contentType": "application/octet-stream",
    "op": "readallproperties"
  }],
  "links": [
    {
      "rel": "self",
      "href": "https://w3id.org/aas-jsonld/td/v1/aHR0cHM6Ly9mYWJyaWthbS5jb20vaWRzL3NtL29yZGVyaW5n",
      "type": "application/td+json"
    },
    {
      "rel": "ua:HasTypeDefinition",
      "href": "nsu=http://opcfoundation.org/UA/I4AAS/v3/;i=1013"
    },
    {
      "rel": "ua:HasComponent",
      "href": "https://w3id.org/aas-jsonld/td/v1/aHR0cHM6Ly9mYWJyaWthbS5jb20vaWRzL3NtL29yZGVyaW5n/node/Q29sbGVjdGlvbnNJbnNpZGVBTGlzdA",
      "type": "application/td+json",
      "uav:refId": "i=47",
      "uav:refName": "CollectionsInsideAList"
    }
  ]
}
```

The list Object is the root of a sibling TD. It names its parent in both forms required for
connectivity and names its ordered child from the parent side:

```jsonc
{
  "@type": ["Thing", "uav:object", "aas:SubmodelElementList", "i4aas:AASSubmodelElementListType"],
  "id": "https://w3id.org/aas-jsonld/node/v1/aHR0cHM6Ly9mYWJyaWthbS5jb20vaWRzL3NtL29yZGVyaW5n/Q29sbGVjdGlvbnNJbnNpZGVBTGlzdA",
  "uav:id": "nsu=https://example.com/aas/instances/;s=i4aas3:E:36:22:https://fabrikam.com/ids/sm/orderingCollectionsInsideAList",
  "uav:componentOf": [
    "nsu=https://example.com/aas/instances/;s=i4aas3:S:36:https://fabrikam.com/ids/sm/ordering"
  ],
  "uav:hasComponent": [
    "nsu=https://example.com/aas/instances/;s=i4aas3:E:36:25:https://fabrikam.com/ids/sm/orderingCollectionsInsideAList[0]"
  ],
  "aas:SubmodelElementList/value": [
    {
      "@id": "https://w3id.org/aas-jsonld/node/v1/aHR0cHM6Ly9mYWJyaWthbS5jb20vaWRzL3NtL29yZGVyaW5n/Q29sbGVjdGlvbnNJbnNpZGVBTGlzdFswXQ"
    }
  ],
  "links": [
    {
      "rel": "ua:HasTypeDefinition",
      "href": "nsu=http://opcfoundation.org/UA/I4AAS/v3/;i=1031"
    },
    {
      "rel": "uav:componentOf",
      "href": "https://w3id.org/aas-jsonld/td/v1/aHR0cHM6Ly9mYWJyaWthbS5jb20vaWRzL3NtL29yZGVyaW5n",
      "type": "application/td+json"
    },
    {
      "rel": "ua:HasOrderedComponent",
      "href": "https://w3id.org/aas-jsonld/td/v1/aHR0cHM6Ly9mYWJyaWthbS5jb20vaWRzL3NtL29yZGVyaW5n/node/Q29sbGVjdGlvbnNJbnNpZGVBTGlzdFswXQ",
      "type": "application/td+json",
      "uav:refId": "i=49",
      "uav:refName": "0"
    }
  ]
}
```

The list member is another sibling TD. Its position is explicit and its `uav:componentOf` link
points to the list TD, not to either node's AAS RDF subject:

```jsonc
{
  "@type": ["Thing", "uav:object", "aas:SubmodelElementCollection", "i4aas:AASSubmodelElementCollectionType"],
  "id": "https://w3id.org/aas-jsonld/node/v1/aHR0cHM6Ly9mYWJyaWthbS5jb20vaWRzL3NtL29yZGVyaW5n/Q29sbGVjdGlvbnNJbnNpZGVBTGlzdFswXQ",
  "uav:id": "nsu=https://example.com/aas/instances/;s=i4aas3:E:36:25:https://fabrikam.com/ids/sm/orderingCollectionsInsideAList[0]",
  "uav:browseName": "nsu=https://example.com/aas/instances/;0",
  "uav:componentOf": [
    "nsu=https://example.com/aas/instances/;s=i4aas3:E:36:22:https://fabrikam.com/ids/sm/orderingCollectionsInsideAList"
  ],
  "uav:index": 0,
  "forms": [{
    "href": "opc.tcp://example.com:4840/?id=nsu=https://example.com/aas/instances/;s=i4aas3:E:36:25:https://fabrikam.com/ids/sm/orderingCollectionsInsideAList%5B0%5D",
    "contentType": "application/octet-stream",
    "op": "readallproperties"
  }],
  "links": [
    {
      "rel": "ua:HasTypeDefinition",
      "href": "nsu=http://opcfoundation.org/UA/I4AAS/v3/;i=1029"
    },
    {
      "rel": "uav:componentOf",
      "href": "https://w3id.org/aas-jsonld/td/v1/aHR0cHM6Ly9mYWJyaWthbS5jb20vaWRzL3NtL29yZGVyaW5n/node/Q29sbGVjdGlvbnNJbnNpZGVBTGlzdA",
      "type": "application/td+json"
    }
  ]
}
```

**The bundle carries the Asset Administration Shell, not a description of one.** Every TD root
carries its own AAS content in the AAS vocabulary — `aas:Referable/idShort`,
`aas:Property/value`, `aas:HasSemantics/semanticId` — and the containment properties of the
metamodel, `aas:Submodel/submodelElements` and `aas:SubmodelElementList/value`, reference the sibling
subjects. Discarding every triple outside the AAS namespace from the union leaves the graph of
clause 1 of the JSON-LD mapping. The independent final-byte validator performs that comparison in
both directions and checks every ordering occurrence.

**The `uav` terms carry only what the AAS does not say.** The AAS gives the tree and the order; the
`uav` terms give the NodeId, the BrowseName, the ObjectType, the ReferenceType and the modelling
rule, none of which the metamodel has a field for.

**The NamespaceUri is a real one.** `uav:id` is an ExpandedNodeId in the string form of OPC 10000-6
and the WoT drafts define no placeholder syntax for a namespace. `https://example.com/aas/instances/`
above is the Server's instance namespace, written out. A document that cannot know the target
namespace omits `uav:id` instead; see F.5.

**Subject, TD document and protocol address are separate.** For an ordinary absolute AAS identifier,
the TD `id` is that identifier unchanged. An identifier that cannot be used directly, or one inside
a namespace reserved for generated subjects, uses the collision-free encoded form of the JSON-LD
mapping. The `self` link identifies the sibling TD document, and the `opc.tcp` form identifies the
OPC UA Node. A converter does not derive one from another. It parses the ExpandedNodeId from the
form, resolves containment through sibling TD links and uses the AAS subject only for RDF edges.

A list member has no short name, so its BrowseName is its index — the rule clause 6.1.3 states.

### F.5 Implementer notes {#sec-f-5-implementer-notes}

This subclause is informative.

- *The reference type is where the order lives, and the index is what recovers it.* The link `rel`
  states whether the collection is a sequence; `uav:index` states where each member sits. A
  converter that emits one without the other produces a list a serializer cannot restore, which
  clause 6.1.4 is about.
- *`uav:componentOf` is directional and complete.* Every non-root Object TD names the parent
  ExpandedNodeId and links to the parent sibling TD. The parent independently lists the child in
  `uav:hasComponent` and links to it with the exact ReferenceType. Reversing either direction or
  replacing either sibling TD target builds a different tree.
- *A containment link does not rename its target.* If the typed parent-to-child link carries
  `uav:refName`, it is the target TD's BrowseName local name. It may be omitted where the target TD
  supplies that name. An Operation role and array index belong to the AAS role array, NodeId path
  and `uav:index`; they are not substituted for the child's own BrowseName.
- *A form address is not an RDF subject.* Every form is an `opc.tcp` URL with an explicit endpoint
  and an `id` query parameter that decodes to the same TD root's `uav:id`. Characters significant
  to a URI query and percent escapes inside the ExpandedNodeId are encoded at the URI layer.
- *Do not synthesise a type when the `@type` binding resolves.* The types of this specification are loaded
  from `Opc.Ua.I4AAS.NodeSet2.xml`. A converter that generates its own type of the same name leaves
  the Server holding two type hierarchies, and a Client written against this specification
  recognises neither.
- *Mandatory members of the resolved type are populated, not duplicated.* `AASPropertyType` declares
  `ValueType` as Mandatory. A document that also declares `ValueType` populates that declaration; a
  converter that adds a sibling produces a node carrying the member twice.
- *NodeIds are derived, not allocated.* Clause 6.1.3 fixes the node-kind-discriminated,
  escaped, length-prefixed encoding of the AAS identifier and `idShortPath`, so two documents
  describing the same submodel produce the same NodeIds. A converter that generates NodeIds from
  the browse path instead — which *WoT Connectivity* §6.5.4 permits where a document supplies none —
  produces a subtree that no longer matches this specification. Supply `uav:id` on every node.
- *A document that cannot know the instance namespace omits `uav:id`.* An ExpandedNodeId names a
  namespace, and the namespace a Server materializes instances into is the Server's to choose. An
  author writing for a known Server writes it out. An author writing a portable document omits
  `uav:id` and accepts browse-path NodeIds, or publishes the document per Server. There is no
  placeholder: nothing in the WoT drafts defines one, and a document carrying an invented one
  produces ExpandedNodeIds that name a namespace no Server has.

### F.6 Type-binding conformance {#sec-f-6-type-binding-conformance}

The type binding is part of the published WoT Binding. The examples carry both forms of §5.2.1 and
the validation runs honour them independently:

| Form honoured | Required outcome |
|---|---|
| compact model name in `@type` only | every projected Object has the clause 6.2 ObjectType |
| `ua:HasTypeDefinition` link only | the same nodes have the same ObjectTypes |
| both forms | both resolve to the same Node; disagreement invalidates the document |
| neither form | the projection falls back to `BaseObjectType` unless a Thing Model supplies a type |

`uav:congruentType` remains reconciliation metadata and **shall not** substitute for either form.
The compact name is resolved through the local model context of WoT Binding §5.1.5. The link is
resolved by exact ExpandedNodeId. A converter **shall not** manufacture a second ObjectType with the
same name: the target is the ObjectType already loaded from `Opc.Ua.I4AAS.NodeSet2.xml`.

---

## (informative) — Correspondence to the AAS API of IDTA-01002 Part 2 {#anx-g annex=informative}

This annex is informative.

IDTA-01002 Part 2 defines an HTTP API over the same metamodel this specification maps. The two are
different bindings of one model, not two models: a Client that has a node reaches the same content a
Client that has a URL reaches. This annex says which OPC UA Service answers each operation, so that
a Server implementing both does not implement them twice.

The general rule is that a **resource** of the AAS API is a node of this specification, and the
operations on it are the OPC UA Services on that node. Read replaces GET, Write replaces PATCH with
the `$value` modifier, and Browse replaces the collection endpoints.

| AAS API operation | OPC UA equivalent |
|---|---|
| `GetAllAssetAdministrationShells` | Browse the registry root, clause 6.5.2 |
| `GetAssetAdministrationShellById` | Browse to the shell group whose identifier matches, clause 6.5.3 |
| `GetAllSubmodels`, `GetAllSubmodelReferences` | Browse the shell's submodel references |
| `GetSubmodelById` | Read the `AASSubmodelType` subtree, or call `GetSubmodel` for the document form |
| `GetSubmodelById-ValueOnly` (`$value`) | Read the value Variables of the subtree; clause 6.1.2 assigns each its xsd type |
| `GetSubmodelById-Metadata` (`$metadata`) | Read the subtree with the value Variables excluded |
| `GetSubmodelById-Reference` (`$reference`) | Read the node's `AASReferenceDataType` form |
| `GetSubmodelElementByPath` | Read the node whose NodeId clause 6.1.3 derives from that `idShortPath` |
| `PatchSubmodelElementValueByPath` | Write that node's `Value` |
| `GetFileByPath`, `PutFileByPath` | `Open`, `Read`/`Write`, `Close` on the `AASFileType` node |
| **`InvokeOperation`** | **Call `Invoke` on the `AASOperationType` node, clause 6.2.5** |
| `InvokeOperationAsync`, `GetOperationAsyncResult` | no counterpart; see clause 6.2.5 |
| `SearchAllAssetAdministrationShellIdsByAssetLink` | Call `LookupShellsByAssetLink`, clause 6.5.5 |
| `GenerateSerializationByIds` | The environment documents of clause 6.5.10 |
| `GetSelfDescription` | Read `Server.ServerCapabilities.ServerProfileArray` |

Three differences are structural rather than incidental, and an implementation should not try to
paper over them.

**The path is a NodeId, not a string.** The AAS API addresses an element by a base64url-encoded
identifier and an `idShortPath`. Clause 6.1.3 derives its escaped, length-prefixed String NodeId from
the same two parts, so the mapping is mechanical, but the encoding is not the same and a gateway
converts rather than passes through.

**The level and extent parameters have no counterpart.** `level=core|deep` and
`extent=withBlobValue|withoutBlobValue` shape one response document. OPC UA shapes a response by
what the caller asked to Read and by the disclosure tier of clause 6.5.7, which is a different
mechanism with a different granularity.

**Paging is a continuation point.** The AAS API returns a `cursor`; OPC UA returns a
ContinuationPoint from Browse. Both are opaque to the caller and neither is convertible into the
other.

A Server that implements both bindings **should** publish the IDTA profile identifier it satisfies —
for example `https://admin-shell.io/aas/API/3/0/SubmodelServiceSpecification/SSP-001` — in
`ServerProfileArray` alongside the OPC UA profile URIs, so that one array answers the conformance
question for either kind of Client.

## Types the prose does not introduce {#sec-types-not-introduced}

The types below are declared by the model. Each clause was generated because no clause of this document named its type; fold them into the prose where they belong.

### AASAnyUri {#sec-aasanyuri}

An xs:anyURI value. A subtype of String, since String carries xs:string.

*Table - AASAnyUri Definition* {#tbl-aasanyuri-definition defines=AASAnyUri}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASAnyUri |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:String defined in OPC 10000-3 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AAS-ValueFidelity |  |  |  |  |  |

### AASHexBinary {#sec-aashexbinary}

An xs:hexBinary value. ByteString carries xs:base64Binary, whose octets are the same, so the hexadecimal form is carried by this subtype.

*Table - AASHexBinary Definition* {#tbl-aashexbinary-definition defines=AASHexBinary}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASHexBinary |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:ByteString defined in OPC 10000-3 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AAS-ValueFidelity |  |  |  |  |  |

### AASNonPositiveInteger {#sec-aasnonpositiveinteger}

An xs:nonPositiveInteger value: an integer at most zero.

*Table - AASNonPositiveInteger Definition* {#tbl-aasnonpositiveinteger-definition defines=AASNonPositiveInteger}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASNonPositiveInteger |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Integer defined in [](#ref-uapart5) |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AAS-ValueFidelity |  |  |  |  |  |

### AASNegativeInteger {#sec-aasnegativeinteger}

An xs:negativeInteger value: an integer below zero. A subtype of AASNonPositiveInteger, following the xsd restriction hierarchy.

*Table - AASNegativeInteger Definition* {#tbl-aasnegativeinteger-definition defines=AASNegativeInteger}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASNegativeInteger |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 2:AASNonPositiveInteger defined in [](#sec-aasnonpositiveinteger) |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AAS-ValueFidelity |  |  |  |  |  |

### AASPositiveInteger {#sec-aaspositiveinteger}

An xs:positiveInteger value: an integer above zero. A subtype of UInteger, which carries xs:nonNegativeInteger.

*Table - AASPositiveInteger Definition* {#tbl-aaspositiveinteger-definition defines=AASPositiveInteger}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASPositiveInteger |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:UInteger defined in [](#ref-uapart5) |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AAS-ValueFidelity |  |  |  |  |  |

### AASGYear {#sec-aasgyear}

An xs:gYear value, such as 2026. A Gregorian year denotes a period, for which OPC UA has no DataType, so the value is its lexical form.

*Table - AASGYear Definition* {#tbl-aasgyear-definition defines=AASGYear}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASGYear |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:String defined in OPC 10000-3 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AAS-ValueFidelity |  |  |  |  |  |

### AASGYearMonth {#sec-aasgyearmonth}

An xs:gYearMonth value, such as 2026-08.

*Table - AASGYearMonth Definition* {#tbl-aasgyearmonth-definition defines=AASGYearMonth}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASGYearMonth |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:String defined in OPC 10000-3 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AAS-ValueFidelity |  |  |  |  |  |

### AASGMonth {#sec-aasgmonth}

An xs:gMonth value, such as --08.

*Table - AASGMonth Definition* {#tbl-aasgmonth-definition defines=AASGMonth}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASGMonth |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:String defined in OPC 10000-3 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AAS-ValueFidelity |  |  |  |  |  |

### AASGMonthDay {#sec-aasgmonthday}

An xs:gMonthDay value, such as --08-07.

*Table - AASGMonthDay Definition* {#tbl-aasgmonthday-definition defines=AASGMonthDay}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASGMonthDay |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:String defined in OPC 10000-3 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AAS-ValueFidelity |  |  |  |  |  |

### AASGDay {#sec-aasgday}

An xs:gDay value, such as ---07.

*Table - AASGDay Definition* {#tbl-aasgday-definition defines=AASGDay}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASGDay |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:String defined in OPC 10000-3 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AAS-ValueFidelity |  |  |  |  |  |

### AASAssetKindDataType {#sec-aasassetkinddatatype}

Whether a shell describes a product model, an individual item, a batch, a role, or none of these. The three granularity levels a product passport is issued at map onto Type, Instance and Batch.

*Table - AASAssetKindDataType Definition* {#tbl-aasassetkinddatatype-definition defines=AASAssetKindDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASAssetKindDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |

### AASModellingKindDataType {#sec-aasmodellingkinddatatype}

Whether an element defines a shape or carries values.

*Table - AASModellingKindDataType Definition* {#tbl-aasmodellingkinddatatype-definition defines=AASModellingKindDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASModellingKindDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |

### AASEntityTypeDataType {#sec-aasentitytypedatatype}

Whether a composition entity is managed within its parent or has a shell of its own.

*Table - AASEntityTypeDataType Definition* {#tbl-aasentitytypedatatype-definition defines=AASEntityTypeDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASEntityTypeDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |

### AASDirectionDataType {#sec-aasdirectiondatatype}

The direction of an event element.

*Table - AASDirectionDataType Definition* {#tbl-aasdirectiondatatype-definition defines=AASDirectionDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASDirectionDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |

### AASStateOfEventDataType {#sec-aasstateofeventdatatype}

Whether an event element is currently active.

*Table - AASStateOfEventDataType Definition* {#tbl-aasstateofeventdatatype-definition defines=AASStateOfEventDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASStateOfEventDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |

### AASQualifierKindDataType {#sec-aasqualifierkinddatatype}

What a qualifier qualifies, and therefore whether it may change.

*Table - AASQualifierKindDataType Definition* {#tbl-aasqualifierkinddatatype-definition defines=AASQualifierKindDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASQualifierKindDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |

### AASReferenceTypesDataType {#sec-aasreferencetypesdatatype}

Whether a reference addresses something inside the model or outside it.

*Table - AASReferenceTypesDataType Definition* {#tbl-aasreferencetypesdatatype-definition defines=AASReferenceTypesDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASReferenceTypesDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |

### AASKeyTypesDataType {#sec-aaskeytypesdatatype}

The kind of thing a reference key addresses. The enumeration is closed: a value outside it cannot round-trip, so an implementation rejects it rather than dropping it.

*Table - AASKeyTypesDataType Definition* {#tbl-aaskeytypesdatatype-definition defines=AASKeyTypesDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASKeyTypesDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |

### AASDataTypeDefXsdDataType {#sec-aasdatatypedefxsddatatype}

The xsd type a value is expressed in. All thirty of the metamodel's values are listed. Clause 6.3.1 assigns each one OPC UA DataType, and no DataType to two of them.

*Table - AASDataTypeDefXsdDataType Definition* {#tbl-aasdatatypedefxsddatatype-definition defines=AASDataTypeDefXsdDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASDataTypeDefXsdDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |

### AASDataTypeIec61360DataType {#sec-aasdatatypeiec61360datatype}

The data type of a concept definition expressed in the IEC 61360 data specification.

*Table - AASDataTypeIec61360DataType Definition* {#tbl-aasdatatypeiec61360datatype-definition defines=AASDataTypeIec61360DataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASDataTypeIec61360DataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |

### AASSubmodelElementsDataType {#sec-aassubmodelelementsdatatype}

The element kind a SubmodelElementList constrains its members to.

*Table - AASSubmodelElementsDataType Definition* {#tbl-aassubmodelelementsdatatype-definition defines=AASSubmodelElementsDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASSubmodelElementsDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |

### AASDisclosureTierDataType {#sec-aasdisclosuretierdatatype}

Whether an entity is readable without authentication. It advertises the tier so a Consumer can discover it; it does not enforce it.

*Table - AASDisclosureTierDataType Definition* {#tbl-aasdisclosuretierdatatype-definition defines=AASDisclosureTierDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASDisclosureTierDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |

### AASLoadStateDataType {#sec-aasloadstatedatatype}

The materialization state of one stored document under the updateable registry profile.

*Table - AASLoadStateDataType Definition* {#tbl-aasloadstatedatatype-definition defines=AASLoadStateDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASLoadStateDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AAS-UpdateableRegistry |  |  |  |  |  |

### AASMaterializationOutcomeDataType {#sec-aasmaterializationoutcomedatatype}

What a Materialize call did to one document.

*Table - AASMaterializationOutcomeDataType Definition* {#tbl-aasmaterializationoutcomedatatype-definition defines=AASMaterializationOutcomeDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASMaterializationOutcomeDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AAS-UpdateableRegistry |  |  |  |  |  |

### AASKeyDataType {#sec-aaskeydatatype}

One step of a reference path. Keys are ordered, and the order is part of the reference's meaning.

*Table - AASKeyDataType Definition* {#tbl-aaskeydatatype-definition defines=AASKeyDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASKeyDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Structure defined in OPC 10000-3 |  |  |  |  |  |

### AASReferenceDataType {#sec-aasreferencedatatype}

A reference, external or model-navigating, expressed as an ordered key path.

*Table - AASReferenceDataType Definition* {#tbl-aasreferencedatatype-definition defines=AASReferenceDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASReferenceDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Structure defined in OPC 10000-3 |  |  |  |  |  |

### AASLangStringDataType {#sec-aaslangstringdatatype}

One language-tagged string. A multi-language value is an array of these, and the array order is preserved.

*Table - AASLangStringDataType Definition* {#tbl-aaslangstringdatatype-definition defines=AASLangStringDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASLangStringDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Structure defined in OPC 10000-3 |  |  |  |  |  |

### AASSpecificAssetIdDataType {#sec-aasspecificassetiddatatype}

A domain-specific key an asset is discoverable by.

*Table - AASSpecificAssetIdDataType Definition* {#tbl-aasspecificassetiddatatype-definition defines=AASSpecificAssetIdDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASSpecificAssetIdDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Structure defined in OPC 10000-3 |  |  |  |  |  |

### AASAdministrativeInformationDataType {#sec-aasadministrativeinformationdatatype}

Administrative information. It records a single current revision: the entity's history is carried by the registry, which the metamodel has no equivalent of.

*Table - AASAdministrativeInformationDataType Definition* {#tbl-aasadministrativeinformationdatatype-definition defines=AASAdministrativeInformationDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASAdministrativeInformationDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Structure defined in OPC 10000-3 |  |  |  |  |  |

### AASQualifierDataType {#sec-aasqualifierdatatype}

A qualifier constraining or annotating an element.

*Table - AASQualifierDataType Definition* {#tbl-aasqualifierdatatype-definition defines=AASQualifierDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASQualifierDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Structure defined in OPC 10000-3 |  |  |  |  |  |

### AASEmbeddedDataSpecificationDataType {#sec-aasembeddeddataspecificationdatatype}

A data specification carried by an element, paired with its content.

*Table - AASEmbeddedDataSpecificationDataType Definition* {#tbl-aasembeddeddataspecificationdatatype-definition defines=AASEmbeddedDataSpecificationDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASEmbeddedDataSpecificationDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Structure defined in OPC 10000-3 |  |  |  |  |  |

### AASDataSpecificationIec61360DataType {#sec-aasdataspecificationiec61360datatype}

The IEC 61360 data specification content of a concept definition.

*Table - AASDataSpecificationIec61360DataType Definition* {#tbl-aasdataspecificationiec61360datatype-definition defines=AASDataSpecificationIec61360DataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASDataSpecificationIec61360DataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Structure defined in OPC 10000-3 |  |  |  |  |  |

### AASExtensionDataType {#sec-aasextensiondatatype}

A proprietary extension carried on a Referable. Extensions round-trip verbatim; a reader that does not understand one preserves it unchanged.

*Table - AASExtensionDataType Definition* {#tbl-aasextensiondatatype-definition defines=AASExtensionDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASExtensionDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Structure defined in OPC 10000-3 |  |  |  |  |  |

### AASResourceDataType {#sec-aasresourcedatatype}

A pointer to external content, such as a thumbnail.

*Table - AASResourceDataType Definition* {#tbl-aasresourcedatatype-definition defines=AASResourceDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASResourceDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Structure defined in OPC 10000-3 |  |  |  |  |  |

### AASOperationVariableDataType {#sec-aasoperationvariabledatatype}

One input, output or in-out variable of an operation, carried as a reference to the element node that holds it so that the element's own representation is not duplicated.

*Table - AASOperationVariableDataType Definition* {#tbl-aasoperationvariabledatatype-definition defines=AASOperationVariableDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASOperationVariableDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Structure defined in OPC 10000-3 |  |  |  |  |  |

### AASAuthorizationOptionDataType {#sec-aasauthorizationoptiondatatype}

One authorization option a Consumer may use. It is authorization configuration only and never carries credentials, which are supplied out of band.

*Table - AASAuthorizationOptionDataType Definition* {#tbl-aasauthorizationoptiondatatype-definition defines=AASAuthorizationOptionDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASAuthorizationOptionDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Structure defined in OPC 10000-3 |  |  |  |  |  |

### AASAttestationDataType {#sec-aasattestationdatatype}

A non-authoritative discovery hint for a separate attestation or OCI referrer Resource. It never represents a package Version, and its presence is not verification: a Consumer retrieves and verifies the separate artifact itself.

*Table - AASAttestationDataType Definition* {#tbl-aasattestationdatatype-definition defines=AASAttestationDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASAttestationDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Structure defined in OPC 10000-3 |  |  |  |  |  |

### AASMaterializationResultDataType {#sec-aasmaterializationresultdatatype}

The result of materializing one document. A call returns one of these per document it considered, reporting per document whether it was unchanged, materialized, retired or failed.

*Table - AASMaterializationResultDataType Definition* {#tbl-aasmaterializationresultdatatype-definition defines=AASMaterializationResultDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASMaterializationResultDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Structure defined in OPC 10000-3 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AAS-UpdateableRegistry |  |  |  |  |  |

### AASValueReferencePairDataType {#sec-aasvaluereferencepairdatatype}

One permitted value paired with the reference identifying its meaning.

*Table - AASValueReferencePairDataType Definition* {#tbl-aasvaluereferencepairdatatype-definition defines=AASValueReferencePairDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASValueReferencePairDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Structure defined in OPC 10000-3 |  |  |  |  |  |

### AASValueListDataType {#sec-aasvaluelistdatatype}

The non-empty list of permitted values for an IEC 61360 data specification.

*Table - AASValueListDataType Definition* {#tbl-aasvaluelistdatatype-definition defines=AASValueListDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASValueListDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Structure defined in OPC 10000-3 |  |  |  |  |  |

### AASLevelTypeDataType {#sec-aasleveltypedatatype}

The four IEC 61360 level flags. Every flag is explicit.

*Table - AASLevelTypeDataType Definition* {#tbl-aasleveltypedatatype-definition defines=AASLevelTypeDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AASLevelTypeDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Structure defined in OPC 10000-3 |  |  |  |  |  |
