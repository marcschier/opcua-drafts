# Asset Administration Shell Packages - Version 1.0-rc3

<!-- words: AAS AASX OCI aasx aasxregistries aasxregistry idta oci -->
<!-- words: packageidentifier artifacttype attestations digestalg aasidentifiers -->
<!-- words: hasdocument versionid xid xref referrer referrers untagged -->
<!-- words: fabrikam contoso reproducibility unregistered subresource -->
<!-- words: dpp cosign attestation packageid registryurl namespace -->
<!-- words: handover mediatype opencontainers openusd submodel submodels -->
<!-- words: schemaVersion artifactType -->

## Abstract

This specification defines how an Asset Administration Shell (AAS) is packaged
as an AASX artifact and distributed through a content-addressable registry, and
how such a package store is projected into the xRegistry document format and API
[specification][xRegistry Core]. It is a companion to the
[AAS Registry specification](xRegistry-AAS.md) and shares its
[model definition](xRegistry-AAS.model.json).

## Table of Contents

- [Asset Administration Shell Packages - Version 1.0-rc3](#asset-administration-shell-packages---version-10-rc3)
  - [Abstract](#abstract)
  - [Table of Contents](#table-of-contents)
  - [1. Overview](#1-overview)
    - [1.1. Why a Package Is a Different Thing](#11-why-a-package-is-a-different-thing)
    - [1.2. Relationship to the AAS Registry](#12-relationship-to-the-aas-registry)
    - [1.3. Versioning and Content Addressing](#13-versioning-and-content-addressing)
  - [2. Notations and Terminology](#2-notations-and-terminology)
  - [3. Package Store Model](#3-package-store-model)
    - [3.1. Package Stores](#31-package-stores)
    - [3.2. Packages](#32-packages)
    - [3.3. Formats](#33-formats)
  - [4. The OCI Binding](#4-the-oci-binding)
    - [4.1. Structural Mapping](#41-structural-mapping)
    - [4.2. Media Types](#42-media-types)
    - [4.3. Manifest Shape](#43-manifest-shape)
    - [4.4. Identifiers](#44-identifiers)
  - [5. Signing and Attestation](#5-signing-and-attestation)
    - [5.1. Attaching an Attestation](#51-attaching-an-attestation)
    - [5.2. Surfacing Attestations](#52-surfacing-attestations)
    - [5.3. Verification](#53-verification)
  - [6. Security](#6-security)
  - [Annex A. Registration Status of the Media Types](#annex-a-registration-status-of-the-media-types)

## 1. Overview

An AASX package is the file format in which an Asset Administration Shell is
exchanged: a package holding one or more shells, their Submodels, and the files
those Submodels reference. It is what a manufacturer hands over at the point of
sale, what a supplier ships with a component, and what is archived when a product
leaves the market.

Packages have a different lifecycle from the registry entries they contain. A
registry entry is mutable — a Submodel is corrected, a measurement is added, a
status changes. A package is a release: it is produced once, it is expected not
to change, and its value depends on a recipient being able to prove that it has
not.

That is the property a content-addressable registry provides, and it is why this
document exists as a separate binding rather than as a clause of the
[AAS Registry specification](xRegistry-AAS.md).

### 1.1. Why a Package Is a Different Thing

The AAS API series provides a package file server: an interface for storing and
retrieving AASX packages, in which a package has an assigned identifier and lists
the shells it contains. That interface says nothing about integrity, provenance
or immutability, because those were not its purpose.

They are the purpose here. A handover package, a type-approval package or an
archived passport is exactly the kind of artifact that a recipient has to be able
to verify long after the party that produced it has stopped answering requests.
An [OCI][OCI Distribution] registry addresses artifacts by the digest of their
content, stores arbitrary media alongside a declared artifact type, and carries a
standard mechanism for attaching signatures to an artifact after it has been
published. Those three properties are what this binding uses.

Nothing here requires OCI. [Section 3](#3-package-store-model) defines a package
store abstractly; [Section 4](#4-the-oci-binding) binds it to OCI, and another
binding could bind it elsewhere.

### 1.2. Relationship to the AAS Registry

A package store and an AAS Registry answer different questions about the same
assets:

| Question | Answered by |
|---|---|
| What does this asset's carbon footprint say today? | the registry, from the current Version |
| What did it say last March? | the registry, from an earlier Version |
| What exactly did the supplier hand over, and can I prove it? | a package |

The two are linked in both directions. A `package` MAY carry a `shell` pointing
at the shell it is the packaged form of, where the same registry serves both. A
package's `aasidentifiers` lists the AAS identifiers it contains, so a Consumer
can tell what a package holds without retrieving and opening it.

Neither link is mandatory. A package store MAY be served entirely on its own, and
an AAS Registry MAY be served with no package store at all.

### 1.3. Versioning and Content Addressing

A `package` Resource has Versions like any other, and the rules of the AAS
Registry apply unchanged: the identifier binds to the Resource, and a
`packageid` MUST NOT be derived from the package bytes. A Resource is the
umbrella over its Versions, so an id computed from content would produce a new
Resource on every release rather than a new Version of one.

Content addressing enters at the Version level. Each Version carries a `digest`
of the exact bytes a Consumer retrieves, and that digest — not the `versionid` —
is the integrity anchor:

> A `versionid` identifies *which release* a Consumer wants. A `digest`
> identifies *what that release contains*. A Consumer that has verified a digest
> has verified the artifact; a Consumer that has only matched a `versionid` has
> verified nothing.

The distinction matters because release labels are mutable in most package
stores and digests are not. Where a store permits a label to be moved to
different content, an implementation MUST reflect the move as a new Version
rather than by changing an existing Version's `digest`. A Version's `digest` is
immutable once published.

## 2. Notations and Terminology

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD",
"SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be
interpreted as described in [RFC 2119](https://tools.ietf.org/html/rfc2119).

This document uses the terminology of the [AAS Registry
specification](xRegistry-AAS.md), and additionally:

- **Package** — an AASX artifact: one retrievable unit holding one or more
  shells together with their Submodels and referenced files.
- **Package store** — a system that stores packages and returns them by name.
- **Attestation** — a signature, provenance statement or other assertion about
  a package, produced by an identified party and verifiable independently of the
  store that holds it.

## 3. Package Store Model

The model definition resides in the [model.json](xRegistry-AAS.model.json) file shared with
the [AAS Registry specification](xRegistry-AAS.md). This document defines the
`aasxregistries` Group type and its `packages` Resource type.

### 3.1. Package Stores

An `aasxregistry` Group is one package store, or one namespace within one.

- `registryurl` is the base URL of the backing store.
- `namespace` is the portion of that store this Group covers, where the store is
  subdivided.

Separating stores into Groups rather than flattening them keeps a registry able
to front several stores at once — a public one and an internal one, or one per
supplier — while presenting a single collection to a Consumer.

### 3.2. Packages

A `package` Resource is one AASX package served as a document.

- `packageidentifier` is REQUIRED and is the package's name as held by the
  backing store. It is the authority for the package's identity, and the
  `packageid` is the symbolic identifier derived from it
  ([Section 4.4](#44-identifiers)).
- `format` is REQUIRED ([Section 3.3](#33-formats)).
- `digest` and `digestalg` carry the content hash of the exact bytes a Consumer
  retrieves. `digestalg` is REQUIRED when `digest` is present. A package Version
  SHOULD carry a `digest`; a package store that cannot supply one is not
  providing the property this binding exists for.
- `aasidentifiers` lists the AAS Identifiable ids the package contains.
- `artifacttype` is the media type declaring what the artifact is, where the
  backing store carries one ([Section 4.2](#42-media-types)).
- `shell` points at the shell this package is the packaged form of, where the
  same registry serves it.
- `subject` is the digest of the artifact this one is attached to, where this
  Resource is itself an attestation rather than a package
  ([Section 5](#5-signing-and-attestation)).
- `attestations` lists the attestations attached to this package
  ([Section 5.2](#52-surfacing-attestations)).

A `package` MUST NOT carry a `digest` for bytes the registry has not verified.

### 3.3. Formats

| `format` | Document |
|---|---|
| `AASX/3.0`, `AASX/3.1` | An AASX package as defined by the AAS package file format specification of that version |
| `Opaque/1.0` | An artifact this store serves but does not interpret |

The enumeration is not strict. An attestation surfaced as a Resource in its own
right is served with `Opaque/1.0` and identified by its `artifacttype`.

## 4. The OCI Binding

This clause binds the package store model to an [OCI][OCI Distribution]
registry. It is one binding of several possible ones, and an implementation MAY
serve the same model over a different store.

### 4.1. Structural Mapping

| xRegistry | OCI |
|---|---|
| `aasxregistry` Group | one registry, or one namespace within it |
| `package` Resource | one repository |
| Version | one tag |
| `digest` | the manifest digest |
| document | the package blob |
| `artifacttype` | the manifest `artifactType` |
| `subject` | the manifest `subject` digest |
| `attestations` | the entries returned for this manifest by the referrers interface |

A Consumer retrieving a Version's document receives the package blob, not the
manifest. The manifest is metadata about the artifact and is surfaced through
the Resource's attributes; an implementation MUST NOT return a manifest where a
document is requested.

Untagged manifests — those reachable only by digest — MAY be omitted from the
Versions collection. An implementation that omits them MUST still resolve a
`digest` that names one, because an attestation's `subject` refers to a digest
and not to a tag.

### 4.2. Media Types

A package is stored with an artifact type declaring what it is. This
specification defines the following values:

| Artifact | Media type |
|---|---|
| AASX package | `application/vnd.idta.aasx.v3+zip` |
| AAS environment, JSON serialization | `application/vnd.idta.aas.v3+json` |
| AAS environment, XML serialization | `application/vnd.idta.aas.v3+xml` |
| Submodel, JSON serialization | `application/vnd.idta.aas-submodel.v3+json` |

These values are **proposals and are not registered**; see
[Annex A](#annex-a-registration-status-of-the-media-types). An implementation
MUST treat an unrecognized artifact type as opaque rather than rejecting the
artifact, so that a registry that adopted a different value remains readable.

The `format` attribute and the `artifacttype` attribute are not the same thing
and MUST NOT be conflated. `format` is the xRegistry statement of what the
document is; `artifacttype` is whatever the backing store recorded. A registry
projecting a store whose artifacts were pushed before these values existed will
carry a `format` of `AASX/3.0` and an `artifacttype` that is absent or
unrecognized, and that is a correct projection.

### 4.3. Manifest Shape

A package is stored as a manifest whose `artifactType` is the value from
[Section 4.2](#42-media-types), whose configuration blob is the standard empty
descriptor, and whose single layer is the package itself:

```json
{
  "schemaVersion": 2,
  "mediaType": "application/vnd.oci.image.manifest.v1+json",
  "artifactType": "application/vnd.idta.aasx.v3+zip",
  "config": {
    "mediaType": "application/vnd.oci.empty.v1+json",
    "size": 2,
    "digest": "sha256:44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a"
  },
  "layers": [
    {
      "mediaType": "application/vnd.idta.aasx.v3+zip",
      "size": 918273,
      "digest": "sha256:5d41402abc4b2a76b9719d911017c592a1b2c3d4e5f60718293a4b5c6d7e8f90"
    }
  ],
  "annotations": {
    "org.opencontainers.image.created": "2026-08-07T09:00:00Z"
  }
}
```

The empty configuration descriptor is used because an AASX package has no
separate configuration document: everything a Consumer needs is inside the
package. An implementation MUST NOT invent a configuration blob to carry
metadata that belongs in xRegistry attributes.

A package with exactly one layer is the normal case. An implementation MAY store
a package as several layers where the store benefits from it, and MUST then
present the reassembled package as the document.

### 4.4. Identifiers

An OCI repository name is more constrained than an AAS identifier and
differently constrained from an xRegistry entity id. The rule is the same as in
the AAS Registry:

> A `package`'s `packageidentifier` MUST be its repository name as held by the
> store, and its `packageid` MUST be the
> [symbolic identifier][symbolic identifier] of that `packageidentifier`. The
> `packageidentifier` attribute is REQUIRED and is the authority: an
> implementation MUST NOT recover a repository name by attempting to invert the
> construction.

A `versionid` is the tag as held by the store. Tags are already constrained to a
character set that xRegistry accepts, so a tag is used unchanged; where a store
permits a tag this specification's grammar does not, the symbolic identifier
construction applies to it as well.

Note that the AAS identifiers a package contains are unaffected by any of this.
They are carried verbatim in `aasidentifiers`, and a Consumer matching a package
to a shell matches on those, never on the derived ids.

## 5. Signing and Attestation

A package is worth verifying. The whole reason to distribute a handover document
or an archived passport as an immutable artifact is that a recipient can
establish who produced it and that it has not been altered since.

### 5.1. Attaching an Attestation

An attestation is stored as a separate artifact whose `subject` is the digest of
the manifest it attests, and whose `artifactType` declares what kind of
assertion it makes. The store's referrers interface then returns it when queried
for that subject.

This shape is used rather than embedding a signature in the package because it
lets a package be signed more than once, by different parties, at different
times, without the package changing. A supplier signs at handover; a testing
authority attaches a conformity attestation later; a recipient attaches its own
acceptance record. All three refer to one unchanged artifact.

An implementation MUST NOT alter a package in order to attach an attestation to
it. An attestation that changed the digest of the thing it attests would be
worthless.

### 5.2. Surfacing Attestations

Attestations appear in two places, and an implementation MAY do either or both:

- As entries in the `attestations` array of the package they attest. Each entry
  carries the `artifacttype` of the assertion, its `digest`, and where the store
  makes it available the `signer` that produced it. This is the convenient form:
  a Consumer reading a package sees what has been asserted about it.
- As `package` Resources in their own right, carrying a `subject` naming the
  digest they attest and a `format` of `Opaque/1.0`. This is the complete form:
  the attestation is retrievable, and its bytes can be verified.

Where both are present they MUST agree. The `attestations` array is a summary of
what the store holds; it is not itself evidence, and a Consumer MUST NOT treat
the presence of an entry as verification.

### 5.3. Verification

A Consumer that requires provenance SHOULD:

1. Retrieve the package Version and compute its digest.
2. Compare that digest against the Version's `digest` attribute. A mismatch
   MUST be treated as a failure, and the package MUST NOT be used.
3. Retrieve the attestations whose `subject` is that digest.
4. Verify each attestation against the trust material for its `artifacttype`,
   by whatever means that attestation format defines.
5. Establish that the verified signer is one the Consumer is willing to trust
   for this purpose. A valid signature by an unknown party establishes only that
   the artifact has not changed since that party signed it.

Step 5 is the one most often skipped and the one that carries the meaning. This
specification defines where attestations live and how they are surfaced; it does
not define whose attestations matter, which is a policy question for the
Consumer and, for regulated artifacts, for the regulation.

## 6. Security

This specification inherits the security considerations of the
[xRegistry Core specification][xRegistry Core] and of the
[AAS Registry specification](xRegistry-AAS.md), and adds the following.

A `digest` attribute is a claim by the registry. A Consumer that has not itself
computed the digest of the bytes it received has verified nothing, however
authoritative the registry appears. Where a registry federates a package it does
not host, it MUST NOT publish a `digest` for bytes it has not verified.

Package stores commonly permit a release label to be moved to different content.
Where the backing store allows this, a `versionid` alone is not a stable
reference and a Consumer that requires one MUST refer to the `digest`.

An attestation establishes what a signer asserted, not that the assertion is
true. A package can be correctly signed and still contain incorrect data, and a
signature by a party the Consumer does not know establishes nothing about
provenance.

Finally, a package is a disclosure boundary. An AASX package contains whatever
its producer put in it, and a package produced for one recipient can contain
Submodels that are controlled data in the sense of the
[AAS Registry specification](xRegistry-AAS.md). An implementation MUST NOT assume that a
package is safe to serve publicly because the shell it derives from is, and
SHOULD apply the disclosure controls of that document to packages as well.

## Annex A. Registration Status of the Media Types

This annex is informative.

The media types in [Section 4.2](#42-media-types) are **not registered**. At the
time of writing no artifact type for AAS or AASX content exists in any registry
of media types, and no prior practice for distributing AAS content as
content-addressable artifacts was found. These values are proposed here so that
implementations converge rather than each inventing their own.

They follow the vendor-tree conventions used by other ecosystems that distribute
non-container artifacts this way, in which the artifact type names the producing
organization and the artifact, and the version of the underlying specification
appears in the type rather than in a parameter.

The appropriate venue for registering them is the organization that maintains
the AAS specification series. Until that happens, an implementation MUST tolerate
a different value, and SHOULD record whatever value it found in `artifacttype`
rather than normalizing it.

[xRegistry Core]: https://xregistry.io/xreg/xregistryspecs/core-v1/docs/spec.html
[symbolic identifier]: ../../core-specs/xregistry/README.md
[OCI Distribution]: https://github.com/opencontainers/distribution-spec
