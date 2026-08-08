# Upstream defect register — AAS RDF serialization

**Pinned upstream:** `admin-shell-io/aas-specs-metamodel` at tag **`V3.0.7`**, commit
`21e68502e367b72fd82cfa29488a686cbd3892a5`. Namespace `https://admin-shell.io/aas/3/0/`.

| Artefact | Path | Size |
|---|---|---|
| OWL ontology | `schemas/rdf/rdf-ontology.ttl` | 90 614 |
| SHACL schema | `schemas/rdf/shacl-schema.ttl` | 49 645 |
| JSON Schema | `schemas/json/aas.json` | 45 448 |
| Matched examples | `schemas/{json,rdf}/examples/generated/` | 2 426 pairs |

Copies of the first three are vendored beside this file in `upstream/`. The example corpus is
fetched by `tools/fetch_corpus.py` into `.corpus/`, which is not tracked.

## Artefact precedence

Where the prose, the generated examples and the SHACL schema disagree, this specification takes
them in this order, and records the disagreement below rather than silently choosing:

1. **SHACL schema** — it is executable, so an implementation can be tested against it.
2. **Generated examples** — they are produced by the same toolchain that produces the schemas.
3. **`rdf.adoc` prose** — normative in intent, but demonstrably not what the artefacts do.

## D1 — The root `Identifiable`'s `idShort` is not serialized

**Severity: high. Systematic, fully characterised.**

Of the 2 424 readable matched pairs, **2 383 differ from their JSON counterpart by exactly this
rule and nothing else**, and the remaining 41 agree exactly — those being the cases whose root
carries no `idShort`. There are **zero** unexplained differences, so this is a single defect rather
than a family of them.

The `idShort` of a root `AssetAdministrationShell`, `Submodel` or `ConceptDescription` produces no
`aas:Referable/idShort` triple. The `idShort` of every nested element is serialized correctly.

```jsonc
// schemas/json/examples/generated/AdministrativeInformation/minimal.json
{ "assetAdministrationShells": [ {
    "id": "something_142922d6",
    "idShort": "something_783819f1",     // present
    "modelType": "AssetAdministrationShell", ... } ] }
```

```turtle
# schemas/rdf/examples/generated/AdministrativeInformation/minimal.ttl
<something_142922d6> rdf:type aas:AssetAdministrationShell ;
    <https://admin-shell.io/aas/3/0/Identifiable/id> "something_142922d6"^^xs:string ;
    # no Referable/idShort triple
.
```

**Consequence for this specification.** The corpus is usable as a conformance oracle only once this
deviation is declared. The lifting defined here emits the triple; the conformance runner therefore
compares against the corpus *modulo D1*, and records D1 as an upstream defect rather than
reproducing it.

## D2 — Order is discarded, including where order carries meaning

**Severity: high. Stated by the specification as a design rule, so it is a design defect and not an
implementation bug.**

`rdf.adoc` design rule: *"Multiple object values are represented by repeating the property, one for
each value object."* No `rdf:List`, no `rdf:Seq`, no container membership properties, no index.

This is defensible for a set-valued aggregation. It is not defensible for two cases where the
metamodel gives the order meaning:

- **`Reference/keys`** — the key sequence *is* the reference path. Serialized as repeated,
  unordered `aas:Reference/keys` triples, a three-key path `Submodel → Blob → FragmentReference`
  cannot be reconstructed.
- **`SubmodelElementList/value`** when `orderRelevant` is true. The `orderRelevant` flag itself
  survives as `"true"^^xs:boolean`, so the graph asserts that the order matters while withholding
  it.

**Consequence.** No JSON-LD construct repairs this within the normative graph. `@list` emits an
`rdf:List`, which is neither isomorphic to repeated triples nor matched by the published SHACL.
Ordering is therefore carried in the enrichment graph, by an index predicate rather than an
`rdf:List`, so the published SHACL and ordinary SPARQL both continue to work.

## D3 — Generated Turtle declares no base IRI

**Severity: medium.**

No generated file declares `@base`. Subject terms are written as relative IRI references:

```turtle
<something_142922d6> rdf:type aas:AssetAdministrationShell ;
```

Per Turtle 1.1 §2.4 a relative reference resolves against the retrieval URL, so the same document
denotes different subjects depending on where it was fetched from. The prose does not require a
base.

**Consequence.** The lifting defined here **requires** a base IRI as an explicit parameter and
defines the resulting subject terms in terms of it.

## D4 — A non-IRI `id` has no defined serialization

**Severity: high. A genuine gap, not a contradiction.**

An AAS `Identifiable.id` is an `xs:string` and is routinely an IRDI, for example
`0173-1#02-AAO677#002`. The RDF mapping uses the `id` **verbatim** as the subject term while also
emitting it as an `xs:string` literal. Applied to an IRDI this yields `<0173-1#02-AAO677#002>`,
which is not a legal IRI: the second `#` is forbidden in a fragment by RFC 3986 §3.5, and Turtle
parsers reject it.

`rdf.adoc` says only that *"if no IRI is predefined, a globally unique IRI is generated"*, and gives
no algorithm. No generated example exercises an IRDI `id`; the generator emits only
`something_…`, `urn:…` and `https://…` values, so the case is untested upstream.

**Consequence.** The lifting defined here specifies a deterministic skolemization for an `id` that
is not a legal IRI, and retains the `id` literal unchanged in every case.

## D5 — Prose contradicts the artefacts

**Severity: medium.**

| `rdf.adoc` says | The artefacts do |
|---|---|
| multi-language values become `rdf:langString` | a typed node, `aas:LangStringTextType` / `LangStringNameType`, with separate `AbstractLangString/language` and `AbstractLangString/text` `xs:string` literals; the SHACL expects that node |
| `rdfs:label` is added from `idShort`, `rdfs:comment` from `description` | no generated instance carries either; both appear only on class and property definitions in the ontology |

**Consequence.** Precedence above applies: the artefacts win, and this specification does not emit
`rdfs:label` or `rdfs:comment` on instances.

## D6 — Two corpus files are not valid UTF-8 JSON

**Severity: low. Noted so the counts reconcile.**

`BasicEventElement/maxIntervalOverPatternExamples/only_seconds` and
`Blob/contentTypeOverPatternExamples/number prefix and suffix` do not parse. 2 424 of the 2 426
matched pairs are usable.

## Reporting

D1 to D5 are to be reported upstream. D1, D3 and D4 are implementation or specification gaps that
could be fixed without a breaking change. D2 is a design decision, and the report should present it
as a question about `Reference/keys` specifically, where the loss is semantic rather than
cosmetic.
