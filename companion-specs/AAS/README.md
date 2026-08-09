# Asset Administration Shell

All the Asset Administration Shell work in one folder: an OPC UA companion specification, a JSON-LD
mapping for authoring an AAS as linked data, the xRegistry submission that describes the same
registry over HTTP, a DPP and battery passport identifier mapping, and the study behind them.

## Files

| File | What it is | Target |
|---|---|---|
| `OPC-UA-AAS.md` | **OPC 30270 v3.00** — the AAS V3 metamodel mapped losslessly onto OPC UA, together with an AAS Registry built on the abstract xRegistry base | OPC Foundation |
| `Opc.Ua.I4AAS.NodeSet2.xml` | Generated NodeSet | — |
| `Opc.Ua.I4AAS.NodeIds.csv` | Generated NodeIds | — |
| `xRegistry-AAS.md` | The AAS registry model as proposed to the xRegistry project | xRegistry |
| `xRegistry-AAS-Packages.md` | AASX packages as content-addressed, signable artifacts | xRegistry |
| `xRegistry-AAS.model.json` | The xRegistry model definition | xRegistry |
| `AAS-JsonLd.md` | **JSON-LD as a format an AAS is authored in**, and the conversions that make an authored document exportable as JSON, XML and AASX | IDTA |
| `aas.context.jsonld` | The JSON-LD context, generated from the pinned ontology and JSON Schema | IDTA |
| `AAS-DPP-Vocabulary.md` | The DPP and battery passport identifier mapping | IDTA |
| `dpp/mappings.sssom.tsv` | The mapping set, as SSSOM | IDTA |
| `UAV-TYPEREF-PROPOSAL.md` | The one WoT term Annex F needs, proposed to `OPCF-Members/spec-drafts` | OPC Foundation |
| `examples/wot/` | A Thing Description per corpus fixture, each projecting to the AddressSpace of Annex F | — |
| `AAS-xRegistry-Study.md` | The study behind all of the above | — |
| `tools/build_model.py` | Generates the NodeSet, the CSV and Annex A | — |
| `tools/validate_local.py` | Validates the generated NodeSet | — |
| `tools/roundtrip_check.py` | Proves the mapping is lossless, and proves the proof has teeth | — |
| `tools/fixtures/` | The round-trip corpus | — |
| `tools/jsonld/` | Lifting, lowering, context generation, conformance, the DPP inventory and the WoT bridge | — |
| `jsonld/` | The pinned upstream artefacts, the JSON-LD fixtures and `UPSTREAM-DEFECTS.md` | — |

