# AAS Registry — xRegistry mapping study

This folder holds the design study behind an **xRegistry registry model for the
Asset Administration Shell**, and the record of what was built from it.

Unlike its neighbours in `cloud-specs/`, this folder contains no OPC UA
information model and no NodeSet. The specifications it produced were written
for the [xRegistry project](https://github.com/xregistry/spec) rather than for
the OPC Foundation, in the same way `core-specs/xregistry/xRegistry-OPC-UA-Api.md`
is. The study lives here because it belongs beside the other registry work, and
because the OPC UA binding of xRegistry is what would carry this model into an
AddressSpace.

Files:

- `AAS-xRegistry-Study.md` — the study: prior art, the identifier problem and
  how it was solved, the federation design, the product passport analysis, and
  an honest account of what the mapping cannot express.

## What came out of it

Three documents, proposed to the xRegistry project from
[`marcschier/spec@aas-domain-spec`](https://github.com/marcschier/spec/tree/aas-domain-spec):

| Document | What it is |
|---|---|
| `models/aas/spec.md` | The AAS registry model — shells, submodels, concept dictionaries, federation, disclosure tiers, product passport profile |
| `models/aas/oci.md` | AASX packages as content-addressed, signable artifacts |
| `models/aas/model.json` | The shared model definition, four group types |

The branch is stacked on the OpenUSD registry branch, because the identifier
construction is cited from that specification rather than duplicated.

## The three findings that mattered

**The AAS registry/repository split already exists in xRegistry.** AAS separates
a registry holding descriptors that say where an entity is served from a
repository holding the entity itself. xRegistry expresses that as the difference
between a resource with a stored document and one carrying a URL or an `xref` —
same identity, different hosting. Federation across a supply chain needed no new
machinery, only an explicit rule that identity is never carried by an endpoint.

**Version history is what the mapping adds.** An AAS records one current
revision and no history. EN 18222 requires a product passport to be retrievable
as it stood on a given date, and EN 18239 requires changes to controlled
passport data to be auditable and tamper-evident over time. A plain AAS server
has nothing to answer either from. This is the strongest argument for the
projection, and it was not obvious before reading the standards.

**Disclosure tiering is two-thirds expressible.** Segmentation and advertisement
work. Enforcement does not: access rights are required at data-element
granularity, and an xRegistry document is opaque bytes, so a decision falling
between two elements of one document cannot be taken by the model at all. The
specification says so rather than implying otherwise, and gives two conformant
ways to work within it.

## A note on sources

Part of this study was made against CEN/CLC/JTC 24 committee texts and an OPC
Foundation working draft. Those documents are licensed, and several were under
formal vote at the time. They are referenced **by standard number and title
only**; no text, table or figure from any of them is reproduced here.
