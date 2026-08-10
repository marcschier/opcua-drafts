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
<!-- words: templatenamespace dictionaryidentifier storeidentifier -->
<!-- words: submodeltemplateid conceptdictionaryid aasxregistryid historypolicy -->

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
> `xid` either way. A registry MAY begin hosting an entity that was created as
> an `xref` descriptor without changing its identity. Once the registry has
> accepted any local Version for that Resource, however, it MUST NOT convert
> the Resource to `xref`: the Core conversion removes the local Version
> collection and would violate the retain-all history contract. Such a
> conversion request MUST fail without changing the Resource or any retained
> Version.

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
the `administration` attribute. A `submodel`, `conceptdescription`, `package` or
`referrer` is a **content-bearing Resource**. The first three are defined with
`versionmode` set to `modifiedat`, `singleversionroot` set to `true` and
`maxversions` set to `0`. A `referrer` is immutable and contains exactly one
retained Version.

The xRegistry Core 1.0-rc3 lifecycle is intentionally permissive: it allows an
existing Version to be replaced, and `maxversions: 0` means no numeric limit but
still permits an implementation to prune Versions. Those permissions are not
sufficient for an as-of-date or audit service. This specification narrows them
as follows:

- For a `submodel`, `conceptdescription` or `package`, the first accepted
  content state MUST create a Version. Any later change to the document bytes,
  document URL, `contenttype`, `format`, or any domain attribute defined for
  the Version other than its source identity MUST create a new Version with a
  new `versionid`. Correcting a value is a change; it MUST NOT overwrite the
  Version that carried the incorrect value. A different source identity creates
  a different Resource. For a `referrer`, the immutable manifest digest is the
  Resource source identity, so any changed referrer is a different Resource; an
  existing referrer MUST NOT gain a second Version.
- Once created, a Version's document, document location, `contenttype`,
  `format`, source identity and domain attributes MUST be immutable. Changing
  which Version is the default, and the Core metadata that reports that choice,
  does not alter a Version's content state.
- Every Version MUST be retained without expiration and remain directly
  retrievable by its Version `xid` for the operational lifetime of the
  registry. A conforming implementation MUST NOT prune or delete a Version, and
  MUST NOT destructively delete the owning Resource or Group. For history-bearing
  Resources, explicit `maxversions: 0` declares that there is no numeric cap and
  the Core permission to prune at that value does not apply. A `referrer` has
  `maxversions: 1` because it contains exactly one immutable Version, which is
  retained in full. The required `meta.historypolicy` value `retain-all` makes
  this stronger retention rule discoverable. `historypolicy` is a domain
  extension declared by `metaattributes`; a Producer MUST NOT place it in
  xRegistry's reserved system-managed `resourceattributes` object.
- A new Version's `modifiedat` is the time at which the registry accepted that
  content state. To answer an as-of-time request for a history-bearing Resource,
  a Consumer selects the Version with the greatest `modifiedat` not later than
  the requested time, breaking a timestamp tie by the case-insensitive ordering
  of `versionid`.

The runtime representation of that domain retention policy is inside the
Resource `meta` object:

```json
{
  "meta": {
    "historypolicy": "retain-all"
  }
}
```

These requirements are observable: a conformance test can write two different
documents, retrieve both Version `xid`s, and verify that the first still returns
its original state. A service that keeps only the latest document MUST NOT
claim the as-of-date or audit behaviour defined by this specification.

The following identity rules also apply:

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

