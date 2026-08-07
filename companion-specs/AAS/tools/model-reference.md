<a id="annex-a"></a>

## Annex A — Information model

This annex is the normative node reference. It is generated from `tools/build_model.py` and always matches `Opc.Ua.I4AAS.NodeSet2.xml`. All nodes are defined in the companion namespace `http://opcfoundation.org/UA/xRegistry/` (which requires the base OPC UA namespace); the numeric NodeIds shown are **draft** identifiers within that namespace. The **Declared in** column marks members inherited from a supertype.

### Type overview

| NodeId | BrowseName | NodeClass | Subtype of |
|---|---|---|---|
| ns=1;i=1001 | [AASReferableType](#type-AASReferableType) | ObjectType | [BaseObjectType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.2) |
| ns=1;i=1002 | [AASIdentifiableType](#type-AASIdentifiableType) | ObjectType | [AASReferableType](#type-AASReferableType) |
| ns=1;i=1003 | [AASHasSemanticsType](#type-AASHasSemanticsType) | ObjectType | [BaseObjectType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.2) |
| ns=1;i=1004 | [AASHasKindType](#type-AASHasKindType) | ObjectType | [BaseObjectType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.2) |
| ns=1;i=1005 | [AASHasDataSpecificationType](#type-AASHasDataSpecificationType) | ObjectType | [BaseObjectType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.2) |
| ns=1;i=1006 | [AASQualifiableType](#type-AASQualifiableType) | ObjectType | [BaseObjectType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.2) |
| ns=1;i=1010 | [AASEnvironmentType](#type-AASEnvironmentType) | ObjectType | [FolderType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.6) |
| ns=1;i=1011 | [AASType](#type-AASType) | ObjectType | [AASIdentifiableType](#type-AASIdentifiableType) |
| ns=1;i=1012 | [AASAssetInformationType](#type-AASAssetInformationType) | ObjectType | [BaseObjectType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.2) |
| ns=1;i=1013 | [AASSubmodelType](#type-AASSubmodelType) | ObjectType | [AASIdentifiableType](#type-AASIdentifiableType) |
| ns=1;i=1030 | [AASConceptDescriptionType](#type-AASConceptDescriptionType) | ObjectType | [AASIdentifiableType](#type-AASIdentifiableType) |
| ns=1;i=1020 | [AASSubmodelElementType](#type-AASSubmodelElementType) | ObjectType | [AASReferableType](#type-AASReferableType) |
| ns=1;i=1021 | [AASPropertyType](#type-AASPropertyType) | ObjectType | [AASSubmodelElementType](#type-AASSubmodelElementType) |
| ns=1;i=1022 | [AASMultiLanguagePropertyType](#type-AASMultiLanguagePropertyType) | ObjectType | [AASSubmodelElementType](#type-AASSubmodelElementType) |
| ns=1;i=1023 | [AASRangeType](#type-AASRangeType) | ObjectType | [AASSubmodelElementType](#type-AASSubmodelElementType) |
| ns=1;i=1024 | [AASBlobType](#type-AASBlobType) | ObjectType | [AASSubmodelElementType](#type-AASSubmodelElementType) |
| ns=1;i=1025 | [AASFileType](#type-AASFileType) | ObjectType | [AASSubmodelElementType](#type-AASSubmodelElementType) |
| ns=1;i=1026 | [AASReferenceElementType](#type-AASReferenceElementType) | ObjectType | [AASSubmodelElementType](#type-AASSubmodelElementType) |
| ns=1;i=1027 | [AASRelationshipElementType](#type-AASRelationshipElementType) | ObjectType | [AASSubmodelElementType](#type-AASSubmodelElementType) |
| ns=1;i=1028 | [AASAnnotatedRelationshipElementType](#type-AASAnnotatedRelationshipElementType) | ObjectType | [AASRelationshipElementType](#type-AASRelationshipElementType) |
| ns=1;i=1029 | [AASSubmodelElementCollectionType](#type-AASSubmodelElementCollectionType) | ObjectType | [AASSubmodelElementType](#type-AASSubmodelElementType) |
| ns=1;i=1031 | [AASSubmodelElementListType](#type-AASSubmodelElementListType) | ObjectType | [AASSubmodelElementType](#type-AASSubmodelElementType) |
| ns=1;i=1032 | [AASEntityType](#type-AASEntityType) | ObjectType | [AASSubmodelElementType](#type-AASSubmodelElementType) |
| ns=1;i=1033 | [AASBasicEventElementType](#type-AASBasicEventElementType) | ObjectType | [AASSubmodelElementType](#type-AASSubmodelElementType) |
| ns=1;i=1034 | [AASOperationType](#type-AASOperationType) | ObjectType | [AASSubmodelElementType](#type-AASSubmodelElementType) |
| ns=1;i=1035 | [AASCapabilityType](#type-AASCapabilityType) | ObjectType | [AASSubmodelElementType](#type-AASSubmodelElementType) |
| ns=1;i=1100 | [AASRegistryType](#type-AASRegistryType) | ObjectType | ns=1;i=63000 |
| ns=1;i=1101 | [AASShellGroupType](#type-AASShellGroupType) | ObjectType | ns=1;i=63001 |
| ns=1;i=1102 | [AASSubmodelFileType](#type-AASSubmodelFileType) | ObjectType | ns=1;i=63002 |
| ns=1;i=1103 | [AASSubmodelTemplateGroupType](#type-AASSubmodelTemplateGroupType) | ObjectType | ns=1;i=63001 |
| ns=1;i=1104 | [AASConceptDictionaryGroupType](#type-AASConceptDictionaryGroupType) | ObjectType | ns=1;i=63001 |
| ns=1;i=1105 | [AASConceptDescriptionFileType](#type-AASConceptDescriptionFileType) | ObjectType | ns=1;i=63002 |
| ns=1;i=1106 | [AASPackageStoreGroupType](#type-AASPackageStoreGroupType) | ObjectType | ns=1;i=63001 |
| ns=1;i=1107 | [AASPackageFileType](#type-AASPackageFileType) | ObjectType | ns=1;i=63002 |
| ns=1;i=1199 | [AASValueString](#type-AASValueString) | DataType | String |
| ns=1;i=1200 | [AASAssetKindDataType](#type-AASAssetKindDataType) | DataType | Enumeration |
| ns=1;i=1201 | [AASModellingKindDataType](#type-AASModellingKindDataType) | DataType | Enumeration |
| ns=1;i=1202 | [AASEntityTypeDataType](#type-AASEntityTypeDataType) | DataType | Enumeration |
| ns=1;i=1203 | [AASDirectionDataType](#type-AASDirectionDataType) | DataType | Enumeration |
| ns=1;i=1204 | [AASStateOfEventDataType](#type-AASStateOfEventDataType) | DataType | Enumeration |
| ns=1;i=1205 | [AASQualifierKindDataType](#type-AASQualifierKindDataType) | DataType | Enumeration |
| ns=1;i=1206 | [AASReferenceTypesDataType](#type-AASReferenceTypesDataType) | DataType | Enumeration |
| ns=1;i=1207 | [AASKeyTypesDataType](#type-AASKeyTypesDataType) | DataType | Enumeration |
| ns=1;i=1208 | [AASDataTypeDefXsdDataType](#type-AASDataTypeDefXsdDataType) | DataType | Enumeration |
| ns=1;i=1209 | [AASDataTypeIec61360DataType](#type-AASDataTypeIec61360DataType) | DataType | Enumeration |
| ns=1;i=1210 | [AASSubmodelElementsDataType](#type-AASSubmodelElementsDataType) | DataType | Enumeration |
| ns=1;i=1211 | [AASDisclosureTierDataType](#type-AASDisclosureTierDataType) | DataType | Enumeration |
| ns=1;i=1220 | [AASKeyDataType](#type-AASKeyDataType) | DataType | [Structure](https://reference.opcfoundation.org/specs/OPC-10000-5/8.24) |
| ns=1;i=1221 | [AASReferenceDataType](#type-AASReferenceDataType) | DataType | [Structure](https://reference.opcfoundation.org/specs/OPC-10000-5/8.24) |
| ns=1;i=1222 | [AASLangStringDataType](#type-AASLangStringDataType) | DataType | [Structure](https://reference.opcfoundation.org/specs/OPC-10000-5/8.24) |
| ns=1;i=1223 | [AASSpecificAssetIdDataType](#type-AASSpecificAssetIdDataType) | DataType | [Structure](https://reference.opcfoundation.org/specs/OPC-10000-5/8.24) |
| ns=1;i=1224 | [AASAdministrativeInformationDataType](#type-AASAdministrativeInformationDataType) | DataType | [Structure](https://reference.opcfoundation.org/specs/OPC-10000-5/8.24) |
| ns=1;i=1225 | [AASQualifierDataType](#type-AASQualifierDataType) | DataType | [Structure](https://reference.opcfoundation.org/specs/OPC-10000-5/8.24) |
| ns=1;i=1226 | [AASEmbeddedDataSpecificationDataType](#type-AASEmbeddedDataSpecificationDataType) | DataType | [Structure](https://reference.opcfoundation.org/specs/OPC-10000-5/8.24) |
| ns=1;i=1227 | [AASDataSpecificationIec61360DataType](#type-AASDataSpecificationIec61360DataType) | DataType | [Structure](https://reference.opcfoundation.org/specs/OPC-10000-5/8.24) |
| ns=1;i=1228 | [AASExtensionDataType](#type-AASExtensionDataType) | DataType | [Structure](https://reference.opcfoundation.org/specs/OPC-10000-5/8.24) |
| ns=1;i=1229 | [AASResourceDataType](#type-AASResourceDataType) | DataType | [Structure](https://reference.opcfoundation.org/specs/OPC-10000-5/8.24) |
| ns=1;i=1230 | [AASOperationVariableDataType](#type-AASOperationVariableDataType) | DataType | [Structure](https://reference.opcfoundation.org/specs/OPC-10000-5/8.24) |
| ns=1;i=1231 | [AASAuthorizationOptionDataType](#type-AASAuthorizationOptionDataType) | DataType | [Structure](https://reference.opcfoundation.org/specs/OPC-10000-5/8.24) |
| ns=1;i=1232 | [AASAttestationDataType](#type-AASAttestationDataType) | DataType | [Structure](https://reference.opcfoundation.org/specs/OPC-10000-5/8.24) |

### Object types

<a id="type-AASReferableType"></a>

#### AASReferableType  (ns=1;i=1001)

*Inherits from:* [BaseObjectType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.2)

Abstract base of everything in the metamodel that can be referred to by a short name. Carries the identifying and descriptive attributes every element has.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| IdShort | Variable | String | Optional | AASReferableType | The short name, unique only within its parent. It is never an identifier: two elements from different publishers routinely share one. Absent for an element inside a SubmodelElementList, which is addressed by index instead. |
| Category | Variable | String | Optional | AASReferableType | Deprecated in the metamodel and retained only so that a document carrying it round-trips unchanged. |
| DisplayNameSet | Variable | [AASLangStringDataType](#type-AASLangStringDataType)\[\] | Optional | AASReferableType | Display name per language. |
| DescriptionSet | Variable | [AASLangStringDataType](#type-AASLangStringDataType)\[\] | Optional | AASReferableType | Description per language. |
| Extensions | Variable | [AASExtensionDataType](#type-AASExtensionDataType)\[\] | Optional | AASReferableType | Proprietary extensions, preserved verbatim. |
| ModelType | Variable | String | Mandatory | AASReferableType | The metamodel class name of this element. It is redundant with the ObjectType and is carried so that a serialization produced from the AddressSpace is byte-identical to the one that produced it. |

<a id="type-AASIdentifiableType"></a>

#### AASIdentifiableType  (ns=1;i=1002)

*Inherits from:* [AASReferableType](#type-AASReferableType)

Abstract base of the metamodel elements that carry a globally unique identifier: shells, submodels and concept descriptions.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| Id | Variable | String | Mandatory | AASIdentifiableType | The globally unique identifier, up to 2048 characters. It is arbitrary text and can never be a BrowseName, so it is carried here and the node is named by the derived identifier instead. |
| Administration | Variable | [AASAdministrativeInformationDataType](#type-AASAdministrativeInformationDataType) | Optional | AASIdentifiableType | Administrative information: a single current revision, with no history. |

<a id="type-AASHasSemanticsType"></a>

#### AASHasSemanticsType  (ns=1;i=1003)

*Inherits from:* [BaseObjectType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.2)

Abstract base of the elements that declare what concept they are an occurrence of.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| SemanticId | Variable | [AASReferenceDataType](#type-AASReferenceDataType) | Optional | AASHasSemanticsType | The concept this element is an occurrence of. It is what makes an element discoverable by meaning rather than by name. |
| SupplementalSemanticIds | Variable | [AASReferenceDataType](#type-AASReferenceDataType)\[\] | Optional | AASHasSemanticsType | Further concepts this element corresponds to, which is how one element is made discoverable through more than one dictionary. |

<a id="type-AASHasKindType"></a>

#### AASHasKindType  (ns=1;i=1004)

*Inherits from:* [BaseObjectType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.2)

Abstract base of the elements that distinguish a template from an instance.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| Kind | Variable | [AASModellingKindDataType](#type-AASModellingKindDataType) | Optional | AASHasKindType | Whether this element defines a shape or carries values. |

<a id="type-AASHasDataSpecificationType"></a>

#### AASHasDataSpecificationType  (ns=1;i=1005)

*Inherits from:* [BaseObjectType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.2)

Abstract base of the elements that carry data specifications.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| EmbeddedDataSpecifications | Variable | [AASEmbeddedDataSpecificationDataType](#type-AASEmbeddedDataSpecificationDataType)\[\] | Optional | AASHasDataSpecificationType | Data specifications carried by this element. |

<a id="type-AASQualifiableType"></a>

#### AASQualifiableType  (ns=1;i=1006)

*Inherits from:* [BaseObjectType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.2)

Abstract base of the elements that can be qualified.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| Qualifiers | Variable | [AASQualifierDataType](#type-AASQualifierDataType)\[\] | Optional | AASQualifiableType | Qualifiers constraining or annotating this element. |

<a id="type-AASEnvironmentType"></a>

#### AASEnvironmentType  (ns=1;i=1010)

*Inherits from:* [FolderType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.6)

The container of shells, submodels and concept descriptions - the unit an AAS serialization carries and the root a source generator materializes into a Server.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| <AssetAdministrationShell> | Object |  | OptionalPlaceholder | AASEnvironmentType | A shell held by this environment. |
| <Submodel> | Object |  | OptionalPlaceholder | AASEnvironmentType | A submodel held by this environment. Submodels are top-level: one submodel may be referenced by several shells, which is why they are not nested inside them. |
| <ConceptDescription> | Object |  | OptionalPlaceholder | AASEnvironmentType | A concept description held by this environment. |

<a id="type-AASType"></a>

#### AASType  (ns=1;i=1011)

*Inherits from:* [AASIdentifiableType](#type-AASIdentifiableType)

An Asset Administration Shell: the digital representation of one asset, carrying the asset's identity and references to the submodels that describe it.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| AssetInformation | Object |  | Mandatory | AASType | The identity of the asset this shell represents. |
| SubmodelReferences | Variable | [AASReferenceDataType](#type-AASReferenceDataType)\[\] | Optional | AASType | References to the submodels describing this asset. A submodel is not owned by the shell that references it. |
| DerivedFrom | Variable | [AASReferenceDataType](#type-AASReferenceDataType) | Optional | AASType | The Type shell this Instance shell was derived from, so an individual item can be traced to its product model. |
| EmbeddedDataSpecifications | Variable | [AASEmbeddedDataSpecificationDataType](#type-AASEmbeddedDataSpecificationDataType)\[\] | Optional | AASType | Data specifications carried by this shell. |

<a id="type-AASAssetInformationType"></a>

#### AASAssetInformationType  (ns=1;i=1012)

*Inherits from:* [BaseObjectType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.2)

The identity of the asset a shell represents, as distinct from the identity of the shell itself.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| AssetKind | Variable | [AASAssetKindDataType](#type-AASAssetKindDataType) | Mandatory | AASAssetInformationType | Whether the asset is a product model, an individual item, a batch, a role, or none of these. |
| GlobalAssetId | Variable | String | Optional | AASAssetInformationType | The globally unique identifier of the asset itself. Where the asset carries an identification link, that link is this value, and it is what connects a code scanned from a physical product to this Server. |
| AssetType | Variable | String | Optional | AASAssetInformationType | The identifier of the asset type this asset is an occurrence of. |
| SpecificAssetIds | Variable | [AASSpecificAssetIdDataType](#type-AASSpecificAssetIdDataType)\[\] | Optional | AASAssetInformationType | The additional keys the asset is discoverable by. |
| DefaultThumbnail | Variable | [AASResourceDataType](#type-AASResourceDataType) | Optional | AASAssetInformationType | A pointer to a representative image of the asset. |

<a id="type-AASSubmodelType"></a>

#### AASSubmodelType  (ns=1;i=1013)

*Inherits from:* [AASIdentifiableType](#type-AASIdentifiableType)

One coherent aspect of an asset, identified in its own right and typed by its SemanticId: a nameplate, technical data, a carbon footprint, a bill of material.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| Kind | Variable | [AASModellingKindDataType](#type-AASModellingKindDataType) | Optional | AASSubmodelType | Whether this submodel carries values or defines a shape other submodels are built from. |
| SemanticId | Variable | [AASReferenceDataType](#type-AASReferenceDataType) | Optional | AASSubmodelType | The concept this submodel is an occurrence of. |
| SupplementalSemanticIds | Variable | [AASReferenceDataType](#type-AASReferenceDataType)\[\] | Optional | AASSubmodelType | Further concepts this submodel corresponds to. |
| Qualifiers | Variable | [AASQualifierDataType](#type-AASQualifierDataType)\[\] | Optional | AASSubmodelType | Qualifiers on this submodel. |
| EmbeddedDataSpecifications | Variable | [AASEmbeddedDataSpecificationDataType](#type-AASEmbeddedDataSpecificationDataType)\[\] | Optional | AASSubmodelType | Data specifications carried by this submodel. |
| <SubmodelElement> | Object |  | OptionalPlaceholder | AASSubmodelType | An element of this submodel. |

<a id="type-AASConceptDescriptionType"></a>

#### AASConceptDescriptionType  (ns=1;i=1030)

*Inherits from:* [AASIdentifiableType](#type-AASIdentifiableType)

The definition a SemanticId resolves to - what makes two submodels from different vendors comparable.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| IsCaseOf | Variable | [AASReferenceDataType](#type-AASReferenceDataType)\[\] | Optional | AASConceptDescriptionType | Concepts in other dictionaries this concept corresponds to, which is how a Server bridges two classification systems without asserting that either is canonical. |
| EmbeddedDataSpecifications | Variable | [AASEmbeddedDataSpecificationDataType](#type-AASEmbeddedDataSpecificationDataType)\[\] | Optional | AASConceptDescriptionType | The data specifications defining this concept. |

<a id="type-AASSubmodelElementType"></a>

#### AASSubmodelElementType  (ns=1;i=1020)

*Inherits from:* [AASReferableType](#type-AASReferableType)

Abstract base of every element that can appear inside a submodel.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| SemanticId | Variable | [AASReferenceDataType](#type-AASReferenceDataType) | Optional | AASSubmodelElementType | The concept this element is an occurrence of. |
| SupplementalSemanticIds | Variable | [AASReferenceDataType](#type-AASReferenceDataType)\[\] | Optional | AASSubmodelElementType | Further concepts this element corresponds to. |
| Qualifiers | Variable | [AASQualifierDataType](#type-AASQualifierDataType)\[\] | Optional | AASSubmodelElementType | Qualifiers on this element. |
| EmbeddedDataSpecifications | Variable | [AASEmbeddedDataSpecificationDataType](#type-AASEmbeddedDataSpecificationDataType)\[\] | Optional | AASSubmodelElementType | Data specifications carried by this element. |
| Index | Variable | UInt32 | Optional | AASSubmodelElementType | The element's position within its parent SubmodelElementList. OPC UA References are unordered, so an ordered collection carries its order explicitly or loses it. Present only for an element inside a list. |

<a id="type-AASPropertyType"></a>

#### AASPropertyType  (ns=1;i=1021)

*Inherits from:* [AASSubmodelElementType](#type-AASSubmodelElementType)

A single typed value. The value is carried twice: as a typed Variable for the native projection a generic Client expects, and as its exact lexical form, because several xsd types have no faithful OPC UA equivalent.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| ValueType | Variable | [AASDataTypeDefXsdDataType](#type-AASDataTypeDefXsdDataType) | Mandatory | AASPropertyType | The xsd type the value is expressed in. |
| Value | Variable | i=24 | Optional | AASPropertyType | The value in its native OPC UA representation, for reading. Where the declared ValueType cannot be represented faithfully, this is the nearest representation and RawValue is authoritative. |
| RawValue | Variable | [AASValueString](#type-AASValueString) | Mandatory | AASPropertyType | The value in the exact xsd lexical form the metamodel carries. This is the normative carrier for round-tripping: where it and Value disagree, RawValue wins. |
| ValueId | Variable | [AASReferenceDataType](#type-AASReferenceDataType) | Optional | AASPropertyType | A reference to the value, where the value is itself an identified concept. |

<a id="type-AASMultiLanguagePropertyType"></a>

#### AASMultiLanguagePropertyType  (ns=1;i=1022)

*Inherits from:* [AASSubmodelElementType](#type-AASSubmodelElementType)

A value expressed in one or more languages. The array order is preserved, because the metamodel's serialization is ordered and a round trip that reordered it would not reproduce its input.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| Value | Variable | [AASLangStringDataType](#type-AASLangStringDataType)\[\] | Optional | AASMultiLanguagePropertyType | The language-tagged values, in order. |
| ValueId | Variable | [AASReferenceDataType](#type-AASReferenceDataType) | Optional | AASMultiLanguagePropertyType | A reference to the value, where the value is itself an identified concept. |

<a id="type-AASRangeType"></a>

#### AASRangeType  (ns=1;i=1023)

*Inherits from:* [AASSubmodelElementType](#type-AASSubmodelElementType)

A closed or half-open interval of a single typed value.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| ValueType | Variable | [AASDataTypeDefXsdDataType](#type-AASDataTypeDefXsdDataType) | Mandatory | AASRangeType | The xsd type the bounds are expressed in. |
| Min | Variable | [AASValueString](#type-AASValueString) | Optional | AASRangeType | The lower bound in its exact lexical form. Absent means unbounded below, which is different from a bound of zero. |
| Max | Variable | [AASValueString](#type-AASValueString) | Optional | AASRangeType | The upper bound in its exact lexical form. Absent means unbounded above. |

<a id="type-AASBlobType"></a>

#### AASBlobType  (ns=1;i=1024)

*Inherits from:* [AASSubmodelElementType](#type-AASSubmodelElementType)

Binary content carried inline.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| Value | Variable | ByteString | Optional | AASBlobType | The content bytes. |
| ContentType | Variable | String | Mandatory | AASBlobType | Media type of the content. |

<a id="type-AASFileType"></a>

#### AASFileType  (ns=1;i=1025)

*Inherits from:* [AASSubmodelElementType](#type-AASSubmodelElementType)

A pointer to content held outside the element.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| Value | Variable | String | Optional | AASFileType | Path or URL to the content. |
| ContentType | Variable | String | Mandatory | AASFileType | Media type of the content. |

<a id="type-AASReferenceElementType"></a>

#### AASReferenceElementType  (ns=1;i=1026)

*Inherits from:* [AASSubmodelElementType](#type-AASSubmodelElementType)

An element whose value is a reference.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| Value | Variable | [AASReferenceDataType](#type-AASReferenceDataType) | Optional | AASReferenceElementType | The reference. |

<a id="type-AASRelationshipElementType"></a>

#### AASRelationshipElementType  (ns=1;i=1027)

*Inherits from:* [AASSubmodelElementType](#type-AASSubmodelElementType)

A directed relationship between two referenced things.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| First | Variable | [AASReferenceDataType](#type-AASReferenceDataType) | Mandatory | AASRelationshipElementType | The first, or source, end of the relationship. |
| Second | Variable | [AASReferenceDataType](#type-AASReferenceDataType) | Mandatory | AASRelationshipElementType | The second, or target, end of the relationship. |

<a id="type-AASAnnotatedRelationshipElementType"></a>

#### AASAnnotatedRelationshipElementType  (ns=1;i=1028)

*Inherits from:* [AASRelationshipElementType](#type-AASRelationshipElementType)

A relationship carrying data elements that annotate it, such as a quantity or a position.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| <Annotation> | Object |  | OptionalPlaceholder | AASAnnotatedRelationshipElementType | A data element annotating this relationship. |

<a id="type-AASSubmodelElementCollectionType"></a>

#### AASSubmodelElementCollectionType  (ns=1;i=1029)

*Inherits from:* [AASSubmodelElementType](#type-AASSubmodelElementType)

An unordered set of elements, each identified by its own IdShort.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| <SubmodelElement> | Object |  | OptionalPlaceholder | AASSubmodelElementCollectionType | An element of this collection. |

<a id="type-AASSubmodelElementListType"></a>

#### AASSubmodelElementListType  (ns=1;i=1031)

*Inherits from:* [AASSubmodelElementType](#type-AASSubmodelElementType)

An ordered sequence of elements. Its members have no IdShort, so they are named by index and carry their position in Index; that is what lets the sequence be reconstructed from a Browse result.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| OrderRelevant | Variable | Boolean | Optional | AASSubmodelElementListType | Whether the order carries meaning. Order is preserved either way, because a round trip must reproduce its input whether or not the order is significant. |
| TypeValueListElement | Variable | [AASSubmodelElementsDataType](#type-AASSubmodelElementsDataType) | Mandatory | AASSubmodelElementListType | The element kind every member is constrained to. |
| SemanticIdListElement | Variable | [AASReferenceDataType](#type-AASReferenceDataType) | Optional | AASSubmodelElementListType | The concept every member is an occurrence of, where they share one. |
| ValueTypeListElement | Variable | [AASDataTypeDefXsdDataType](#type-AASDataTypeDefXsdDataType) | Optional | AASSubmodelElementListType | The xsd type every member's value is expressed in, where they share one. |

<a id="type-AASEntityType"></a>

#### AASEntityType  (ns=1;i=1032)

*Inherits from:* [AASSubmodelElementType](#type-AASSubmodelElementType)

A component of a composition. A self-managed entity carries the identifier of its own shell, which is what makes a bill of material traversable across organizations.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| EntityType | Variable | [AASEntityTypeDataType](#type-AASEntityTypeDataType) | Mandatory | AASEntityType | Whether the component has its own shell or is managed within its parent. |
| GlobalAssetId | Variable | String | Optional | AASEntityType | The identifier of the component's own asset, for a self-managed entity. |
| SpecificAssetIds | Variable | [AASSpecificAssetIdDataType](#type-AASSpecificAssetIdDataType)\[\] | Optional | AASEntityType | Additional keys the component is discoverable by. |
| <Statement> | Object |  | OptionalPlaceholder | AASEntityType | A statement about the component. |

<a id="type-AASBasicEventElementType"></a>

#### AASBasicEventElementType  (ns=1;i=1033)

*Inherits from:* [AASSubmodelElementType](#type-AASSubmodelElementType)

An event source or sink.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| Observed | Variable | [AASReferenceDataType](#type-AASReferenceDataType) | Mandatory | AASBasicEventElementType | What the event observes. |
| Direction | Variable | [AASDirectionDataType](#type-AASDirectionDataType) | Mandatory | AASBasicEventElementType | Whether the event is produced or consumed. |
| State | Variable | [AASStateOfEventDataType](#type-AASStateOfEventDataType) | Mandatory | AASBasicEventElementType | Whether the event source is active. |
| MessageTopic | Variable | String | Optional | AASBasicEventElementType | The topic events are delivered on. Where the delivery endpoint is itself catalogued, the registry entry points at it. |
| MessageBroker | Variable | [AASReferenceDataType](#type-AASReferenceDataType) | Optional | AASBasicEventElementType | The broker delivering the events. |
| LastUpdate | Variable | [AASValueString](#type-AASValueString) | Optional | AASBasicEventElementType | When the event last fired, in its exact lexical form. |
| MinInterval | Variable | [AASValueString](#type-AASValueString) | Optional | AASBasicEventElementType | Minimum interval between events, in its exact lexical form. |
| MaxInterval | Variable | [AASValueString](#type-AASValueString) | Optional | AASBasicEventElementType | Maximum interval between events, in its exact lexical form. |

<a id="type-AASOperationType"></a>

#### AASOperationType  (ns=1;i=1034)

*Inherits from:* [AASSubmodelElementType](#type-AASSubmodelElementType)

An invocable operation.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| InputVariables | Variable | [AASOperationVariableDataType](#type-AASOperationVariableDataType)\[\] | Optional | AASOperationType | The operation's input variables, in order. |
| OutputVariables | Variable | [AASOperationVariableDataType](#type-AASOperationVariableDataType)\[\] | Optional | AASOperationType | The operation's output variables, in order. |
| InoutputVariables | Variable | [AASOperationVariableDataType](#type-AASOperationVariableDataType)\[\] | Optional | AASOperationType | The operation's in-out variables, in order. |
| <Variable> | Object |  | OptionalPlaceholder | AASOperationType | An element carrying one of the operation's variables. |

<a id="type-AASCapabilityType"></a>

#### AASCapabilityType  (ns=1;i=1035)

*Inherits from:* [AASSubmodelElementType](#type-AASSubmodelElementType)

A declared capability of the asset. It carries no value of its own; the element's identity and semantics are the whole of its content.

<a id="type-AASRegistryType"></a>

#### AASRegistryType  (ns=1;i=1100)

*Inherits from:* ns=1;i=63000

The AAS Registry root - an xRegistry RegistryType, and therefore a FolderType - whose group folders hold shells, submodel templates, concept dictionaries and packages. Exposed as a well-known object under the Server object, so any Client that reaches the standard Server object discovers it.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| <ShellGroup> | Object |  | OptionalPlaceholder | AASRegistryType | A shell folder held by the registry. |
| <SubmodelTemplateGroup> | Object |  | OptionalPlaceholder | AASRegistryType | A submodel template family held by the registry. |
| <ConceptDictionaryGroup> | Object |  | OptionalPlaceholder | AASRegistryType | A concept dictionary held by the registry. |
| <PackageStoreGroup> | Object |  | OptionalPlaceholder | AASRegistryType | A package store held by the registry. |
| LookupShellsByAssetLink | Method |  | Optional | AASRegistryType | Return the shells discoverable by an asset key. This is the discovery question - given a serial number or a part identifier, which shells describe it - answered without the caller browsing the whole collection. |
| GetSubmodel | Method |  | Optional | AASRegistryType | Return a submodel document and enough metadata to parse it, given its identifier. The method form of the document fast path, for a Client that has an identifier rather than a node. |

<a id="type-AASShellGroupType"></a>

#### AASShellGroupType  (ns=1;i=1101)

*Inherits from:* ns=1;i=63001

An xRegistry GroupType holding the submodel documents of one shell. Its source identity is the shell's authored identifier, from which the GroupId is constructed. It is distinct from AASType, which models the same shell as a live node tree rather than as a catalogue entry.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| AasIdentifier | Variable | String | Mandatory | AASShellGroupType | The shell's authored identifier, verbatim. It is the group's source identity: the GroupId is the symbolic identifier constructed from it, and Name is this identifier. |
| AssetKind | Variable | [AASAssetKindDataType](#type-AASAssetKindDataType) | Mandatory | AASShellGroupType | Whether the shell describes a product model, an individual item or a batch. |
| GlobalAssetId | Variable | String | Optional | AASShellGroupType | The identifier of the asset itself, as distinct from the shell describing it. |
| AssetType | Variable | String | Optional | AASShellGroupType | The identifier of the asset type this asset is an occurrence of. |
| SpecificAssetIds | Variable | [AASSpecificAssetIdDataType](#type-AASSpecificAssetIdDataType)\[\] | Optional | AASShellGroupType | The keys this shell is discoverable by. |
| Administration | Variable | [AASAdministrativeInformationDataType](#type-AASAdministrativeInformationDataType) | Optional | AASShellGroupType | Administrative information carried by the shell. |
| DerivedFrom | Variable | String | Optional | AASShellGroupType | The identifier of the Type shell this Instance shell was derived from. |
| DisclosureTier | Variable | [AASDisclosureTierDataType](#type-AASDisclosureTierDataType) | Optional | AASShellGroupType | Whether this entity is readable without authentication. |
| Authorization | Variable | [AASAuthorizationOptionDataType](#type-AASAuthorizationOptionDataType)\[\] | Optional | AASShellGroupType | The authorization options a Consumer may use to obtain access. |
| EventEndpoint | Variable | String | Optional | AASShellGroupType | The catalogued endpoint delivering change events for this shell, where one is published. |
| ShellNode | Variable | NodeId | Optional | AASShellGroupType | The AASType node modelling this same shell as a live node tree, where the Server also implements the metamodel half. The catalogue entry and the node tree are different nodes for the same shell, and this is the link between them. |
| <Submodel> | Object |  | OptionalPlaceholder | AASShellGroupType | A submodel document held by this shell. |

<a id="type-AASSubmodelFileType"></a>

#### AASSubmodelFileType  (ns=1;i=1102)

*Inherits from:* ns=1;i=63002

An xRegistry ResourceType whose file content is one submodel document. Each version is one revision, which is what gives a shell the lifecycle history the metamodel does not itself provide.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| SubmodelIdentifier | Variable | String | Mandatory | AASSubmodelFileType | The submodel's authored identifier, verbatim. It is the resource's source identity, from which the ResourceId is constructed, and it is invariant across the submodel's versions. |
| SemanticId | Variable | String | Optional | AASSubmodelFileType | The concept this submodel is an occurrence of - the attribute a Consumer filters on to find, for example, every carbon footprint submodel in a registry. |
| SupplementalSemanticIds | Variable | String\[\] | Optional | AASSubmodelFileType | Further concepts this submodel corresponds to. |
| Kind | Variable | [AASModellingKindDataType](#type-AASModellingKindDataType) | Optional | AASSubmodelFileType | Whether the submodel carries values or defines a shape. |
| Template | Variable | String | Optional | AASSubmodelFileType | The identifier of the template this submodel was built from. It is an identifier and not a pointer, so it resolves identically whether or not this registry also serves the template. |
| Digest | Variable | String | Optional | AASSubmodelFileType | Digest of the exact document bytes a Consumer retrieves. A registry does not publish one for bytes it has not itself seen. |
| DigestAlg | Variable | String | Optional | AASSubmodelFileType | The algorithm used to compute Digest. Present whenever Digest is. |
| IsDefault | Variable | Boolean | Optional | AASSubmodelFileType | Whether this is the version served when none is selected. |
| Ancestor | Variable | String | Optional | AASSubmodelFileType | The version this one derives from. A root version's ancestor is itself. |
| DisclosureTier | Variable | [AASDisclosureTierDataType](#type-AASDisclosureTierDataType) | Optional | AASSubmodelFileType | Whether this document is readable without authentication. A document is wholly one tier or the other: a boundary falling between elements inside a document cannot be expressed here. |
| Authorization | Variable | [AASAuthorizationOptionDataType](#type-AASAuthorizationOptionDataType)\[\] | Optional | AASSubmodelFileType | The authorization options a Consumer may use to obtain access. |
| SubmodelNode | Variable | NodeId | Optional | AASSubmodelFileType | The AASSubmodelType node modelling this same submodel as a live node tree, where the Server also implements the metamodel half. |

<a id="type-AASSubmodelTemplateGroupType"></a>

#### AASSubmodelTemplateGroupType  (ns=1;i=1103)

*Inherits from:* ns=1;i=63001

An xRegistry GroupType holding one publisher's family of submodel templates. Keeping templates in a group of their own is what lets a Consumer building a new asset list templates while a Consumer reading an asset lists instances.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| TemplateNamespace | Variable | String | Mandatory | AASSubmodelTemplateGroupType | The publisher's template namespace, verbatim. It is the group's source identity. |
| Publisher | Variable | String | Optional | AASSubmodelTemplateGroupType | The organization publishing this template family. |
| <Submodel> | Object |  | OptionalPlaceholder | AASSubmodelTemplateGroupType | A submodel template held by this family. |

<a id="type-AASConceptDictionaryGroupType"></a>

#### AASConceptDictionaryGroupType  (ns=1;i=1104)

*Inherits from:* ns=1;i=63001

An xRegistry GroupType holding one dictionary of concept definitions - the definitions a SemanticId elsewhere in the registry resolves to.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| DictionaryIdentifier | Variable | String | Mandatory | AASConceptDictionaryGroupType | The dictionary's identifier, verbatim. It is the group's source identity. |
| <ConceptDescription> | Object |  | OptionalPlaceholder | AASConceptDictionaryGroupType | A concept definition held by this dictionary. |

<a id="type-AASConceptDescriptionFileType"></a>

#### AASConceptDescriptionFileType  (ns=1;i=1105)

*Inherits from:* ns=1;i=63002

An xRegistry ResourceType whose file content is one concept description document.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| ConceptIdentifier | Variable | String | Mandatory | AASConceptDescriptionFileType | The concept's authored identifier, verbatim, which is the value that appears as a SemanticId elsewhere. It is the resource's source identity. Dictionary identifiers frequently use a syntax unrelated to any URI scheme, which is precisely why the identifier is carried here and the node is named by the derived one. |
| IsCaseOf | Variable | String\[\] | Optional | AASConceptDescriptionFileType | Concepts in other dictionaries this concept corresponds to. |

<a id="type-AASPackageStoreGroupType"></a>

#### AASPackageStoreGroupType  (ns=1;i=1106)

*Inherits from:* ns=1;i=63001

An xRegistry GroupType holding packages - one store, or one namespace within one.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| StoreIdentifier | Variable | String | Mandatory | AASPackageStoreGroupType | The store's identifier, verbatim. It is the group's source identity. |
| RegistryUrl | Variable | String | Optional | AASPackageStoreGroupType | Base URL of the backing package store. |
| <Package> | Object |  | OptionalPlaceholder | AASPackageStoreGroupType | A package held by this store. |

<a id="type-AASPackageFileType"></a>

#### AASPackageFileType  (ns=1;i=1107)

*Inherits from:* ns=1;i=63002

An xRegistry ResourceType whose file content is one package: an immutable release addressed by digest and optionally attested by signatures.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| PackageIdentifier | Variable | String | Mandatory | AASPackageFileType | The package's name as held by the backing store, verbatim. It is the resource's source identity. |
| ArtifactType | Variable | String | Optional | AASPackageFileType | The media type identifying what the artifact is, where the backing store carries one. |
| Digest | Variable | String | Optional | AASPackageFileType | Digest of the exact package bytes. This is the integrity anchor: a version identifies which release a Consumer wants, a digest identifies what that release contains. |
| DigestAlg | Variable | String | Optional | AASPackageFileType | The algorithm used to compute Digest. |
| AasIdentifiers | Variable | String\[\] | Optional | AASPackageFileType | The shell identifiers this package contains, so a Consumer can tell what it holds without retrieving and opening it. |
| Subject | Variable | String | Optional | AASPackageFileType | The digest of the artifact this one attests, where it is an attestation rather than a package. |
| Attestations | Variable | [AASAttestationDataType](#type-AASAttestationDataType)\[\] | Optional | AASPackageFileType | The signatures and attestations attached to this package. |

### DataTypes

<a id="type-AASValueString"></a>

#### AASValueString  (ns=1;i=1199)

*Subtype of:* String

The xsd lexical form of a typed value, as authored. A subtype of String so that a lexical value is distinguishable from an ordinary string by its DataType rather than by which Variable it came from - the pattern OPC UA already uses for DecimalString, DurationString, DateString and TimeString. The xsd type the form denotes is declared separately, in ValueType.

<a id="type-AASAssetKindDataType"></a>

#### AASAssetKindDataType  (ns=1;i=1200)

*Subtype of:* Enumeration

Whether a shell describes a product model, an individual item, a batch, a role, or none of these. The three granularity levels a product passport is issued at map onto Type, Instance and Batch.

| Field | DataType | Description |
|---|---|---|
| Type |  | The shell describes a product model rather than an individual item. |
| Instance |  | The shell describes one individual physical item. |
| Batch |  | The shell describes a production lot. |
| Role |  | The shell describes a role rather than a physical asset. |
| NotApplicable |  | Asset kind does not apply. |

<a id="type-AASModellingKindDataType"></a>

#### AASModellingKindDataType  (ns=1;i=1201)

*Subtype of:* Enumeration

Whether an element defines a shape or carries values.

| Field | DataType | Description |
|---|---|---|
| Template |  | Defines the shape other elements are built from; carries no values for an individual asset. |
| Instance |  | Carries values for one asset. |

<a id="type-AASEntityTypeDataType"></a>

#### AASEntityTypeDataType  (ns=1;i=1202)

*Subtype of:* Enumeration

Whether a composition entity is managed within its parent or has a shell of its own.

| Field | DataType | Description |
|---|---|---|
| CoManagedEntity |  | The entity has no shell of its own and is managed within its parent. |
| SelfManagedEntity |  | The entity has its own shell, identified by GlobalAssetId; this is what makes a bill of material traversable across organizations. |

<a id="type-AASDirectionDataType"></a>

#### AASDirectionDataType  (ns=1;i=1203)

*Subtype of:* Enumeration

The direction of an event element.

| Field | DataType | Description |
|---|---|---|
| Input |  | The event is consumed by the element. |
| Output |  | The event is produced by the element. |

<a id="type-AASStateOfEventDataType"></a>

#### AASStateOfEventDataType  (ns=1;i=1204)

*Subtype of:* Enumeration

Whether an event element is currently active.

| Field | DataType | Description |
|---|---|---|
| Off |  | The event source is inactive. |
| On |  | The event source is active. |

<a id="type-AASQualifierKindDataType"></a>

#### AASQualifierKindDataType  (ns=1;i=1205)

*Subtype of:* Enumeration

What a qualifier qualifies, and therefore whether it may change.

| Field | DataType | Description |
|---|---|---|
| ValueQualifier |  | Qualifies the value and may change during the element's lifetime. |
| ConceptQualifier |  | Qualifies the concept and is invariant. |
| TemplateQualifier |  | Qualifies the template the element was built from. |

<a id="type-AASReferenceTypesDataType"></a>

#### AASReferenceTypesDataType  (ns=1;i=1206)

*Subtype of:* Enumeration

Whether a reference addresses something inside the model or outside it.

| Field | DataType | Description |
|---|---|---|
| ExternalReference |  | Points at something outside the metamodel. |
| ModelReference |  | Points at a node within the model, navigated key by key. |

<a id="type-AASKeyTypesDataType"></a>

#### AASKeyTypesDataType  (ns=1;i=1207)

*Subtype of:* Enumeration

The kind of thing a reference key addresses. The enumeration is closed: a value outside it cannot round-trip, so an implementation rejects it rather than dropping it.

| Field | DataType | Description |
|---|---|---|
| AnnotatedRelationshipElement |  |  |
| AssetAdministrationShell |  |  |
| BasicEventElement |  |  |
| Blob |  |  |
| Capability |  |  |
| ConceptDescription |  |  |
| DataElement |  |  |
| Entity |  |  |
| EventElement |  |  |
| File |  |  |
| FragmentReference |  |  |
| GlobalReference |  |  |
| Identifiable |  |  |
| MultiLanguageProperty |  |  |
| Operation |  |  |
| Property |  |  |
| Range |  |  |
| Referable |  |  |
| ReferenceElement |  |  |
| RelationshipElement |  |  |
| Submodel |  |  |
| SubmodelElement |  |  |
| SubmodelElementCollection |  |  |
| SubmodelElementList |  |  |

<a id="type-AASDataTypeDefXsdDataType"></a>

#### AASDataTypeDefXsdDataType  (ns=1;i=1208)

*Subtype of:* Enumeration

The xsd type a value is expressed in. Several of these have no faithful OPC UA equivalent, which is why a value is carried both as a typed Variable and as its exact lexical form.

| Field | DataType | Description |
|---|---|---|
| AnyUri |  |  |
| Base64Binary |  |  |
| Boolean |  |  |
| Byte |  |  |
| Date |  |  |
| DateTime |  |  |
| Decimal |  | Arbitrary precision; has no faithful OPC UA equivalent, so RawValue is the normative carrier. |
| Double |  |  |
| Duration |  | Has no native OPC UA equivalent; RawValue is the normative carrier. |
| Float |  |  |
| GDay |  |  |
| GMonth |  |  |
| GMonthDay |  |  |
| GYear |  |  |
| GYearMonth |  | Partial date; RawValue is the normative carrier. |
| HexBinary |  |  |
| Int |  |  |
| Integer |  | Unbounded; RawValue is the normative carrier. |
| Long |  |  |
| NegativeInteger |  |  |
| NonNegativeInteger |  |  |
| NonPositiveInteger |  |  |
| PositiveInteger |  |  |
| Short |  |  |
| String |  |  |
| Time |  |  |
| UnsignedByte |  |  |
| UnsignedInt |  |  |
| UnsignedLong |  |  |
| UnsignedShort |  |  |

<a id="type-AASDataTypeIec61360DataType"></a>

#### AASDataTypeIec61360DataType  (ns=1;i=1209)

*Subtype of:* Enumeration

The data type of a concept definition expressed in the IEC 61360 data specification.

| Field | DataType | Description |
|---|---|---|
| Blob |  |  |
| Boolean |  |  |
| Date |  |  |
| File |  |  |
| Html |  |  |
| IntegerCount |  |  |
| IntegerCurrency |  |  |
| IntegerMeasure |  |  |
| Irdi |  |  |
| Iri |  |  |
| Rational |  |  |
| RationalMeasure |  |  |
| RealCount |  |  |
| RealCurrency |  |  |
| RealMeasure |  |  |
| String |  |  |
| StringTranslatable |  |  |
| Time |  |  |
| Timestamp |  |  |

<a id="type-AASSubmodelElementsDataType"></a>

#### AASSubmodelElementsDataType  (ns=1;i=1210)

*Subtype of:* Enumeration

The element kind a SubmodelElementList constrains its members to.

| Field | DataType | Description |
|---|---|---|
| AnnotatedRelationshipElement |  |  |
| BasicEventElement |  |  |
| Blob |  |  |
| Capability |  |  |
| DataElement |  |  |
| Entity |  |  |
| EventElement |  |  |
| File |  |  |
| MultiLanguageProperty |  |  |
| Operation |  |  |
| Property |  |  |
| Range |  |  |
| ReferenceElement |  |  |
| RelationshipElement |  |  |
| SubmodelElement |  |  |
| SubmodelElementCollection |  |  |
| SubmodelElementList |  |  |

<a id="type-AASDisclosureTierDataType"></a>

#### AASDisclosureTierDataType  (ns=1;i=1211)

*Subtype of:* Enumeration

Whether an entity is readable without authentication. It advertises the tier so a Consumer can discover it; it does not enforce it.

| Field | DataType | Description |
|---|---|---|
| Public |  | Readable without authentication. |
| Controlled |  | Requires an authenticated role. |

<a id="type-AASKeyDataType"></a>

#### AASKeyDataType  (ns=1;i=1220)

*Subtype of:* [Structure](https://reference.opcfoundation.org/specs/OPC-10000-5/8.24)

One step of a reference path. Keys are ordered, and the order is part of the reference's meaning.

| Field | DataType | Description |
|---|---|---|
| Type | [AASKeyTypesDataType](#type-AASKeyTypesDataType) | The kind of thing this key addresses. |
| Value | String | The identifier value at this key. |

<a id="type-AASReferenceDataType"></a>

#### AASReferenceDataType  (ns=1;i=1221)

*Subtype of:* [Structure](https://reference.opcfoundation.org/specs/OPC-10000-5/8.24)

A reference, external or model-navigating, expressed as an ordered key path.

| Field | DataType | Description |
|---|---|---|
| Type | [AASReferenceTypesDataType](#type-AASReferenceTypesDataType) | Whether the reference is external or navigates the model. |
| ReferredSemanticId | [AASReferenceDataType](#type-AASReferenceDataType) | The semantic identifier of the thing referred to, where known. |
| Keys | [AASKeyDataType](#type-AASKeyDataType)\[\] | The ordered key path. At least one key is present. |

<a id="type-AASLangStringDataType"></a>

#### AASLangStringDataType  (ns=1;i=1222)

*Subtype of:* [Structure](https://reference.opcfoundation.org/specs/OPC-10000-5/8.24)

One language-tagged string. A multi-language value is an array of these, and the array order is preserved.

| Field | DataType | Description |
|---|---|---|
| Language | String | BCP 47 language tag. |
| Text | String | The text in that language. |

<a id="type-AASSpecificAssetIdDataType"></a>

#### AASSpecificAssetIdDataType  (ns=1;i=1223)

*Subtype of:* [Structure](https://reference.opcfoundation.org/specs/OPC-10000-5/8.24)

A domain-specific key an asset is discoverable by.

| Field | DataType | Description |
|---|---|---|
| Name | String | The key name, for example serialNumber or manufacturerPartId. |
| Value | String | The key value. |
| ExternalSubjectId | [AASReferenceDataType](#type-AASReferenceDataType) | The subject this key is disclosed to, where the key is not public. |
| SemanticId | [AASReferenceDataType](#type-AASReferenceDataType) | The concept this key is an occurrence of. |
| SupplementalSemanticIds | [AASReferenceDataType](#type-AASReferenceDataType)\[\] | Further concepts this key corresponds to. |

<a id="type-AASAdministrativeInformationDataType"></a>

#### AASAdministrativeInformationDataType  (ns=1;i=1224)

*Subtype of:* [Structure](https://reference.opcfoundation.org/specs/OPC-10000-5/8.24)

Administrative information. It records a single current revision: the entity's history is carried by the registry, which the metamodel has no equivalent of.

| Field | DataType | Description |
|---|---|---|
| Version | String | Version label. |
| Revision | String | Revision label; only meaningful when Version is present. |
| Creator | [AASReferenceDataType](#type-AASReferenceDataType) | The party that created the entity. |
| TemplateId | String | The template the entity was built from. |
| EmbeddedDataSpecifications | [AASEmbeddedDataSpecificationDataType](#type-AASEmbeddedDataSpecificationDataType)\[\] | Data specifications carried by this administrative information. |

<a id="type-AASQualifierDataType"></a>

#### AASQualifierDataType  (ns=1;i=1225)

*Subtype of:* [Structure](https://reference.opcfoundation.org/specs/OPC-10000-5/8.24)

A qualifier constraining or annotating an element.

| Field | DataType | Description |
|---|---|---|
| Kind | [AASQualifierKindDataType](#type-AASQualifierKindDataType) | What the qualifier qualifies. |
| Type | String | The qualifier type name. |
| ValueType | [AASDataTypeDefXsdDataType](#type-AASDataTypeDefXsdDataType) | The xsd type the value is expressed in. |
| Value | [AASValueString](#type-AASValueString) | The value in its exact lexical form. |
| ValueId | [AASReferenceDataType](#type-AASReferenceDataType) | A reference to the value, where it is itself an identified concept. |
| SemanticId | [AASReferenceDataType](#type-AASReferenceDataType) | The concept this qualifier is an occurrence of. |
| SupplementalSemanticIds | [AASReferenceDataType](#type-AASReferenceDataType)\[\] | Further concepts this qualifier corresponds to. |

<a id="type-AASEmbeddedDataSpecificationDataType"></a>

#### AASEmbeddedDataSpecificationDataType  (ns=1;i=1226)

*Subtype of:* [Structure](https://reference.opcfoundation.org/specs/OPC-10000-5/8.24)

A data specification carried by an element, paired with its content.

| Field | DataType | Description |
|---|---|---|
| DataSpecification | [AASReferenceDataType](#type-AASReferenceDataType) | Reference to the data specification template. |
| DataSpecificationContent | [AASDataSpecificationIec61360DataType](#type-AASDataSpecificationIec61360DataType) | The content, in the IEC 61360 data specification. |

<a id="type-AASDataSpecificationIec61360DataType"></a>

#### AASDataSpecificationIec61360DataType  (ns=1;i=1227)

*Subtype of:* [Structure](https://reference.opcfoundation.org/specs/OPC-10000-5/8.24)

The IEC 61360 data specification content of a concept definition.

| Field | DataType | Description |
|---|---|---|
| PreferredName | [AASLangStringDataType](#type-AASLangStringDataType)\[\] | Preferred name per language. |
| ShortName | [AASLangStringDataType](#type-AASLangStringDataType)\[\] | Short name per language. |
| Unit | String | Unit symbol. |
| UnitId | [AASReferenceDataType](#type-AASReferenceDataType) | Reference to the unit concept. |
| SourceOfDefinition | String | Where the definition comes from. |
| Symbol | String | Symbol for the concept. |
| DataType | [AASDataTypeIec61360DataType](#type-AASDataTypeIec61360DataType) | The IEC 61360 data type. |
| Definition | [AASLangStringDataType](#type-AASLangStringDataType)\[\] | Definition per language. |
| ValueFormat | String | Format of the value. |
| ValueList | String | Permitted values, serialized in the metamodel's own form. |
| Value | [AASValueString](#type-AASValueString) | The value in its exact lexical form. |
| LevelType | String | Which of min, nom, typ and max apply. |

<a id="type-AASExtensionDataType"></a>

#### AASExtensionDataType  (ns=1;i=1228)

*Subtype of:* [Structure](https://reference.opcfoundation.org/specs/OPC-10000-5/8.24)

A proprietary extension carried on a Referable. Extensions round-trip verbatim; a reader that does not understand one preserves it unchanged.

| Field | DataType | Description |
|---|---|---|
| Name | String | Extension name. |
| ValueType | [AASDataTypeDefXsdDataType](#type-AASDataTypeDefXsdDataType) | The xsd type the value is expressed in. |
| Value | [AASValueString](#type-AASValueString) | The value in its exact lexical form. |
| RefersTo | [AASReferenceDataType](#type-AASReferenceDataType)\[\] | What the extension refers to. |
| SemanticId | [AASReferenceDataType](#type-AASReferenceDataType) | The concept this extension is an occurrence of. |
| SupplementalSemanticIds | [AASReferenceDataType](#type-AASReferenceDataType)\[\] | Further concepts this extension corresponds to. |

<a id="type-AASResourceDataType"></a>

#### AASResourceDataType  (ns=1;i=1229)

*Subtype of:* [Structure](https://reference.opcfoundation.org/specs/OPC-10000-5/8.24)

A pointer to external content, such as a thumbnail.

| Field | DataType | Description |
|---|---|---|
| Path | String | Path or URL to the resource. |
| ContentType | String | Media type of the resource. |

<a id="type-AASOperationVariableDataType"></a>

#### AASOperationVariableDataType  (ns=1;i=1230)

*Subtype of:* [Structure](https://reference.opcfoundation.org/specs/OPC-10000-5/8.24)

One input, output or in-out variable of an operation, carried as a reference to the element node that holds it so that the element's own representation is not duplicated.

| Field | DataType | Description |
|---|---|---|
| ValueNodeId | NodeId | The submodel element node carrying this variable. |

<a id="type-AASAuthorizationOptionDataType"></a>

#### AASAuthorizationOptionDataType  (ns=1;i=1231)

*Subtype of:* [Structure](https://reference.opcfoundation.org/specs/OPC-10000-5/8.24)

One authorization option a Consumer may use. It is authorization configuration only and never carries credentials, which are supplied out of band.

| Field | DataType | Description |
|---|---|---|
| Type | String | Authorization type, for example OAuth2, Plain, SASL, X509Cert or APIKey. |
| Mechanism | String | SASL mechanism name, used only when Type is SASL. |
| ResourceUri | String | The resource authorization is requested for. |
| AuthorityUri | String | The authority authorization is obtained from. |

<a id="type-AASAttestationDataType"></a>

#### AASAttestationDataType  (ns=1;i=1232)

*Subtype of:* [Structure](https://reference.opcfoundation.org/specs/OPC-10000-5/8.24)

A signature or attestation attached to a package. Its presence is not verification: a Consumer retrieves and verifies the artifact itself.

| Field | DataType | Description |
|---|---|---|
| ArtifactType | String | Media type identifying what kind of attestation this is. |
| Digest | String | Digest of the attestation artifact. |
| Signer | String | The party that produced the attestation. |

### Methods

| Method | Owning type | Input arguments | Output arguments |
|---|---|---|---|
| LookupShellsByAssetLink | [AASRegistryType](#type-AASRegistryType) | Name, Value | Shells |
| GetSubmodel | [AASRegistryType](#type-AASRegistryType) | SubmodelIdentifier | Document, Format, ContentType |
| LookupShellsByAssetLink | AASRegistry | Name, Value | Shells |
| GetSubmodel | AASRegistry | SubmodelIdentifier | Document, Format, ContentType |

