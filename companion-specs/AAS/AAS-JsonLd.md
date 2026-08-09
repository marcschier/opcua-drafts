# Asset Administration Shell — JSON-LD Mapping

**Status — working draft.** This document specifies a JSON-LD mapping for the Asset Administration
Shell, as a fourth technical data format alongside the XML, JSON and RDF mappings of IDTA-01001
Part 1. It is not published by, endorsed by, or submitted to the Industrial Digital Twin Association.

**Target:** IDTA-01001 Part 1, chapter *Mappings (normative)*.

| | |
|---|---|
| Version | 0.1.0, working draft |
| Metamodel | Asset Administration Shell V3.0 |
| Upstream baseline | `admin-shell-io/aas-specs-metamodel` tag `V3.0.7`, commit `21e68502e367` |
| Licence | Creative Commons Attribution 4.0 International, `SPDX-License-Identifier: CC-BY-4.0` |

All clauses whose heading carries the suffix *(normative)* are normative. All other clauses,
including every annex of this document, are informative.

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**, **SHOULD**, **SHOULD
NOT**, **RECOMMENDED**, **MAY** and **OPTIONAL** are to be interpreted as described in RFC 2119.

## Contents

- [Preamble](#preamble)
  - [Scope of this document](#scope-of-this-document)
  - [Structure of the document](#structure-of-the-document)
  - [Working principles](#working-principles)
- [Terms and definitions](#terms-and-definitions)
- [1 The canonical JSON-LD form (normative)](#1-the-canonical-json-ld-form-normative)
- [2 Lifting (normative)](#2-lifting-normative)
  - [2.1 Parameters](#21-parameters)
  - [2.2 Subject terms](#22-subject-terms)
  - [2.3 Class assignment](#23-class-assignment)
  - [2.4 Member resolution](#24-member-resolution)
  - [2.5 Values](#25-values)
  - [2.6 Enumerations](#26-enumerations)
- [3 The ordering graph (normative)](#3-the-ordering-graph-normative)
- [4 Lowering (normative)](#4-lowering-normative)
- [5 The JSON-LD context (normative)](#5-the-json-ld-context-normative)
- [5A Export (normative)](#5a-export-normative)
- [5B Authoring an AAS inside a Thing Description (normative)](#5b-authoring-an-aas-inside-a-thing-description-normative)
- [6 Conformance (normative)](#6-conformance-normative)
- [Annex A — Constraints](#annex-a--constraints)
- [Annex B — Deviations from the RDF mapping](#annex-b--deviations-from-the-rdf-mapping)
- [Annex C — Conformance results](#annex-c--conformance-results)
- [Annex D — Worked example](#annex-d--worked-example)
- [Bibliography](#bibliography)

## Preamble

### Scope of this document

This document defines **JSON-LD as a format an Asset Administration Shell is authored in**, and the
conversions that make an authored document usable everywhere an AAS is expected.

The goal is that an author writes an AAS as JSON-LD, using the vocabulary the OWL ontology of
IDTA-01001 Part 1 already publishes, and that the result is:

- **an AAS**, exportable as JSON, as XML and as an AASX package through a registry, without loss;
- **RDF**, so it can be queried, linked to other data and validated against the published SHACL
  schema; and
- **usable inside a W3C Thing Description**, so a WoT document carrying the AAS vocabulary
  materializes the AddressSpace the OPC UA AAS companion specification defines. Annex F of that
  document states that correspondence.

The canonical form is therefore a JSON-LD document whose shape follows the JSON mapping and whose
meaning follows the RDF mapping. The two already exist and already agree on the metamodel; what has
been missing is the document that lets one artefact be both.

It defines:

- a **canonical JSON-LD form**, which an author writes and a processor reads (clause 1);
- a **lifting**, which converts that form, or a plain AAS JSON document, to an RDF graph;
- an **ordering graph**, which carries the information the RDF mapping does not represent;
- a **lowering**, which converts an RDF graph back to an AAS JSON document, and so to XML and AASX
  through the existing serializations;
- a **JSON-LD context**, which is what makes the authored document JSON-LD in the first place;
- three **conformance claims**, which are independent of one another.

It does not define a new vocabulary. The class and property IRIs are those of the OWL ontology
published with IDTA-01001 Part 1, in the namespace `https://admin-shell.io/aas/3/0/`. Terms this
document adds, and only those, are in the namespace `https://w3id.org/aas-jsonld/`.

### Structure of the document

Clause 1 places the JSON-LD format among the existing formats. Clauses 2 to 4 define the conversion
in both directions. Clause 5 defines the context and states what it does not do. Clause 6 defines
conformance. The annexes list the constraints, record the deviations from the RDF mapping, report
the measured results, and give a worked example.

### Working principles

**The vocabulary is not restated.** The class hierarchy, the property IRIs, the datatype and object
ranges, and the enumeration members are read from the published ontology. A property IRI does not
appear in this document except in an example.

**The two directions are specified separately and tested separately.** Agreement with the RDF
mapping and preservation of the source document are different properties, and a document can have
one without the other.

## Terms and definitions

**lifting** — the conversion of an AAS JSON document into an RDF graph.

**lowering** — the conversion of an RDF graph into an AAS JSON document.

**core graph** — the RDF graph a lifting produces, containing only triples that the RDF mapping of
IDTA-01001 Part 1 also produces.

**ordering graph** — a separate named graph carrying the position of each member of each
array-valued member of the source document.

**enrichment graph** — the ordering graph together with any further graph a profile of this document
defines.

**root Identifiable** — an `AssetAdministrationShell`, `Submodel` or `ConceptDescription` that
appears in one of the three top-level collections of an `Environment`.

## 1 The canonical JSON-LD form (normative)

IDTA-01001 Part 1 defines the technical data formats XML, JSON and RDF. This document defines a
fourth, **JSON-LD**, whose media type is `application/ld+json`.

The canonical form takes its **shape** from the JSON mapping and its **meaning** from the RDF
mapping. An Asset Administration Shell in JSON-LD:

- **MUST** carry a `@context` member referencing the context of clause 5, either by its IRI or by
  value;
- **MUST** use the member names, nesting and `modelType` discriminator of the JSON mapping;
- **MUST NOT** rename, add, remove or reorder a member relative to that mapping.

A document meeting these rules is an AAS JSON document and a JSON-LD document at the same time. It
is therefore accepted unchanged by a JSON-mapping reader that ignores `@context` as an unknown
member, and by a JSON-LD processor.

An implementation **MAY** accept a plain AAS JSON document with no `@context` and apply the context
of clause 5 to it. Whether the `@context` is written in the document or supplied by the reader does
not change the graph.

The RDF graph a JSON-LD document denotes is the graph the lifting of clause 2 produces. A JSON-LD
processor applying the context alone produces part of that graph; clause 5 states which part it does
not produce, and clause 6 states which conformance unit requires which.

## 2 Lifting (normative)

### 2.1 Parameters

A lifting takes two parameters:

- the AAS JSON document; and
- a **base IRI**, which **MUST** be an absolute IRI.

An implementation **MUST** require the base IRI. It **MUST NOT** default it to the location the
document was retrieved from.

> The RDF mapping writes a subject term such as `<something_142922d6>`, which is a relative IRI
> reference, and the published examples declare no base. Two copies of one document retrieved from
> two locations then denote different subjects.

### 2.2 Subject terms

The subject term of a **root Identifiable** is derived from its `id`:

1. Where `id` is an absolute IRI containing at most one `#`, the subject term **MUST** be that IRI.
2. Otherwise, where `id` is a relative IRI reference, the subject term **MUST** be `id` resolved
   against the base IRI.
3. Otherwise, the subject term **MUST** be

   ```text
   https://w3id.org/aas-jsonld/id/<hex>
   ```

   where `<hex>` is the lower-case hexadecimal SHA-256 of the UTF-8 encoding of `id`.

Rule 3 covers an `id` that is not a legal IRI. An IRDI such as `0173-1#02-AAO677#002` is such an id:
its second `#` is not permitted in a fragment by RFC 3986, so it cannot be used as an IRI, and the
RDF mapping does not say what to do instead.

The construction of rule 3 is one way. An implementation **MUST NOT** recover an `id` by inverting
it, and **MUST** recover it by reading `aas:Identifiable/id`, which clause 2.4 requires in every
case.

The subject term of every node other than a root Identifiable **MUST** be a blank node.

### 2.3 Class assignment

Every node **MUST** carry exactly one `rdf:type`, naming its concrete class. An implementation
**MUST NOT** assert a superclass; a consumer obtains superclasses from the ontology.

The class of a node is determined as follows:

1. Where the JSON object carries `modelType`, the class **MUST** be the value of `modelType`.
2. Otherwise, the class **MUST** be the range of the property that reaches the object, as declared
   by the ontology.

Rule 2 covers `Reference`, `Key`, `Qualifier`, `AssetInformation`, `AdministrativeInformation`, the
language-string types, and every other class the JSON mapping does not discriminate.

Where rule 2 applies and the declared range is abstract, the document is invalid (`AASLD-002`).

### 2.4 Member resolution

For each member of a JSON object other than `modelType`, an implementation **MUST** determine the
property IRI by taking the class of the object and its superclasses, in order from the class
upwards, and selecting the first property whose name matches the member name.

Where no property matches, the document is invalid (`AASLD-001`).

The member `modelType` **MUST NOT** produce a triple of its own; it determines the class per
clause 2.3.

### 2.5 Values

Where the resolved property is an `owl:DatatypeProperty`, the object of the triple **MUST** be a
literal whose datatype IRI is the declared range.

Where the resolved property is an `owl:ObjectProperty` whose range is not an enumeration, the object
**MUST** be the subject term of the node produced by lifting the nested JSON object.

A JSON array **MUST** produce one triple per member, all with the same predicate. The order of the
members is not represented in the core graph; clause 3 defines how it is carried.

### 2.6 Enumerations

Where the resolved property is an `owl:ObjectProperty` whose range is an enumeration, the object
**MUST** be the individual of that enumeration whose local name corresponds to the JSON value.

The correspondence is by case-insensitive comparison of the JSON value, with any prefix up to and
including the first `:` removed, against the local name of each individual. The JSON value
`"xs:int"` therefore denotes `aas:DataTypeDefXsd/Int`.

Where no individual corresponds, the document is invalid (`AASLD-003`).

## 3 The ordering graph (normative)

The RDF mapping of IDTA-01001 Part 1 represents multiple values by repeating the property. RDF
imposes no order on the resulting triples, so the order of every JSON array is lost. This is
material for `Reference/keys`, where the key sequence is the reference path, for a
`SubmodelElementList` whose `orderRelevant` is true, and for a multi-language value.

An implementation producing an ordering graph **MUST** place it in the named graph

```text
https://w3id.org/aas-jsonld/graph/order
```

and **MUST NOT** place any triple of the core graph in it.

For each member of each array-valued member of the source document, the ordering graph **MUST**
contain one occurrence node with the following properties, in the namespace
`https://w3id.org/aas-jsonld/`:

| Property | Object |
|---|---|
| `rdf:type` | `aas-ld:Occurrence` |
| `aas-ld:subject` | the subject term of the object that carries the array |
| `aas-ld:property` | the property IRI the array produced |
| `aas-ld:member` | the object term of the triple this occurrence positions |
| `aas-ld:index` | the zero-based position, as `xsd:nonNegativeInteger` |

An implementation **MUST** record the position of every member of every array-valued member. It
**MUST NOT** record positions only for those members whose order the metamodel gives meaning to.

> Restricting the ordering graph to an enumerated set of properties leaves the remaining arrays
> restored by chance, and a multi-language value is among them.

The ordering graph **MUST NOT** use `rdf:List`. An `rdf:List` is not the shape the RDF mapping
produces, is not accepted by the SHACL schema published with IDTA-01001 Part 1, and turns a direct
SPARQL pattern into a traversal.

## 4 Lowering (normative)

A lowering takes a core graph and, optionally, an ordering graph.

An implementation **MUST** treat the core graph as a set. It **MUST NOT** derive the order of an
array from the order in which triples were received.

For each subject that carries `aas:Identifiable/id` and whose class is `AssetAdministrationShell`,
`Submodel` or `ConceptDescription`, the implementation **MUST** emit a JSON object in the
corresponding top-level collection.

For each node:

- the member name of a property **MUST** be the segment of the property IRI after the final `/`;
- a member **MUST** be an array where the JSON Schema published with IDTA-01001 Part 1 declares it
  an array, and a single value otherwise;
- `modelType` **MUST** be emitted where, and only where, that JSON Schema declares it;
- an enumeration individual **MUST** be emitted in its JSON spelling.

Where an ordering graph is present, the members of an array **MUST** be emitted in `aas-ld:index`
order. Where it is absent, the order of an array is implementation defined.

## 5 The JSON-LD context (normative)

The context published with this document at `aas.context.jsonld` **MUST** be used unchanged where a
JSON-LD processor interprets an AAS JSON document.

The context is a JSON-LD 1.1 context. It:

- aliases `modelType` to `@type`;
- defines one type-scoped context per discriminated class, which resolves each member name to the
  property IRI of clause 2.4;
- defines property-scoped contexts, which resolve the member names of a class the JSON mapping does
  not discriminate;
- defines the JSON spelling of every enumeration value whose spelling does not contain `:`, inside
  the scoped context of each property whose range is that enumeration.

An enumeration spelling is **not** defined at the top level of the context. Seventeen spellings are
also the names of discriminated classes - `Submodel` is a `KeyTypes` member and a class - and a
top-level definition of one silently replaces the other. `Instance` is a member of two
enumerations, so a single top-level definition could only mean one of them. Scoping each spelling to
the property that admits it removes both problems.

A JSON-LD processor applying the context alone does **not** produce the graph of clause 2. It does
not produce:

- the subject term of a root Identifiable, which remains a blank node, because a context maps a
  member either to `@id` or to a literal and `id` is required as both;
- the `rdf:type` of a node the JSON mapping does not discriminate, because supplying one requires
  redefining the `@type` keyword within a scoped context, which JSON-LD does not permit;
- the enumeration individual for a `DataTypeDefXsd` value, because a term containing `:` is read as
  a compact IRI which JSON-LD requires to expand to its own definition.

An implementation claiming a conformance unit of clause 6 **MUST** implement clauses 2 to 4. It
**MUST NOT** rely on the context alone.

Annex C reports how much of the core graph's predicates and non-blank objects the context produces.

## 5A Export (normative)

An authored JSON-LD document is exportable in every serialization IDTA-01001 Part 1 defines, without
loss and without a separate authoring step.

- **JSON.** Removing the `@context` member yields the AAS JSON document, because clause 1 requires
  the shape to be that of the JSON mapping. No other change is permitted.
- **XML.** The JSON document is converted by the XML mapping of IDTA-01001 Part 1, unchanged.
- **AASX.** The JSON or XML document is placed in a package by the mapping of IDTA-01005, unchanged.
- **RDF.** The lifting of clause 2 produces the graph; the ordering graph of clause 3 accompanies it.

Where a Server serves the document through a registry, the environment documents of clause 9.10 of
the OPC UA AAS companion specification are these same serializations, filtered to the caller.

An implementation **MUST NOT** require a round trip through RDF to export JSON, XML or AASX. The
authored document already is the JSON document.

## 5B Authoring an AAS inside a Thing Description (normative)

The vocabulary of clause 1 is usable inside a W3C Thing Description, so that one document describes
an asset both as a Thing and as an Asset Administration Shell.

A Thing Description carrying AAS content **MUST**:

- bind the `aas` prefix to `https://admin-shell.io/aas/3/0/` in its `@context`;
- carry the AAS content under members whose terms resolve to that namespace, per clause 5; and
- where the projected AddressSpace is to be the one the OPC UA AAS companion specification defines,
  follow Annex F of that document.

Annex F specifies the correspondence, including the `uav:typeref` binding that types a projected
node with an ObjectType the Server has already loaded. A Thing Description meeting it materializes
the nodes clause 5.6 of that specification defines, and the same document exports as JSON, XML and
AASX per clause 5A.

`examples/wot/` holds one such Thing Description per fixture of the conformance corpus.

## 6 Conformance (normative)

The three conformance units are independent. An implementation **MAY** claim any subset, and
**MUST NOT** present one as implying another.

| Unit | Requires |
|---|---|
| `AASLD-RdfCompatible` | For every AAS JSON document, the core graph of clause 2 is isomorphic to the graph the RDF mapping of IDTA-01001 Part 1 produces from the same document, given the same base IRI, **or** differs from it only by the `aas:Referable/idShort` triple of a root Identifiable. The allowance is necessary because the published examples do not agree with each other on that member; Annex B states it and Annex C reports the two cases separately. |
| `AASLD-JsonRoundTrip` | For every AAS JSON document, lifting per clause 2 with the ordering graph of clause 3 and lowering per clause 4 produces the source document. Members of the three top-level collections may be reordered; no other difference is permitted. |
| `AASLD-Linked` | The ordering graph of clause 3 is produced. |

`AASLD-JsonRoundTrip` **MUST NOT** be claimed by an implementation that does not produce the
ordering graph. Annex C reports the proportion of documents for which the core graph alone is
sufficient; it is not all of them.

## Annex A — Constraints

| Constraint | Statement |
|---|---|
| `AASLD-001` | A member of a JSON object, other than `modelType`, shall resolve to a property of the object's class or of one of its superclasses. |
| `AASLD-002` | A JSON object that carries no `modelType` shall be reached by a property whose declared range is a concrete class. |
| `AASLD-003` | The value of a member whose property range is an enumeration shall correspond to an individual of that enumeration. |
| `AASLD-004` | The base IRI shall be an absolute IRI. |
| `AASLD-005` | A subject term produced by the hash construction of clause 2.2 shall not be inverted to recover an identifier. |

## Annex B — Deviations from the RDF mapping

This annex is informative.

The lifting of clause 2 differs from the RDF mapping of IDTA-01001 Part 1 in two respects, both
deliberate.

**A base IRI is required.** The RDF mapping writes relative IRI references and its published
examples declare no base, so the subject a document denotes depends on where the document was
fetched from. Clause 2.1 requires the base as a parameter.

**An `id` that is not a legal IRI has a defined subject term.** The RDF mapping uses `id` verbatim
as the subject term. Applied to an IRDI this produces a term RFC 3986 does not permit and a Turtle
parser rejects. Clause 2.2 rule 3 defines a subject term for that case. No published example
exercises it.

**The root `idShort` allowance of clause 6.** For 2 361 of the 2 424 readable example pairs the
published JSON carries an `idShort` on the root `Identifiable` for which the published Turtle has no
`aas:Referable/idShort` triple. Clause 2.4 requires the triple, so the lifting emits it and the two
graphs differ by exactly that. `AASLD-RdfCompatible` therefore admits this one difference and
nothing else. Where the root carries no `idShort` — 41 of the pairs — no allowance is needed and the
graphs are isomorphic outright. The deviation is in the published examples rather than in the
mapping rules: the `idShortOverPattern` cases, where `idShort` is the subject of the test, do carry
the triple.

`UPSTREAM-DEFECTS.md`, beside this document, records these and the further defects found in the
upstream artefacts while this document was prepared, with the evidence for each.

## Annex C — Conformance results

This annex is informative. The figures are produced by `tools/jsonld/conformance.py` and
`tools/jsonld/make_context.py` over the 2 426 matched JSON and Turtle example pairs published with the
pinned upstream release, of which 2 424 are readable.

**`AASLD-RdfCompatible`**

| | cases |
|---|---|
| isomorphic to the core graph of clause 2 | 41 of 2 424 (1.7%) |
| isomorphic once the root `idShort` allowance is applied | 2 361 |
| **conforming to the unit as clause 6 defines it** | **2 402 of 2 424 (99.1%)** |
| differing | 22 |

The 41 are the documents whose root carries no `idShort`, so the allowance is not needed. For the
other 2 361 the published Turtle omits a triple the published JSON requires, and the two agree only
once that triple is set aside. Annex B records this as a deviation.

The 22 are cases in which the published JSON and Turtle examples describe different instances; they
are recorded as an upstream defect and are not reconcilable by any lifting.

**`AASLD-JsonRoundTrip`**

| | cases |
|---|---|
| restored with the ordering graph | 2 424 of 2 424 (100%) |
| **structurally order-bearing, so not guaranteed by the core graph** | **308 of 2 424 (12.7%)** |
| restored from the core graph under every one of ten permutations | 2 117 |
| failed under at least one permutation | 307 |

A document carries an array of two or more members, or it does not. Where it does, the core graph
does not represent that array's order and no lowering can guarantee it; a particular permutation may
still come back right. The structural figure answers the question and does not sample. The
ten-permutation figure is reported beside it because the two agreeing to within one case is what
establishes that neither is an artefact of the sampling.

**The context of clause 5**

| | |
|---|---|
| predicate and object pairs of the core graph reproduced | 22 327 of 30 614 (72.9%) |
| documents whose graph is reproduced exactly | 0 of 2 424 |

| Cause | Cases affected |
|---|---|
| root subject is a blank node | 2 424 of 2 424 |
| enumeration value left as a compact IRI | 2 291 |
| node has no `rdf:type` | 1 385 |

The pairs are counted with the subject discarded and blank node objects excluded, because a blank
node cannot match by label. The figure is about predicates and their non-blank objects, not about
the graph as a whole.

## Annex D — Worked example

This annex is informative. The document is `jsonld/fixtures/example-irdi-identifier.json`; the graph is the
output of `tools/jsonld/lift.py` with base IRI `https://example.org/aas/`.

```json
{
  "submodels": [
    {
      "id": "0173-1#02-AAO677#002",
      "idShort": "Nameplate",
      "modelType": "Submodel",
      "submodelElements": [
        {
          "idShort": "MaxTemperature",
          "modelType": "Property",
          "valueType": "xs:decimal",
          "value": "85.0",
          "semanticId": {
            "type": "ExternalReference",
            "keys": [ { "type": "GlobalReference", "value": "0173-1#02-AAO677#002" } ]
          }
        }
      ]
    }
  ]
}
```

The `id` is an IRDI, so clause 2.2 rule 3 applies and the subject term is the hash construction. The
`id` itself remains available as a literal.

```turtle
@prefix aas:    <https://admin-shell.io/aas/3/0/> .
@prefix aas-ld: <https://w3id.org/aas-jsonld/> .
@prefix xs:     <http://www.w3.org/2001/XMLSchema#> .

<https://w3id.org/aas-jsonld/id/4a508ebd70e19917cd187073e2ff250e75d464260868f755e40ccb04d95948ca>
    a aas:Submodel ;
    aas:Identifiable/id      "0173-1#02-AAO677#002"^^xs:string ;
    aas:Referable/idShort    "Nameplate"^^xs:string ;
    aas:Submodel/submodelElements [
        a aas:Property ;
        aas:Referable/idShort     "MaxTemperature"^^xs:string ;
        aas:Property/valueType    aas:DataTypeDefXsd/Decimal ;
        aas:Property/value        "85.0"^^xs:string ;
        aas:HasSemantics/semanticId [
            a aas:Reference ;
            aas:Reference/type aas:ReferenceTypes/ExternalReference ;
            aas:Reference/keys [
                a aas:Key ;
                aas:Key/type  aas:KeyTypes/GlobalReference ;
                aas:Key/value "0173-1#02-AAO677#002"^^xs:string ] ] ] .
```

`valueType` is `"xs:decimal"` in JSON and the individual `aas:DataTypeDefXsd/Decimal` in RDF, per
clause 2.6. The `semanticId` keys carry their position in the ordering graph:

```turtle
# graph https://w3id.org/aas-jsonld/graph/order
[] a aas-ld:Occurrence ;
   aas-ld:subject  _:reference ;
   aas-ld:property aas:Reference/keys ;
   aas-ld:member   _:key ;
   aas-ld:index    "0"^^xs:nonNegativeInteger .
```

## Bibliography

- IDTA-01001-3-0, *Specification of the Asset Administration Shell — Part 1: Metamodel*, Industrial
  Digital Twin Association.
- `admin-shell-io/aas-specs-metamodel`, tag `V3.0.7`: `schemas/rdf/rdf-ontology.ttl`,
  `schemas/rdf/shacl-schema.ttl`, `schemas/json/aas.json`.
- W3C, *JSON-LD 1.1*, W3C Recommendation, 16 July 2020.
- W3C, *RDF 1.1 Concepts and Abstract Syntax*, W3C Recommendation, 25 February 2014.
- W3C, *XML Schema Part 2: Datatypes Second Edition*, W3C Recommendation, 28 October 2004.
- IETF, RFC 3986, *Uniform Resource Identifier (URI): Generic Syntax*.
- IETF, RFC 2119, *Key words for use in RFCs to Indicate Requirement Levels*.
