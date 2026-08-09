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
- [1 Technical data format JSON-LD (normative)](#1-technical-data-format-json-ld-normative)
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
- [6 Conformance (normative)](#6-conformance-normative)
- [Annex A — Constraints](#annex-a--constraints)
- [Annex B — Deviations from the RDF mapping](#annex-b--deviations-from-the-rdf-mapping)
- [Annex C — Conformance results](#annex-c--conformance-results)
- [Annex D — Worked example](#annex-d--worked-example)
- [Bibliography](#bibliography)

## Preamble

### Scope of this document

This document defines how an Asset Administration Shell expressed in the JSON mapping of
IDTA-01001 Part 1 is represented as RDF through JSON-LD, and how such a representation is converted
back.

It defines:

- a **lifting**, which converts an AAS JSON document to an RDF graph;
- an **ordering graph**, which carries the information the RDF mapping does not represent;
- a **lowering**, which converts an RDF graph back to an AAS JSON document;
- a **JSON-LD context**, which allows a JSON-LD processor to interpret an AAS JSON document
  directly, within the limits clause 5 states;
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

## 1 Technical data format JSON-LD (normative)

IDTA-01001 Part 1 defines the technical data formats XML, JSON and RDF. This document defines a
fourth, **JSON-LD**, whose media type is `application/ld+json`.

A JSON-LD representation of an Asset Administration Shell **MUST** be an AAS JSON document as
defined by the JSON mapping, unchanged, to which a `@context` member has been added.

A conforming implementation **MUST NOT** require any other change to the JSON document. In
particular it **MUST NOT** require a member to be renamed, added, removed or reordered.

The RDF graph a JSON-LD representation denotes is the graph the lifting of clause 2 produces. A
JSON-LD processor applying the context of clause 5 produces a subset of that graph; clause 5 states
which part.

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
- defines the JSON spelling of every enumeration value whose spelling does not contain `:`.

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

Annex C reports how much of the graph the context produces.

## 6 Conformance (normative)

The three conformance units are independent. An implementation **MAY** claim any subset, and
**MUST NOT** present one as implying another.

| Unit | Requires |
|---|---|
| `AASLD-RdfCompatible` | For every AAS JSON document, the core graph of clause 2 is isomorphic to the graph the RDF mapping of IDTA-01001 Part 1 produces from the same document, given the same base IRI. |
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

`UPSTREAM-DEFECTS.md`, beside this document, records these and the further defects found in the
upstream artefacts while this document was prepared, with the evidence for each.

## Annex C — Conformance results

This annex is informative. The figures are produced by `tools/conformance.py` and
`tools/make_context.py` over the 2 426 matched JSON and Turtle example pairs published with the
pinned upstream release, of which 2 424 are readable.

**`AASLD-RdfCompatible`**

| | cases |
|---|---|
| isomorphic to the published Turtle | 2 402 of 2 424 (99.1%) |
| differing | 22 |

The 22 are cases in which the published JSON and Turtle examples describe different instances; they
are recorded as an upstream defect and are not reconcilable by any lifting.

**`AASLD-JsonRoundTrip`**

| | cases |
|---|---|
| restored with the ordering graph | 2 424 of 2 424 (100%) |
| restored from the core graph alone | 2 249 of 2 424 (92.8%) |
| restored only with the ordering graph | 175 (7.2%) |

The triples are shuffled before lowering, so the figures measure the graph rather than a
serializer's output order.

**The context of clause 5**

| | |
|---|---|
| predicate and object pairs of the core graph reproduced | 4 575 of 7 366 (62.1%) |
| documents whose graph is reproduced exactly | 0 |

| Cause | Cases affected |
|---|---|
| root subject is a blank node | 198 of 198 |
| node has no `rdf:type` | 194 |
| enumeration value left as a compact IRI | 145 |

## Annex D — Worked example

This annex is informative. The document is `fixtures/example-irdi-identifier.json`; the graph is the
output of `tools/lift.py` with base IRI `https://example.org/aas/`.

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
