# The OPC 20020 template contract

Everything below was established by unpacking
`templates/OPC 20020 - UA Companion Specification Template v1.01.19.docx`. A `.docx` is a ZIP;
the parts that matter are `word/document.xml`, `word/styles.xml`, `word/numbering.xml`,
`word/settings.xml` and `docProps/custom.xml`.

`word-drafts/tools/opcdocx/contract.py` is the executable form of this document.

## Clause skeleton

The template ships these clauses in this order:

| # | Clause | Build treatment |
|---|---|---|
| 1 | Scope | generated; the template's closing "OPC Foundation" boilerplate is kept |
| 2 | Normative references | generated; the template's intro paragraph and NOTE are kept |
| 3 | Terms, abbreviated terms and conventions | 3.1–3.3 generated, **3.4 kept verbatim** |
| 4 | EDITING Guidelines | **deleted** — the template says to delete it before publication |
| 5 | General information to \<title\> and OPC UA | 5.1 generated, **5.2 kept verbatim** (5 figures) |
| 6 | Use cases | generated |
| 7 | \<title\> Information Model overview | generated |
| 8 | OPC UA ObjectTypes | generated from the NodeSet |
| 9 | OPC UA EventTypes | dropped when the model defines none |
| 10 | OPC UA VariableTypes | dropped when the model defines none |
| 11 | OPC UA DataTypes | generated from the NodeSet |
| 12 | OPC UA ReferenceTypes | dropped when the model defines none |
| 13 | Instances | dropped when the model declares none |
| 14 | Well-Known BrowseNames | dropped when there are none |
| 15 | Profiles and Conformance Units | generated |
| 16 | Namespaces | generated |
| Annex A | (normative) \<Title\> Namespace and mappings | **kept verbatim**, plus a generated node reference |

Deleting clause 4 shifts everything after it. That is fine: Word renumbers, and every
cross-reference is a field.

## Numbering

```text
Heading1        numPr numId=23              -> "1", "2", ...
Heading2..5     pStyle-linked, abstractNum 14 -> "1.1", "1.1.1", ...
ANNEXtitle      numPr numId=14 (abstractNum 16, upperLetter) -> "Annex A"
ANNEX-heading1  same sequence, level 1       -> "A.1"
```

**A heading must contain no literal clause number.** Word supplies it.

Captions carry a `SEQ` field:

```text
TABLE-title    "Table " + { SEQ Table \* ARABIC } + " – " + caption
FIGURE-title   "Figure " + { SEQ Figure \* ARABIC } + " – " + caption
```

Cross-references are `REF` fields: `{ REF _Clause_c7_11 \r \h }` for a clause number,
`{ REF _Tab_x \h }` for a table. The three tables of contents are `TOC` fields:

```text
{ TOC \o "1-3" \h \z \u }
{ TOC \t "FIGURE-title" \c \h }
{ TOC \t "TABLE-title" \c \h }
```

## Table grammars

### Type definition (template Table 2)