The three `xRegistry-*` files are a **mirror** of what was proposed to the xRegistry project from
[`marcschier/spec@aas-domain-spec`](https://github.com/marcschier/spec/tree/aas-domain-spec). If that
branch changes in review, refresh the copy here.

## JSON-LD, and authoring an AAS as linked data

`AAS-JsonLd.md` defines JSON-LD as a format an AAS is **authored** in. An authored document is an
AAS JSON document and a JSON-LD document at once, so it exports as JSON, XML and AASX through the
existing serializations, and it is RDF that validates against the SHACL schema IDTA publishes.

It does not define a vocabulary. IDTA already publishes a normative OWL ontology and SHACL schema at
`https://admin-shell.io/aas/3/0/`, and those IRIs are reused. Only the ordering-graph terms are
minted.

Two gaps in the published RDF mapping motivate it, both measured over the 2 424 readable example
pairs of the pinned upstream release rather than argued:

- **308 documents (12.7%) carry an array of two or more members**, whose order the RDF mapping
  discards. That includes `Reference/keys`, where the key sequence *is* the reference path.
- **An `id` that is not a legal IRI has no defined subject term.** An IRDI such as
  `0173-1#02-AAO677#002` cannot be an IRI, and no published example exercises the case.

| Claim | Result |
|---|---|
| `AASLD-RdfCompatible` | 2 402 of 2 424 (99.1%): 41 isomorphic outright, 2 361 under the root `idShort` allowance |
| `AASLD-JsonRoundTrip`, with the ordering graph | 2 424 of 2 424 (100%) |
| structurally order-bearing, not guaranteed by the core graph | 308 of 2 424 (12.7%) |
| the context alone | 72.9% of the core graph's predicates and non-blank objects |

`jsonld/UPSTREAM-DEFECTS.md` records seven defects found in the pinned upstream artefacts, with the
evidence for each.

## Authoring an AAS as a Thing Description

Annex F of `OPC-UA-AAS.md` states the correspondence between a WoT Thing Description carrying the
AAS vocabulary and the AddressSpace this specification defines. `examples/wot/` holds one Thing
Description per corpus fixture; each projects to exactly the nodes clause 5.6 materializes.

It needs one term the WoT drafts do not yet have — `uav:typeref`, which types a projected node with
an ObjectType the Server has already loaded. `UAV-TYPEREF-PROPOSAL.md` states it, presents the
alternatives that use only published vocabulary, and gives the converter behaviour it requires. It is
raised as `OPCF-Members/spec-drafts` PR #19.

## Regenerate and validate

```powershell
python companion-specs\AAS\tools\build_model.py
python companion-specs\AAS\tools\validate_local.py
python companion-specs\AAS\tools\roundtrip_check.py

# JSON-LD: fetch the pinned corpus (untracked), regenerate the context, run the claims
python companion-specs\AAS\tools\jsonld\fetch_corpus.py
python companion-specs\AAS\tools\jsonld\make_context.py --measure
python companion-specs\AAS\tools\jsonld\conformance.py

# DPP: read the published templates, regenerate the mapping set
python companion-specs\AAS\tools\jsonld\dpp_inventory.py
python companion-specs\AAS\tools\jsonld\dpp_map.py

# WoT: regenerate examples\wot and check Annex F
python companion-specs\AAS\tools\jsonld\wot_bridge.py <environment.json> --proposed
```

Without the corpus the JSON-LD tools fall back to `jsonld/fixtures/`, so a clone runs offline.
`rdflib` and `pyld` are required.

## Version 3.00 supersedes v1.00

The published OPC 30270 maps the AAS v1.x metamodel. This revision is breaking, for three reasons
that no ordering would have avoided:

- **AAS V3 is not backward compatible with v1.x.** `Asset` and `View` are gone, `AssetInformation`
  and `SpecificAssetId` are new, the identifier type discriminator was removed, and the submodel
  element set was reshaped.
- **The mapping is now lossless**, and reversibility cannot be retrofitted compatibly — it needs a
  value carried in a form the original mapping has no room for, an order carried explicitly, and a
  distinction between absent and empty that the original does not draw.
- **The registry is now part of the specification**, which introduces the xRegistry base as a
  required model.

The namespace URI is unchanged and the model version distinguishes the two; a Client checks the
model version before assuming either shape.

## The two halves

A Server may implement either, or both.

| | Metamodel clauses | Registry clauses |
|---|---|---|
| Unit | one shell's metamodel, in nodes | a catalogue of shells, as folders and files |
| Granularity | per submodel element | per submodel document |
| Access | Read, Write, Call | Open, Read, Close |
| Answers | what is this asset's value now | which shells exist, at what versions, where else served |
| Versioning | none — the metamodel has none | xRegistry Versions |

Where both are present the same shell appears twice, once as a live node tree and once as a
catalogue entry, and the specification defines the link between them. The registry half is what
supplies the version history the metamodel does not have — which matters wherever a record must be
retrievable as it stood on a date.

## Losslessness, and why it shapes everything

`AAS → AddressSpace → AAS` reproduces the original, and the reverse likewise. That requirement is
what makes it possible to compile an AAS into a Server with a source generator, because a mapping in
which any choice is left to the implementer cannot be generated. It forces five decisions:

- **Each xsd type is assigned its own OPC UA DataType.** A built-in where one denotes the type, a
  subtype defined here where two would otherwise share one, as with `xs:anyURI` against `xs:string`
  or `xs:hexBinary` against `xs:base64Binary`. The declared type is read from the value node, and
  the value is carried once. `ValueType` remains Mandatory because the metamodel makes it mandatory
  while making the value optional.
- **Equivalence is judged in the xsd value space.** AAS carries values as strings and defines no
  equality on them; XML Schema defines identity on the value space and a canonical lexical form per
  type. A round trip emits the canonical form, so `"1.500000"` returns as `"1.5"`: equivalent, not
  identical.
- **Order is stated by the ReferenceType and recovered from `Index`.** A list whose `orderRelevant`
  is true uses `HasOrderedComponent`; one whose `orderRelevant` is false uses `HasComponent` and is
  compared as a bag. `Index` carries the position, because Browse is not required to return
  references in order.
- **Identity is deterministic**: String NodeIds built from the AAS identifier and the metamodel's
  own `idShortPath`, so the identifier a generator computes is the one the AAS API already uses.
- **Absent and empty stay different**: an absent field has no node, an empty collection has a node
  with no children.

Annex B of the specification lists every metamodel field and where it lives.

## Regenerate and validate

```powershell
python companion-specs\AAS\tools\build_model.py
python companion-specs\AAS\tools\validate_local.py
python companion-specs\AAS\tools\roundtrip_check.py
```

`build_model.py` emits the NodeSet, the CSV and Annex A, and injects the annex into the
specification, so the prose and the model cannot drift apart. `roundtrip_check.py` runs both
directions over the corpus and then runs a negative control that breaks one normative rule at a
time, so a green result means the rules are load-bearing rather than that the comparison is blind.

Draft numeric NodeIds use the provisional `1001+` block in `http://opcfoundation.org/UA/I4AAS/`;
final NodeIds are assigned by the OPC Foundation.

## A note on sources

Part of the study was made against CEN/CLC/JTC 24 committee texts and an OPC Foundation working
draft. Those documents are licensed, and several were under formal vote at the time. They are
referenced **by standard number and title only**; no text, table or figure from them is reproduced.

The published OPC 30270 v1.00 is likewise license-restricted and is **not** copied. This revision is
authored against the AAS V3 metamodel, which is published under CC BY 4.0, in the standard
companion-specification clause structure.
