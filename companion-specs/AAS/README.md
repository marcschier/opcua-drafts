# Asset Administration Shell

All the Asset Administration Shell work in one folder: an OPC UA companion specification, the
xRegistry submission that describes the same registry over HTTP, and the study behind both.

## Files

| File | What it is | Target |
|---|---|---|
| `OPC-UA-AAS.md` | **OPC 30270 v3.00** — the AAS V3 metamodel mapped losslessly onto OPC UA, together with an AAS Registry built on the abstract xRegistry base | OPC Foundation |
| `Opc.Ua.I4AAS.NodeSet2.xml` | Generated NodeSet | — |
| `Opc.Ua.I4AAS.NodeIds.csv` | Generated NodeIds | — |
| `xRegistry-AAS.md` | The AAS registry model as proposed to the xRegistry project | xRegistry |
| `xRegistry-AAS-Packages.md` | AASX packages as content-addressed, signable artifacts | xRegistry |
| `xRegistry-AAS.model.json` | The xRegistry model definition | xRegistry |
| `AAS-xRegistry-Study.md` | The study behind all of the above | — |
| `tools/build_model.py` | Generates the NodeSet, the CSV and Annex A | — |
| `tools/validate_local.py` | Validates the generated NodeSet | — |
| `tools/roundtrip_check.py` | Proves the mapping is lossless, and proves the proof has teeth | — |
| `tools/fixtures/` | The round-trip corpus | — |

The three `xRegistry-*` files are a **mirror** of what was proposed to the xRegistry project from
[`marcschier/spec@aas-domain-spec`](https://github.com/marcschier/spec/tree/aas-domain-spec). If that
branch changes in review, refresh the copy here.

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
which any choice is left to the implementer cannot be generated. It forces four decisions:

- **A value is carried as three facts, not one.** Most xsd types map onto an OPC UA built-in
  directly — `Decimal`, `Integer`, `UInteger` and `Duration` all exist. What a typed value alone
  cannot carry is which xsd type it was authored as, since several map onto one OPC UA type, and
  the exact lexical form, since `1.500000` and `1.5` are the same number written differently. So an
  element carries `Value`, `ValueType` and a Mandatory `RawValue` of type `AASValueString`, a
  `String` subtype. `RawValue` is normative for round-tripping.
- **Order is stated and recoverable.** An ordered list uses `HasOrderedComponent`, the OPC UA
  ReferenceType that says a collection is a sequence, and each member also carries an `Index`,
  because Browse is not required to return references in order.
- **Identity is deterministic**: String NodeIds built from the AAS identifier and the metamodel's
  own `idShortPath`, so the identifier a generator computes is the one the AAS API already uses.
- **Absent and empty stay different**: an absent field has no node, an empty collection has a node
  with no children.

Annex B of the specification is the proof — every metamodel field, and where it lives.

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