Group metadata and the Resource default selection are mutable. Content-bearing
Resources are append-only under the requirements of
[Section 1.4](#14-versioning): an update creates a Version and destructive
Version or Resource deletion is not a conforming operation. An implementation
that projects a read-only backing system MUST declare the restriction through
its [`capabilities`][xRegistry Core].

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
  retrieves. `digestalg` is REQUIRED when `digest` is present and is
  case-sensitive; only the exact enum spellings `Sha256`, `Sha384` and
  `Sha512` are valid.

A `submodel` MUST NOT carry a `digest` for bytes the registry has not itself
seen. Publishing a digest for a delegated document would assert an integrity
guarantee the registry cannot keep.

### 4.3. Submodel Templates

A `submodeltemplate` Group is one publisher's family of Submodel Templates. Its
Submodels are the ones whose `kind` is `Template`.

- `templatenamespace` is REQUIRED and is the publisher's authored namespace for
  the template family. It is the sole authority for the Group's identity, and
  `submodeltemplateid` is its symbolic identifier.
- `publisher` names the publishing organization. It is descriptive metadata
  and MUST NOT be used as an identity.

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

- `dictionaryidentifier` is REQUIRED and is the dictionary's authored
  identifier. It is the sole authority for the Group's identity, and
  `conceptdictionaryid` is its symbolic identifier.
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

| Entity type | REQUIRED source identity | Derived entity id |
|---|---|---|
| `shell` | `aasidentifier` | `shellid` |
| `submodeltemplate` | `templatenamespace` | `submodeltemplateid` |
| `conceptdictionary` | `dictionaryidentifier` | `conceptdictionaryid` |
| `aasxregistry` | `storeidentifier` | `aasxregistryid` |
| `submodel` | `submodelidentifier` | `submodelid` |
| `conceptdescription` | `conceptidentifier` | `conceptdescriptionid` |
| `package` | `packageidentifier` | `packageid` |
| `referrer` | `manifestdigest` | `referrerid` |

Each source identity in the table is the sole authority for that entity. The
derived entity id MUST be the
[symbolic identifier](#51-aas-identifiers-and-xids) of the exact source identity,
and an implementation MUST NOT recover a source identity by attempting to
invert the construction. Once an entity is created, its source identity MUST NOT
change; a different source identity creates a different entity. A Resource's
full source identity is the tuple of its parent Group source identity and its
own source identity; consequently its full `xid` is a pure function of that
tuple and the two model collection names.

The construction is defined here in full. It builds a **symbolic identifier**
from a source string; the result is a dot-separated token in the alphabet
`A-Z a-z 0-9 _ . -`, a strict subset of what xRegistry permits, so that it is
simultaneously safe in a URL, on a command line and as a file name in the
[file-system representation][xRegistry primer].

1. Split the source into an *authority* and a *path*. For an absolute URI with
   an authority component the authority is the host together with its port when
   present, and the path is the URI path; the scheme, userinfo, query and
   fragment are discarded. This authority form is used only when the untouched
   source string is an RFC 3986 absolute URI with a syntactically valid scheme
   and authority. The scheme MUST begin at the first character of the source,
   raw whitespace is not permitted, percent escapes are well-formed, the path,
   query and fragment use RFC 3986 characters, an IP literal is bracketed and
   syntactically valid, and a present port is decimal in the range 0 through
   65535. An implementation MUST validate the untouched source before using a
   URI library's parsed result, because such libraries can discard leading
   spaces or control characters.
   For a URN the authority is empty and the path is the URN split on `:`.
   Otherwise — including leading or trailing whitespace, a malformed bracketed
   host, textual or out-of-range port, or other URI parsing failure in a
   free-form source — the authority is empty and the exact source is split on
   `/`. An implementation MUST NOT reject a source identity solely because URI
   parsing fails.
2. Reverse the authority's `.`-separated labels (`contoso.com` becomes `com`,
   `contoso`), appending the port, where present, as a further label. A
   bracketed IP literal is one label; dots within that literal are not label
   separators.
3. Percent-decode each path segment and discard the empty ones.
4. Normalize each label: replace every run of characters outside
   `A-Z a-z 0-9 _ . -` with a single `-`; collapse runs of `-` and runs of `.`;
   strip leading and trailing `-` and `.`; discard a label that becomes empty.
   Letter case is preserved.
5. Join the surviving labels with `.`. If no label survives, the identifier is
   `_`.
6. If the readable prefix is longer than 63 characters, drop trailing labels —
   never the first — until it is at most 63 characters long. If the first
   surviving label is itself longer than 63 characters, truncate it to 63 and
   strip any trailing `-` or `.`. If that produces an empty prefix, use `_`.
7. Append `.` followed by all 64 lower-case hexadecimal characters of the
   SHA-256 digest of the UTF-8 encoding of the **exact source string**. This
   suffix is ALWAYS present. Its presence MUST NOT depend on the contents of a
   registry, a collision lookup or insertion order.

The construction is deterministic and closed-form, so a Producer and a Consumer
agree without a registry lookup. The same source identity therefore produces the
same id when it is the only entity in a collection, when a normalized-prefix
collision is present, and when entities are inserted in any order. The
construction is one-way, so only the forward direction is defined: an
implementation recovers an AAS identifier by reading the `aasidentifier`,
`submodelidentifier`, `conceptidentifier` or other source-identity attribute,
never by inverting the construction. Applied to AAS identifiers it gives:

| Source identity | Derived id |
|---|---|
| `https://fabrikam.com/aas/pump/SN-001` | `com.fabrikam.aas.pump.SN-001.07e57fb738a86393146c877d2808f53a695b5c561676cf9e10a89a127e2124a3` |
| `https://contoso.com/ids/sm/nameplate` | `com.contoso.ids.sm.nameplate.118270ac2b1c9a2ea6a8a1baa6f97baf78cc576226978fbbbf36afdab3f4ee0d` |
| `0173-1#02-AAO677#002` | `0173-1-02-AAO677-002.4a508ebd70e19917cd187073e2ff250e75d464260868f755e40ccb04d95948ca` |
| `urn:uuid:2c4c1b0e-0e2a-4e2f-9a7e-3b3a1b7c9d21` | `urn.uuid.2c4c1b0e-0e2a-4e2f-9a7e-3b3a1b7c9d21.4c1bae38c355378c18a8b6a293df1ffa4143c4c0e591150417973255a6d265e9` |
| `http://[` | `http.0e5178f5dcc20d0b0c03a2996580308beaaad626bec2d6379bfa2e09aec87622` |

Three properties of the construction matter here specifically:

- **It is independent of registry state.** The hash of the exact source string
  is always present. For example, `https://example.com/ids/a+b` and
  `https://example.com/ids/a:b` share the readable prefix
  `com.example.ids.a-b` but have different suffixes, and either one has the
  same id whether or not the other is present. This is not an optimization: an
  identifier scheme that allowed registry contents or insertion order to
  change an id would break federation and the no-reassignment requirement.
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

An `xref` descriptor MUST be established before this registry accepts a local
Version for that Resource. A Resource with one or more retained local Versions
MUST NOT be converted in place to `xref`, even if another registry now serves
the same entity. A conforming implementation MUST reject that operation and
leave every Version directly retrievable. This restriction narrows the Core
`xref` conversion semantics in order to preserve the mandatory history in
[Section 1.4](#14-versioning).

This is what makes AAS registries composable across a supply chain. An
integrator's registry can describe a supplier's component and delegate the bytes
to the supplier's own registry, without copying the supplier's content and
without either party re-authoring anything.

The identity rule is the one that makes it work, and it is absolute:

> Identity is carried by the source-identity attributes of
> [Section 5.1](#51-aas-identifiers-and-xids) and the `xid` derived from them,
> never by an endpoint. A registry that exposes a local proxy for a remote
> entity MUST retain the remote entity's source identities, and MUST NOT treat
> the local endpoint as part of that entity's identity. The external authority
> identifies the serving endpoint, not the entity.

Consequently:

- Every source-identity attribute in the table of
  [Section 5.1](#51-aas-identifiers-and-xids) MUST be stable across federated
  registries. A federating registry MUST NOT rewrite one.
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

A conformance test for this rule creates and retains two local Versions,
attempts to convert their Resource to `xref`, and verifies that the operation
fails and both original Version `xid`s still return their original documents.

### 5.4. Discovery

The AAS API series provides a discovery service that maps asset keys onto shell
identifiers. In this model that is a filter over the `shells` collection, and no
separate service is needed:

```http
GET /shells?filter=globalassetid=https://fabrikam.com/asset/SN-001
GET /shells?filter=specificassetids[*].value=SN-001
GET /shells?filter=assetkind=Instance,derivedfrom=/shells/com.fabrikam.type.pump.053294821d06d4b69f58c3ff86c228fe5bc9f04ca3c0473a0ceb7c5296bd16c3
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
([Section 1.4](#14-versioning)). The retained immutable Version stack supplies
the auditable record of content changes; where a Version also carries a digest,
a Consumer can additionally verify the integrity of the bytes it retrieved.

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
| Delete shell by id | no destructive equivalent while the Group owns retained content-bearing Resources |
| Get all submodels of a shell | `GET /shells/<SHELLID>/submodels` |
| Get submodel by id | `GET /shells/<SHELLID>/submodels/<SUBMODELID>` |
| Get submodel metadata | append the `$details` suffix |
| Replace submodel | `PUT` the document, creating a new Version |
| Delete submodel | no conforming destructive equivalent; all Versions remain addressable |
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
