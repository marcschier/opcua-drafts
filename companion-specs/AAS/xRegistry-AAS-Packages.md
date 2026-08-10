# Asset Administration Shell Packages - Version 1.0-rc3

<!-- words: AAS AASX OCI aasx aasxregistries aasxregistry idta oci -->
<!-- words: packageidentifier artifacttype attestations digestalg aasidentifiers -->
<!-- words: hasdocument versionid xid xref referrer referrers untagged -->
<!-- words: fabrikam contoso reproducibility unregistered subresource -->
<!-- words: dpp cosign attestation packageid registryurl namespace -->
<!-- words: handover mediatype opencontainers openusd submodel submodels -->
<!-- words: schemaVersion artifactType -->
<!-- words: storeidentifier manifestdigest subjectmanifestdigest historypolicy packagebase64 aasxregistryid -->

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
    - [3.3. Referrers](#33-referrers)
    - [3.4. Formats](#34-formats)
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

Every accepted package content state MUST create an immutable retained Version
under [Section 1.4 of the AAS Registry specification](xRegistry-AAS.md#14-versioning).
A package Version's `digest`, `digestalg`, document bytes and domain attributes
MUST NOT change after creation.

The OCI binding has two different content addresses. `manifestdigest` identifies
the immutable OCI manifest and is the source identity from which `versionid` is
derived. `digest` and `digestalg` identify the package blob returned as the
Version document. A tag identifies neither: it is a mutable alias whose raw
value and current target are recorded in a Resource `meta.tags` entry.

An OCI referrer manifest is not a package release. Each attestation or other
referrer is represented by a separate `referrer` Resource and MUST NOT be added
as a Version of a `package` Resource. A late referrer therefore cannot become
the package Resource's default Version under `modifiedat` selection.

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

- `storeidentifier` is REQUIRED and is the stable authored identifier of the
  package store or store namespace. It is the sole authority for the Group's
  identity, and `aasxregistryid` is its
  [symbolic identifier](xRegistry-AAS.md#51-aas-identifiers-and-xids).
- `registryurl` is the current base URL of the backing store.
- `namespace` is the portion of that store this Group covers, where the store is
  subdivided.

Separating stores into Groups rather than flattening them keeps a registry able
to front several stores at once — a public one and an internal one, or one per
supplier — while presenting a single collection to a Consumer.

`registryurl` and `namespace` are routing metadata and MUST NOT be used as
identity. Moving a store without changing `storeidentifier` does not change its
Group `xid`.

### 3.2. Packages

A `package` Resource is one AASX package served as a document.

- `packageidentifier` is REQUIRED and is the package's name as held by the
  backing store. It is the authority for the package's identity, and the
  `packageid` is the symbolic identifier derived from it
  ([Section 4.4](#44-identifiers)).
- `format` is REQUIRED ([Section 3.4](#34-formats)).
- `digest` and `digestalg` are REQUIRED and carry the content hash of the exact
  package blob bytes a Consumer retrieves.
- `manifestdigest` carries the immutable release-manifest digest. It is REQUIRED
  by the OCI binding and is distinct from `digest`.
- `aasidentifiers` lists the AAS Identifiable ids the package contains.
- `artifacttype` is the media type declaring what the artifact is, where the
  backing store carries one ([Section 4.2](#42-media-types)).
- `shell` points at the shell this package is the packaged form of, where the
  same registry serves it.

A `package` MUST NOT carry a `digest` for bytes the registry has not verified.
Its `meta.historypolicy` MUST be `retain-all`.

A package Resource's `meta` object MAY also carry mutable tag discovery
metadata:

- `meta.tags` is an array of entries carrying a raw `tag` and its current
  `manifestdigest`. The raw tag is a value, never a map or object key.

`historypolicy` and `tags` are domain extensions declared by `metaattributes`
and serialized in the Resource `meta` object. A Producer MUST NOT place them in
xRegistry's reserved system-managed `resourceattributes` object. `tags` MUST
NOT be a Version attribute. Updating it MUST NOT alter a Version's document,
attributes, `epoch` or `modifiedat`.

### 3.3. Referrers

A `referrer` Resource is one immutable OCI referrer manifest and the
attestation or other artifact blob that its single layer describes. Each
referrer manifest MUST create a separate Resource in the `referrers`
collection. A `referrer` Resource MUST contain exactly one immutable Version.

- `manifestdigest` is REQUIRED and is the exact OCI referrer manifest digest.
  It is the sole Resource and Version source identity. Both `referrerid` and
  `versionid` MUST be its
  [symbolic identifier](xRegistry-AAS.md#51-aas-identifiers-and-xids).
- `subjectmanifestdigest` is REQUIRED and is the package manifest digest named
  by the OCI manifest's `subject` descriptor.
- `artifacttype` is REQUIRED and identifies the kind of assertion.
- `digest` and `digestalg` are REQUIRED and verify the exact referrer artifact
  blob returned as the Resource document.
- `signer`, where present, identifies the party established when the immutable
  Resource is created.
- `format` MUST be `Opaque/1.0`.

A different referrer manifest digest creates a different `referrer` Resource;
it MUST NOT create another Version of an existing referrer Resource. A
Producer MUST NOT place `subject`, `attestations` or referrer summaries on a
`package` Version. Consequently, adding a referrer cannot affect the package
Resource's Version collection or its default Version.

### 3.4. Formats

| Resource | `format` | Document |
|---|---|---|
| `package` | `AASX/3.0`, `AASX/3.1` | An AASX package as defined by the AAS package file format specification of that version |
| `referrer` | `Opaque/1.0` | An attestation or other referrer artifact the store serves but does not interpret |

The package enumeration is not strict. A `referrer` Resource uses only
`Opaque/1.0` and is identified more specifically by its `artifacttype`.

## 4. The OCI Binding

This clause binds the package store model to an [OCI][OCI Distribution]
registry. It is one binding of several possible ones, and an implementation MAY
serve the same model over a different store.

### 4.1. Structural Mapping

| xRegistry | OCI |
|---|---|
| `aasxregistry` Group | one registry, or one namespace within it |
| `package` Resource | one repository |
| Version `manifestdigest` | one immutable manifest digest |
| Version `versionid` | symbolic identifier of `manifestdigest` |
| Resource `meta.tags[].tag` and `meta.tags[].manifestdigest` | one mutable raw tag-to-manifest-digest alias |
| `digest` and `digestalg` | the single package-layer blob digest |
| document | the package blob |
| `artifacttype` | the manifest `artifactType` |
| `referrer` Resource | one immutable OCI referrer manifest |
| Referrer `manifestdigest` | the referrer manifest digest and sole Resource and Version source identity |
| Referrer `subjectmanifestdigest` | the manifest `subject.digest` |
| Referrer `digest` and `digestalg` | the single referrer-layer blob digest |

A Consumer retrieving a Version's document receives the package blob, not the
manifest. The manifest is metadata about the artifact and is surfaced through
the Resource's attributes; an implementation MUST NOT return a manifest where a
document is requested.

A Consumer retrieving a `referrer` Resource receives the referrer artifact
blob, not the referrer manifest. Package releases and referrers occupy separate
Resource collections; an implementation MUST NOT project a referrer manifest
as a package Version.

An implementation MAY be unable to discover an untagged manifest that it has
never observed. Once it has exposed a manifest as a Version, it MUST retain that
Version after all tags move away from it. It MUST also resolve an observed
manifest by `manifestdigest`, because an attestation's `subject` refers to the
manifest digest and never to a tag or package-blob digest.

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

The manifest MUST contain exactly one package layer. The layer descriptor's
digest algorithm maps to `digestalg`, and its encoded digest value maps to
`digest`. This one-to-one rule makes the Version document and the bytes covered
by `digest` the same object; a multi-layer manifest is not a conforming package
Version in this binding.

The descriptor algorithms `sha256`, `sha384` and `sha512` map respectively to
`digestalg` values `Sha256`, `Sha384` and `Sha512`. A Producer MUST compute the
package-blob digest with the algorithm named by the descriptor and retain that
exact mapped value in the immutable Version; it MUST NOT substitute `Sha256`.
`digestalg` is case-sensitive: only the exact enum spellings `Sha256`, `Sha384`
and `Sha512` are valid. A descriptor that uses any other digest algorithm MUST
NOT be exposed as a conforming package Version.

The digest of the exact manifest bytes is `manifestdigest`. It MUST NOT be copied
into `digest`, because a Consumer receives the layer blob as the Version
document and therefore cannot verify those bytes against the manifest digest.

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

An OCI Version's `manifestdigest` MUST be the digest returned for the exact
manifest bytes, including its algorithm prefix, and its `versionid` MUST be the
[symbolic identifier][symbolic identifier] of that `manifestdigest`.
`manifestdigest` is the sole authority for Version identity. A tag MUST NOT be
used as a `versionid`.

Tags are represented only by the mutable Resource `meta.tags` array. Each entry
MUST carry exactly one raw `tag` and one `manifestdigest`. The raw tag MUST match
`[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}` and MUST be preserved byte-for-byte,
including case and a leading underscore. An implementation MUST NOT use the raw
tag as a map or object key because legal OCI tags are not necessarily legal
xRegistry names.

Each current raw tag MUST appear in exactly one entry. Moving a tag updates that
entry's `manifestdigest`. If the target manifest has not previously been
exposed, the move also creates a new immutable Version; it never edits or
replaces the old Version.

The following tag movement is illustrative. For compactness the rows use
`Opaque/1.0` test blobs rather than complete AASX archives, and show them in
base64 so that their byte verification is reproducible:

| State | Tag `Release_2026.08` target | Version source identity | Package blob (`packagebase64`) | `digest` |
|---|---|---|---|---|
| Initial | `sha256:843f1b84d5129f49ddb26231c1f21fbe9ba5c78d3362731c27f16d1e467c20d0` | same `manifestdigest` | `QUFTWC1wYWNrYWdlLXYxCg==` | `bb9aa6f9880d42b5c4afa6e61baa9b4e4e510e65c332ab62e85a1231c8f7517c` |
| After movement | `sha256:14acf7d897aac9be7dcbcbb3cf57debfb650646e238078b34b1ef301f925b4ad` | same `manifestdigest` | `QUFTWC1wYWNrYWdlLXYyCg==` | `e0c5a0a7d7a81a59853efc1b731eb1ffb8b54016c72dbca93ac33d32bb49f656` |

The corresponding `versionid` values are
`sha256-843f1b84d5129f49ddb26231c1f21fbe9ba5c78d3362731c27f16d1e.4bd67a322e75782f07dda3c551755917b7e8ab393d601e04330d83a34308a790`
and
`sha256-14acf7d897aac9be7dcbcbb3cf57debfb650646e238078b34b1ef301.a30f75ef2b758b023c6fb7d5f00cd82578775423eb4792b08f8b3e10e83aebf2`.

Both rows use `digestalg` `Sha256`. After movement the Resource contains both
immutable Versions, while the `Release_2026.08` entry contains only the second
`manifestdigest`. Computing SHA-256 over each decoded package blob produces its
row's `digest`; computing it over the manifest bytes produces `manifestdigest`,
which is a different verification step.

The array representation preserves legal tags that cannot be xRegistry map
keys. The final entry below has the maximum OCI tag length of 128 characters:

```json
{
  "meta": {
    "tags": [
      {
        "tag": "Release_2026.08",
        "manifestdigest": "sha256:14acf7d897aac9be7dcbcbb3cf57debfb650646e238078b34b1ef301f925b4ad"
      },
      {
        "tag": "_stable",
        "manifestdigest": "sha256:14acf7d897aac9be7dcbcbb3cf57debfb650646e238078b34b1ef301f925b4ad"
      },
      {
        "tag": "Rxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "manifestdigest": "sha256:843f1b84d5129f49ddb26231c1f21fbe9ba5c78d3362731c27f16d1e467c20d0"
      }
    ]
  }
}
```

Note that the AAS identifiers a package contains are unaffected by any of this.
They are carried verbatim in `aasidentifiers`, and a Consumer matching a package
to a shell matches on those, never on the derived ids.

## 5. Signing and Attestation

A package is worth verifying. The whole reason to distribute a handover document
or an archived passport as an immutable artifact is that a recipient can
establish who produced it and that it has not been altered since.

### 5.1. Attaching an Attestation

An attestation is stored as a separate artifact whose `subject` is the
`manifestdigest` of the manifest it attests, and whose `artifactType` declares
what kind of assertion it makes. The store's referrers interface then returns it
when queried for that manifest digest.

This shape is used rather than embedding a signature in the package because it
lets a package be signed more than once, by different parties, at different
times, without the package changing. A supplier signs at handover; a testing
authority attaches a conformity attestation later; a recipient attaches its own
acceptance record. All three refer to one unchanged artifact.

An implementation MUST NOT alter a package in order to attach an attestation to
it. An attestation that changed the digest of the thing it attests would be
worthless.

### 5.2. Surfacing Attestations

An attestation MUST be represented by its own immutable `referrer` Resource in
the package store Group. It MUST NOT be represented as a Version of the
`package` Resource it attests and MUST NOT be summarized by mutable metadata on
that package. A Consumer discovers attestations by selecting `referrer`
Resources whose `subjectmanifestdigest` equals the package
`manifestdigest`.

The referrer manifest digest is the sole source identity for the Resource and
its one Version. The Resource is therefore retrievable by `referrerid`, its
single Version is retrievable by `versionid`, and its returned blob bytes are
verified with that Version's `digest` and exact case-sensitive `digestalg`.

For example, later discovery of an attestation for the first manifest in
[Section 4.4](#44-identifiers) creates a `referrer` Resource whose
`referrerid` and `versionid` are both
`sha256-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.9f447b1b473d359884f2b8541a1ad0b7d194ed59b79e8eee48047ec4830564fd`.
The single Version has these domain attributes; decoding `attestationbase64`
and computing SHA-256 produces the stated `digest`:

```json
{
  "manifestdigest": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "subjectmanifestdigest": "sha256:843f1b84d5129f49ddb26231c1f21fbe9ba5c78d3362731c27f16d1e467c20d0",
  "format": "Opaque/1.0",
  "artifacttype": "application/vnd.dev.cosign.simplesigning.v1+json",
  "signer": "did:example:manufacturer",
  "digestalg": "Sha256",
  "digest": "a5dec971ce22f8a8080036cbc2a16273368074ed1c0e7be8bcfe51970bccfe19",
  "attestationbase64": "YXR0ZXN0YXRpb24tdjEK"
}
```

`attestationbase64` is present only to make the example bytes reproducible; it
is not a model attribute.

Immediately before and after this Resource is added, the package Resource's
default Version remains the Version identified by
`sha256:14acf7d897aac9be7dcbcbb3cf57debfb650646e238078b34b1ef301f925b4ad`.
Adding the referrer MUST NOT modify that package Resource's Version collection,
`defaultversionid`, document, attributes, `epoch` or `modifiedat`. This remains
true even when package defaults are selected automatically by `modifiedat`,
because referrer Versions belong to a different Resource collection.

### 5.3. Verification

A Consumer that requires provenance SHOULD:

1. Retrieve the manifest by `manifestdigest`, compute the digest of the exact
   manifest bytes and compare it with `manifestdigest`. A mismatch MUST be
   treated as a failure.
2. Read the single package-layer descriptor and confirm that its algorithm and
   encoded digest equal the Version's `digestalg` and `digest`.
3. Retrieve the package blob, compute its digest using `digestalg`, and compare
   it with `digest`. A mismatch MUST be treated as a failure, and the package
   MUST NOT be used.
4. Retrieve `referrer` Resources whose `subjectmanifestdigest` is the package
   `manifestdigest`, retrieve each referrer manifest by its `manifestdigest`,
   verify the manifest against that digest, and verify the returned attestation
   blob against the Resource's `digest` using its exact `digestalg`.
5. Verify each attestation against the trust material for its `artifacttype`,
   by whatever means that attestation format defines.
6. Establish that the verified signer is one the Consumer is willing to trust
   for this purpose. A valid signature by an unknown party establishes only that
   the artifact has not changed since that party signed it.

Step 6 is the one most often skipped and the one that carries the meaning. This
specification defines where attestations live and how they are surfaced; it does
not define whose attestations matter, which is a policy question for the
Consumer and, for regulated artifacts, for the regulation.

## 6. Security

This specification inherits the security considerations of the
[xRegistry Core specification][xRegistry Core] and of the
[AAS Registry specification](xRegistry-AAS.md), and adds the following.

A `manifestdigest` or `digest` attribute is a claim by the registry. A Consumer
that has not itself computed the manifest digest over the manifest bytes and the
package digest over the returned blob bytes has verified neither object,
however authoritative the registry appears. Where a registry federates a
package it does not host, it MUST NOT publish a `digest` for bytes it has not
verified.

Package stores commonly permit a release label to be moved to different content.
Where the backing store allows this, a tag is not a stable reference. A Consumer
that requires one MUST refer to the immutable `manifestdigest` or its derived
Version `xid`, and MUST verify the returned package bytes against `digest`.

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
[symbolic identifier]: xRegistry-AAS.md#51-aas-identifiers-and-xids
[OCI Distribution]: https://github.com/opencontainers/distribution-spec