Column grid, in twentieths of a point: `1696, 1134, 2127, 1275, 1843, 851` (total 8926 —
the template's text width). Geometry: `tblW=8926 dxa`, `jc=center`, 12 pt grey outer borders,
6 pt grey inner, `tblLayout=fixed`, `tblLook=0000`. Cell text uses `TableText`.

```text
| Attribute        | Value (gridSpan 5)                                          |   <- bold, bottom double
| BrowseName       | 2:OpenUsdStageType                                          |
| IsAbstract       | False                                                       |
| References | NodeClass | BrowseName | DataType | TypeDefinition | Other       |   <- bold, top+bottom double
| Subtype of the 0:BaseObjectType defined in OPC 10000-5 … (gridSpan 6)          |
| 0:HasProperty | Variable | RootLayerIdentifier | 0:String | 0:PropertyType | M |
| Conformance Units (gridSpan 6)                                                 |   <- bold, bottom double
| OU-Stage (gridSpan 6)                                                          |   <- one row per unit
| OU-Integrity (gridSpan 6)                                                      |
```

The `Other` column uses the short forms of template Table 3: `M`, `O`, `MP`, `OP`, `RO`, `RW`,
`WO`, comma-separated.

The DataType column uses the array notation of clause 3.4.1.1:

| ValueRank | ArrayDimensions | Printed |
|---|---|---|
| −1 | — | `0:Int32` |
| 0 | — | `0:Int32{OneOrMoreDimensions}` |
| 1 | omitted or `{0}` | `0:Int32[]` |
| 2 | `{3,0}` | `0:Int32[3][]` |
| −2 | — | `0:Int32{Any}` |
| −3 | — | `0:Int32{ScalarOrOneDimension}` |

A BrowseName from another namespace carries its index prefix (`0:EngineeringUnits`); the
document's own namespace is printed without one.

### The other five

| Template table | Columns |
|---|---|
| Table 4 — additional References | SourceBrowsePath, Reference Type, Is Forward, TargetBrowsePath |
| Table 5 — additional subcomponents | BrowsePath, References, NodeClass, BrowseName, DataType, TypeDefinition, Others |
| Table 6 — Attribute values for child Nodes | BrowsePath, \<Attribute name\> Attribute |
| Tables 12–14 — Structures | Name, Type, Description (+ Optional **or** Allow Subtypes, never both) |
| Tables 31/33 — Enumeration / OptionSet items | Name, Value, Description |

## Styles

180 styles, about 90 of them custom. The ones a generator needs:

| Purpose | Style |
|---|---|
| Body text | `PARAGRAPH`, `PARAGRAPHCompressed`, `PARAGRAPHKWNP` |
| Headings | `Heading1`…`Heading5`, `ANNEXtitle`, `ANNEX-heading1`…`3`, `HEADINGNonumber` |
| Captions | `TABLE-title`, `FIGURE-title` |
| Figures | `FIGURE`, `Figure0`, `FIGURE-uncaptioned` |
| Table cells | `TableText`, `TableTextWithTabs`, `TableHead`, `TableNotes`, `TABLE-col-heading` |
| Terms | `TERM-number3`, `TERM`, `TERM-definition`, `TERM-note`, `TERM-example`, `TERM-source` |
| Code | `CODE`, `CODE-TableCell`, `MethodSignature` |
| Notes | `NOTE`, `EXAMPLE` |
| References | `ReferenceDocuments` |
| Spacing | `spacer` |
| Character | `VARIABLE` (identifiers), `Reference`, `SUBscript`, `SUPerscript` |

## Prohibitions

| Guideline | Rule |
|---|---|
| 1 | Figures **shall** be embedded PowerPoint/Excel/Visio objects. Inline Word drawing objects are forbidden, *including code blocks captioned as figures*. |
| 2 | Headings, table titles and figure titles: first letter capital, everything else lower case except proper nouns and type names. |
| 3 | No `HasSubtype` references in type-definition tables — they conflict with the ConformanceUnit references. |
| 4 | Compress embedded PowerPoint and Visio to keep the file small. |
| 5 | No links to `reference.opcfoundation.org`. Cite `OPC 10000-N` and list it in clause 2. **Exception:** Annex A, where the template itself mandates the NodeSet download URLs. |

## Embedded object markup

```xml
<w:p><w:pPr><w:pStyle w:val="FIGURE"/></w:pPr>
  <w:r><w:object w:dxaOrig="..." w:dyaOrig="...">
    <v:shape id="_x0000_i1025" type="#_x0000_t75" style="width:...pt;height:...pt" o:ole="">
      <v:imagedata r:id="rIdPreview" o:title=""/>
    </v:shape>
    <o:OLEObject Type="Embed" ProgID="PowerPoint.Show.12" ShapeID="_x0000_i1025"
                 DrawAspect="Content" ObjectID="_1900000001" r:id="rIdEmbed"/>
  </w:object></w:r>
</w:p>
```xml

The `v:shapetype id="_x0000_t75"` definition must appear once before the first `v:shape` that
references it. Parts: the preview under `word/media/*.png` (relationship type `image`) and the
presentation under `word/embeddings/*.pptx`.

**The embedding relationship type depends on the file, not on the ProgID:**

| Embedded file | Relationship type |
|---|---|
| `.pptx`, `.sldx`, `.xlsx`, `.docx`, `.vsdx` — an OPC package | `.../relationships/package` |
| `.bin`, `.vsd` — a compound file | `.../relationships/oleObject` |

Getting this wrong produces a document that opens correctly and loses every embedded object the
next time Word saves it. `[Content_Types].xml` also needs an override for the part, e.g.
`application/vnd.openxmlformats-officedocument.presentationml.presentation`.

## Document properties

`docProps/custom.xml` drives the cover and both headers through `DOCPROPERTY` fields:

```text
Version  Published  OPCVersion  OPCReleaseType  Part Name  Part Number
HeaderLeft  DocNumber  HeaderRight  TemplateVersion  "Date completed"
```

## Regions kept verbatim

| Region | Why |
|---|---|
| Cover, template revision table, legal front matter, revision highlights | Mandatory boilerplate; only tokens are substituted. |
| Clause 3.4 *Conventions used in this document* (Tables 1–14) | Defines the table grammar the rest of the document obeys. Its `<some>Type` examples are the template's own and stay. |
| Clause *Introduction to OPC Unified Architecture* | Carries the five standard OPC UA figures as OLE objects. |
| Annex A skeleton | The NodeSet and supplementary-file URLs, and the capability identifier. |
| Back matter | The closing rule. |

Placeholder tokens substituted inside them: `<title>`, `<Title>`, `<short name>`,
`<other organization>`, `<OPC Foundation (if joint work)>`, `<Part Name>`, `Part <mm>`,
`<NamespaceUri>`, `<Version>`, `Draft 1.xy`.
