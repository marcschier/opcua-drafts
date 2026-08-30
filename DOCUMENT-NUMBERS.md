# Document numbers

Every specification published from this repository is named by an OPC document number: the
number is the identity of the document, and the specification publisher uses it to name the
artifacts — `OPC 99003-1` becomes `artifacts/OPC-99003-1.xml` and `artifacts/OPC-99003-1.docx`.

**The numbers below are placeholders.** The OPC Foundation assigns real numbers on submission.
The `99xxx` block is outside every range the Foundation uses, so a placeholder cannot be mistaken
for an assignment and cannot collide with one. Each document also carries `releaseType: Draft`,
which is what puts the provisional banner on the cover.

This file exists because the number has to be unique across both repositories and neither
repository can see the other. A document that is public today may be released into
`OPCF-Members/spec-drafts` tomorrow, and it keeps its number when it moves — so the two copies of
this file are identical, and a number is allocated here before it is written into a
`manifest.json`.

## Allocation

A number identifies a *series*; the suffix identifies a part within it. A series with one part
still writes the suffix, because a second part is a common outcome and renumbering a published
document is not.

| Number | Series | Part | Specification | Repository |
|---|---|---|---|---|
| OPC 99001 | OPC UA for Apache Arrow Encoding | -1 | Columnar DataEncoding, PubSub batches and historian access | public |
| OPC 99002 | OPC UA for Apache Avro Encoding | -1 | Binary DataEncoding and PubSub message mapping | private |
| OPC 99003 | OPC UA for Data Channels | -1 | Streaming over an established SecureChannel | both |
| OPC 99003 | OPC UA for Data Channels | -3 | Amendments to OPC 10000-3: Address Space Model | both |
| OPC 99003 | OPC UA for Data Channels | -4 | Amendments to OPC 10000-4: Services | both |
| OPC 99003 | OPC UA for Data Channels | -6 | Amendments to OPC 10000-6: Mappings | both |
| OPC 99004 | OPC UA for xRegistry | -1 | Registry base model | both |
| OPC 99005 | OPC UA for Observability Export | -1 | Bindings to OpenTelemetry | both |
| OPC 99006 | OPC UA for Schema Registry | -1 | In-server registry of encoding schemas | public |
| OPC 99007 | OPC UA for Generators | -1 | Generator sets | public |
| OPC 99008 | OPC UA for OpenUSD | -1 | Binding | private |
| OPC 99008 | OPC UA for OpenUSD | -2 | Scene Materialization | private |
| OPC 99009 | OPC UA for WoT Binding | -1 | JSON-LD vocabulary and NodeSet2 mapping | private |
| OPC 99010 | OPC UA for WoT Connectivity | -1 | Thing Description registry and projection | private |
| OPC 99011 | OPC UA for Vision | -1 | Machine vision systems | public |
| OPC 99012 | OPC UA Vision | — | Research whitepaper; not a companion specification | public |

The Data Channels part digits mirror the core part each document amends, so OPC 99003-4 amends
OPC 10000-4. The alternative — numbering them -2, -3, -4 in the order they were written — loses
the one fact a reader needs from the number.

## What is not numbered

A number names a document the Foundation publishes. Three kinds of file in these repositories are
not that.

**Addenda are annexes of the specification they extend**, not documents. Each is named as a
`markdown` key in its parent's manifest and read in with an `{include}` directive, which is where
it already sits in the Word rendering:

| File | Published as |
|---|---|
| `observability-export/di/OPC-UA-DI-Observability-Export-Addendum.md` | OPC 99005-1, Annex D |
| `observability-export/di/OPC-UA-DIDeviceHealth-Observability-Export-Addendum.md` | OPC 99005-1, Annex E |
| `observability-export/facets/OPC-UA-Facets-Observability-Export-Addendum.md` | OPC 99005-1, Annex F |
| `observability-export/pumps/OPC-UA-Pumps-Observability-Export-Addendum.md` | OPC 99005-1, Annex G |
| `observability-export/robotics/OPC-UA-Robotics-Observability-Export-Addendum.md` | OPC 99005-1, Annex H |
| `openusd-binding/pumps/OPC-UA-Pumps-OpenUSD-Bindings-Addendum.md` | OPC 99008-1, Annex G |
| `openusd-binding/robotics/OPC-UA-Robotics-OpenUSD-Bindings-Addendum.md` | OPC 99008-1, Annex H |
| `vision/machine-vision/OPC-UA-Inspection-Vision-Addendum.md` | OPC 99011-1 |
| `vision/robotics/OPC-UA-Robotics-Vision-Addendum.md` | OPC 99011-1 |

**Two documents target xRegistry rather than the OPC Foundation.** `xRegistry-OPC-UA-Api.md` and
`xRegistry-OpenUsd.md` are xRegistry domain specifications: they use RFC 2119 upper-case normative
language because that is what the xRegistry specifications use, and they must be submittable to
that body as they are. Building them into the OPC 20020 template would change what they are. They
stay markdown, and the `check_links` and `check_yaml_json` gates continue to cover them.

**Explanatory and measurement documents are neither.**
`observability-export/di/OPC-UA-DI-Pumps-Inheritance.md` explains how two addenda compose, and
`core-specs/extras/performance/OPC-UA-Encoding-Performance-Comparison.md` reports measurements.
Both are read alongside a specification rather than published as one.

Generated files — `tools/model-reference.md`, `*.NodeSet2.xml`, `*.NodeIds.csv` — are artifacts of
a build and never carry a number.

## Allocating a number

Take the next unused series number, write the whole row here first, and then write it into the
specification's `manifest.json` as `identity.docNumber` together with the matching
`output.sts` and `output.documentationCsv` paths. Copy the file to the other repository in the
same change, so the two never disagree about what a number means.

When the Foundation assigns real numbers, the substitution is this table, one `manifest.json`
field per document, and the `output` paths beside it.
