# ADR-to-`uav` semantic crosswalk (design-input, informative)

> Informative background — **not** part of the normative [OPC UA — WoT Binding](../../WoT-Binding/OPC-UA-WoT-Binding.md) specification. The normative meaning of every `uav` model and platform term is defined by Section 6 (with per-term concept, usage, and examples) and its validation rules in Section 7 of that specification. This document is kept in `extras/` purely to record the design inputs and is linked only from README/extras documentation.

The model and platform vocabulary of the WoT Binding was informed by two architecture decision records (**ADR 0029** and **ADR 0032**) used only as design inputs. This crosswalk records how the neutral concepts of those design inputs are realized by the `uav` terms. It uses no vendor prefix, namespace, or modelling-language name; only the neutral concept name and the `uav` term appear. **No** vocabulary, prefix, or namespace of those design inputs is reused in the specification.

| Source ADR concept | `uav` term | Semantics realized |
| --- | --- | --- |
| Composite-model flag | `uav:isComposite` | The type is decomposed into named parts. |
| Event-affordance flag | `uav:isEvent` | The affordance projects an event definition. |
| Capability facet link | `rel: uav:capability` | An exposed capability or interface-like mix-in. |
| Component sub-model link | `rel: uav:componentModel` | An owned, contained sub-component model. |
| Plain relationship link | `rel: uav:reference` | A non-hierarchical, untyped relationship. |
| Typed relationship link | `rel: uav:typedReference` + `uav:refType` | A relationship qualified by an explicit reference type. |
| Parent (container) link | `rel: uav:componentOf` | The parent under which the instance is exposed (inverse `HasComponent`). |
| Relationship name | `uav:refName` | The name a relationship is exposed under. |
| Relationship type | `uav:refType` | The reference type of a typed relationship. |
| Containment (child set) | `uav:contains` | The parts a composite directly contains. |
| Containment (parent) | `uav:containedIn` | The single composite that contains a part. |
| Co-typed / congruent definition | `uav:congruentType` | A structurally congruent shared definition. |
| Naming namespace | `uav:nameNamespace` | The absolute IRI naming namespace of local names. |
| Value scale factor | `uav:scaleFactor` | Linear factor, engineering = raw × factor. |
| Retained decimal places | `uav:decimalPlaces` | Fractional places kept after scaling. |
| Property group set | `uav:propertyGroups` | Named groups of properties. |
| Event group set | `uav:eventGroups` | Named groups of events. |
| Action group set | `uav:actionGroups` | Named groups of actions. |
| Group membership | `uav:memberOf` | The group a member belongs to. |
| Unit-carrying property locator | `uav:unitProperty` | JSON Pointer to the unit string property; quantity kind via QUDT. |
| Opaque annotation bag | `uav:metadata` | Verbatim implementation metadata. |
| Semantic identity | `uav:semanticId` | Absolute IRI semantic identifier. |
| Per-property configuration | `uav:propertyConfiguration` | Opaque property configuration. |
| Per-action configuration | `uav:actionConfiguration` | Opaque action configuration. |
| Per-event configuration | `uav:eventConfiguration` | Opaque event configuration. |
| Inherited-member inclusion | `uav:includeInherited` | Whether inherited members are in scope. |
| Open-content flag | `uav:additionalProperties` | Whether instances may carry undeclared members. |
| External schema pointer | `uav:externalSchema` | URI/path to a custom DataType or payload schema. |
| Instantiation rule | `uav:modellingRule` | Exactly one of `Mandatory`, `Optional`, `MandatoryPlaceholder`, `OptionalPlaceholder`. |
