# Asset Administration Shell Registry Service - Version 1.0-rc3

<!-- words: AAS AASX idShort semanticId semanticid submodel submodels -->
<!-- words: submodelid submodelidentifier submodeltemplate submodeltemplates -->
<!-- words: aasidentifier aasidentifiers aasxregistries aasxregistry -->
<!-- words: assetkind globalassetid assettype specificassetids externalsubjectid -->
<!-- words: derivedfrom conceptdictionaries conceptdictionary conceptdescription -->
<!-- words: conceptdescriptions conceptidentifier iscaseof idshort templateid -->
<!-- words: disclosuretier authorityuri resourceuri eventendpoint packageidentifier -->
<!-- words: artifacttype attestations digestalg hasdocument xid xids xref -->
<!-- words: dpp passports remanufacturer recyclers fabrikam contoso -->
<!-- words: interoperate federatable subtypes unresolvable scraping -->
<!-- words: Identifiable Referable versionid versionids opc ua -->
<!-- words: cencenelec changelog conceptdescriptionid dictid fsp iec -->
<!-- words: irdi iri metamodel mitigations packageid regid -->
<!-- words: shellid validateformat webstore supplementalsemanticids -->

## Abstract

This specification defines an Asset Administration Shell (AAS) registry
extension to the xRegistry document format and API
[specification][xRegistry Core]. An AAS Registry allows for the storage,
management, discovery and federation of Asset Administration Shells, the
Submodels that describe them and the concept definitions that give those
Submodels meaning.

## Table of Contents

