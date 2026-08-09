# AAS JSON-LD mapping

A JSON-LD mapping for the Asset Administration Shell, as a fourth technical data format alongside
the XML, JSON and RDF mappings of IDTA-01001 Part 1.

| | |
|---|---|
| [`AAS-JsonLd.md`](AAS-JsonLd.md) | the specification |
| [`aas.context.jsonld`](aas.context.jsonld) | the JSON-LD context, generated from the pinned tables |
| [`UPSTREAM-DEFECTS.md`](UPSTREAM-DEFECTS.md) | the defects found in the upstream artefacts, with evidence |
| `upstream/` | the pinned ontology, SHACL schema and JSON Schema |
| `fixtures/` | 15 example pairs vendored so the tools run offline |
| `tools/` | the lifting, the lowering, the context generator and the conformance runner |

## What this adds

IDTA already publishes an OWL ontology and a SHACL schema for the AAS metamodel, and RDF is already
a normative serialization. This document does not define a vocabulary; it reuses
`https://admin-shell.io/aas/3/0/`. What is missing upstream is a defined conversion from the JSON
serialization to RDF, and a representation of the information the RDF serialization does not carry.

Two gaps motivate it, both measured over the 2 424 readable example pairs published with the pinned
release rather than argued:

- **The RDF serialization cannot represent 175 documents (7.2%) faithfully.** It discards the order
  of every multi-valued property, including `Reference/keys`, where the key sequence *is* the
  reference path. Those 175 documents come back different from how they went in.
- **An `id` that is not a legal IRI has no defined subject term.** An IRDI such as
  `0173-1#02-AAO677#002` cannot be an IRI, and no published example exercises the case.

## Results

| Claim | Result |
|---|---|
| `AASLD-RdfCompatible` | 2 402 of 2 424 (99.1%) isomorphic to the published Turtle |
| `AASLD-JsonRoundTrip`, with the ordering graph | 2 424 of 2 424 (100%) |
| `AASLD-JsonRoundTrip`, core graph alone | 2 249 of 2 424 (92.8%) |
| the context of clause 5, alone | 62.1% of the graph; 0 documents exactly |

The context is a convenience layer, not the conformance mechanism, and the specification says which
three things it cannot do and why a JSON-LD processor rejects each attempt.

## Run it

```powershell
# fetch the pinned example corpus into .corpus (untracked, ~2400 pairs)
python companion-specs\AAS\jsonld\tools\fetch_corpus.py

# regenerate the context and measure what it reaches
python companion-specs\AAS\jsonld\tools\make_context.py --measure

# the three conformance claims
python companion-specs\AAS\jsonld\tools\conformance.py
```

Without the corpus the tools fall back to `fixtures/`, so a clone runs offline. `rdflib` is required
for graph comparison and `pyld` for the context measurement.

```powershell
python companion-specs\AAS\jsonld\tools\lift.py <input.json> --base https://example.org/aas/
python companion-specs\AAS\jsonld\tools\lower.py <graph.nt> --order <order.nt>
```
