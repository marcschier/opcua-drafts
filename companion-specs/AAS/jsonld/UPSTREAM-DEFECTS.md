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

## D1 — The JSON and RDF example generators emit different instances

**Severity: high for anyone using the corpus as an oracle. Not a defect in the RDF *serialization
rules*, which was my first reading of it, but in the *example corpus*.**

The two halves of a matched pair are meant to describe one instance. Mostly they do not.

In 2 361 of 2 424 readable pairs the JSON root `Identifiable` carries an `idShort` for which the
Turtle has no `aas:Referable/idShort` triple. Lifting those pairs and comparing as RDF graphs shows
the root `idShort` is the **only** difference: suppress it and the graphs are isomorphic.

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

It is **not** a rule that the root `idShort` is dropped. In the `idShortOverPatternExamples` cases,
where `idShort` is the subject of the test, the Turtle does carry it. The pattern is consistent with
the two generators populating optional fields differently rather than with a serialization rule, and
D7 below shows the divergence is not confined to `idShort`.

**Consequence.** The corpus is usable as an oracle once this deviation is declared. The lifting
defined here emits the triple; `tools/conformance.py` retries a failing case without it and counts
the case as conforming when that alone reconciles the two.

## D7 — The generators diverge on more than `idShort`

**Severity: medium. 22 of 2 424 pairs.**

In `Operation/idShortOverPatternExamples/*` the nested `Entity` differs in substance, not only in an
optional label:

| | JSON | Turtle |
|---|---|---|
| `entityType` | `SelfManagedEntity` | `SelfManagedEntity` |
| `idShort` | `something_c8b0a9a0` | absent |
| `globalAssetId` | absent | `urn:an-example03:cc3a7d47` |

These are different instances, so no lifting can reconcile them and none should try. They are
excluded from the oracle and reported upstream.

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

**Measured cost.** 175 of 2 424 corpus documents (7.2%) cannot be restored from the core graph and
are restored exactly once the ordering graph is present. See the result table below.

The loss is not confined to the cases one would guess. Every array-valued property is affected,
including multi-language values, whose array order the metamodel's own JSON serialization preserves.
The lifting therefore records the position of every member of every array rather than of an
enumerated list of properties, and which properties those are is read from the pinned JSON Schema.

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

## What a JSON-LD context can and cannot do

The plan originally proposed shipping a `@context` you drop into an unmodified AAS JSON file. That
is impossible, and `tools/make_context.py` measures how impossible with a real JSON-LD 1.1 processor
rather than arguing it. The generated `aas.context.jsonld` uses every relevant JSON-LD 1.1 facility —
`modelType` aliased to `@type`, type-scoped contexts to disambiguate keys that recur across classes
with different property IRIs, property-scoped contexts to reach objects that carry no discriminator —
and still reaches only part of the graph.

Over 200 corpus documents, against the lifting:

| | |
|---|---|
| predicate/object pairs reproduced | **4 575 of 7 366 (62.1%)** |
| documents whose graph matches exactly | **0** |

Three causes, each measured, each a clause the lifting has to carry:

| Cause | Cases affected |
|---|---|
| root subject is a blank node, not an IRI | 198 of 198 |
| nested object has no `rdf:type` | 194 |
| enumeration value left as a compact IRI | 145 |

**The root subject.** The normative RDF uses an `Identifiable`'s `id` twice, as the subject IRI and
as an `aas:Identifiable/id` literal. A context maps a key to one or the other, never both, so
mapping `id` to the literal leaves every root a blank node.

**The nested type.** `Reference`, `Key`, `Qualifier`, `AssetInformation` and the language-string
types carry `rdf:type` in the normative RDF but have no `modelType` in the JSON for a context to
alias. Injecting one would mean redefining the `@type` keyword inside a scoped context, which JSON-LD
forbids outright: a processor rejects the context with *"keywords cannot be overridden"*.

**The enumeration spelling.** `DataTypeDefXsd` is written `xs:int` in JSON and is the individual
`aas:DataTypeDefXsd/Int` in RDF. A term containing a colon is read as a compact IRI, and JSON-LD
requires it to expand to its own definition, so aliasing it is rejected with *"term in form of IRI
must expand to definition"*. All 30 `DataTypeDefXsd` values are affected; the other ten
enumerations, whose spellings carry no colon, alias correctly.

The context is therefore published as a convenience layer for JSON-LD-native consumers, and the
lifting is the conformance mechanism.

## Result

Running `tools/conformance.py` over the pinned corpus.

**`AASLD-RdfCompatible`** — the lifted graph against the upstream Turtle, by graph isomorphism:

| | cases |
|---|---|
| isomorphic outright | 41 |
| isomorphic once the root `idShort` is accounted for (D1) | 2 361 |
| **conforming** | **2 402 of 2 424 (99.1%)** |
| differing — generator divergence (D7) | 22 |
| unreadable (D6) | 2 |

**`AASLD-JsonRoundTrip`** — lift, then lower, and compare against the source document. The triples
are shuffled before lowering, because RDF is a set and a consumer gets no order guarantee; without
shuffling the measurement records the serializer's sort order rather than the graph's content.

| | cases |
|---|---|
| restored **with** the ordering graph | **2 424 of 2 424 (100%)** |
| restored from the **core graph alone** | 2 249 of 2 424 (92.8%) |
| restored **only** with the ordering graph | **175 (7.2%)** |

Those 175 documents are what defect D2 costs. They are not exotic: they are ordinary documents with
a multi-key `Reference`, an ordered `SubmodelElementList`, or a multi-language value with more than
one entry. The normative RDF serialization cannot express them faithfully, and the enrichment graph
recovers every one.

This is the measurement the specification rests on. It is also the answer to the question of whether
the existing RDF serialization plus a framing tool would have been enough: for 92.8% of documents it
would, and for the rest it would silently return a different document from the one that went in.

## Reporting

D1 to D7 are to be reported upstream. D1, D3, D4, D6 and D7 are implementation or specification gaps
that could be fixed without a breaking change. D2 is a design decision, and the report should
present it as a question about `Reference/keys` specifically, where the loss is semantic rather than
cosmetic, and should carry the 175-document measurement rather than an argument.