- [Asset Administration Shell Registry Service - Version 1.0-rc3](#asset-administration-shell-registry-service---version-10-rc3)
  - [Abstract](#abstract)
  - [Table of Contents](#table-of-contents)
  - [1. Overview](#1-overview)
    - [1.1. Shells, Submodels and Concepts](#11-shells-submodels-and-concepts)
    - [1.2. Registry, Repository and Descriptor](#12-registry-repository-and-descriptor)
    - [1.3. Relationship to Other xRegistry Specs](#13-relationship-to-other-xregistry-specs)
    - [1.4. Versioning](#14-versioning)
    - [1.5. Document Store](#15-document-store)
  - [2. Notations and Terminology](#2-notations-and-terminology)
    - [2.1. Notational Conventions](#21-notational-conventions)
    - [2.2. Terminology](#22-terminology)
  - [3. AAS Registry Model](#3-aas-registry-model)
  - [4. AAS Registry](#4-aas-registry)
    - [4.1. Shells](#41-shells)
    - [4.2. Submodels](#42-submodels)
    - [4.3. Submodel Templates](#43-submodel-templates)
    - [4.4. Concept Dictionaries](#44-concept-dictionaries)
    - [4.5. Formats](#45-formats)
  - [5. Relationships and Cross-References](#5-relationships-and-cross-references)
    - [5.1. AAS Identifiers and xids](#51-aas-identifiers-and-xids)
    - [5.2. Composition and Bills of Material](#52-composition-and-bills-of-material)
    - [5.3. Federation](#53-federation)
    - [5.4. Discovery](#54-discovery)
    - [5.5. AAS Registry to Schema Registry](#55-aas-registry-to-schema-registry)
    - [5.6. AAS Registry to Endpoint Registry](#56-aas-registry-to-endpoint-registry)
  - [6. Disclosure Tiers](#6-disclosure-tiers)
  - [7. Product Passport Profile](#7-product-passport-profile)
  - [8. Security](#8-security)
  - [Annex A. Correspondence to the AAS HTTP API](#annex-a-correspondence-to-the-aas-http-api)

## 1. Overview

The Asset Administration Shell is the digital representation of an asset:
the standardized envelope in which a manufacturer publishes what a machine, a
component or a product is, what it can do, and what has happened to it. It is
defined by [IEC 63278-1][IEC63278] and by the Asset Administration Shell
specification series, whose metamodel and HTTP API this specification maps onto
xRegistry.

An AAS Registry serves three purposes that the xRegistry core model already
supports and that AAS implementations otherwise build separately: it is a
catalogue that can be listed and filtered, a document store that returns the
bytes of a Submodel, and a federation point that can describe entities it does
not itself host.

It also supplies one thing the AAS metamodel does not have at all. An AAS
records a single current revision; there is no version history, no changelog and
no way to ask what a Submodel said last March. xRegistry Versions provide
exactly that, which matters wherever a regulator requires an auditable record
rather than a current value. See [Section 1.4](#14-versioning).

### 1.1. Shells, Submodels and Concepts

Three kinds of entity carry identity in the AAS metamodel, and this
specification maps each one:

- An **Asset Administration Shell** is the envelope for one asset. It carries
  the asset's identity and points at the Submodels that describe it.
- A **Submodel** is one coherent aspect of that asset: its nameplate, its
  technical data, its carbon footprint, its bill of material. Submodels are the
  unit a publisher curates and a Consumer retrieves.
- A **Concept Description** is the definition a Submodel's `semanticid` refers
  to. It is what makes two Submodels from different vendors comparable.

A Submodel is not owned by the shell that references it. One Submodel MAY be
referenced by several shells, which is why this specification maps Submodels to
Resources and uses [`xref`][xRegistry xref] to share them rather than copying
them; see [Section 5.3](#53-federation).

### 1.2. Registry, Repository and Descriptor

The AAS API series separates a *Registry*, which stores descriptors that say
where an entity is served, from a *Repository*, which stores the entity itself.
Implementations usually deploy them as different services.

This specification does not reproduce that split, because xRegistry already
expresses it. A Resource whose document is stored is a repository entry. The
same Resource carrying a [`<RESOURCE>url`][xRegistry Core] or an
[`xref`][xRegistry xref] instead of stored bytes is a descriptor. Both have the
same `xid`, the same identifier attributes and the same collection membership;
only the hosting differs.

The consequence is worth stating plainly, because it is what makes this model
useful for federation:

> Whether an AAS Registry hosts an entity or merely describes it is a property
> of that entity's storage, not of its identity. A Consumer resolves the same
> `xid` either way, and a registry MAY convert between the two without the
> entity's identity changing.

### 1.3. Relationship to Other xRegistry Specs

An AAS Registry is complementary to the xRegistry
[Schema][xRegistry Schema] and [Endpoint][xRegistry Endpoint] registries:

- A Submodel Template constrains the shape of the Submodels built from it.
  Where that shape is also expressed as a schema document in an xRegistry Schema
  Registry, the two MAY be cross-referenced; see
  [Section 5.5](#55-aas-registry-to-schema-registry).
- A Submodel whose values are driven by live data has that data delivered by
  some endpoint, which MAY be managed by an xRegistry Endpoint Registry; see
  [Section 5.6](#56-aas-registry-to-endpoint-registry).

These cross-references are informative: an implementation MAY validate them, but
this specification does not require that all referents resolve.

The identifier rules of [Section 5.1](#51-aas-identifiers-and-xids) define the
symbolic identifier construction in full, so that this specification is readable
without a second document open. Any registry that adopts the same construction
addresses the same entity by the same `xid`.

Packaging an AAS as an AASX artifact for immutable, signed distribution is
defined in the companion document [AAS Packages](xRegistry-AAS-Packages.md), which shares this
model definition.

### 1.4. Versioning

An Asset Administration Shell records administrative information — a version
label, a revision label, a creator — but **no history**. Nothing in the
metamodel retains what a Submodel previously said, and nothing distinguishes a
correction from a new observation.

This specification therefore does not reflect the AAS version label into
[`versionid`][xRegistry version-ids]. The AAS labels are carried unchanged in
the `administration` attribute, and the xRegistry Core versioning rules apply
unchanged on top of them. A `submodel` is defined with `versionmode` set to
`modifiedat`, so Versions are ordered by the time the revision was made, and a
Consumer asking for the Submodel as it stood at a given moment reads the newest
Version not later than that moment.

Two rules follow:

- **The identifier binds to the Resource, not to the Version.** All Versions of
  one `submodel` share one `submodelidentifier` and one `submodelid`; they
  differ only in `versionid`. An AAS Submodel id denotes the Submodel across its
  whole life. That durability is the point: a Reference authored inside a Shell
  or another Submodel names the Submodel, not a revision of it. An id that
  resolved to a Version would defeat the registry's ability to serve a corrected
  document, because a Consumer holding that id would re-resolve to a different
  entity the moment a new revision was published.
- **A `submodelid` MUST NOT be derived from the document bytes.** A Resource is
  the umbrella over its Versions. An id computed from content would therefore
  change on every revision and split one logical Submodel into a new Resource
  each time, which is the opposite of what a Resource is for. The content hash
  belongs at Version level, where it is the `digest`
  ([Section 4.2](#42-submodels)); the id is derived only from the
  `submodelidentifier`, which is Version-invariant.

A Consumer that does not select a Version explicitly MUST receive the Resource's
default Version. An `xid` that addresses a specific Version MUST NOT be used as
an AAS identifier.

A change that violates the Resource's [`compatibility`][xRegistry compatibility]
policy MUST result in a new Resource, not a new Version.

### 1.5. Document Store

An AAS Registry is a document store: `submodels`, `conceptdescriptions` and
`packages` are all defined with [`hasdocument`][xRegistry hasdocument] set to
`true`. A GET against a Resource Version's [`self`][xRegistry self] URL returns
the entity bytes with the appropriate content-type, and Resource metadata is
returned in HTTP headers or through the `$details` suffix.

This is what lets unmodified AAS tooling consume a registry: the document a
Consumer retrieves is byte-for-byte the Submodel serialization the publisher
produced, not a re-encoding of it.

It is also the boundary of what this specification can express. An AAS Submodel
has internal structure — elements addressed by a path within the document — and
the AAS API exposes operations on those elements. xRegistry addresses documents.
Element-level read, element-level update and element-level access control are
therefore outside this model; see [Section 6](#6-disclosure-tiers) for what that
means where a regulation requires them.

## 2. Notations and Terminology

### 2.1. Notational Conventions

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD",
"SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be
interpreted as described in [RFC 2119](https://tools.ietf.org/html/rfc2119).

For clarity, OPTIONAL attributes (specification-defined and extensions) are
OPTIONAL for clients to use, but the servers' responsibility will vary.
Server-unknown extension attributes MUST be silently stored in the backing
datastore. Specification-defined, and server-known extension, attributes MUST
generate an error if the corresponding feature is not supported or enabled.

Note that the term "attribute" is used to denote a key/value pair of metadata,
and this is distinct from an element within a Submodel document, which this
specification does not address.

### 2.2. Terminology

This specification defines the following terms:

#### 2.2.1. Asset Administration Shell

The digital representation of one asset: an identified envelope holding the
asset's identity and references to the Submodels that describe it. Abbreviated
AAS throughout.

#### 2.2.2. Submodel

One coherent aspect of an asset, identified in its own right and typed by a
`semanticid`. A Submodel is the unit this specification serves as a document.

#### 2.2.3. Submodel Template

A Submodel whose `kind` is `Template`. It defines the shape that Submodels built
from it follow, and carries no values for any individual asset.

#### 2.2.4. Descriptor

A Resource that describes an entity this registry does not host, carrying a
`<RESOURCE>url` or an `xref` in place of stored bytes. See
[Section 1.2](#12-registry-repository-and-descriptor).

## 3. AAS Registry Model

The model definition for an AAS Registry resides in the
[model.json](xRegistry-AAS.model.json) file. It defines four Group types. The first three are
defined by this document; `aasxregistries` is defined by [AAS Packages](xRegistry-AAS-Packages.md)
and appears in the same model definition because the two share one registry.

| Group type | One instance is | Resources |
|---|---|---|
| `shells` | one Asset Administration Shell | `submodels` |
| `submodeltemplates` | one template family | `submodels` |
| `conceptdictionaries` | one concept dictionary | `conceptdescriptions` |
| `aasxregistries` | one package store | `packages` |

`submodeltemplates` obtains its `submodels` Resource type through
[`ximportresources`][xRegistry Core] rather than declaring its own. This is
deliberate: a template and the Submodels built from it are then the same
Resource model type, which is what permits an `xref` between them and what keeps
one definition of what a Submodel is.

## 4. AAS Registry

An AAS Registry MAY be served together with other xRegistry Group types in one
registry, and an implementation MAY support any subset of the four Group types.

This model is fully mutable: the create, update and delete semantics of the
xRegistry Core specification apply to every entity. An implementation that
projects a read-only backing system MUST declare the restriction through its
[`capabilities`][xRegistry Core] rather than by rejecting the model.

### 4.1. Shells

A `shell` Group is one Asset Administration Shell. Its `shellid` is the symbolic
identifier of its `aasidentifier` ([Section 5.1](#51-aas-identifiers-and-xids)).

- `aasidentifier` is REQUIRED and is the authored AAS Identifiable id. It is the
  authority for the shell's identity.
- `assetkind` is REQUIRED and records whether the shell represents a product
  type, an individual item, a production batch, a role or none of these. The
  distinction is not cosmetic: a passport issued for a model, for a batch and for
  an item are different documents with different obligations, and a Consumer
  MUST NOT treat one as the other.
- `globalassetid` identifies the asset itself rather than the shell that
  describes it. Where the asset carries an identification link conforming to
  [IEC 61406][IEC61406], that link SHOULD be the `globalassetid`, which is what
  connects a code scanned from a physical product to this registry.
- `specificassetids` carries the additional keys an asset is discoverable by —
  a serial number, a manufacturer part id, a batch id. Each entry MAY carry an
  `externalsubjectid` naming the subject the key is disclosed to.
- `derivedfrom` points at the Type shell an Instance shell was derived from.

An implementation MUST NOT rely on `idshort` for identity. It is unique only
within its parent, and two shells from different publishers routinely share one.

### 4.2. Submodels

A `submodel` Resource is one Submodel served as a document. Its `submodelid` is
the symbolic identifier of its `submodelidentifier`.

- `submodelidentifier` is REQUIRED and is the authored Submodel Identifiable id.
- `format` is REQUIRED and states the serialization of the document
  ([Section 4.5](#45-formats)).
- `semanticid` is the identifier of the concept this Submodel is an occurrence
  of. It is the attribute a Consumer filters on to find, for example, every
  carbon footprint Submodel in a registry, and it SHOULD be present on every
  Submodel that is an occurrence of a published template.
- `supplementalsemanticids` carries further concept identifiers the same
  Submodel corresponds to, which is how one Submodel is made discoverable
  through more than one dictionary.
- `kind` distinguishes a Submodel that carries values from one that defines a
  shape. A Submodel whose `kind` is `Template` SHOULD reside in a
  `submodeltemplate` Group; see [Section 4.3](#43-submodel-templates).
- `template` is the identifier of the Submodel Template this Submodel was built
  from. It is an identifier and not a pointer, so that it resolves identically
  whether or not this registry also serves the template.
- `digest` and `digestalg` carry the content hash of the exact bytes a Consumer
  retrieves. `digestalg` is REQUIRED when `digest` is present.

A `submodel` MUST NOT carry a `digest` for bytes the registry has not itself
seen. Publishing a digest for a delegated document would assert an integrity
guarantee the registry cannot keep.

### 4.3. Submodel Templates

A `submodeltemplate` Group is one publisher's family of Submodel Templates. Its
Submodels are the ones whose `kind` is `Template`.

Separating templates from instances into different Group types, rather than
mixing them in one collection, keeps the two listable independently: a Consumer
building a new asset lists templates, and a Consumer reading an asset lists
instances. Because the Resource type is shared, a template and an instance
remain the same model type and MAY cross-reference one another.

There is no requirement that a template be served by the same registry as the
Submodels built from it, and in practice templates are published centrally while
instances are published per-asset. This is an ordinary federation case; see
[Section 5.3](#53-federation).

### 4.4. Concept Dictionaries

A `conceptdictionary` Group is one dictionary of concept definitions, and its
`conceptdescriptions` are the definitions a `semanticid` resolves to.

- `conceptidentifier` is REQUIRED and is the authored Concept Description
  Identifiable id. It is the value that appears as a `semanticid` elsewhere.
- `iscaseof` lists the identifiers of concepts in other dictionaries that this
  concept corresponds to, which is how a registry bridges two classification
  systems without asserting that either is canonical.

Concept identifiers are frequently issued by external dictionaries whose
identifier syntax is unrelated to any URI scheme. Those identifiers are carried
verbatim in `conceptidentifier`; only the derived `conceptdescriptionid` is
constrained by xRegistry's grammar.

### 4.5. Formats

The `format` attribute follows the xRegistry convention of a name and a version
separated by `/`. The values defined by this specification are:

| `format` | Document |
|---|---|
| `AAS-Submodel/3.0`, `AAS-Submodel/3.1`, `AAS-Submodel/3.2` | A Submodel serialized as defined by the AAS metamodel of that version |
| `AAS-ConceptDescription/3.0`, `/3.1`, `/3.2` | A Concept Description serialized as defined by the AAS metamodel of that version |
| `EN18223-Compressed/1.0` | A product passport in the compressed serialization defined by EN 18223 |
| `EN18223-Expanded/1.0` | A product passport in the expanded serialization defined by EN 18223 |
| `Opaque/1.0` | A document this registry serves but does not interpret |

The `format` enumerations are not strict: a registry MAY serve documents in
formats this specification does not enumerate, and MUST record the format it
used rather than omitting the attribute. A Consumer that does not recognize a
`format` MUST treat the document as opaque and MUST NOT attempt format
validation on it.

The two `EN18223` formats are the reason a product passport is not simply an
AAS Submodel; see [Section 7](#7-product-passport-profile).

## 5. Relationships and Cross-References

### 5.1. AAS Identifiers and xids

xRegistry constrains each entity id to [RFC 3986][RFC3986] `unreserved`
characters plus `:` and `@`, starting with a letter, a digit or `_`, at most 128
characters long, and unique case-insensitively within its parent. An AAS
Identifiable id is a free-form string of up to 2048 characters, conventionally
an IRI, an IRDI or a URN.

An identifier such as `https://example.com/aas/pump-001` is not a valid entity id
because of its solidus characters, and a dictionary identifier of the form
`0173-1#02-AAO677#002` is not one because of its number signs. Almost no real
AAS identifier is usable verbatim.

This specification therefore does not equate them. It derives one from the other
by a **closed-form, one-way construction**, and keeps the authored identifier as
the authority:

> A `shell`'s `aasidentifier` MUST be its authored AAS Identifiable id, and its
> `shellid` MUST be the [symbolic identifier](#51-aas-identifiers-and-xids) of that
> `aasidentifier`. A `submodel`'s `submodelidentifier` and a
> `conceptdescription`'s `conceptidentifier` relate to `submodelid` and
> `conceptdescriptionid` in the same way. Those attributes are REQUIRED and are
> the authority: an implementation MUST NOT recover an AAS identifier by
> attempting to invert the construction.

The construction is defined here in full. It builds a **symbolic identifier**
from a source string; the result is a dot-separated token in the alphabet
`A-Z a-z 0-9 _ . -`, a strict subset of what xRegistry permits, so that it is
simultaneously safe in a URL, on a command line and as a file name in the
[file-system representation][xRegistry primer].

1. Split the source into an *authority* and a *path*. For an absolute URI with
   an authority component the authority is the host together with its port when
   present, and the path is the URI path; the scheme, userinfo, query and
   fragment are discarded. For a URN the authority is empty and the path is the
   URN split on `:`. Otherwise — the usual case for an IRDI — the authority is
   empty and the path is the source split on `/`.
2. Reverse the authority's `.`-separated labels (`contoso.com` becomes `com`,
   `contoso`), appending the port, where present, as a further label.
3. Percent-decode each path segment and discard the empty ones.
4. Normalize each label: replace every run of characters outside
   `A-Z a-z 0-9 _ . -` with a single `-`; collapse runs of `-` and runs of `.`;
   strip leading and trailing `-` and `.`; discard a label that becomes empty.
   Letter case is preserved.
5. Join the surviving labels with `.`. If no label survives, the identifier is
   `_`.
6. If the result is longer than 128 characters, drop trailing labels — never the
   first — until it is at most 119 characters long; if that first label is itself
   longer than 119 characters, truncate it to 119 and strip any trailing `-` or
   `.`. Then append the disambiguator of step 7.
7. Where step 6 truncated the result, or where the result would collide
   case-insensitively with an existing sibling in the same collection, append `.`
   followed by the first eight lower-case hexadecimal characters of the SHA-256
   of the UTF-8 encoding of the **exact source string**. The disambiguator is a
   function of the identifier, not of any document, so it does not change when a
   new Version is written.

The construction is deterministic, so a Producer and a Consumer agree without a
lookup table, and it is lossy, so only the forward direction is defined: an
implementation recovers an AAS identifier by reading the `aasidentifier`,
`submodelidentifier` or `conceptidentifier` attribute, never by inverting the
construction. Applied to AAS identifiers it gives:

| Authored AAS id | Derived id |
|---|---|
| `https://fabrikam.com/aas/pump/SN-001` | `com.fabrikam.aas.pump.SN-001` |
| `https://contoso.com/ids/sm/nameplate` | `com.contoso.ids.sm.nameplate` |
| `0173-1#02-AAO677#002` | `0173-1-02-AAO677-002` |
| `urn:uuid:2c4c1b0e-0e2a-4e2f-9a7e-3b3a1b7c9d21` | `urn.uuid.2c4c1b0e-0e2a-4e2f-9a7e-3b3a1b7c9d21` |

Three properties of the construction matter here specifically:

- **It disambiguates collisions.** The construction is lossy, and two distinct
  AAS identifiers can normalize to one token. Where they would, a hash of the
  exact source string is appended. This is not an optimization: an identifier
  scheme that allowed two assets to share one id would violate the
  no-reassignment and distinctness requirements that
  [EN 18219][EN18219] places on product identifiers.
- **The hash is of the identifier, not of the document.** A Submodel's values
  change constantly; its identity does not.
- **Percent-encoding is not available.** It is the usual answer for characters
  outside the unreserved set, and [EN 18219][EN18219] itself specifies it for
  identifiers used as URIs, but the percent character is not a legal xRegistry
  id character. A derived, deterministic construction is what remains, and
  [EN 18219][EN18219] contemplates exactly that in requiring a product
  identifier to be a URL or derivable into one by a specified conversion method.

An implementation MAY instead expose base64url of the AAS identifier as the id,
which is reversible and is what the AAS HTTP API itself uses in URL path
segments. It is not used here because it is unreadable, because it defeats the
[file-system representation][xRegistry primer], and because it fails outright
for identifiers longer than 96 bytes.

Note that [EN 18219][EN18219] governs the identifier of a *product*, not the id
of a registry entity. The derived id is an addressing construct within one
registry; the authored identifier attribute is the normative one, and it is the
value that MUST be exchanged with any system outside this registry.

### 5.2. Composition and Bills of Material

An asset is rarely alone. A battery pack contains modules, a module contains
cells, and each of those MAY be an asset with a shell of its own, often held by
a different organization.

The AAS metamodel expresses this inside a Submodel, using entity elements that
carry the `globalassetid` of a component's own shell. This specification does
not duplicate that structure as registry metadata, because doing so would create
two sources of truth that drift. Instead:

- A composition relationship is authored inside the bill-of-material Submodel,
  in whatever form the applicable template defines.
- The identifiers it carries are `globalassetid` values, not `xid`s, so that
  they resolve identically for a Consumer holding the document and for one
  reading it from a different registry.
- A Consumer that wishes to traverse the composition resolves each
  `globalassetid` through discovery ([Section 5.4](#54-discovery)), which MAY
  lead to another registry entirely.

A registry MUST NOT rewrite the identifiers inside a document it serves. A
rewritten identifier no longer matches what the authoring system recorded, and
the composition ceases to be traversable from anywhere else.

### 5.3. Federation

A registry need not host every shell or Submodel it knows about. An entity that
this registry describes but does not store is published with an
[`xref`][xRegistry xref], or with a `<RESOURCE>url` naming its location, instead
of a stored document.

This is what makes AAS registries composable across a supply chain. An
integrator's registry can describe a supplier's component and delegate the bytes
to the supplier's own registry, without copying the supplier's content and
without either party re-authoring anything.

The identity rule is the one that makes it work, and it is absolute:

> Identity is carried by the AAS identifier attributes and the `xid` derived
> from them, never by an endpoint. A registry that exposes a local proxy for a
> remote entity MUST retain the remote entity's identifier attributes, and MUST
> NOT treat the local endpoint as part of that entity's identity. The external
> authority identifies the serving endpoint, not the entity.

Consequently:

- An `aasidentifier`, a `submodelidentifier` and a `conceptidentifier` MUST be
  stable across federated registries. A federating registry MUST NOT rewrite
  them.
- The same entity therefore has the same `xid` in every registry that describes
  it, because the construction of
  [Section 5.1](#51-aas-identifiers-and-xids) is deterministic. A Consumer
  moving between registries re-resolves nothing.
- A delegated entity carries no `digest` of its own unless the delegating
  registry has verified the bytes it points at.
- A Consumer follows a federation link exactly as it would consult the next
  resolver in its chain, and MAY stop as soon as an entity resolves.

Because a Submodel is not owned by its shell, `xref` also serves the ordinary
case of one Submodel shared by several shells within one registry. Both source
and target are the same Resource model type, which the model definition
guarantees.

### 5.4. Discovery

The AAS API series provides a discovery service that maps asset keys onto shell
identifiers. In this model that is a filter over the `shells` collection, and no
separate service is needed:

```http
GET /shells?filter=globalassetid=https://fabrikam.com/asset/SN-001
GET /shells?filter=specificassetids[*].value=SN-001
GET /shells?filter=assetkind=Instance,derivedfrom=/shells/com.fabrikam.type.pump
```

Finding every Submodel of a given kind is likewise a filter on `semanticid`,
which is the query a passport assembler makes:

```http
GET /shells/<SHELLID>/submodels?filter=semanticid=<CONCEPT>&inline=*
```

An implementation SHOULD bound the results it returns for an unauthenticated
collection query. A registry that serves product passports is subject to
requirements to prevent mass extraction of its contents, and an unbounded
collection endpoint is exactly such an extraction surface; see
[Section 6](#6-disclosure-tiers).

### 5.5. AAS Registry to Schema Registry

A Submodel Template constrains the shape of the Submodels built from it. Where
that shape is also published as a schema document — for validation, for code
generation, or because a consumer's tooling speaks schemas rather than
templates — the schema MAY be served by an xRegistry
[Schema Registry][xRegistry Schema] and referenced from the template.

The reference is informative. A registry MAY validate a Submodel document
against such a schema and record the outcome through the Core
`validateformat` mechanism, but this specification does not require it.

### 5.6. AAS Registry to Endpoint Registry

An AAS MAY publish change events, and AAS implementations commonly deliver them
over a message broker. Those are asynchronous endpoints, and describing them is
the province of the xRegistry [Endpoint Registry][xRegistry Endpoint], not of
this specification.

A `shell` MAY therefore carry an `eventendpoint` naming the Endpoint Registry
entry that delivers its change events. It is a URL rather than an `xid` because
an `xid` is resolved relative to the registry that carries it, and the Endpoint
Registry serving an event stream is usually a different registry.

Note that the Endpoint Registry describes endpoints for message and event
transfer, and explicitly not general-purpose HTTP API surfaces. The data-read
interface of an AAS is not an endpoint in that sense and MUST NOT be modelled as
one.

## 6. Disclosure Tiers

Some assets carry data that cannot be shown to everyone. A product passport is
the clearest case: part of its content is public, and part is disclosed only to
an authenticated actor holding a particular role.

This specification can express two of the three things that requires, and cannot
express the third. Stating that boundary precisely is more useful than implying
a completeness this model does not have.

**Segmentation is expressible.** A registry serves public content as stored
documents and represents controlled content as descriptors
([Section 1.2](#12-registry-repository-and-descriptor)), so that the public
surface and the controlled surface are different Resources with different
hosting.

**Advertisement is expressible.** Every entity MAY carry:

- `disclosuretier`, which is `public` where the entity is readable without
  authentication and `controlled` where it is not; and
- `authorization`, an array in which each entry describes one authorization
  option a Consumer MAY use, in the shape the
  [Endpoint Registry][xRegistry Endpoint] defines for the same purpose: a
  `type`, a `mechanism` where the type calls for one, and the `authorityuri` and
  `resourceuri`
  that say where authorization is obtained and what it is obtained for.

`authorization` is authorization configuration only. It MUST NOT carry
credentials, keys, passwords or tokens; those are supplied out of band.

**Enforcement is not expressible.** Access decisions are made by the serving
implementation, and this specification defines no policy language, no role
model and no per-caller attribute visibility. That is a deliberate inheritance
from the xRegistry Core specification, which places authentication and
authorization out of scope.

The limitation goes further than that, and implementers need to understand its
shape. A regulation can require access rights to be enforced at the granularity
of an individual data element within a passport. An xRegistry document is
opaque bytes, so a decision that falls between two elements of one
document cannot be taken by this model at all. Two mitigations are available and
both are conformant:

- A registry MAY publish tier-specific Resources whose documents are already
  the redacted projection appropriate to that tier, so that every document is
  wholly public or wholly controlled and the boundary falls between Resources.
- A registry MAY omit controlled entries entirely from responses to
  unauthenticated callers, since advertising that a controlled Submodel exists
  is itself a disclosure.

A registry that serves public data MUST NOT require authentication to read it.

## 7. Product Passport Profile

A digital product passport is a regulated document, and an Asset Administration
Shell is not one. A passport can be *derived* from a shell when the shell holds
the Submodels a regulation requires, but the passport's own data model,
serializations and API are defined separately, by [EN 18223][EN18223] and
[EN 18222][EN18222] respectively.

Three consequences bear on this specification, and an implementation claiming
passport support MUST observe them:

1. **A passport is a document, not the registry.** A registry that serves
   Submodels does not thereby serve passports. A passport document is served as
   a `submodel` whose `format` is one of the `EN18223` values of
   [Section 4.5](#45-formats), and its content is the passport serialization,
   not an AAS Submodel serialization.
2. **The passport data model is narrower than the AAS metamodel.** It admits
   collections, single-valued and multi-valued data elements, multi-language
   data elements and references to related resources. AAS constructs outside
   that set have no passport counterpart, and an implementation MUST NOT assume
   that an arbitrary Submodel can be projected into a passport.
3. **A passport API is not this API.** [EN 18222][EN18222] defines its own
   resource paths, its own registration operation and an interface addressing
   individual data elements within a passport. Serving an AAS Registry does not
   make an implementation conformant to it, and this specification does not
   claim that it does.

What this model does contribute is the part a plain AAS server cannot provide.
[EN 18222][EN18222] requires a passport to be retrievable as it stood at a given
date. The AAS metamodel has no version history, so an AAS server has nothing to
answer that request from. An AAS Registry answers it from Versions
([Section 1.4](#14-versioning)), and the same Version stack supplies the
auditable, tamper-evident record of changes that access-rights requirements
depend on.

The `assetkind` attribute carries the granularity a passport is issued at.
`Type` is a product model, `Instance` an individual item and `Batch` a
production lot, and a Consumer MUST NOT substitute one for another.

## 8. Security

This specification inherits the security considerations of the
[xRegistry Core specification][xRegistry Core] and adds the following.

An AAS Registry frequently holds commercially sensitive information about
physical assets, and the metadata is sensitive even where the documents are not.
A `specificassetids` entry can reveal a serial number, and the mere existence of
a shell can reveal that an organization holds an asset. An implementation
SHOULD treat collection listings as disclosing, and SHOULD apply the same access
control to them as to the entities they enumerate.

Registries that serve regulated passports are additionally subject to
requirements on the prevention of bulk extraction. An implementation SHOULD
bound or rate-limit collection queries, and SHOULD do so in a way that does not
impede access to information that has to remain publicly available.

Where a `digest` is present a Consumer SHOULD verify it against the bytes it
retrieved before trusting a document, particularly for a document obtained
through federation. Where stronger provenance is needed, packages carry
signatures and attestations; see [AAS Packages](xRegistry-AAS-Packages.md).

## Annex A. Correspondence to the AAS HTTP API

This annex is informative. It maps the operations of the AAS HTTP API onto their
xRegistry equivalents, for readers who know that interface.

| AAS operation | xRegistry equivalent |
|---|---|
| Get all shells | `GET /shells` |
| Get shell by id | `GET /shells/<SHELLID>` |
| Create shell | `POST /shells` |
| Delete shell by id | `DELETE /shells/<SHELLID>` |
| Get all submodels of a shell | `GET /shells/<SHELLID>/submodels` |
| Get submodel by id | `GET /shells/<SHELLID>/submodels/<SUBMODELID>` |
| Get submodel metadata | append the `$details` suffix |
| Replace submodel | `PUT` the document, creating a new Version |
| Delete submodel | `DELETE /shells/<SHELLID>/submodels/<SUBMODELID>` |
| Get all shell descriptors | `GET /shells` where entries carry a URL or `xref` |
| Get descriptor by id | `GET /shells/<SHELLID>` for the same entity |
| Look up shells by asset link | `GET /shells?filter=specificassetids[*].value=<VALUE>` |
| Look up by global asset id | `GET /shells?filter=globalassetid=<VALUE>` |
| Get all concept descriptions | `GET /conceptdictionaries/<DICTID>/conceptdescriptions` |
| Get AASX package by id | `GET /aasxregistries/<REGID>/packages/<PACKAGEID>` |
| Get shells changed since | `GET /shells?filter=modifiedat>=<TIMESTAMP>` |
| Get submodel as of a date | select the newest Version not later than that date |
| Get submodel element by path | no equivalent; see [Section 1.5](#15-document-store) |
| Invoke an operation | no equivalent; this model does not address behaviour |

Two rows have no equivalent, and both have the same cause: xRegistry addresses
documents rather than structures within them. An implementation that requires
element-level access or operation invocation delegates those to the AAS
interface of the system it projects.

[xRegistry Core]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html
[xRegistry primer]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/primer.html
[xRegistry Endpoint]: https://xregistry.io/xreg/xregistryspecs/endpoint-v1/docs/spec.html
[xRegistry Schema]: https://xregistry.io/xreg/xregistryspecs/schema-v1/docs/spec.html
[xRegistry self]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#self-attribute
[xRegistry xref]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#xref-attribute
[xRegistry compatibility]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#compatibility-attribute
[xRegistry version-ids]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#version-ids
[xRegistry hasdocument]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html#hasdocument
[RFC3986]: https://datatracker.ietf.org/doc/html/rfc3986#section-2.3
[IEC63278]: https://webstore.iec.ch/publication/65628
[IEC61406]: https://webstore.iec.ch/publication/67673
[EN18219]: https://standards.cencenelec.eu/dyn/www/f?p=205:110:0::::FSP_PROJECT:79143
[EN18222]: https://standards.cencenelec.eu/dyn/www/f?p=205:110:0::::FSP_PROJECT:79146
[EN18223]: https://standards.cencenelec.eu/dyn/www/f?p=205:110:0::::FSP_PROJECT:79147
