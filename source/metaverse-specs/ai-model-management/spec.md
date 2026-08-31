## Scope {#sec-scope}

This specification defines an OPC UA information model that lets a Server describe:

- **what model it is running** — identity, version, framework, format, and the digest that makes the artefact verifiable;
- **what that model was trained on** — including whether the data was real, synthetic or both;
- **where inference executes** — in the Server, on an edge node, in a cloud service, or in a simulator;
- **how to actually run it** — one invocation surface that does not change with any of the above (clause 8);
- **how to run a model this Server does not host** — the wire contract, the credential, the capabilities, and what happens when the link fails (clause 9);
- **how a model gets here** — pulling one from a catalogue and either describing it where it stands or bringing its bytes across, with the digest checked at the moment that matters (clause 10);
- **whether it may be used at all** — what it is for, where it stops working, how it measured, and whether calling it sends plant data off site (clause 11);
- **how a model is replaced** — the capture, label, train and promote loop, and who is allowed to complete it.

### Motivation {#sec-motivation}

An industrial AI model is not device firmware. It is an artefact the operator or system integrator supplies, versions and approves, and the same physical equipment runs different models over its life. Someone has to be able to ask *which model produced this decision, what was it trained on, and who promoted it* — and today, no OPC UA specification lets them.

Three IDTA submodel templates describe the pieces — **IDTA 02060** for a model nameplate, **IDTA 02058** for a dataset, **IDTA 02059** for a deployment — but they are Asset Administration Shell templates, not an OPC UA address space. This model aligns with them member-for-member so that an AAS can be populated from these nodes without loss, while remaining browsable, subscribable and callable in its own right.

**Nothing here is specific to any one kind of input.** `TaskKind` is a String. `SourceKind` distinguishes real capture from simulator output. The learning loop runs `Idle → Collecting → Labelling → Training → Validating → Ready → Promoted`. A vibration-analysis model, a process soft sensor and a quality classifier all need exactly this, and none of them need a lens — which is why the model is domain-neutral by construction rather than by convention, and why its validator fails the build if a type name acquires a domain term.

### What this specification does not do {#sec-what-this-specification-does-not-do}

- It does **not** carry model artefacts or training data. `ArtifactUri` says where the bytes are; the bytes travel by whatever means already moves large files, and `Digest` is what makes the retrieval verifiable.
- It does **not** define what an inference payload *contains*. Clause 8 defines the envelope — routing, parameters, accounting, why output stopped, which model answered — and leaves the payload opaque, because what you pass to a model and what comes back is domain vocabulary: an image and a set of detections, a spectrum and a fault class. An envelope that tried to type that would need extending for every domain that ever adopted it.
- It does **not** define a training algorithm, a scheduler or an MLOps platform. `TriggerTraining` requests training and `LearningJobType` observes it; where the training runs is out of scope, and clause 7 is explicit that a Server may implement only the capture stages.
- It is **not** a governance or compliance framework. It records what is needed to answer provenance questions; whether an installation is permitted to run a given model is decided elsewhere.

### Capabilities and versioning {#sec-capabilities-and-versioning}

This specification covers the model, the dataset, the deployment, the learning loop, the invocation surface, consumption of externally hosted models, the catalogue and the import bridge.

The NodeSet declares **two** `RequiredModel` entries: the base OPC UA namespace, and *OPC UA — xRegistry*, because the catalogue of clause 10 is a domain extension of that abstract registry rather than a private invention. That is a real cost and it is taken deliberately — a model catalogue **is** a registry, and defining a second one here would leave two incompatible ways to describe the same artefact.

It is worth being precise about what that dependency does **not** reach. A consuming specification still binds to this one through a plain `NodeId` Property (§4.2) and takes no NodeSet dependency of its own, so a vision or condition-monitoring Server is unaffected by this model's dependencies. The obligation lands on a Server that implements *this* specification, not on one that merely points at it.

---

## Scenarios {#sec-scenarios}

This clause is **informative**. It sets out the arrangements this specification is meant to support, each with the flow that realises it, so that a reader can find the one resembling their installation before reading the normative clauses that define its parts.

The scenarios are not alternatives to choose between. A single Server commonly implements several — a plant that runs a model locally, calls a hosted one for a second opinion, and imports both from a corporate catalogue is doing three of them at once.

### A model runs on the machine {#sec-a-model-runs-on-the-machine}

The simplest arrangement, and the most common in practice: the artefact sits on the controller and executes in its own process.

```{figure}
id: fig-aim-local
caption: A model hosted on the machine
source: figures/AiModelManagement-Fig1-Local.png
```

Nothing is remote, so `Source` is null, `EgressPermitted` is false and `FallbackPolicy` is typically `Fail` — there is nothing to fall back to. Annex D works this end to end for an ONNX classifier.

**Facets:** AI-Base, AI-Invoke, AI-Signatures.

### The model runs somewhere else {#sec-the-model-runs-somewhere-else}

The Server has no model of its own and calls one hosted elsewhere — an appliance on the plant network, or a service beyond it.

```{figure}
id: fig-aim-remote
caption: Inference delegated to a remote endpoint
source: figures/AiModelManagement-Fig2-Remote.png
```

The client's call is unchanged from §4.1 — that is the point of §8.1. What changes is the trust boundary, and clause 9 is what makes the arrangement describable: the wire contract, the credential reference, and whether calling it sends plant data off site.

**Facets:** AI-Base, AI-Invoke, AI-Federation, AI-Residency.

### The link drops and something else answers {#sec-the-link-drops-and-something-else-answers}

The arrangement §4.2 needs in order to be usable on a line that cannot stop.

```{figure}
id: fig-aim-fallback
caption: Fallback when the remote endpoint is unreachable
source: figures/AiModelManagement-Fig3-Fallback.png
```

The branch worth noticing is the middle one: the caller asked nothing different and got an answer from a **different model**, so `ModelUsed` is the only thing that says so. Annex C works this through with a WAN failure.

**Facets:** as §4.2, plus a second deployment for the fallback.

### A model arrives from a catalogue {#sec-a-model-arrives-from-a-catalogue}

How a model gets onto a machine at all, whether by federating its description or by bringing its bytes.

```{figure}
id: fig-aim-import
caption: Importing a model from a catalogue
source: figures/AiModelManagement-Fig4-Import.png
```

Staging is where the digest is verified, because it is the one moment a substituted artefact would enter the system (§10.4).

**Facets:** AI-Catalogue, AI-Import.

### A large payload will not fit in a call {#sec-a-large-payload-will-not-fit-in-a-call}

An image or a sample window exceeds what a `ByteString` can carry, so the exchange is chunked.

```{figure}
id: fig-aim-stream
caption: Streaming a payload too large for a single call
source: figures/AiModelManagement-Fig5-Stream.png
```

`Invoke` is the shortcut that works while everything is small; this is the general path (§8.2.4).

**Facets:** AI-Base, AI-Transfer.

### The answer arrives later {#sec-the-answer-arrives-later}

Work that does not finish while a caller waits — a batch scored overnight, an analysis over recorded data.

```{figure}
id: fig-aim-async
caption: Deferred inference
source: figures/AiModelManagement-Fig6-Async.png
```

**Facets:** AI-Base, AI-InvokeAsync.

### Corrections become the next model {#sec-corrections-become-the-next-model}

An operator disagrees with a verdict, the correction is retained, and it eventually becomes a model version.

```{figure}
id: fig-aim-learning
caption: Corrections becoming the next model
source: figures/AiModelManagement-Fig7-Learning.png
```

Most Servers implement only part of this — capture the corrections and leave training to an external system (§7.3).

**Facets:** AI-Base, AI-Dataset, AI-Learning.

### Someone asks what produced a decision {#sec-someone-asks-what-produced-a-decision}

Not an operation but a question, and the reason several members exist at all.

```{figure}
id: fig-aim-explain
caption: Explaining a decision
source: figures/AiModelManagement-Fig8-Explain.png
```

**Facets:** AI-Base, and whichever of AI-Catalogue, AI-Dataset and AI-Import the installation implements.

---

## Overview and concepts {#sec-overview-and-concepts}

### Objects and relationships {#sec-objects-and-relationships}

```{figure}
id: fig-aim-concepts
caption: Objects and the relationships between them
source: figures/AiModelManagement-Fig9-Concepts.png
```

A dataset trains a model; a deployment executes one; a client calls the deployment. Where the model runs somewhere this Server does not control, the deployment names a **source** that says how to reach it and what to do when it cannot. Where a model comes from a catalogue, an **import job** brings it — as a description, or as bytes. A learning job accumulates a new dataset, produces a candidate, and promotes it, at which point the deployment executes a different model and the cycle repeats.

The four questions this arrangement is arranged to answer:

| Question | Where it is answered |
|---|---|
| What is running, and can I audit it? | `ModelType`, `DatasetType`, §12.1 |
| How do I run it? | `DeploymentType.Invoke` (§8) |
| What if it is not here, or stops answering? | `ModelSourceType`, `FallbackPolicy` (§9) |
| How did it get here, and may it be used? | `ModelImportJobType` (§10), `ModelCardType` (§11) |

A dataset trains a model; a deployment executes one. A learning job accumulates a new dataset, produces a candidate, and promotes it — at which point the deployment executes a different model and the cycle repeats.

`UsesModel` and `TrainedOn` are **references**, because they are structural. `Dataset`, `BaseModel` and `CandidateModel` on a learning job are **NodeId Properties**, because a job's relationships change as it runs and a reference set that churns is harder to observe than a value that changes.

### Binding from a consuming specification {#sec-binding-from-a-consuming-specification}

A specification that runs inference — a vision model, a condition-monitoring model — binds by holding a **`NodeId` Property** naming a `DeploymentType` instance. It does **not** take a `RequiredModel` on this NodeSet and does **not** define a ReferenceType into it.

That keeps both specifications loadable alone. A Server that describes its deployment some other way names that node instead, and a Server that implements neither is unaffected. The cost is that the provenance chain of §12 is only available where both are implemented, which is why it is stated as a conformance condition rather than assumed.

### Model ownership {#sec-model-ownership}

This is the assumption the whole model rests on, so it is stated plainly.

The equipment manufacturer does not supply the model. The operator or the system integrator does, and replaces it, and is answerable for it. A Server therefore **shall** describe the model it is *currently* running rather than the one it shipped with, and `PromoteModel` **shall** require an authorization distinct from the one that permits ordinary operation (§12.3).

The consequence for a reader: every member of `ModelType` is about *this* artefact, and none of it is nameplate data that could have been printed at the factory.

---

## Information model {#sec-information-model}

The AddressSpace figures in this document use the OPC UA graphical notation of OPC 10000-3. A Node of an instance NodeClass — Object, Variable or View — is a plain rectangle, a Method is a rounded rectangle, and a type — ObjectType, VariableType, ReferenceType or DataType — is a rectangle standing on a shadow. An abstract type is set in *italics*, and a Node whose BrowseName is a placeholder is written in angle brackets. A `HasTypeDefinition` reference carries a solid arrowhead; a `HasComponent` reference is the plain unlabelled arrow; every other ReferenceType is drawn with its BrowseName on the arrow. A figure shows the part of the model its clause describes, never the whole of it.

```{figure}
id: fig-aim-notation
caption: Graphical notation used by the AddressSpace figures
source: figures/AiModelManagement-FigNotation.png
```

### Type hierarchy {#sec-type-hierarchy}

The root holds the containers a client browses. `Models` and `Deployments` are Mandatory — a Server that manages no models has nothing to expose here; the rest are Optional:

<!-- model-figure: root=ns=2;i=1001 require=mandatory external=BaseObjectType  graph=figures/fig-aim-root.mmd -->

```{figure}
id: fig-aim-root
caption: The root and the containers it holds
source: figures/AiModelManagement-FigRoot.png
```

Every job is a Part 10 program, and the abstract base carries what every job has:

<!-- model-figure: root=ns=2;i=1006 require=mandatory external=ProgramStateMachineType  graph=figures/fig-aim-jobs.mmd -->

```{figure}
id: fig-aim-jobs
caption: Every job is a program
source: figures/AiModelManagement-FigJobs.png
```

| Type | NodeId | Subtype of |
|---|---|---|
| `AiRootType` | `ns=2;i=1001` | `BaseObjectType` |
| `ModelType` | `ns=2;i=1002` | `BaseObjectType` |
| `DatasetType` | `ns=2;i=1003` | `BaseObjectType` |
| `DeploymentType` | `ns=2;i=1004` | `BaseObjectType` |
| `AiJobType` (abstract) | `ns=2;i=1006` | `ProgramStateMachineType` (`i=2391`) |
| `LearningJobType` | `ns=2;i=1005` | `AiJobType` |
| `ModelImportJobType` | `ns=2;i=1007` | `AiJobType` |
| `InferenceJobType` | `ns=2;i=1008` | `AiJobType` |
| `ModelSourceType` | `ns=2;i=1009` | `BaseObjectType` |
| `EvaluationRunType` | `ns=2;i=1014` | `BaseObjectType` |
| `ModelCardType` | `ns=2;i=1015` | `BaseObjectType` |
| `ModelRegistryType` | `ns=2;i=1010` | xRegistry `RegistryType` |
| `ModelPublisherType` | `ns=2;i=1011` | xRegistry `GroupType` |
| `ModelResourceType` | `ns=2;i=1012` | xRegistry `ResourceType` |
| `DatasetResourceType` | `ns=2;i=1013` | xRegistry `ResourceType` |

`LearningJobType` keeps NodeId `1005` although it now sits below `1006`. NodeIds here are **append-only**: a type that acquires a base type does not move, because renumbering to make the file read tidily would break every client that cached an identifier.

### `ModelType` {#sec-modeltype}

`ModelType` describes one trained artefact: which it is, where it came from, and what it accepts and returns. It is the node a client reaches when it asks what produced a result, and the node an auditor reaches when it asks whether that artefact is the one that was approved. Its member set is aligned with the IDTA 02060 AI Model Nameplate submodel template, so an Asset Administration Shell can be populated from it without loss.

An instance is created when a model becomes known to the Server — whether it was imported from a catalogue (clause 10), trained by a learning job (clause 7), or configured by hand — and it outlives any single deployment of it, because the same artefact may be executed in several places at once.

`ModelId`, `Name`, `Version`, `Digest` and `DigestAlgorithm` are **Mandatory**. The first three because a model that cannot be named cannot be discussed; the last two because clause 12 depends on them, and a rule that depends on an Optional member is a rule a conformant Server can silently not satisfy.

**`ModelId` carries the source system's own identifier, verbatim.** Where a model came from a catalogue or a remote endpoint, it is the string that system uses — the string a client would send back to reach the same model there. It is not derived from the other members and it is not reformatted, because its value is that two Servers integrating the same source produce the same one. Where the triple below cannot be recovered, `ModelId` is what remains comparable.

**`Name` is a `LocalizedText` whose `Text` is the source's name for the model, carried across unchanged.** A Server **may** add a translation for display and **shall not** translate, reformat or prettify the `Text` itself. The type is `LocalizedText` because that is how this model types names and retyping it would break every implementation; what is localizable is the presentation, not the identity. Two Servers that fetched one model from two mirrors are meant to produce the same string, and a name adjusted for house style is a name that no longer matches.

**`Publisher` names the organisation that produced the model**, not the one serving it. A hosted endpoint that reports its own operator as the owner has answered a different question, and a Server **shall not** publish the serving organisation there: a `Publisher` of `azure` or `aws` for a model somebody else trained defeats the purpose §6.2.1 gives it, which is recognising the same artefact across two installations that fetched it from different places. Where only the serving organisation is known, `Publisher` is left empty.

Leaving it empty is the right answer more often than it looks. `Publisher` and `Version` are best-effort against a source that publishes one opaque identifier and nothing else, and a decomposition guessed from the shape of that identifier is worth less than an honest gap — it is a convention of the vendor's naming, not a field they promised, and it changes without notice. `ModelId` is the member that always holds.

`TaskKind` is a **String**, not an enumeration. The set of things models do is not closed, and an enumeration would date faster than the models it describes.

`LabelClasses` is an ordered array whose **index** is the contract. A consuming specification's class identifier refers to a position in it, so a Server **shall not** reorder it in place: a model whose class 3 silently becomes class 4 produces results that are wrong in a way nothing detects.

*Table - ModelType Definition* {#tbl-modeltype-definition defines=ModelType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:ModelType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:BaseObjectType defined in OPC 10000-5 |  |  |  |  |  |
| 0:HasProperty | Variable | 2:ModelId | 0:String | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:Name | 0:LocalizedText | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:Version | 0:String | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:Framework | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:Format | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:TaskKind | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:Digest | 0:ByteString | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:DigestAlgorithm | 0:String | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:ArtifactUri | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:ProvenanceUri | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:LabelClasses | 0:String[] | 0:PropertyType | O |
| 0:HasComponent | Variable | 2:Inputs | 2:TensorSignatureDataType[] | 0:BaseDataVariableType | O |
| 0:HasComponent | Variable | 2:Outputs | 2:TensorSignatureDataType[] | 0:BaseDataVariableType | O |
| 0:HasComponent | Object | 2:Card |  | 2:ModelCardType | O |
| 0:HasProperty | Variable | 2:Publisher | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:ParameterCount | 0:UInt64 | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:Quantization | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:SafetyPolicyUri | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:DigestProvenance | 2:DigestProvenanceEnum | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:PublishedAt | 0:UtcTime | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:LastModifiedAt | 0:UtcTime | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AiModelManagement |  |  |  |  |  |

#### Model identity {#sec-model-identity}

`Publisher` completes the `Publisher`, `Name`, `Version` triple by which every catalogue in practice identifies a model (§10.2). It is what makes the same model recognisable across two installations that fetched it from different mirrors — the digests will match, but only if someone already suspected the two were the same artefact, and the triple is what raises that suspicion.

`ProvenanceUri` is the hand-off point to whatever system governs approval. This model records *what is deployed and where it came from*; who signed it off, against which release criteria, under what retention policy, is the business of the organisation's governance system and deliberately not modelled here.

#### Cost and precision {#sec-cost-and-precision}

`ParameterCount` is a crude proxy for what a model will cost to run, and is the one such figure that is universally published.

`Quantization` names the numeric precision the artefact is stored in — `fp32`, `int8`, `fp8`. This is **not** a packaging detail. A quantized model is a different artefact that produces different answers, and treating it as a variant of the original is how a model evaluated at full precision ends up deployed at reduced precision without anyone re-measuring it. §11.3 requires the derivation to be stated as well.

`SafetyPolicyUri` names the policy applied to this model's output, where one is. Like every URI here it is untrusted input (§12.2).

`Card` reaches the `ModelCardType` of §11.1. The split is deliberate: the nameplate answers *which artefact is this*, the card answers *should this be running on my line*, and those are asked by different people at different times.

#### When the artefact appeared, and when it last moved {#sec-when-the-artefact-appeared-and-when-it-last-moved}

`PublishedAt` records when the source first published the model, and a Server **shall not** substitute its own acquisition time — a Server that did would make every model it serves appear to date from its last restart, and the value is only useful because it is the source's.

It answers for a model what `CreatedAt` (§6.3) already answers for a dataset, and the argument transfers unchanged: a model trained before a process change may no longer represent the line it runs on. It is also, for a source that publishes one opaque identifier and no decomposable version, frequently the only datum by which two models can be ordered at all.

`LastModifiedAt` records when the artefact behind the model last changed at the source, and exists for one case in particular. §9.3 defines `FollowsRef`, where the artefact **can** change with nothing else changing, and §12.3.1 requires repointing to be treated as an authorization-bearing act, pointing at `AiJobType.RequestedBy` for the record. But a reference that moves *at the source* produces no job, so there is no `RequestedBy` and no `StartedAt` — and without this member the audit trail §12.3.1 demands cannot be constructed on the one path that clause exists to cover. **A Server whose deployment follows a mutable reference shall populate `LastModifiedAt`.**

Neither is the Server's `SourceTimestamp`. That records when this Server acquired a value; after a restart and a re-read it says today for a model published two years ago.

`Inputs` and `Outputs` carry `TensorSignatureDataType` (`ns=2;i=3050`) — name, element type, shape with `-1` for a dynamic axis, and an optional layout hint. This is what lets a client check that what it intends to send matches what the model expects, before it sends it.

Clause 8 leaves the invocation payload opaque, so these signatures are the **only** machine-readable description of what a deployment will accept. A client that ignores them discovers a shape mismatch as a rejected call at run time; one that reads them discovers it at configuration time, which is the difference between a commissioning problem and a production one.

### `DatasetType` {#sec-datasettype}

`DatasetType` describes the samples a model was trained or validated on. It exists so that a question asked about a model's behaviour — why it fails on a particular part, whether it has ever seen a condition — can be answered by looking at what it learned from, rather than by inference from its outputs. Its member set is aligned with the IDTA 02058 AI Dataset submodel template.

It is read at two moments in practice: when a model is being reviewed for use, and when a model has failed in the field and someone is establishing whether the failure was foreseeable.

`SourceKind` (`DatasetSourceEnum`, `ns=2;i=3004`) is `Real` 0, `Synthetic` 1 or `Mixed` 2, and is **Mandatory**. It is the provenance a reviewer needs when synthetic data is involved, and the one question about a dataset that cannot be answered by looking at it. `Mixed` is not a hedge — synthetic pre-training followed by real fine-tuning is the common industrial arrangement, and forcing it into either neighbouring value would misdescribe it.

`SampleCount` and `CreatedAt` describe the scale and the vintage of the data, and both matter when a model is being judged: a classifier trained on four hundred samples and one trained on four million invite different amounts of trust, and a dataset assembled before a process change may no longer represent the line it is used on. `LabelClasses` names what the samples were labelled with. `ArtifactUri` says where the data itself can be obtained and `Digest` establishes that whatever is retrieved from there is the data this node describes — the same pairing, and the same reasoning, as on a model.

`LabelClasses` carries the same index-is-the-contract rule as `ModelType`. A dataset whose class list disagrees in **order** with the model trained on it is not detectably wrong anywhere — every identifier resolves, every count is plausible, and every label is off by one.

A dataset is a **sibling** of the model rather than a part of it. It outlives the models trained on it and is cited by several, which is why `TrainedOn` (§6.5) is a repeating reference and why the catalogue gives datasets their own resource type (§10.1).

*Table - DatasetType Definition* {#tbl-datasettype-definition defines=DatasetType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:DatasetType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:BaseObjectType defined in OPC 10000-5 |  |  |  |  |  |
| 0:HasProperty | Variable | 2:DatasetId | 0:String | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:Name | 0:LocalizedText | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:Version | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:SourceKind | 2:DatasetSourceEnum | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:SampleCount | 0:UInt64 | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:LabelClasses | 0:String[] | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:CreatedAt | 0:UtcTime | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:ArtifactUri | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:Digest | 0:ByteString | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AiModelManagement |  |  |  |  |  |

### `DeploymentType` {#sec-deploymenttype}

`DeploymentType` is a model made executable somewhere. Where `ModelType` describes an artefact, a deployment describes an arrangement for running it — on what hardware, at what location, under what latency expectation, with what happens when it cannot serve. One model may have several deployments and each names exactly one model (§6.5), which is what allows the same artefact to run at the edge and in a central service without the two being confused for one another.

It is the node a client actually interacts with: every Method in clause 8 hangs here, and every member clause 9 adds is about this arrangement rather than about the artefact. Its member set is aligned with the IDTA 02059 AI Deployment submodel template.

`InferenceLocation` (`InferenceLocationEnum`, `ns=2;i=3001`) is `OnServer` 0, `EdgeOffServer` 1, `Cloud` 2 or `InSimulator` 3, and is **Mandatory**.

> This property changes **where the computation happens and therefore the trust boundary**. It changes nothing else — not the result contract, not the model's identity, not what a client does with the output. A client that branches on it for any reason other than latency, availability or trust has misread it.

`AcceleratorKind` (`AcceleratorKindEnum`, `ns=2;i=3002`) states the class of device executing the model — `Cpu`, `Gpu`, `Npu`, `Fpga`, `Tpu` or `Other`. A client reads it to understand why two deployments of the same artefact do not perform alike, and an operator reads it when deciding where a newly imported model can reasonably be placed. `AcceleratorName` carries the specific part alongside it as free text, because an enumeration cannot keep pace with the accelerators that ship each year, and the part number is what a support engineer actually needs when a deployment behaves differently from an apparently identical one.

`LatencyBudget` states the latency this deployment is expected to meet. It is written when the deployment is commissioned, by whoever knows what the process requires, and read continuously thereafter by anything watching for regression. Its value is in the comparison rather than the number: without a declared expectation, a deployment that has become three times slower is indistinguishable from one that was always slow, and the degradation is noticed only when something downstream fails.

`BatchSize` reports the configured inference batch size, and exists mainly so that latency can be interpreted rather than merely measured. A large batch trades per-item latency for throughput deliberately, so a `LatencyBudget` breach on a batched deployment may mean nothing is wrong at all — a client that reads the budget without the batch size will raise alarms that have no fault behind them.

*Table - DeploymentType Definition* {#tbl-deploymenttype-definition defines=DeploymentType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:DeploymentType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:BaseObjectType defined in OPC 10000-5 |  |  |  |  |  |
| 0:HasProperty | Variable | 2:DeploymentId | 0:String | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:InferenceLocation | 2:InferenceLocationEnum | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:AcceleratorKind | 2:AcceleratorKindEnum | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:AcceleratorName | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:EndpointUri | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:LatencyBudget | 0:Duration | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:BatchSize | 0:UInt32 | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:State | 2:DeploymentStateEnum | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:Source | 0:NodeId | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:VersionBinding | 2:VersionBindingEnum | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:BoundRef | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:FallbackPolicy | 2:FallbackPolicyEnum | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:Reachability | 2:ReachabilityEnum | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:ConsecutiveFailures | 0:UInt32 | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:LastSuccessAt | 0:UtcTime | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:RateLimit | 2:RateLimitDataType | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:Capabilities | 2:CapabilityDataType[] | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:DataJurisdiction | 0:String | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:EgressPermitted | 0:Boolean | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:RetainsInput | 0:Boolean | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:EgressPolicyUri | 0:String | 0:PropertyType | O |
| 0:HasComponent | Method | 2:Invoke |  |  | O |
| 0:HasComponent | Method | 2:InvokeAsync |  |  | O |
| 0:HasComponent | Method | 2:GetCapabilities |  |  | O |
| 0:HasProperty | Variable | 2:MaxInlinePayloadSize | 0:UInt32 | 0:PropertyType | M |
| 0:HasComponent | Method | 2:BeginTransfer |  |  | O |
| 0:HasProperty | Variable | 2:ApiDialect | 2:ApiDialectEnum | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:EndpointDescriptionUri | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:RuntimeIdentity | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:ObservedLatency | 0:Duration | 0:PropertyType | O |
| 0:HasComponent | Object | 2:PromotionRecords |  | 0:FolderType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AiModelManagement |  |  |  |  |  |

#### Invoke {#sec-deploymenttype-invoke type=DeploymentType method=Invoke}

Run inference and return the result. The payload is opaque here: what goes in and comes out is the consuming specification's vocabulary, and an envelope that tried to type it would have to be extended for every domain. What this Method fixes is everything AROUND the payload - routing, parameters, accounting, why it stopped, and which model actually ran.

The signature does not change with InferenceLocation. A deployment served from the Server's own process and one served from a remote service are called identically; the location changes the trust boundary and the latency, and nothing else.

**Signature**

```text
Invoke (
  [in]  0:ByteString                 Payload,
  [in]  0:String                     PayloadUri,
  [in]  0:String                     ContentType,
  [in]  0:KeyValuePair[]             Parameters,
  [in]  0:Duration                   Timeout,
  [out] 0:ByteString                 ResponsePayload,
  [out] 0:String                     ResponseContentType,
  [out] 0:NodeId                     ModelUsed,
  [out] 2:UsageDataType              Usage,
  [out] 2:FinishReasonEnum           FinishReason,
  [out] 2:SafetyAssessmentDataType[] SafetyAssessment,
  [out] 0:Duration                   RetryAfter,
  [out] 0:Boolean                    TransferRequired,
  [out] 0:NodeId                     Transfer);
```

*Table - Invoke Method Arguments* {#tbl-invoke-method-arguments}

| **Argument** | **Description** |
| --- | --- |
| Payload | Request body. |
| PayloadUri | Location the request body is read from, where it is supplied by reference rather than carried. A Server SHALL accept exactly one of Payload and PayloadUri and SHALL reject a call supplying both or neither. Untrusted input subject to clause 12.2, and named data the execution site will read, so clause 9.5 applies to it. |
| ContentType | Media type of Payload. |
| Parameters | Call parameters such as a sampling temperature or an output length bound. A Server SHALL reject a parameter it does not support rather than ignore it: a caller whose parameter was silently dropped believes it took effect. |
| Timeout | How long the caller will wait. Zero means the Server's default. |
| ResponsePayload | Response body. |
| ResponseContentType | Media type of ResponsePayload. |
| ModelUsed | The model that ACTUALLY produced this response. Not necessarily the one the deployment names now: a fallback answered from a different deployment, and a FollowsRef binding may have moved. The provenance chain of clause 12 walks this. |
| Usage | What the call consumed. |
| FinishReason | Why output stopped. A caller that ignores this will accept a truncated answer as a complete one. |
| SafetyAssessment | Findings from the safety policy, if any applied. |
| RetryAfter | How long to wait before retrying, where the failure was a capacity one. Zero when retrying immediately is as good as waiting, and meaningless when the failure was not retryable. |
| TransferRequired | True when the deployment produced a response too large to return inline. ResponsePayload is then empty and the work is NOT lost - Transfer names where to read it. A client that ignores this reads an empty payload and concludes the model returned nothing. |
| Transfer | InferenceTransferType instance holding the response, where TransferRequired is true. Null otherwise. |

#### InvokeAsync {#sec-deploymenttype-invokeasync type=DeploymentType method=InvokeAsync}

Submit inference to be completed later, returning immediately with the job that will carry the result. For work that does not finish while a caller waits - a batch scored overnight, an analysis over recorded data.

**Signature**

```text
InvokeAsync (
  [in]  0:ByteString     Payload,
  [in]  0:String         PayloadUri,
  [in]  0:String         ContentType,
  [in]  0:KeyValuePair[] Parameters,
  [out] 0:NodeId         Job);
```

*Table - InvokeAsync Method Arguments* {#tbl-invokeasync-method-arguments}

| **Argument** | **Description** |
| --- | --- |
| Payload | Request body. |
| PayloadUri | Location the request body is read from, where it is supplied by reference rather than carried. Exactly one of Payload and PayloadUri on the same terms as Invoke. This is the argument that lets a batch already sitting in the plant's object store be scored without being copied through the Session first. |
| ContentType | Media type of Payload. |
| Parameters | Call parameters. |
| Job | InferenceJobType instance tracking the request. The caller subscribes to it rather than polling. |

#### GetCapabilities {#sec-deploymenttype-getcapabilities type=DeploymentType method=GetCapabilities}

Report what this deployment can do, refreshed from the execution site rather than from cache. Defined because a remote endpoint's capabilities change without anything in this address space changing.

**Signature**

```text
GetCapabilities (
  [out] 2:CapabilityDataType[] Capabilities);
```

*Table - GetCapabilities Method Arguments* {#tbl-getcapabilities-method-arguments}

| **Argument** | **Description** |
| --- | --- |
| Capabilities | Current capabilities. |

#### BeginTransfer {#sec-deploymenttype-begintransfer type=DeploymentType method=BeginTransfer}

Opens a chunked exchange for a payload that will not fit inline, returning the InferenceTransferType instance to write into. This is the general path: Invoke is the shortcut that happens to work when everything is small.

**Signature**

```text
BeginTransfer (
  [in]  0:String  ContentType,
  [in]  0:UInt64  RequestSize,
  [out] 0:NodeId  Transfer,
  [out] 0:Boolean Accepted);
```

*Table - BeginTransfer Method Arguments* {#tbl-begintransfer-method-arguments}

| **Argument** | **Description** |
| --- | --- |
| ContentType | Media type of the request body. |
| RequestSize | Expected request size in bytes, or 0 when not known in advance. A Server that cannot accommodate the stated size refuses here rather than after the client has uploaded it. |
| Transfer | InferenceTransferType instance to write the request into. |
| Accepted | False when the Server declined to open the exchange. |

#### Operational members {#sec-operational-members}

The members described so far establish what a deployment *is*. Using one draws on members that later clauses add, and it is worth seeing them together, because a client assembling a call reads across all four groups rather than working clause by clause.

`Invoke`, `InvokeAsync` and `GetCapabilities`, with the `Capabilities` list beside them, are what a client calls and what it reads before calling. They are added by clause 8. A client that intends to use a typed profile consults `Capabilities` at configuration time; one that only ever sends an opaque payload can call `Invoke` without reading anything else.

`Source`, `VersionBinding` and `BoundRef` describe where execution happens and whether the artefact behind it can change without notice. Clauses 8.2 and 8.3 define them. These are read once when a deployment is commissioned and again whenever an audit asks what was running at a given time, since a `FollowsRef` binding means the answer can differ between two moments with nothing else having changed.

`FallbackPolicy`, `Reachability`, `ConsecutiveFailures`, `LastSuccessAt` and `RateLimit` describe whether the deployment is currently able to serve and what happens when it is not. Clause 9.4 defines them. A supervisory client subscribes to these rather than polling them, because the moment they change is precisely the moment it needs to act.

`DataJurisdiction`, `EgressPermitted`, `RetainsInput` and `EgressPolicyUri` state where input data goes. Clause 9.5 defines them. They are read by whoever approves a deployment rather than by whoever calls it, and they are stated on the deployment rather than the model because the same model deployed twice can answer differently.

`ApiDialect`, `EndpointDescriptionUri` and `RuntimeIdentity` describe the contract a caller must satisfy and what is currently behind it. §9.2 and §9.3 define them, and unlike the four groups above they are read *before the first call ever succeeds*, because a client that does not know what shape its `Payload` should take cannot make one.

#### What a caller must send {#sec-what-a-caller-must-send}

`Invoke` takes an opaque `ByteString`, and §8.2 argues at length for keeping it opaque. That argument is about the payload's **contents**, and it leaves a question it does not answer: a client browsing an unfamiliar deployment can see that `Invoke` exists and has no way to learn whether the bytes should be a chat-completions request body, an inference protocol body, or something a vendor documents elsewhere.

For a tensor deployment `Inputs` and `Outputs` answer it, which is why §6.2 calls them the only machine-readable description of what a deployment accepts. For every deployment whose contract is a JSON request body rather than a tensor set, they are empty and nothing answers it at all.

`ApiDialect` (`ApiDialectEnum`, `ns=2;i=3007`) does, naming **which** contract the opaque bytes are expected to satisfy without typing what is in them. `EndpointDescriptionUri` says where that contract is documented, and is untrusted input under §12.2.

**A Server shall populate `ApiDialect` on every deployment whose payload contract is not described by `Inputs` and `Outputs`**, and **should** populate `EndpointDescriptionUri` wherever `ApiDialect` is `Proprietary` — which is the same *should* §9.2 applies to a source, for the same reason: `Proprietary` with no description names nothing.

This is the same enumeration §9.2 uses, and deliberately so. A deployment that federates a remote endpoint generally passes the payload through, so the contract a client sends to this Server and the contract this Server speaks onward are the same one, and giving them two vocabularies would invite them to disagree. Where they genuinely differ — a Server that translates — the deployment states what **it** accepts, because that is the one a caller has to satisfy.

#### Deployment state {#sec-deployment-state}

`State` (`DeploymentStateEnum`, `ns=2;i=3003`) reports the deployment as this Server holds it: `Inactive` when it is declared but not serving, `Ready` when it can serve and has no work in progress, `Active` while it is serving, `Degraded` when it is serving below the quality it was configured for, and `Faulted` when it cannot serve at all.

It is **Mandatory** because availability decisions rest on it. A consuming specification deciding whether to route work to a deployment reads `State` and nothing else, and the learning loop of clause 7 uses it to establish whether a promoted model is actually in service. A member that carried those decisions while being omissible would leave a conformant Server unable to answer the question its clients most often ask.

`Degraded` earns its place between `Active` and `Faulted`. A deployment that is answering but missing its `LatencyBudget`, or falling back to a slower accelerator, is neither healthy nor broken, and collapsing it into either neighbour would either hide a developing fault or stop a line that is still producing usable results.

That comparison needs a published input, and `ObservedLatency` is it: the most recent inference latency this Server measured. `LatencyBudget` states what the deployment is *expected* to meet and is set by whoever commissioned it; `ObservedLatency` states what it *did*. **A Server that reports `Degraded` on latency grounds shall populate `ObservedLatency`**, so the state it publishes can be checked against the numbers it publishes rather than being taken on trust.

Without it the rule above would be untestable — a Server could report `Degraded`, or fail to, and nothing a client could read would distinguish a correct implementation from an incorrect one. A normative statement that cannot be observed to be satisfied or violated is not a requirement.

A client is not obliged to use it. End-to-end latency is measurable from the calling side, and a client that measures its own sees the transport as well. What `ObservedLatency` adds is the Server's own view of the execution site, which is the half a caller cannot separate out — and against a federated deployment it is the only view of the remote leg that exists.

Where a deployment executes somewhere this Server does not control, `State` is not the whole picture — a correctly configured deployment can be unable to reach its execution site. Clause 9 adds `Reachability` for that, and §9.4 sets out how the two combine.

### `UsesModel` and `TrainedOn` {#sec-usesmodel-and-trainedon}

A `DeploymentType` instance **shall** have **exactly one** `UsesModel` reference, and its target **shall** be a `ModelType` instance.

This is the defined path from a running deployment to the model it is configured to serve now. Zero references leaves the deployment's current model unknown; more than one makes that current configuration ambiguous. It is not a historical record: a client asking which model produced a retained result follows the invocation-time `ModelUsed` identity instead (§8.2.1 and §12.1).

`TrainedOn` links a model to a dataset it was trained or validated on. It is optional and may repeat: a model whose training data cannot be named is a model whose behaviour cannot be explained, but not every installation holds that information.

#### Promotion history {#sec-promotion-history}

`PromotionRecordType` (`ns=2;i=1019`) is the authoritative audit record of one successful substitution of a deployment's configured `UsesModel` target. A deployment has an Optional `PromotionRecords` folder containing `PromotionRecordType` instances. The folder is **conditionally required wherever the configured `UsesModel` target can change**, whether by `PromoteModel`, rollback, an automatic administrative policy, or a followed mutable reference. A deployment whose configured target is fixed for its lifetime may omit it.

Each record is immutable and read-only after creation. `RecordId` is unique across the Server. `Deployment` is the deployment's convenience NodeId and `DeploymentId` is its snapshotted identifier. `PreviousModel` and `NewModel` are Mandatory convenience NodeIds; clients **shall not** depend on those nodes remaining present or resolvable. `PreviousModelIdentity` and `NewModelIdentity` are Mandatory `ModelIdentitySnapshotDataType` (`ns=2;i=3057`) values containing `ModelId`, `Version`, `Digest`, `DigestAlgorithm` and `DigestProvenance` as they stood when the change took effect. Those snapshots are self-contained and remain authoritative after either model node or its artefact location disappears.

`DigestProvenance` is part of the identity snapshot because digest bytes without their evidence class are ambiguous. A retained digest declared by a source does not become one computed by this Server merely because the source node disappeared, and a digest verified during staging must not lose that stronger fact. Snapshotting `DigestProvenanceEnum` preserves the trust conclusion of §12.1.1 together with the value it qualifies.

`EvaluationRun` optionally names the gating run. Where it is populated, `EvaluationRunId` **shall** contain the run's `RunId` snapshot; it remains meaningful if the run node is later removed. `ChangedAt`, `ChangedBy` and `ChangeKind` are Mandatory. `ChangedBy` is the authenticated principal that authorized or initiated the action; for an automatic substitution it is the Server's stable system identity. `Reason` is Optional and for a human.

`ModelChangeKindEnum` (`ns=2;i=3016`) classifies the **trigger**, never the apparent ordering of version strings:

| Value | Trigger |
|---|---|
| `Promotion` | An approved candidate replaced the serving model |
| `Rollback` | An operator or policy restored a previously used model |
| `AutomaticSubstitution` | The Server automatically changed the configured `UsesModel` target |
| `MutableReferenceRepoint` | A followed mutable reference resolved to another model |
| `OtherAdministrativeReplacement` | Another administrative action replaced the configured model |

Versions are opaque strings and need not be sortable; a change is not a rollback merely because one version compares lower than another. Implementations **shall** classify by the action that caused the substitution.

The Server **shall create and expose the record atomically with the successful `UsesModel` substitution**. A client shall not be able to observe the new reference without its record, or a record for a substitution that did not take effect. Failed or rejected changes create no successful record. The complete history for a deployment **shall** be retained for at least that deployment's lifetime.

A per-invocation `FallBackTo` response does not change the configured `UsesModel` target. It is represented by the invocation's `ModelUsed` and **shall not** create a promotion record. `AutomaticSubstitution` applies only where the Server actually changes `UsesModel`; it is not a synonym for request routing.

### `AiJobType` {#sec-aijobtype}

Every long-running operation in this model — learning, importing a model, inference that does not return while the caller waits — derives from `AiJobType`, which derives from the OPC 10000-10 `ProgramStateMachineType`.

That base supplies the lifecycle (`Ready`, `Running`, `Suspended`, `Halted`), the transition events, and the `Start`, `Suspend`, `Resume` and `Halt` Methods. None of it is redefined here. A hand-rolled state variable would have had to reinvent the transition events to be observable, and would have been observable *differently* from every other program in a Server.

`AiJobType` adds `JobId`, `LastError`, `StartedAt`, `FinishedAt`, `Progress` and `RequestedBy`.

`Progress` is a fraction from 0.0 to 1.0. A Server **shall not** report a value it is guessing: null is informative, a fabricated 0.5 is not, and a progress bar that is wrong is worse than one that is absent because it is acted on.

`RequestedBy` records the identity that started the job, at the moment it started. §12.3 requires it for any job that can promote a model — an authorization check that leaves no record answers "was this allowed" but not "who did it".

**The lifecycle and the phase are different questions.** `LearningJobType.State` says what stage the loop is in; the inherited `CurrentState` says whether the program is running. A Server **shall** keep them consistent: a job whose `State` is `Failed` **shall not** report a `CurrentState` of `Running`.

Annex A is the authoritative node reference and carries every member with its DataType, ValueRank and ModellingRule.

---

*Table - AiJobType Definition* {#tbl-aijobtype-definition defines=AiJobType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AiJobType |  |  |  |  |
| IsAbstract | True |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:ProgramStateMachineType defined in [](#ref-uapart5) |  |  |  |  |  |
| 0:HasProperty | Variable | 2:JobId | 0:String | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:LastError | 0:LocalizedText | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:StartedAt | 0:UtcTime | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:FinishedAt | 0:UtcTime | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:Progress | 0:Double | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:RequestedBy | 0:String | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AiModelManagement |  |  |  |  |  |

## The learning loop (normative) {#sec-the-learning-loop-normative}

`LearningJobType` exists so that corrections arriving from a consuming application have somewhere to accumulate and a defined path into a new model version.

```{figure}
id: fig-aim-loop
caption: States of the learning loop
source: figures/AiModelManagement-Fig10-Loop.png
```

`LearningJobStateEnum` (`ns=2;i=3005`) carries exactly these eight states.

| From | Trigger | To |
|---|---|---|
| `Idle` | `StartCollection` | `Collecting` |
| `Collecting` | `StopCollection` | `Labelling` |
| `Collecting`, `Labelling` | `TriggerTraining` accepted | `Training` |
| `Training` | Server: training finished | `Validating` |
| `Validating` | Server: candidate met acceptance criteria | `Ready` |
| `Validating` | Server: candidate rejected | `Failed` |
| `Ready` | `PromoteModel` | `Promoted` |
| `Promoted`, `Failed` | `StartCollection` | `Collecting` |
| `Training`, `Validating` | Server: error | `Failed` |

Transitions marked *Server* are driven by the Server or its training backend; the rest are Method-driven. A Server **shall not** perform a transition that is not in this table, **shall** populate `LastError` on entry to `Failed`, and **shall** have `CandidateModel` non-null on entry to `Ready` — a `Ready` job with nothing to promote cannot be acted on.

`Promoted` and `Failed` both return to `Collecting`, which is what makes this a loop rather than a one-shot. A job that promoted a model last month is the same job that starts gathering evidence for the next one.

### Method behaviour and StatusCodes (normative) {#sec-method-behaviour-and-statuscodes-normative}

`StartCollection` and `StopCollection` are **idempotent**: calling either in the state it would move to is `Good` and changes nothing. Retrying after a lost response is otherwise indistinguishable from a second request.

`TriggerTraining` returns `Accepted`. It returns `Accepted = false` **with `Good`** where the request was valid but the Server queued nothing — an external training system declined it, for instance — and `LastError` **shall** then carry the reason. This is not an error: the request was understood and refused, and a Bad StatusCode would tell a caller to retry something that will be refused again.

`PromoteModel` takes a `Deployment` or null. **Null means every deployment fed by this job**, and a Server **shall** promote to all of them or to none. `PromotedModel` returns the model now in use, which is the same node in either case because it identifies the model rather than the deployment; a caller needing to know which deployments changed browses their `UsesModel` references afterwards.

| StatusCode | Condition |
|---|---|
| `Bad_InvalidState` | `StartCollection` when `State` is not `Idle`, `Collecting`, `Promoted` or `Failed`; `TriggerTraining` when `State` is not `Collecting` or `Labelling`; `PromoteModel` when `State` is not `Ready` |
| `Bad_NothingToDo` | `TriggerTraining` when `SamplesCollected` is 0 |
| `Bad_NotFound` | `PromoteModel` when `Deployment` is non-null and does not resolve, or when `CandidateModel` is null |
| `Bad_UserAccessDenied` | The caller is not authorized; `PromoteModel` requires the distinct authorization of §12.3 |

**A Server may implement only part of this.** A Server that captures corrections and leaves training to an external MLOps system implements `StartCollection` and `StopCollection`, drives the state to `Labelling`, and stops. The state machine is the same either way, and a client reads `State` to learn how far this Server goes rather than inferring it from which Methods exist.

`SamplesCollected` counts what has accumulated, including corrections fed back. `LastError` is the diagnostic for `Failed`, is for a human, and **shall not** be parsed.

**Promotion is the operation that matters.** `PromoteModel` makes the candidate the model deployments use — it changes what the equipment does without changing anything a reader of the address space would notice, which is exactly the change that needs a separate permission (§12.3).

A null `Deployment` argument means *every* deployment fed by this job. A Server **shall** promote to all of them or to none: a partial promotion leaves two lines judging the same parts by different models, which is a fault that shows up as an inexplicable disagreement between stations rather than as an error anywhere.

### Relationship to models and deployments {#sec-relationship-to-models-and-deployments}

The loop is the **producing** half of this specification; clauses 8 to 9 are the consuming half, and three joins connect them.

`BaseModel` and `CandidateModel` are `ModelType` instances like any other, so a candidate carries the same `Digest`, the same `Card` and the same lineage obligations as a model that arrived from a catalogue. A model that a Server trained is not privileged over one it imported — §11.3 requires the candidate to state `DerivedFrom` the base it started from, for the same reason a quantized model must.

Promotion **should** be gated on an `EvaluationRunType` (§11.2) whose `Passed` is true. This specification does not require it, because a Server that captures corrections and hands training to an external system may legitimately never see an evaluation — but a Server that promotes without one has no recorded answer to *why was this allowed*, and the question is asked after failures rather than before them.

Where the promoted model backs a deployment whose `VersionBinding` is `FollowsRef` (§9.3), promotion and repointing are two routes to the same outcome. §12.3.1 requires both to be authorized alike.

### Partial implementation {#sec-partial-implementation}

The state machine describes the whole loop; almost no Server implements the whole loop.

A Server that only captures corrections implements `StartCollection` and `StopCollection`, drives `State` to `Labelling`, and stops. One that also promotes but trains elsewhere implements `PromoteModel` and lets `Training` and `Validating` be driven by its MLOps backend. Both are conformant to **AI-Learning** provided the transitions they *do* perform are the ones in §7.

This is why `State` is read rather than inferred from which Methods exist. A client that probed for Methods would learn what a Server can be asked to do; reading `State` tells it how far this job actually got, which is the question it has.

### Events (normative) {#sec-events-normative}

`ModelPromotedEventType` is raised when a deployment's configured `UsesModel` target is successfully substituted.

A client can already subscribe to a deployment's `UsesModel` reference and see that it changed. What it cannot see that way is *who* changed it, *which* evaluation justified it, or *what it was before* — and those are precisely the questions asked after a batch has been rejected and someone wants to know what decided it. This event carries them at the moment they are known, rather than leaving them to be reconstructed from whatever logging the Server happens to keep.

| Member | Type | Rule | Meaning |
|---|---|---|---|
| `Deployment` | NodeId | M | The deployment whose model changed |
| `NewModel` | NodeId | M | The `ModelType` now being served |
| `PreviousModel` | NodeId | O | What it was serving, or null where it served none |
| `EvaluationRun` | NodeId | O | The `EvaluationRunType` that gated the promotion, or null |
| `PromotedBy` | String | O | The authenticated identity that authorized or initiated the change; the Server's stable system identity for an automatic substitution |
| `PromotionRecord` | NodeId | O | The authoritative `PromotionRecordType` created with the substitution |

**It is raised on every configured substitution, not only on `PromoteModel`.** A rollback, automatic change of `UsesModel`, mutable-reference repoint, and any other administrative substitution raise it too. A per-invocation fallback that leaves `UsesModel` unchanged does not: `ModelUsed` records that invocation-time choice. `ChangeKind` on the record identifies why the configured target changed; clients shall not infer promotion or rollback by ordering `PreviousModel.Version` and `NewModel.Version`.

**`PromotedBy` exists because `BaseEventType` has no user field.** §12.3 requires promotion to carry an authorization distinct from every other Method on the job, and that requirement is unobservable if the identity that exercised it is not recorded where the act is. A Server **shall** populate it with the principal as it authenticated them, and **shall not** populate it with a service account standing in for a human operator where the human is known. An automatic substitution uses the Server's stable system identity and agrees with the record's `ChangedBy`.

**A null `EvaluationRun` is information, not an omission.** §7.2 says promotion **should** be gated on an `EvaluationRunType` whose `Passed` is true. Where it was not, null here is the observable consequence — which is the fact an audit is looking for, and the reason the field is not simply left off when unused.

**The record is authoritative.** `PromotionRecord` is Optional in the type for compatibility, but a Server claiming **AI-Events shall populate it on every event**. The record is created in the same atomic operation as the successful `UsesModel` substitution; the event is raised only after that operation succeeds. `Deployment`, `PreviousModel`, `NewModel`, `EvaluationRun` and `PromotedBy` remain event fields so existing filters work, and wherever populated they **shall agree** with the corresponding record fields. Failed substitutions produce neither a successful record nor a promotion event.

**Where it is raised.** The well-known `AiModelManagement` object declares `EventNotifier` with the `SubscribeToEvents` bit set and is the target of a `HasNotifier` reference from the Server object, so a client subscribes at either. `SourceNode` **shall** be the `DeploymentType` instance named by `Deployment`. `Severity` **should** be 500 or above: a promotion changes what every downstream verdict means, and a client filtering for things that matter should not have to know this event's name to find it.

**Degradation is a state, and is already modelled as one.** This clause defines no Condition or Alarm type. A deployment that has become unreachable or slow is in a *state* that persists, and `DeploymentType.Reachability`, `State` and `ObservedLatency` already carry it as Variables a client subscribes to — which is what OPC UA models a persistent state with. A Server that additionally needs an operator to *acknowledge* such a state uses the base OPC UA alarm types of OPC 10000-9 with `AlarmConditionType.InputNode` pointing at the `Reachability` Variable; that is what `InputNode` is for, and defining a Condition subtype here would oblige every Server to implement the enable, acknowledge, confirm and shelving machinery in order to report that a network link went away.

---

## Inference (normative) {#sec-inference-normative}

### Location independence {#sec-location-independence}

`DeploymentType.Invoke` runs inference and returns the result, and **one call serves wherever the model runs**.

**Its signature does not change with `InferenceLocation`.** A model executing in the Server's own process and one executing in a remote service are called identically — same Method, same arguments, same outputs, same meanings. This is the single most important property in this clause, and it is not an aspiration: serving runtimes that run on a workstation and the hosted services they mirror already expose the same contract, differing only in where the request is addressed and how it is authenticated. A specification that made the call shape depend on the location would be describing an accident of deployment as though it were a property of the model.

What the location *does* change is the trust boundary, the latency and what fails when the network does. Those are clause 9's subject.

### Payload and envelope {#sec-payload-and-envelope}

`Payload` is a `ByteString` and `ContentType` is its media type. This specification does not say what is inside.

That is not vagueness, it is the boundary. What goes into a model and what comes out is domain vocabulary — an image and a set of detections, a spectrum and a fault class, a maintenance history and a remaining-life estimate. An envelope that tried to type it would have to be extended by every domain that ever adopted this model, and the first domain to need something unforeseen would have to fork it.

What this specification *does* fix is everything around the payload, because none of it is domain-specific and all of it is got wrong when left to each implementer:

| Output | Why it is in the envelope |
|---|---|
| `ModelUsed` | Which model **actually** answered |
| `Usage` | What the call consumed |
| `FinishReason` | Whether the answer is complete |
| `SafetyAssessment` | Whether anything was withheld |
| `RetryAfter` | Whether, and when, to try again |

```{figure}
id: fig-aim-envelope
caption: Request and response envelope
source: figures/AiModelManagement-Fig11-Envelope.png
```

#### `ModelUsed` {#sec-modelused}

A Server **shall** return the model that actually produced the response, which is **not** necessarily the one the deployment names at the time the client looks.

Two mechanisms defined here can move it between the call and the read: a fallback (§9.4) answers from a different deployment entirely, and a `FollowsRef` binding (§9.3) can be repointed at a new version. In both cases the deployment's current model is the *wrong* answer to "what produced this result", and it is wrong in the direction that matters — it names a model that looks plausible.

The provenance chain of §12.1 therefore walks `ModelUsed`, not the deployment.

A consuming specification that persists an inference result **shall** retain this value with the result when historical model identity is part of its contract. *OPC UA for Vision Systems* does so as `VisionResultType.ModelUsed`: its result-to-model path has the same meaning as this Method output and as `InferenceJobType.ModelUsed`.

#### `FinishReason` {#sec-finishreason}

A truncated answer is not a complete one, and nothing else in the response says which it is.

`FinishReason` (`FinishReasonEnum`, `ns=2;i=3006`) is `Stop`, `Length`, `ToolCall`, `Filtered`, `Cancelled` or `Error`.

Only `Stop` means the model finished saying what it had to say. `Length` means output hit a budget and **the result is incomplete**; `Filtered` means a safety policy withheld it; `ToolCall` means the model is waiting for something the caller must supply; `Cancelled` and `Error` speak for themselves.

A client that branches only on the StatusCode will accept a `Length` response as final, because nothing failed. A Server **shall** populate `FinishReason` on every response, including successful ones, so that the distinction is available without inference.

#### `Usage` {#sec-usage}

Accounting is deliberately not expressed in tokens.

`UsageDataType` (`ns=2;i=3052`) carries `UnitKind`, `InputUnits`, `OutputUnits` and `TotalUnits`.

The counts are deliberately **not** named tokens. A token is one accounting unit among several: a model that consumes images, audio seconds or sensor samples meters the same thing in a different unit, and a field called `InputTokens` on such a deployment is either empty or lying. `UnitKind` names the unit — `tokens`, `images`, `samples`, `seconds` — and the three counts are in it.

`TotalUnits` is **not** required to be the sum of the other two. Caching, deduplication and shared prefixes mean the metered total legitimately differs from the arithmetic one, and a client that recomputes it will disagree with the bill.

**Not every execution site meters at all.** A tensor predict contract returns output tensors and nothing that could be counted, and an in-process runtime returns what the library returns. A Server that supplied a count on such a site's behalf would be publishing a measurement it did not take.

An **empty `UnitKind` means the call was not metered**. Where `UnitKind` is empty a Server **shall** set `InputUnits`, `OutputUnits` and `TotalUnits` to zero, and a client **shall not** read those zeros as measured quantities. A Server **shall not** report a non-empty `UnitKind` alongside counts it did not obtain from the execution site.

The sentinel is the empty unit rather than a zero count because the counts cannot carry it: they are `UInt64`, so a Server with nothing to report and one that metered nothing would otherwise encode identically. Naming the unit is what makes the difference between *no measurement* and *a measurement of none* legible, and that difference is the whole of what a client reading `Usage` is entitled to know.

#### Payload size, and why `Invoke` is not the general case {#sec-payload-size-and-why-invoke-is-not-the-general-case}

`Payload` is a `ByteString`, and a `ByteString` is bounded three times over: by the Server's `MaxByteStringLength`, by the channel's negotiated `MaxMessageSize`, and by the Session's `MaxResponseMessageSize`. **This model does not get to choose any of them.** An image, a point cloud or a window of high-rate samples exceeds them routinely, and a call that cannot carry its input is not a call.

So `Invoke` is the **shortcut**, not the general path. `BeginTransfer` is the general path.

**`MaxInlinePayloadSize` is Mandatory on every deployment** and states the largest request or response it will carry inline. A client reads it *before* calling rather than discovering the bound from a rejection, which matters because the three limits above are not all visible to a client — a Server **shall not** publish a value larger than the smallest of them permits. Zero means the deployment accepts nothing inline and `BeginTransfer` is the only way in.

**A client that does not know its payload sizes in advance should use the transfer path from the outset.** Nothing is lost by doing so: the transfer path carries the same envelope and answers the same questions, and a client that starts there never has to discover mid-deployment that a payload has outgrown the shortcut.

##### The exchange {#sec-the-exchange}

`InferenceTransferType` (`ns=2;i=1017`) carries one exchange. `Request` and `Response` are Part 5 **`FileType`** objects, so the client opens the request, writes it in chunks of its own choosing, and closes it; after `Execute`, the response is read the same way.

Nothing here invents a transfer protocol. OPC UA already has one, every client already implements it, and a bespoke chunking scheme would be a second thing to get wrong.

```{figure}
id: fig-aim-exchange
caption: Transferring a payload with the Part 5 FileType methods
source: figures/AiModelManagement-Fig12-Exchange.png
```

`TransferId` names the exchange, and is Mandatory for the same reason every other identifier here is: a client holding several concurrent exchanges needs to say which one it means in a log or a support call, and the NodeId alone is not something a human carries around.

`State` (`TransferStateEnum`, `ns=2;i=3014`) is `Building`, `Ready`, `Executing`, `Completed`, `Failed` or `Expired`. A client reads it rather than inferring progress from which Methods have succeeded, because a transfer that failed mid-write and one that was never started look alike from outside.

`ExpiresAt` is when the Server may reclaim an exchange that has not completed. A client that abandons one would otherwise hold Server resources until its Session ends, and a Server that never reclaimed them would be one denial of service away from unusable. `Abort` releases an exchange early, and a client that has stopped caring about a response **should** call it rather than waiting out the expiry.

##### When the *answer* is too large {#sec-when-the-answer-is-too-large}

The awkward case is not a large request — the client knows its own input size. It is a request that fits and produces a response that does not.

`Invoke` therefore returns **`TransferRequired`** and **`Transfer`**. Where `TransferRequired` is true, `ResponsePayload` is empty and **the work is not lost**: inference ran, and `Transfer` names the exchange to read the response from.

A Server **shall not** fail such a call. Failing it would discard work that has already been done and, worse, would tell the caller nothing about why — a client would see an empty payload and conclude the model returned nothing, which is a different and wrong answer.

##### Streaming {#sec-streaming}

Where output is produced progressively rather than merely being large, §8.5 applies instead: the Server publishes it through a Subscription, and **AI-Stream** optionally carries it over a data channel. The distinction is whether the client wants the answer *as it forms* — a transfer delivers one complete response, however big.

### Parameters {#sec-parameters}

An ignored parameter is worse than a rejected one, which is the whole of the rule below.

`Parameters` is an array of `KeyValuePair`, carrying whatever the deployment accepts — a sampling temperature, an output-length bound, a decoding seed.

A Server **shall** reject a parameter it does not support, and **shall not** ignore it.

This is the one rule in the clause that costs implementers something, and it is worth the cost. A caller that sets a determinism seed and has it silently dropped believes its results are reproducible when they are not. A caller whose safety-relevant bound is discarded believes a limit is in force. Silent acceptance converts a caller's explicit instruction into a false belief, and there is no later point at which the caller can discover it.

### Capabilities {#sec-capabilities}

Capabilities are asked for, never assumed from the kind of model behind a deployment.

`Capabilities` (`CapabilityDataType`, `ns=2;i=3053`) is a list of names with a supported flag — `chat`, `embeddings`, `streaming`, `tool-call`, `structured-output` and whatever else a deployment offers.

It is an **open list of strings, not an enumeration**, for the same reason `TaskKind` is: the set of things models can do is not closed, and an enumeration frozen at publication would be the first part of this specification to date. A client that meets a capability name it does not recognise is in exactly the position of one that meets an enumeration value added after it shipped, and no worse.

`GetCapabilities` re-reads them from the execution site. It exists because a remote endpoint's capabilities change without anything in this address space changing — the cached list on the deployment can be stale in a way nothing else here can.

### Incremental results {#sec-incremental-results}

Where a deployment produces output progressively, a Server **shall** publish it by updating a Variable that a client subscribes to. There is no streaming Method: OPC UA already has the mechanism, and a Method that returned repeatedly would be a second one.

Where the payload is large or the rate is high enough that Subscription overhead dominates, a Server **may** additionally offer the stream over a data channel; that is the **AI-Stream** facet (§13.2) and it is entirely optional. A Server that implements neither answers only through `Invoke`, and is fully conformant.

### Asynchronous inference {#sec-asynchronous-inference}

`InvokeAsync` submits a request and returns immediately with the `InferenceJobType` (`ns=2;i=1008`) instance that will carry the result. The client subscribes to that job rather than polling it.

This is not a convenience. A batch scored overnight and an analysis over months of recorded data are ordinary industrial requests, and modelling them as a Method that blocks for hours would hold a Session open for the duration and lose the work if it dropped. `InferenceJobType` derives from `AiJobType` (§6.6), so it is observed exactly like every other long-running operation here.

```{figure}
id: fig-aim-deferred
caption: Placing, polling and collecting an asynchronous inference
source: figures/AiModelManagement-Fig13-Deferred.png
```

`InferenceJobType` carries `RequestPayload` and `RequestContentType`, `ResponsePayload` and `ResponseContentType`, and the same `ModelUsed`, `Usage`, `FinishReason` and `SafetyAssessment` that `Invoke` returns — the asynchronous path answers the same questions as the synchronous one, which is what makes it a path and not a different feature.

That parity has to extend to size, and §8.6.1 is where it does. The jobs this clause exists for are the ones most likely to produce a result that will not fit in a call, so an asynchronous path bounded by the limits §8.2.4 says this model does not choose would be a path that fails exactly where it was needed.

#### A payload too large to carry, or already somewhere else {#sec-a-payload-too-large-to-carry-or-already-somewhere-else}

Two different problems, and the model answers them separately because they have different remedies.

**A result too large to return inline** is the problem `Invoke` solves with `TransferRequired` and `Transfer`, and `InferenceJobType` carries the same pair on the same terms: `TransferRequired` true means `ResponsePayload` is empty, the work is **not** lost, and `Transfer` names the `InferenceTransferType` to read it from. `MaxInlinePayloadSize` bounds both paths — it is a property of the deployment, not of the Method that happened to be called.

**Data that never needed to move** is a different problem. A batch already sitting in the plant's object store, or a result the execution site writes to storage of its own, is not made smaller by chunking; carrying it through the Session copies it twice for no benefit and makes the Session the bottleneck for both copies.

So `Invoke` and `InvokeAsync` both take a `PayloadUri`, and a Server **shall** accept exactly one of `Payload` and `PayloadUri` and **shall** reject a call supplying both or neither — the same exactly-one rule §10.2 applies to `Source` and `Registry`, for the same reason: two ways of saying where the input is, and a call that used both would not say which one was read. `InferenceJobType.RequestUri` records what was actually submitted, and `ResponseUri` names where the execution site wrote the result when it returns a location rather than bytes.

This is the model's existing idiom rather than a new one. §1.2 already says this specification does not carry artefacts — `ArtifactUri` says where the bytes are — and §10.3's `Federate` mode is the same choice made about a model instead of a payload.

Two obligations come with it, both inherited rather than invented. A `PayloadUri`, `RequestUri` or `ResponseUri` is **untrusted input** under §12.2 and subject to the same resolver policy as every other URI here. And it is an **egress question** under §9.5: a location the execution site reads is a location the input data reaches, so a deployment whose `EgressPermitted` is false **shall not** accept a `PayloadUri` naming somewhere outside the operator's boundary. A URI is a quieter way to move data than a payload, which is exactly why it needs saying.

---

## Consuming a model hosted elsewhere (normative) {#sec-consuming-a-model-hosted-elsewhere-normative}

### `ModelSourceType` {#sec-modelsourcetype}

A URI says where to send bytes and nothing else that calling a remote model requires.

A deployment whose `InferenceLocation` is not `OnServer` executes somewhere the Server must reach over a network. Naming that place is necessary and nowhere near sufficient: a Server holding only a URI knows where to send bytes and nothing about what shape they should take, how to prove it is entitled to send them, what the far end can do, or what to do when it stops answering.

`ModelSourceType` (`ns=2;i=1009`) carries the rest. A deployment names one through its `Source` Property.

| Member | The question it answers |
|---|---|
| `EndpointUri` | Where |
| `ApiDialect` | In what shape |
| `AuthenticationKind`, `CredentialReference`, `TokenAudience` | With what proof of entitlement |
| `Capabilities` | Able to do what |
| `Reachability`, `LastSuccessAt`, `ConsecutiveFailures`, `RateLimit` | Answering, or not |

`SourceId` names the source, and is Mandatory for the same reason every other identifier here is: a source that cannot be named cannot be referred to by the deployment that uses it or by the import job that pulls from it.

*Table - ModelSourceType Definition* {#tbl-modelsourcetype-definition defines=ModelSourceType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:ModelSourceType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:BaseObjectType defined in OPC 10000-5 |  |  |  |  |  |
| 0:HasProperty | Variable | 2:SourceId | 0:String | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:EndpointUri | 0:String | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:ApiDialect | 2:ApiDialectEnum | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:EndpointDescriptionUri | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:AuthenticationKind | 2:AuthenticationKindEnum | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:CredentialReference | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:TokenAudience | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:Reachability | 2:ReachabilityEnum | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:LastSuccessAt | 0:UtcTime | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:ConsecutiveFailures | 0:UInt32 | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:RateLimit | 2:RateLimitDataType | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:Capabilities | 2:CapabilityDataType[] | 0:PropertyType | O |
| 0:HasComponent | Method | 2:TestConnection |  |  | O |
| 0:HasComponent | Method | 2:ListModels |  |  | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AiModelManagement |  |  |  |  |  |

#### TestConnection {#sec-modelsourcetype-testconnection type=ModelSourceType method=TestConnection}

Probe the endpoint and update Reachability. Defined so that a commissioning engineer can establish that credentials and network policy are right BEFORE a deployment depends on them, rather than discovering it from a failed inference.

**Signature**

```text
TestConnection (
  [out] 0:Boolean       Reachable,
  [out] 0:LocalizedText Detail);
```

*Table - TestConnection Method Arguments* {#tbl-testconnection-method-arguments}

| **Argument** | **Description** |
| --- | --- |
| Reachable | Whether the probe succeeded. |
| Detail | Diagnostic. For a human. |

#### ListModels {#sec-modelsourcetype-listmodels type=ModelSourceType method=ListModels}

Enumerate the models the source offers.

**Signature**

```text
ListModels (
  [in]  0:String                   Filter,
  [in]  0:UInt32                   MaxResults,
  [in]  0:ByteString               ContinuationPoint,
  [out] 2:ModelReferenceDataType[] Models,
  [out] 0:ByteString               ContinuationPoint);
```

*Table - ListModels Method Arguments* {#tbl-listmodels-method-arguments}

| **Argument** | **Description** |
| --- | --- |
| Filter | Optional substring or expression; empty for all. |
| MaxResults | Upper bound on returned entries. |
| ContinuationPoint | Empty on the first call; otherwise the value the previous call returned. A cap without a cursor bounds the response and puts every entry past it out of reach, which against a public catalogue means most of them. |
| Models | Publisher, name and version of each model offered. |
| ContinuationPoint | Pass to the next call to continue. Empty when the enumeration is complete, which is how a client knows to stop rather than by comparing counts. |

### Wire contract and authentication {#sec-wire-contract-and-authentication}

`ApiDialect` (`ApiDialectEnum`, `ns=2;i=3007`) is `OpcUaInference`, `RestChatCompletions`, `OpenInferenceProtocol`, `TensorRemoteProcedure`, `EmbeddedRuntime` or `Proprietary`.

These name **the contract the remote endpoint speaks**. `OpcUaInference` is another Server implementing this specification; `RestChatCompletions` is the de-facto REST contract for chat and embeddings that most serving runtimes expose, including ones that run on a single workstation — named here for what it does rather than for whoever published it first, because a literal in a standard should not be an advertisement; `OpenInferenceProtocol` is the KServe-derived predict contract; `TensorRemoteProcedure` covers the tensor-oriented RPC contracts of dedicated inference servers; `EmbeddedRuntime` is an in-process runtime reached through a library rather than a socket. `Proprietary` is an honest admission, and a Server using it **should** populate `EndpointDescriptionUri` — otherwise nothing in the address space says how the endpoint is called.

**How an OPC UA client calls this Server is always §8** — one Method, one opaque payload, one envelope, whatever the source speaks. What the dialect on a *source* does not tell a client is what to put in that payload, and §6.4.2 puts the same enumeration on `DeploymentType` to answer that. The two are read by different parties for different purposes: the source's dialect is what this Server must speak outward, the deployment's is what a caller must speak inward, and a Server that translates between them publishes two different values. A Server that passes the payload through publishes the same value twice, which is not duplication so much as the honest answer given twice.

The literals classify the contract **this Server speaks to that endpoint**, not everything the endpoint could offer. A runtime reached in-process is `EmbeddedRuntime` and the same runtime reached over its own loopback HTTP server is `RestChatCompletions`; a hosted endpoint reached through its OpenAI-compatible surface is `RestChatCompletions` and the same host reached through its native API is `Proprietary`. The value describes the integration, so it is answerable, and a Server that changes how it calls an endpoint changes it.

Where a source serves **only as a catalogue** — §10's import reads from it and nothing calls `Invoke` through it — `ApiDialect` is `Proprietary` and `EndpointDescriptionUri` is populated. The member's value domain is inference contracts, a catalogue speaks none of them, and `Proprietary` is the accurate answer rather than a shortcoming: it says there is no inference contract here to recognise, and the description URI says what there is instead.

`AuthenticationKind` (`AuthenticationKindEnum`, `ns=2;i=3008`) is `Anonymous`, `ApiKey`, `BearerToken`, `WorkloadIdentity` or `MutualTls`. `WorkloadIdentity` is preferred wherever the hosting platform offers it, because it is the only one of the five under which no secret is stored anywhere for an attacker to read.

**It classifies the credential the Server stores, not the handshake it performs.** That is what makes it answerable against endpoints whose handshakes have nothing in common. Where a handshake is driven by an identity the platform assigns and no secret is stored, it is `WorkloadIdentity` whatever token the wire ultimately carries; where a secret is stored, it is `ApiKey` or `BearerToken` according to what the stored thing is. A request-signing scheme is therefore `WorkloadIdentity` when an assigned role signs it and `ApiKey` when a stored key does — one scheme, two values, because the question is what an attacker could steal.

Read as a handshake classifier the member would be unanswerable for most real endpoints, and the five literals are deliberately not a taxonomy of handshakes. A source whose handshake a client genuinely needs described names it through `EndpointDescriptionUri`.

**`CredentialReference` is a name, never a secret.** It identifies the credential in whatever store the Server uses. A Server **shall not** expose credential material through any Attribute of any node in this model, and a client that reads `CredentialReference` learns which credential is in use and nothing about what it is. This is stated as a prohibition rather than left implicit because the address space is a browsable, subscribable, historisable surface, and a secret placed in it is not merely readable — it is archived.

### Version binding {#sec-version-binding}

`VersionBinding` (`VersionBindingEnum`, `ns=2;i=3010`) is `Pinned` or `FollowsRef`.

A **`Pinned`** deployment names one immutable model version. The artefact behind it cannot change without an observable change to the deployment.

A **`FollowsRef`** deployment names a mutable pointer — a branch, a channel, a "latest" alias — in `BoundRef`. The artefact behind it **can** change with nothing else changing.

That second case is a promotion (§7) that nobody called `PromoteModel` for. It has the same effect: what the equipment decides changes, and no reader of the address space sees a structural difference. So §12.3's requirement applies to it unchanged — a Server **shall** treat repointing a followed reference as an authorization-bearing act, not as configuration.

Stating this structurally, rather than as an upgrade-policy setting, is deliberate. What a client needs to know is whether the artefact can move under it. That is a property of the binding. When someone *intends* to move it is a schedule, and a schedule is not something a client can check.

#### What `Pinned` is worth, and what `RuntimeIdentity` adds {#sec-what-pinned-is-worth-and-what-runtimeidentity-adds}

`Pinned` says the artefact cannot change without an observable change to the deployment. How much that is worth depends on what this Server can actually verify, and `DigestProvenance` (§12.1.1) is where a client reads the answer.

Where `DigestProvenance` is `ComputedByServer` or `VerifiedOnStage`, the Server holds the bytes and the guarantee is its own. Where it is `NotAvailable`, the deployment is pinned to a **name** the source promises to hold stable, and `Pinned` records that promise rather than this Server's verification. Both are legitimate; they are not the same assurance, and a Server **shall not** represent the second as the first — which it does not have to do explicitly, because the two are already distinguishable by reading one member.

`RuntimeIdentity` is what closes the remaining gap. An artefact that has not changed can still be served by a different runtime build, a different engine compilation or a different accelerator arrangement, and produce different numbers for the same input. Where the execution site publishes an identity for its serving configuration, `RuntimeIdentity` carries it: opaque, compared only for equality, never parsed — the same contract `Digest` has.

**A change to `RuntimeIdentity` is an observable change to the deployment**, and that is what makes the sentence at the top of this clause true rather than aspirational. Under a `Pinned` binding it is often the *only* observable change available, because the model did not move and nothing else in the address space did either.

It answers a question asked long after the fact. An investigation opened in September into parts built in March walks §12.1's chain, reaches a `Digest` that is empty for good reason, and finds `VersionBinding` `Pinned` — and concludes nothing changed. Historising `RuntimeIdentity` makes *did the serving stack move between March and September* answerable through `HistoryRead`. It does not identify which build served an individual call, and a Server **shall not** be read as claiming that; concurrent calls during a rollover can straddle a change. The coarser question is the one that gets asked.

### Availability and fallback {#sec-availability-and-fallback}

This is the question a plant asks that an inference API does not answer, because an inference API can assume its caller is willing to wait. A line is not.

`FallbackPolicy` (`FallbackPolicyEnum`, `ns=2;i=3009`) is Mandatory on every deployment and states what the Server does when this one cannot serve:

- **`Fail`** — report the failure and produce nothing. This is the safe default: a caller told that nothing happened can decide for itself, and deciding is often its job.
- **`HoldLast`** — keep reporting the most recent successful result. Legitimate only where a stale answer is safe, and the caller **shall** be able to establish the staleness, for which `LastSuccessAt` is sufficient. A Server **shall not** present a held result as fresh.
- **`FallBackTo`** — route to the deployment named by the `FallsBackTo` reference. The answer then comes from a **different model**, and `Invoke` **shall** report that model in `ModelUsed`. A fallback that answered without saying so would break the provenance chain precisely when it matters most.

```{figure}
id: fig-aim-avail
caption: Availability and fallback between deployments
source: figures/AiModelManagement-Fig14-Availability.png
```

The `FallBackTo` branch is the one that needs care: the caller asked nothing different and got an answer from another model, so `ModelUsed` is the only thing that says so.

`FallsBackTo` **shall not** form a cycle. A Server **shall** reject a configuration that closes one rather than discovering it at the moment of failure, which is the worst possible moment.

`Reachability` (`ReachabilityEnum`, `ns=2;i=3013`) is `Unknown`, `Reachable`, `Unreachable` or `Throttled`. `Throttled` is separated from `Unreachable` deliberately: they look alike from the outside and call for opposite responses. An unreachable endpoint should be failed over; a throttled one will serve again shortly and failing it over merely moves the load. `RateLimit` (`RateLimitDataType`, `ns=2;i=3056`) carries `UnitKind`, `Limit`, `Remaining`, `Interval` and `RetryAfter` so a client can tell "the model said no" from "the quota said no".

`ListModels` enumerates what the source offers, returning a `ModelReferenceDataType` for each. It takes a `Filter` and a `MaxResults` because a public catalogue holds more models than any client wants to page through, and a Method that could only return everything would be unusable against exactly the sources this clause exists to reach. It is Optional: a source that serves one known model needs no catalogue.

A cap alone is not enough, and `ContinuationPoint` is why. `MaxResults` bounds the response and, on its own, puts every entry past it permanently out of reach — against a public catalogue that is most of them, which turns the member meant to make the Method usable into the one that truncates it. A client passes an empty `ContinuationPoint` on the first call and the value it received on each call after, and the enumeration is complete when the returned one is empty. That is how a client knows to stop, rather than by comparing a count against a bound it set itself and cannot distinguish from a source that happened to have exactly that many.

`TestConnection` probes the endpoint and updates `Reachability`. It exists so a commissioning engineer can establish that credentials and network policy are right **before** production traffic depends on them, rather than learning it from the first failed inference.

### Data residency and egress {#sec-data-residency-and-egress}

Where the data goes is a different question from who can read it, and only the first is what a plant is asking.

Encryption answers who can read data in flight. It does not answer where the data went, and that is the question a plant is actually asking.

Three members on `DeploymentType` answer it, and all three are about the deployment rather than the model, because the same model deployed twice can give different answers:

- **`DataJurisdiction`** is Mandatory and names where input is processed, in whatever scheme the operator uses — a site, a legal jurisdiction, a named zone. This specification does not fix the vocabulary because the operator's obligations do.
- **`EgressPermitted`** is Mandatory and states whether calling this deployment sends input outside the operator's boundary. A Server **shall** set it true for every deployment whose `InferenceLocation` is `Cloud`, and **shall not** set it false because the channel is encrypted.
- **`RetainsInput`** states whether the far end keeps input after serving the request — for provider-side logging, for evaluation, for training. **Unknown is not a value.** A Server that cannot establish the answer **shall** report `true`, because the assumption that keeps data in is the one that is safe to be wrong about.

`EgressPolicyUri` names the governing policy for a human.

These three members are **end-to-end, not next-hop**. `DataJurisdiction` names where input is ultimately processed; `EgressPermitted` states whether calling this deployment sends input outside the operator's boundary **by any path**; `RetainsInput` covers retention anywhere along that path. A hop that is itself local does not make the answer local.

That distinction is invisible until a deployment federates. A cell Server calling a site Server over the plant network is one local hop with no internet in sight, and if that site Server is itself calling a hosted endpoint the payload leaves the site anyway. The cell Server publishing `EgressPermitted` false is then publishing something untrue about the only thing its caller wanted to know, while satisfying every rule above — because the rule on `EgressPermitted` binds on `InferenceLocation` being `Cloud`, and the cell Server's is `EdgeOffServer`.

So where a deployment's `Source` names another Server implementing this specification, that Server's declarations are part of the answer. A Server **shall** read `DataJurisdiction`, `EgressPermitted` and `RetainsInput` from the upstream deployment it calls, and **shall not** publish values more permissive than the ones it read. A Server that cannot read them **shall** publish `EgressPermitted` and `RetainsInput` true, for the reason already given: the assumption that keeps data in is the one that is safe to be wrong about.

This propagates assertions; it does not verify them. An upstream Server that declares something false makes its downstream neighbours wrong too, and no protocol can fix that. What it does fix is the case where every Server along a chain is honest and the answer still comes out wrong because nobody was obliged to look up.

§12.3.2 states the same rule for the `FallsBackTo` edge. A payload leaves a deployment along exactly two modelled edges, and the rule is the same on both.

---

## The catalogue and model import (normative) {#sec-the-catalogue-and-model-import-normative}

### The catalogue {#sec-the-catalogue}

A model catalogue **is** a registry, which is why this specification extends one rather than inventing a second.

Models come from somewhere: a public hub, a vendor catalogue, an internal MLOps registry. Every such catalogue in practice has the same shape — publishers own namespaces, models and datasets are resources within them, versions are immutable and identified by content, and mutable names point at versions rather than being them.

That shape is a registry, so this specification does not invent one. `ModelRegistryType` (`ns=2;i=1010`), `ModelPublisherType` (`ns=2;i=1011`), `ModelResourceType` (`ns=2;i=1012`) and `DatasetResourceType` (`ns=2;i=1013`) are domain extensions of *OPC UA — xRegistry*'s `RegistryType`, `GroupType` and `ResourceType`.

Two consequences fall out of the base type rather than being designed here, and both are load-bearing:

1. `ResourceType` **is** a `FileType`, so a model artefact a Server holds is readable with the inherited `Open`, `Read` and `Close`. Staging (§10.3) needs no new transport.
2. `ResourceType` already carries `ExternalReference` and `ResourceUrl`, so a catalogue entry whose bytes live elsewhere is expressible without pretending to hold them.

Each type **narrows** what its base left open, as a domain extension must. `ModelRegistryType` overrides the inherited `<Group>` placeholder so it admits `ModelPublisherType` and nothing else; `ModelPublisherType` overrides `<Resource>` so it admits `AiResourceType` and nothing else.

The narrowing reuses the **inherited BrowseNames**, and that detail is the whole mechanism rather than a formality. An InstanceDeclaration is overridden only by one with the same BrowseName, so a subtype that invents its own placeholder name leaves the inherited one fully open beside it — a registry that looks narrowed and still admits any group at all. Clause 13's conformance depends on the narrowing being real, so the validator checks the BrowseName rather than merely checking that some placeholder exists.

`AiResourceType` (`ns=2;i=1016`) is an **abstract** base of `ModelResourceType` and `DatasetResourceType`. It exists because a publisher holds both models and datasets while `<Resource>` can be overridden only once: narrowing to a common base admits exactly the two and nothing else. It adds no members of its own — its whole purpose is to be the type that the single override names.

`ModelResourceType` adds `TaskKind`, `Framework`, `Digest`, `DigestAlgorithm`, `SizeBytes`, `Gated` and `MutableRefs`. `SizeBytes` lets a staging import decide whether it has room before it starts rather than after it fails; `Gated` says the artefact needs an entitlement beyond ordinary authentication, which is otherwise discovered part-way through a transfer; `MutableRefs` names the branches and channels a deployment may follow, which is what makes §9.3's `FollowsRef` checkable rather than a claim. `DatasetResourceType` is a **sibling** of it, not something beneath it, because a dataset outlives the models trained on it and is cited by several.

### Importing a model {#sec-importing-a-model}

A Server reaches an external AI system in **two distinct ways**, and it is worth separating them because both are sometimes called bridging.

Clause 9 covers the first: a Server that runs no model itself calls one hosted elsewhere, request by request, through a `ModelSourceType`. Nothing is brought across — the model stays where it is and the Server is a client of it.

This clause covers the second: a Server obtains a model from a catalogue so that it can afterwards describe it, execute it, or both. That is what `ModelImportJobType` does, and it is a one-time transfer rather than a per-call relationship.

`ModelImportJobType` (`ns=2;i=1007`) brings a model from a catalogue into this Server. It derives from `AiJobType`, so it is started, observed and audited like every other long-running operation here.

It takes a `Source`, a `ModelReference` and a `Mode`, and produces `ImportedModel` — a `ModelType` instance in this Server's address space, carrying an `ImportedFrom` reference back to the catalogue resource it came from. That reference is what makes *"where did this model come from"* answerable later, rather than only at the moment of import when someone happened to be watching.

An import reads from one of **two** things, and the job says which. `Source` names a `ModelSourceType` — a live endpoint the Server calls. `Registry` (`NodeId`, Optional) names a `ModelRegistryType` — a catalogue the Server browses, which is the path §4.4 and §5.1 draw and the one a plant MLOps node actually uses. A Server **shall** populate exactly one of them and **shall** leave the other null. A job that named both would not say which of the two produced the artefact whose digest §10.4 verifies, and that is the one question the job exists to make answerable.

A Server that imports only from endpoints omits `Registry` altogether; `Source` is Mandatory and remains the only path for it. `Registry` is Optional because the registry types of this clause are themselves optional to implement — a Server obliged to expose a member it can never populate learns nothing and teaches a client nothing. A Server claiming **AI-Import** does implement them, because that facet requires **AI-Catalogue** (§13.2), so there the member is present and the exactly-one rule has both of its alternatives available.

`ModelReferenceDataType` (`ns=2;i=3051`) is the `Publisher`, `Name`, `Version` triple. An import takes the triple rather than a URL because a URL says where a copy is today and the triple says which artefact is meant — and the two diverge the moment anyone mirrors anything.

### Import modes {#sec-import-modes}

`ImportModeEnum` (`ns=2;i=3011`) is `Federate`, `Stage` or `Auto`.

**`Federate`** materializes the catalogue entry as a `ModelType` and leaves the artefact where it is. Nothing is downloaded; inference runs at the source. This is the right mode whenever the model is large, the source is reliable, and the plant is content for data to reach it — and it is the mode under which a Server can describe hundreds of models it has never fetched.

**`Stage`** fetches the artefact, verifies it, and makes it locally available so inference can run without the source. `BytesTransferred` tracks progress, which is zero throughout a federating import because a federating import moves none.

**`Auto`** federates, then stages if the target deployment's `InferenceLocation` is `OnServer` or `EdgeOffServer` — because those cannot reach the source at inference time, which makes the choice determined rather than a preference.

```{figure}
id: fig-aim-modes
caption: Import modes
source: figures/AiModelManagement-Fig15-ImportModes.png
```

### Digest verification {#sec-digest-verification}

Staging is the one point in this model where a Server **shall** verify a digest rather than merely publish one.

A staging import is the moment a substituted artefact would enter the system. Before it, the model is a description; after it, it is bytes that will produce decisions.

A Server performing a staging import **shall** compute the digest of the fetched artefact, compare it with the one the catalogue resource declares, and set `DigestVerified` accordingly. Where they differ, it **shall not** deploy the artefact and **shall** leave the job in a failed state with `LastError` populated.

`Cancel` **shall** discard a partially staged artefact rather than leaving it where a later deployment could pick it up. A half-transferred file that survives a cancellation is an unverified artefact with a plausible name.

This is the point at which §12.1's requirement that `Digest` be Mandatory stops being bookkeeping and becomes an executable check. Everywhere else the digest lets someone verify an artefact if they choose to; here the Server **shall**.

---

## Governance and provenance (normative) {#sec-governance-and-provenance-normative}

### Model card {#sec-model-card}

The nameplate does not say whether a model may be used, and that is a separate question asked by different people.

`ModelType` answers *which artefact is this*. It does not answer *should this be running on my line*, and those are different questions asked by different people at different times.

`ModelCardType` (`ns=2;i=1015`), reached through `ModelType.Card`, answers the second. `IntendedUse` and `Limitations` are both **Mandatory**. A card that records only what a model can do describes half its behaviour, and it is the other half — where it stops working, on what inputs, under what conditions — that a commissioning engineer needs in order to decide whether the model suits the installation in front of them. `OutOfScopeUse`, `License`, `EthicalConsiderations` and `ContactUri` are optional.

`TrainingDataCutoff` deserves its own mention. A model cannot know anything after it, and "the model was trained before this existed" is a common and commonly missed explanation for a field failure that otherwise looks like a defect.

`DeprecatedFrom` and `SupportedUntil` are its forward-facing twins, and they are on the card rather than the nameplate for the reason the split exists: *how long will this keep working* is a question about whether the model may run here, not about which artefact it is.

They are different dates with different responses. `DeprecatedFrom` is when the source stops treating the model as current while continuing to serve it — the date that starts a requalification. `SupportedUntil` is when the source stops serving it at all.

The second is worth being blunt about, because its consequence is not the one the surrounding members suggest. On that date the deployment does not degrade; it stops. `Reachability` goes `Unreachable`, `ConsecutiveFailures` climbs, and `FallbackPolicy` decides what happens next — and where that is `FallBackTo`, the line keeps producing while something outside the qualified configuration answers. §12.3.2 constrains that fallback on residency grounds and `ModelUsed` records it faithfully, so nothing here is hidden; it is simply not noticed, because nobody was watching for a date.

That is the whole value of the member. Every other availability facility in this model — `Reachability`, `ConsecutiveFailures`, `LastSuccessAt`, `FallbackPolicy` — is a way of coping *after* the fact. This is the only one whose value is a date in the future, and where a source publishes it in machine-readable form a Server **should** carry it, because a requalification takes longer to schedule than an outage takes to notice.

### Evaluation {#sec-evaluation}

A metric without the threshold it was judged against cannot be acted on.

`EvaluationRunType` (`ns=2;i=1014`) is one measurement of a model against a dataset. It is a first-class object rather than a field on the model because the same model is measured many times, and because the run that gated a promotion must remain readable afterwards to answer why the promotion was allowed.

`RunId`, `EvaluatedModel` and `Metrics` are **Mandatory**: a run that cannot be named, or that does not say which model it measured, or that carries no measurement, records nothing that can be acted on. `Dataset`, `CompletedAt` and `ReportUri` are Optional — a Server may evaluate against data it does not model here, and the full report often lives outside OPC UA entirely.

`EvaluationMetricDataType` (`ns=2;i=3055`) carries `Name`, `Value`, `Unit`, `Threshold`, `Comparison` and `Passed`. **The threshold travels with the metric.** An accuracy of 0.94 means nothing on its own; a reviewer reading it a year later has no way to recover what "good" meant, and the person who knew has moved on.

`Passed` on the run is the conjunction of the individual ones. A Server **shall not** report it true while any metric's `Passed` is false — a summary that disagrees with its own detail is worse than no summary, because it is the field people read.

Models carry `EvaluatedBy` references to their runs. It is optional and repeating: the run that gated promotion is not necessarily the most recent one.

Where an evaluation gates a configured model substitution, the resulting `PromotionRecordType` carries both the convenience `EvaluationRun` NodeId and a durable `EvaluationRunId` snapshot. The NodeId supports browsing while the run exists; the identifier preserves the decision evidence after it is retired. Removing an evaluation node **shall not** permit rewriting or deleting the promotion record that cited it.

### Lineage {#sec-lineage}

Lineage is a **chain**, not a field, and the difference is what makes it usable.

`DerivedFrom` links a model to the one it was fine-tuned, distilled or quantized from.

It is a reference and not a string because lineage is walked. A model three derivations from its base is answerable for all three — a defect in the base is a defect in every descendant — and a field naming only the immediate parent cannot be followed to find out.

`Quantization` on `ModelType` states the numeric precision the artefact is stored in. A quantized model is a **different artefact with different behaviour**, not a packaging detail, and treating it as one is how a model that passed evaluation at full precision ends up deployed at reduced precision without being re-measured.

### Safety assessment {#sec-safety-assessment}

Where a safety policy is applied to an inference call, what it produces is a set of **findings** — each naming a category, how severe it was, and whether anything was withheld as a result.

`SafetyAssessmentDataType` (`ns=2;i=3054`) carries `Category`, `Severity`, `Filtered` and `Detail`, and is returned by `Invoke` where a policy was applied.

`Severity` (`SafetySeverityEnum`, `ns=2;i=3012`) is `None`, `Low`, `Medium` or `High`. `Category` is a **String**, not an enumeration, because harm categories are set by the policy an installation adopts and an industrial taxonomy — out-of-distribution input, unsafe recommendation, sensitive-data exposure — looks nothing like a consumer one. Fixing the categories here would mean fixing them wrong for most adopters.

`Filtered` distinguishes withheld from flagged. A client that treats the two alike will either discard usable output or act on output that was not meant to be acted on.

---

## Security {#sec-security}

### Provenance {#sec-provenance}

Provenance is the point of the digest: without it the other members describe an artefact nobody can confirm they hold.

A published result is traceable to the artefact that produced it by retaining the invocation's `ModelUsed` NodeId and following `ModelUsed` → `ModelType` → `Digest`. The deployment's `UsesModel` reference identifies the model serving now; it is not a historical record. The deployment's `PromotionRecords` preserve how that current configuration changed, with durable previous and new identity snapshots that do not depend on either `ModelType` node remaining present.

`Digest` is Mandatory because the historical chain cannot identify artefact bytes without it (§6.2). `UsesModel` remains exactly-one so a deployment's current serving configuration is unambiguous (§6.5). A Server **shall** populate `Digest` for every model whose artefact is obtainable through `ArtifactUri`.

`DigestAlgorithm` **shall** name a hash function with **at least 256-bit output and no known collision weakness**; `SHA-256` is the default and is always acceptable. It **shall not** be `MD5`, `SHA-1` or a truncated variant — chosen-prefix collisions against those are practical, so a substituted artefact would pass verification, and a verification that can be passed by the wrong artefact is worse than none because it is believed.

```{figure}
id: fig-aim-prov
caption: Provenance of a trained model
source: figures/AiModelManagement-Fig16-Provenance.png
```

#### What a digest is worth, and why an empty one is not a failure {#sec-what-a-digest-is-worth-and-why-an-empty-one-is-not-a-failure}

`Digest` is Mandatory so that its absence is uniform and browsable: a client finds the member on every model and reads an empty value, rather than not finding the member and being unable to tell a model without a digest from a Server that does not implement digests. That is the right trade, and it is worth stating plainly that **most sources cannot fill it**. An endpoint that names models but never their content — which is what a hosted inference API generally is — has no digest to give, and a Server integrating one is behaving correctly when it publishes none.

But "empty" then carries two meanings, and a present value carries three. `DigestProvenance` (`DigestProvenanceEnum`, `ns=2;i=3015`) is **Mandatory** on `ModelType` and separates them:

| Value | `Digest` | What a client may conclude |
|---|---|---|
| `NotAvailable` | empty | The source publishes no digest. There is nothing to obtain and nothing was withheld. |
| `DeclaredBySource` | present | An assertion forwarded. No party the Server can speak for has hashed the artefact. |
| `ComputedByServer` | present | Evidence the Server holds. Nothing independent agrees with it, so a substitution that preceded the Server obtaining the bytes is undetected. |
| `VerifiedOnStage` | present | The Server computed it during a staging import and it matched what the source declared (§10.4). Two independent parties agree, which is the strongest statement this model carries. |

It is Mandatory for the reason `Digest` itself is, stated in §6.2: clause 12 depends on it, and a rule that depends on an Optional member is one a conformant Server can silently not satisfy. A client deciding whether to run a model on a line needs to distinguish *nobody checked* from *two parties agree*, and an Optional member would let a Server decline to answer exactly where the answer matters.

`ModelResourceType` carries the same member as **Optional**, mirroring the `Digest` it qualifies, which is Optional there. A catalogue declaring a digest it did not compute is `DeclaredBySource`; one serving the artefact through the inherited `Open`, `Read` and `Close` can reach `ComputedByServer`.

**A Server shall not put a non-content identifier in `Digest`.** A response fingerprint, a resource name, a storage entity tag and a repository commit identifier are all tempting, all stable, and none of them a digest of the artefact that ran. A client that verified against one would believe it had checked something it had not, which is the failure mode `DigestAlgorithm`'s strength rule exists to prevent — arrived at by a different route. `NotAvailable` is the answer.

Where such an identifier **locates** the artefact or its provenance record, it belongs in `ArtifactUri` or `ProvenanceUri`, which promise nothing about content. Where it identifies something else — a serving configuration, a request route — this model has no member for it, and inventing one out of `Digest` is not the remedy. A datum with no home is better recorded as having none than filed somewhere a client will read it as an artefact digest.

**Provenance does not strengthen by being forwarded.** Where a deployment's `Source` names another Server implementing this specification, that Server publishes a `Digest` and a `DigestProvenance` of its own, and both are readable. A Server **shall not** publish a `DigestProvenance` stronger than the one it read upstream, where the ordering is `NotAvailable` < `DeclaredBySource` < `ComputedByServer` < `VerifiedOnStage`. A digest received across a federation hop and not checked against bytes this Server holds is `DeclaredBySource` however the upstream Server obtained it: republishing its `VerifiedOnStage` would claim a verification this Server did not perform, and the claim would be indistinguishable from one it had. This is the composition rule §9.5 states for residency, applied to the other thing a federated deployment forwards.

#### Broken links {#sec-broken-links}

The walk is: result → `ModelUsed` → `ModelType` → `Digest`, and — where the model was imported — `ImportedFrom` → the catalogue resource it came from.

Two of those links can be broken by a Server that is otherwise behaving correctly:

- Reading the **deployment's current model** instead of `ModelUsed` gives the wrong answer whenever a fallback served the call or a followed reference moved (§8.2.1). It is wrong silently and plausibly, which is the worst combination.
- Trusting a **staged artefact whose digest was never checked** breaks it at the point where an artefact enters the system. §10.4 is where that check is required, and it is the only place in this model where a Server **shall** verify a digest rather than merely publish one.

Promotion history closes a different break: deletion of an old `ModelType`. A promotion record's `ModelIdentitySnapshotDataType` copies `ModelId`, `Version`, `Digest`, `DigestAlgorithm` and `DigestProvenance` when the substitution succeeds. Servers **shall not** reconstruct those values later from a mutable source or overwrite them when a target node changes; the snapshot is evidence of what was known at the change boundary, including whether the digest was merely declared, computed by the Server, or verified on stage.

### URI handling {#sec-uri-handling}

Every URI in this model is untrusted input.

`ArtifactUri`, `ProvenanceUri` and `EndpointUri` are values a client may have written and a Server may resolve. A Server **shall** validate them against a configured policy before resolving, and **shall not** follow one to a scheme or host the policy does not permit.

Where `InferenceLocation` is not `OnServer`, `EndpointUri` **shall** name a scheme that is authenticated and confidential. Inference off the Server means the input data leaves it, and the result comes back from something the Server did not compute — both directions need the channel to be trustworthy.

The set of resolvable URIs grew with clauses 9 to 10, and every addition is a value some client may have written: `ModelSourceType.EndpointUri` and `EndpointDescriptionUri`, `ModelCardType.ContactUri`, `EvaluationRunType.ReportUri`, `ModelType.SafetyPolicyUri`, `EgressPolicyUri`, and the catalogue's inherited `ResourceUrl`. The same policy governs all of them. A Server that validates the ones it remembers and resolves the rest has a policy in name only.

A staging import (§10.3) is the sharpest case, because it fetches bytes that will subsequently produce decisions. A Server **shall** apply the resolver policy to the artefact location **before** transferring, not after — a policy checked on the way out is not a control, and `SizeBytes` exists partly so that the decision can be made without starting.

#### Credential material {#sec-credential-material}

A Server **shall not** expose credential material through any Attribute of any node in this model. `CredentialReference` names a credential in whatever store the Server uses; it never carries one, and `TokenAudience` states what a token is requested *for*, not what it is.

This is stated as a prohibition rather than left to implementers' good sense because the address space is not merely readable. It is browsable by anything with a Session, subscribable so that a value is pushed as it changes, and historisable so that a value read once is retained. A secret placed there is not exposed once — it is published, distributed and archived.

`WorkloadIdentity` is preferred wherever the platform offers it, for the reason that it is the only authentication kind under which there is no secret anywhere to be exposed by a future mistake.

### Promotion authorization {#sec-promotion-authorization}

Promotion needs an authorization of its own, distinct from the one that permits ordinary operation.

A Server **shall** require an authorization for `PromoteModel` distinct from the one that permits reading this model or operating the equipment.

Promotion changes behaviour without changing structure. Nothing in the address space looks different afterwards except a version string, so the usual defence — that a significant change is visible — does not apply here.

Every authorized successful substitution **shall** create its immutable `PromotionRecordType` atomically with the `UsesModel` update. The record's `ChangedBy` carries the authenticated identity as the Server knows it; a Server **shall not** replace a known human principal with an intermediary service account. Automatic policies use the Server's stable system identity and `AutomaticSubstitution`. Authorization failure, validation failure, or any other failed substitution creates no successful record.

#### Followed references {#sec-followed-references}

Promotion has a second door, and a control that guards only the first is misleading rather than merely weaker.

`PromoteModel` is not the only way the model behind a deployment changes. A `FollowsRef` binding (§9.3) moves whenever whoever controls the reference repoints it, and nothing in this address space changes when they do.

A Server **shall** treat repointing a followed reference as the same class of act as calling `PromoteModel`, and **shall** subject it to the same distinct authorization. A control that guards the front door while the side door stands open is not a weaker control — it is a misleading one, because the audit trail shows every promotion having been authorized.

For the same reason `AiJobType.RequestedBy` records who started a job, while the promotion record's `ChangedBy` records who authorized or initiated the actual substitution. The two may differ and shall not be collapsed. An authorization check that leaves no record answers *was this allowed* but not *who did it*, and only the second question can be asked after the fact.

#### Fallback {#sec-fallback}

A fallback changes what answers, not who may ask.

`FallBackTo` (§9.4) routes a call to a different deployment, and therefore a different model, without the caller asking for it.

That is not a privilege escalation — the caller was already entitled to an answer — but it **is** a change in what produced the answer, and §8.2.1 requires it to be visible in `ModelUsed`. A Server **shall not** configure a fallback to a deployment whose `EgressPermitted` or `DataJurisdiction` is more permissive than the deployment falling back to it. Otherwise a network fault silently sends plant data somewhere policy forbids, which is precisely the moment nobody is watching.

Per-invocation fallback does **not** update the original deployment's `UsesModel`, so it creates no `PromotionRecordType` and raises no `ModelPromotedEventType`. If an availability policy instead changes the configured target, that is an `AutomaticSubstitution`, with a record and event on the same terms as every other configured substitution.

### Digest and authorship {#sec-digest-and-authorship}

A digest is not a signature, and the gap between the two is where an installation's real exposure sits.

`Digest` establishes that an artefact is the one described. It does **not** establish who produced it or that they were entitled to. A Server **shall not** present digest verification as authorization, and an installation that needs provenance of authorship needs a signature, which this model does not define.

The distinction sharpens once models arrive through a bridge (§10.2). A staging import verifies that the bytes it fetched match the digest the catalogue declared — so it detects corruption in transfer, and substitution by anyone who could not also edit the catalogue entry. It detects nothing at all about an attacker who could edit both, and the catalogue is the more attractive target precisely because it is the one that many machines read.

So what `DigestVerified` means is narrow and worth stating plainly: **the artefact is the one this catalogue entry described**. Whether that entry described the right artefact is a question about the catalogue, answered by the catalogue's own access control and by whatever signing the publisher applies — neither of which this model can see.

Two practical consequences:

- A Server **shall not** treat `DigestVerified` as evidence that a model is approved for use. §11.1's card and §11.2's evaluation are what an installation reads for that, and `ProvenanceUri` is the hand-off to the system that actually decides.
- An installation whose threat model includes a compromised catalogue **should** verify a publisher signature over the artefact out of band before promotion. This specification records where the artefact came from and what it hashes to, which is what makes such a check possible; it does not perform it.

---

## Profiles and conformance units {#sec-profiles-and-conformance-units}

```{clause}
kind: profiles
```

### Declaring conformance {#sec-declaring-conformance}

A Server declares conformance by exposing `AiRootType` under the Server object with `SpecificationVersion` set to the release it implements.

The NodeSet assigns every Node to one of four conformance units: `AiModelManagement` for the ObjectTypes and their members, `AiModelManagement DataTypes` for the structures and enumerations, `AiModelManagement ReferenceTypes` for the references, and `AiModelManagement Events` for the EventType of §7.4. The facets below are expressed over those Nodes, so a Server claiming a facet implements the units the facet's members belong to.

Facets are **additive and independent** except where a row states otherwise, and only one dependency exists: **AI-Import** requires **AI-Catalogue**, because an import job with nothing to import from is not implementable.

The split matters more here than in a smaller model, because the plausible Servers differ enormously — a device running one fixed model, a gateway calling a hosted one, and a plant MLOps node that may never call `Invoke` at all are three different products rather than three degrees of completeness of one. §13.3 names them as profiles. A single monolithic conformance claim would have made two of the three unclaimable.

**AI-Residency** is deliberately separate from **AI-Federation**. A Server can be perfectly capable of calling a remote model while being unable to state where the data goes, and an operator who needs the second guarantee needs to be able to ask for it by name rather than infer it from the first.

### Facets {#sec-facets}

| Facet | Requires |
|---|---|
| **AI-Base** (mandatory) | `AiRootType` with `Models` and `Deployments`; at least one `ModelType` with `ModelId`, `Name`, `Version`, `Digest`, `DigestAlgorithm` and `DigestProvenance`; where the Server exposes any deployment, each carries `DeploymentId`, `InferenceLocation` and `State` and satisfies the exactly-one `UsesModel` rule of §6.5; where that target can change, the `PromotionRecords` folder, atomic immutable records, complete deployment-lifetime retention and trigger-based `ModelChangeKindEnum` rules of §6.5.1; the digest rules of §12.1 |
| **AI-Dataset** | `DatasetType` instances with `DatasetId` and `SourceKind`, and `TrainedOn` from at least one model |
| **AI-OffServer** | A deployment whose `InferenceLocation` is not `OnServer`, and §12.2's requirement that its `EndpointUri` name an authenticated, confidential scheme |
| **AI-Signatures** | `Inputs` and `Outputs` populated on every model |
| **AI-Learning** | `LearningJobType`, the §7 state model, every Method that drives a transition in it, and the distinct `PromoteModel` authorization of §12.3 |
| **AI-Events** | `ModelPromotedEventType` and every rule of §7.4. A Server claiming it **shall** raise the event on every successful configured `UsesModel` substitution, including rollback, automatic substitution and mutable-reference repoint, and **shall not** raise it merely because a per-invocation fallback answered while `UsesModel` remained unchanged. `PromotionRecord` shall be populated and the legacy filtering fields shall agree with that authoritative record. `PromotedBy` **shall** be populated wherever the change was made by an authenticated principal. |
| **AI-Invoke** | `DeploymentType.Invoke` with `ModelUsed` and `FinishReason` populated on every response, and `Usage` returned on every response — its `UnitKind` empty where the execution site does not meter, per §8.2.3; the §6.4.2 requirement to publish `ApiDialect` where `Inputs`/`Outputs` do not describe the payload contract; the exactly-one `Payload`/`PayloadUri` rule of §8.6.1; and the §8.3 rule that an unsupported parameter is rejected rather than ignored |
| **AI-InvokeAsync** | `InvokeAsync` and `InferenceJobType`, answering the same questions as `Invoke` including size (§8.6.1): the exactly-one `Payload`/`PayloadUri` rule, and `TransferRequired` with `Transfer` where a result outgrew the inline bound |
| **AI-Transfer** | `BeginTransfer` and `InferenceTransferType`, `MaxInlinePayloadSize` on every deployment, and the §8.2.4 rule that `Invoke` reports `TransferRequired` rather than failing a call whose response outgrew the inline bound |
| **AI-Stream** | Incremental results published over a data channel (§8.5). Entirely optional; a Server that answers only through `Invoke` is conformant without it |
| **AI-Federation** | `ModelSourceType` with `ApiDialect`, `AuthenticationKind` and `Reachability`; the credential-secrecy prohibition of §9.2; `FallbackPolicy` on every deployment and the acyclicity rule of §9.4; `LastModifiedAt` on every model reached through a `FollowsRef` binding (§6.2.3); the composition rules of §9.5 and §12.1.1, which forbid a Server publishing residency or digest provenance stronger than what it read upstream |
| **AI-Residency** | `DataJurisdiction`, `EgressPermitted` and `RetainsInput` on every deployment, with the §9.5 rules including the requirement to report `RetainsInput` true when it cannot be established |
| **AI-Catalogue** | `ModelRegistryType`, `ModelPublisherType` and `ModelResourceType`, with the placeholders narrowed as §10.1 requires |
| **AI-Import** | `ModelImportJobType`, the federate/stage/auto modes of §10.3, the exactly-one `Source`/`Registry` rule of §10.2, and the digest verification of §10.4. Requires **AI-Catalogue** |

A Server **shall** publish the URI of every facet and profile it claims in `Server/ServerCapabilities/ServerProfileArray`, which is where a client discovers what it supports without browsing for members and guessing.

### Profiles {#sec-profiles}

A facet is a building block. A **profile** is a complete claim: a named set of facets describing one plausible Server, which is what a procurement document cites and what two vendors implementing the same shape agree they have built.

Four are defined. Each includes **AI-Base**, and a Server **may** claim more than one — a gateway that also mirrors a catalogue claims two, which is the whole reason profiles are composed from facets rather than written out independently.

| Profile | Facets | The Server it describes |
|---|---|---|
| **AI Inference Device Server** | AI-Base, AI-Invoke | Runs models itself. A camera, a controller or an industrial PC executing a model in its own process, describing what it runs and answering calls against it. |
| **AI Inference Gateway Server** | AI-Base, AI-Invoke, AI-OffServer, AI-Federation, AI-Residency | Calls a model hosted elsewhere. The bridge between a plant address space and an external inference service. |
| **AI Model Catalogue Server** | AI-Base, AI-Catalogue, AI-Import | Holds and distributes models without necessarily running any. A plant MLOps node mirroring a corporate registry and staging artefacts onto controllers. |
| **AI Model Lifecycle Server** | AI-Base, AI-Dataset, AI-Learning, AI-Catalogue, AI-Import | Closes the loop of clause 7: accumulates a dataset from the line, trains a candidate, evaluates it, promotes it, and keeps the lineage that explains why. |

**AI-Residency is inside the gateway profile rather than optional to it.** The moment inference leaves the Server the question *where does my data go* has an answer, and a gateway that cannot state it is precisely the arrangement §9.5 exists to prevent. A Server that federates and cannot answer claims the facets individually and not this profile.

The **Inference Device** profile does not include AI-Signatures, though a tensor runtime can usually satisfy it, because a Server serving one model behind a documented request body is a legitimate device and `Inputs`/`Outputs` do not describe a JSON contract (§6.4.2). It is claimed alongside where it holds.

The **Lifecycle** profile is the only one that requires AI-Learning, and it requires AI-Dataset with it. A learning loop whose training data is not described is a loop that cannot be audited, and §12.3's promotion authorization exists to be answerable about exactly that.

None of the four is a subset of another, and that is the point. A device that runs one fixed model, a gateway that runs none, and a catalogue node that may never call `Invoke` are three different products, and a single monolithic profile would have made two of them unclaimable.

### Profile and facet URIs {#sec-profile-and-facet-uris}

A profile name is for a human. `ServerProfileArray` holds URIs, and unless this specification states them two Servers implementing the same profile publish different strings and no client can match either.

Profiles are published under `http://opcfoundation.org/UA-Profile/AI/Server/`:

| Profile | URI suffix |
|---|---|
| AI Inference Device Server | `InferenceDevice` |
| AI Inference Gateway Server | `InferenceGateway` |
| AI Model Catalogue Server | `ModelCatalogue` |
| AI Model Lifecycle Server | `ModelLifecycle` |

Facets are published under `http://opcfoundation.org/UA-Profile/AI/Facet/`, with the suffix being the facet name after the `AI-` prefix: **AI-Base** is `Base`, **AI-InvokeAsync** is `InvokeAsync`, **AI-OffServer** is `OffServer`, and so on for every row of §13.2.

These URIs are **provisional**, on the same terms as the namespace URI and the NodeIds: this is a working-group draft, and the OPC Foundation assigns the final values.

---

| Artifact | Path |
|---|---|
| This specification | `metaverse-specs/ai-model-management/OPC-UA-AI-Model-Management.md` |
| Information model | `metaverse-specs/ai-model-management/Opc.Ua.AiModelManagement.NodeSet2.xml` |
| NodeId assignments | `metaverse-specs/ai-model-management/Opc.Ua.AiModelManagement.NodeIds.csv` |
| Generator | `metaverse-specs/extras/ai-model-management/tools/build_model.py` |
| Validator | `metaverse-specs/extras/ai-model-management/tools/validate_local.py` |
| Annex A (generated) | `metaverse-specs/extras/ai-model-management/tools/model-reference.md` |
| Implementation guides (informative) | `metaverse-specs/extras/ai-model-management/examples/` |
| Guide validator | `metaverse-specs/extras/ai-model-management/examples/tools/validate_examples.py` |

The NodeSet, the CSV and Annex A are generated from a single in-code source of truth and are **deterministic**. The generator is edited; the generated files are not.

The [implementation guides](../../../metaverse-specs/extras/ai-model-management/examples/index.md) are informative and introduce nothing. They map this model onto the systems an implementer is likely to be integrating — Azure AI Foundry, OpenAI, Amazon Bedrock and SageMaker, NVIDIA NIM and Triton, Google Vertex AI, Hugging Face, KServe, embedded runtimes, and another Server implementing this specification. Naming products there rather than here is what lets clause 9.2 name dialects for what they do: the normative document stays neutral and the informative folder beside it does not have to. Every literal of `ApiDialectEnum` and `AuthenticationKindEnum` is exercised by at least one guide, and `validate_examples.py` fails if a guide cites a member this model does not declare.

```powershell
python metaverse-specs\extras\ai-model-management\tools\build_model.py
python metaverse-specs\extras\ai-model-management\tools\validate_local.py
python metaverse-specs\extras\ai-model-management\examples\tools\validate_examples.py
```

---

## Information model reference {#anx-a annex=normative}

```{clause}
kind: annex-a
```

## Informative alignments {#anx-b annex=normative}

Not normative references, and no dependency. Recorded because this model borrowed from them deliberately.

- **IDTA 02060** *AI Model Nameplate* — the member set of `ModelType`. Currently the only standardised description of an industrial AI model.
- **IDTA 02058** *AI Dataset* — the member set of `DatasetType`.
- **IDTA 02059** *AI Model Management* — the member set of `DeploymentType`, including the inference-location concept.
- **OPC 30270** — the OPC UA ⇄ Asset Administration Shell bridge, over which the alignments above become a populated AAS.
- **xRegistry** — [the CNCF specification](https://github.com/xregistry/spec) the OPC UA projection in this repository follows. Its `groups` / `resources` / `versions` structure is what clause 10 extends, and public proxies over model hubs already present exactly the arrangement adopted here: publisher as group, models and datasets as sibling resource types, versions immutable and identified by content, mutable branch and tag names as pointers rather than versions.
- **OPC UA for Vision Systems** in this repository is the first consuming specification. Its `InferencePipelineType.Deployment` is a `NodeId` Property naming a `DeploymentType` here, and its `VisionResultType.ModelUsed` retains the model that actually answered, per §8.2.1. Neither NodeSet requires the other. See the informative [Vision and AI Model Management walkthrough](../../../metaverse-specs/vision-ai-walkthrough.md) for the combined browse path and the informative [external result mapping](../../../metaverse-specs/vision-ai-external-result-mapping.md) for preserving these identities outside the Server without creating another conformance profile.

---

## A worked arrangement (informative) {#anx-c annex=informative}

This annex is **informative**. It shows one arrangement that satisfies clauses 8 to 10, to make the interaction between them concrete. No member here is introduced by this annex; every one is defined in Annex A.

### C.1 The situation {#sec-c-1-the-situation}

A plant runs a surface-inspection model on a finishing line. The model is published in a corporate catalogue. Two things are true at once and pull in opposite directions: the good model is large and runs on a GPU appliance nobody wants to put on every line, and the line must keep running when the network to that appliance does not.

So the plant deploys twice. A **primary** deployment calls the appliance. A **secondary** deployment runs a smaller quantized model on the line controller itself. The primary falls back to the secondary.

### C.2 Getting the models here {#sec-c-2-getting-the-models-here}

Both start as one `ModelImportJobType` each, against a `ModelSourceType` naming the corporate catalogue.

| | Primary | Secondary |
|---|---|---|
| `ModelReference` | `Publisher` = `plant-quality`, `Name` = `surface-defect`, `Version` = `4.2.0` | same publisher and name, `Version` = `4.2.0-int8` |
| `Mode` | `Federate` | `Stage` |
| Result | a `ModelType` describing an artefact that stays in the catalogue | a `ModelType` whose artefact is now on the controller |

The second job fetches bytes, so `BytesTransferred` climbs and `DigestVerified` is the gate: the job compares what it fetched against the `Digest` the `ModelResourceType` declared, and refuses to deploy on mismatch (§10.4). The first job moves nothing, so `BytesTransferred` stays zero.

Both resulting models carry `ImportedFrom` back to the catalogue resource, which is what makes the question *where did this come from* answerable next year rather than only today.

The quantized model additionally carries `DerivedFrom` to the full-precision one and states `Quantization` = `int8`. That is not bookkeeping: it is the reason a reviewer knows the two will not agree on every part, and the reason the secondary needs its own `EvaluationRunType` rather than inheriting the primary's.

### C.3 The two deployments {#sec-c-3-the-two-deployments}

| | Primary | Secondary |
|---|---|---|
| `InferenceLocation` | `EdgeOffServer` | `OnServer` |
| `Source` | the appliance's `ModelSourceType` | null |
| `VersionBinding` | `Pinned` | `Pinned` |
| `FallbackPolicy` | `FallBackTo` | `Fail` |
| `FallsBackTo` | the secondary | — |
| `DataJurisdiction` | `plant-north` | `plant-north` |
| `EgressPermitted` | `false` | `false` |
| `RetainsInput` | `false` | `false` |

The appliance is on the plant network, so nothing leaves the site and `EgressPermitted` is false for both. Had the plant chosen a hosted service instead, §9.5 would have required it to be `true` — and, if the operator could not establish what the provider did with the images, `RetainsInput` `true` as well.

Both are `Pinned`. A `FollowsRef` primary would have been convenient and would have meant the artefact could change without anything else changing, which §9.3 treats as a promotion in disguise.

### C.4 A normal call, and a link failure {#sec-c-4-a-normal-call-and-a-link-failure}

A client calls `Invoke` on the primary with an image as `Payload` and its media type as `ContentType`. The response carries `ModelUsed` naming the full-precision model, `Usage` with `UnitKind` `images` and `InputUnits` 1, and `FinishReason` `Stop`.

Then the switch feeding the appliance fails.

The Server's next attempt does not answer. `Reachability` on the primary goes `Unreachable` and `ConsecutiveFailures` climbs; `LastSuccessAt` stops advancing. Because `FallbackPolicy` is `FallBackTo`, the call is served by the secondary, and this is the part that matters: **the response says so.** `ModelUsed` now names the quantized model, not the one the primary still points at.

A client that logged only the deployment would record that the full-precision model made every judgement that afternoon. A client that reads `ModelUsed` — as §8.2.1 requires — records what actually happened, which is what an audit a month later needs.

Note what did **not** change: the client called the same Method with the same arguments throughout, and never learned that inference moved from an appliance to the local controller except by reading the outputs it was going to read anyway.

### C.5 Throttling {#sec-c-5-throttling}

Had the appliance been saturated rather than unreachable, `Reachability` would have read `Throttled` and `RateLimit.RetryAfter` would have carried a wait.

The distinction is the point of separating the two values. Failing over a throttled endpoint moves load onto the weaker model for no reason; the endpoint will serve again shortly. Failing over an unreachable one is exactly right. From the outside the two look identical, which is why the Server states which it is rather than leaving a client to infer it from a timeout.

---

---

## Deploying a classical model (informative) {#anx-d annex=informative}

This annex is **informative**. Clause 8 is written around an envelope, and some of its vocabulary — capability names like `chat`, accounting in units that are often tokens — comes from the kind of model that made those terms familiar. Most industrial deployments run something else entirely: a fixed-shape tensor model, exported once, executed in-process, answering in microseconds.

This annex works that case end to end to show that the same envelope carries it with nothing bent. Every member named here is defined in Annex A.

### D.1 The model {#sec-d-1-the-model}

A gearbox condition classifier. Exported to **ONNX**, 4.8 MB, takes a window of vibration samples and returns a class distribution over four fault states. It runs on the line controller because a 20 ms budget does not survive a network hop, and because the plant does not permit raw vibration to leave the site.

Nothing about that description needs a member this specification does not already have.

### D.2 In the catalogue {#sec-d-2-in-the-catalogue}

| Member | Value |
|---|---|
| `ModelResourceType` id | `gearbox-fault` under publisher `plant-reliability` |
| `TaskKind` | `classification` |
| `Framework` | `onnxruntime` |
| `Digest` / `DigestAlgorithm` | SHA-256 of the `.onnx` file |
| `SizeBytes` | `5033164` |
| `Gated` | `false` |

`TaskKind` is a String, and `classification` is not drawn from any list this specification publishes. That is the point of it being a String: a catalogue that also holds `regression`, `anomaly-detection` and `remaining-useful-life` needs no amendment here to say so.

`SizeBytes` earns its place in this example. 4.8 MB is nothing; the same catalogue holds a vision model of 340 MB, and a controller with 64 MB of free storage needs to refuse **before** transferring rather than after.

### D.3 Getting it onto the controller {#sec-d-3-getting-it-onto-the-controller}

A `ModelImportJobType` with `Mode` = `Stage`, because `InferenceLocation` will be `OnServer` and an on-server deployment cannot reach the catalogue at inference time.

The job fetches, computes SHA-256 over what arrived, compares it with the `Digest` the catalogue declared, and sets `DigestVerified`. This is the whole of the integrity story for a model that will now decide whether a gearbox is failing, and §10.4 is why it is a **shall** here and nowhere else.

The resulting `ModelType` carries `ImportedFrom` back to the catalogue resource, so a year later *where did this come from* has an answer that does not depend on anyone having written it down.

### D.4 The shape contract {#sec-d-4-the-shape-contract}

`Inputs` and `Outputs` carry `TensorSignatureDataType`, and for a classical model they are the **entire** interface description:

| | `Name` | `ElementType` | `Shape` | `Layout` |
|---|---|---|---|---|
| Input | `window` | `float32` | `-1, 2048, 3` | `NWC` |
| Output | `probabilities` | `float32` | `-1, 4` | |

The leading `-1` is the batch axis, dynamic as ONNX exports usually leave it. `2048` is the window length and `3` the axis count, and both are fixed by the export — send 1024 samples and the runtime rejects the call.

This is why §6.2 insists the signatures are the only machine-readable description of what a deployment accepts. A client that reads them establishes at configuration time that its window length matches; a client that does not discovers it as a rejected call at 3 a.m. And `LabelClasses` — `["healthy", "bearing-wear", "tooth-crack", "misalignment"]` — is what makes `probabilities[2]` mean something, which is exactly why §6.2 forbids reordering it in place.

### D.5 The deployment {#sec-d-5-the-deployment}

| Member | Value |
|---|---|
| `InferenceLocation` | `OnServer` |
| `Source` | null — nothing to reach |
| `ApiDialect` | not applicable; where a source is named for a local runtime it is `EmbeddedRuntime` |
| `AcceleratorKind` | `Cpu` |
| `VersionBinding` | `Pinned` |
| `FallbackPolicy` | `Fail` |
| `DataJurisdiction` | `plant-north` |
| `EgressPermitted` | `false` |
| `RetainsInput` | `false` |
| `LatencyBudget` | 20 ms |

`FallbackPolicy` is `Fail` deliberately. There is no second model, and a condition classifier that quietly returns a stale verdict is worse than one that says it could not answer — the whole value of the reading is that it is current.

`EgressPermitted` is `false` and means it: the bytes never leave the controller, let alone the site.

### D.6 Calling it {#sec-d-6-calling-it}

`Invoke` takes the tensor as `Payload` with a `ContentType` that says how it is encoded — for example `application/octet-stream` for a raw little-endian `float32` buffer in the declared layout, or a media type the deployment publishes for a framed encoding.

**This specification does not standardise a tensor wire format, and that is deliberate.** The candidates — raw buffers, protobuf tensors, Arrow, npy — are each right in some deployment and wrong in others, and a Server that already speaks one to its runtime should not have to transcode into a format chosen here. `ContentType` names which one is in use, which is what a client actually needs, and the shape contract of §D.4 tells it what must be inside whichever it is.

The response comes back through the same envelope:

| Output | Value here |
|---|---|
| `ResponsePayload` | four `float32` probabilities |
| `ModelUsed` | the staged `ModelType` |
| `Usage` | `UnitKind` = `samples`, `InputUnits` = `2048`, `OutputUnits` = `4`, `TotalUnits` = `2048` |
| `FinishReason` | `Stop` |
| `SafetyAssessment` | empty — no policy applies |

`Usage` is the member that would have been mis-modelled had the accounting been named in tokens. This model consumes samples. A field called `InputTokens` here would be either empty or a lie, and §8.2.3 is why it is not called that.

`FinishReason` is `Stop` on every successful call, and a reader may reasonably ask what it is for on a model that cannot truncate. It is for the client, which does not know which kind of model is behind the deployment and should not have to — that is the same-envelope property doing its job.

### D.7 Capabilities {#sec-d-7-capabilities}

What this deployment does **not** advertise is as informative as what it does, and means nothing against it.

`Capabilities` on this deployment names `tensor-inference` supported and nothing else. It does not name `chat`, `streaming` or `tool-call`.

That is not a deficiency and does not make the deployment a partial implementation of anything. `Capabilities` is an **open list** (§8.4) precisely so that a deployment describes what it does rather than scoring itself against a menu — and a client that needs a chat capability finds it absent and looks elsewhere, which is the correct outcome and required no negotiation.

The Server claims **AI-Base**, **AI-Invoke**, **AI-Signatures**, **AI-Residency**, **AI-Catalogue** and **AI-Import**. It claims neither **AI-Federation** — there is nothing remote — nor **AI-Learning**, because this model is retrained offline by the reliability team and promoted by a fresh import. Both absences are ordinary.

## Types the prose does not introduce {#sec-types-not-introduced}

The types below are declared by the model. Each clause was generated because no clause of this document named its type; fold them into the prose where they belong.

### AiRootType {#sec-airoottype}

Server-level entry point. A client that has just connected browses here to find every model, dataset, deployment and learning job the Server describes, without knowing its layout.

*Table - AiRootType Definition* {#tbl-airoottype-definition defines=AiRootType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AiRootType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:BaseObjectType defined in OPC 10000-5 |  |  |  |  |  |
| 0:HasComponent | Object | 2:Models |  | 0:FolderType | M |
| 0:HasComponent | Object | 2:Datasets |  | 0:FolderType | O |
| 0:HasComponent | Object | 2:Deployments |  | 0:FolderType | M |
| 0:HasComponent | Object | 2:LearningJobs |  | 0:FolderType | O |
| 0:HasProperty | Variable | 2:SpecificationVersion | 0:String | 0:PropertyType | M |
| 0:HasComponent | Object | 2:Sources |  | 0:FolderType | O |
| 0:HasComponent | Object | 2:Registries |  | 0:FolderType | O |
| 0:HasComponent | Object | 2:Evaluations |  | 0:FolderType | O |
| 0:HasComponent | Object | 2:Jobs |  | 0:FolderType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AiModelManagement |  |  |  |  |  |

### LearningJobType {#sec-learningjobtype}

One turn of the capture, label, train and promote loop. It exists so that corrections arriving from a consuming application have somewhere to accumulate and a defined path into a new model version. A Server may implement only the capture stages and leave training to an external MLOps system - the state machine is the same either way.

*Table - LearningJobType Definition* {#tbl-learningjobtype-definition defines=LearningJobType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:LearningJobType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 2:AiJobType defined in [](#sec-aijobtype) |  |  |  |  |  |
| 0:HasProperty | Variable | 2:State | 2:LearningJobStateEnum | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:Dataset | 0:NodeId | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:BaseModel | 0:NodeId | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:CandidateModel | 0:NodeId | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:SamplesCollected | 0:UInt64 | 0:PropertyType | O |
| 0:HasComponent | Method | 2:StartCollection |  |  | O |
| 0:HasComponent | Method | 2:StopCollection |  |  | O |
| 0:HasComponent | Method | 2:TriggerTraining |  |  | O |
| 0:HasComponent | Method | 2:PromoteModel |  |  | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AiModelManagement |  |  |  |  |  |

#### StartCollection {#sec-learningjobtype-startcollection type=LearningJobType method=StartCollection}

Begin accumulating samples and corrections into the dataset.

**Signature**

```text
StartCollection ();
```

*Table - StartCollection Method Arguments* {#tbl-startcollection-method-arguments}

| **Argument** | **Description** |
| --- | --- |

#### StopCollection {#sec-learningjobtype-stopcollection type=LearningJobType method=StopCollection}

Stop accumulating samples.

**Signature**

```text
StopCollection ();
```

*Table - StopCollection Method Arguments* {#tbl-stopcollection-method-arguments}

| **Argument** | **Description** |
| --- | --- |

#### TriggerTraining {#sec-learningjobtype-triggertraining type=LearningJobType method=TriggerTraining}

Request that a candidate model be trained from the collected dataset.

**Signature**

```text
TriggerTraining (
  [out] 0:Boolean Accepted);
```

*Table - TriggerTraining Method Arguments* {#tbl-triggertraining-method-arguments}

| **Argument** | **Description** |
| --- | --- |
| Accepted | True when the request was queued. |

#### PromoteModel {#sec-learningjobtype-promotemodel type=LearningJobType method=PromoteModel}

Promote the candidate model so that deployments begin using it. A Server SHALL require a distinct authorization for this Method: it changes what the equipment does without changing anything a reader of the address space would notice, which is precisely the change that needs a separate permission.

**Signature**

```text
PromoteModel (
  [in]  0:NodeId Deployment,
  [out] 0:NodeId PromotedModel);
```

*Table - PromoteModel Method Arguments* {#tbl-promotemodel-method-arguments}

| **Argument** | **Description** |
| --- | --- |
| Deployment | Deployment to update, or null for all. |
| PromotedModel | The model now in use. |

### ModelImportJobType {#sec-modelimportjobtype}

Brings a model from a catalogue into this Server. It federates by default - materializing the catalogue entry as a ModelType whose artefact stays where it is - and stages the artefact when the target deployment could not otherwise reach it. Staging is the moment a substituted artefact would enter, which is why clause 10 requires the Digest to be verified there and nowhere else.

*Table - ModelImportJobType Definition* {#tbl-modelimportjobtype-definition defines=ModelImportJobType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:ModelImportJobType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 2:AiJobType defined in [](#sec-aijobtype) |  |  |  |  |  |
| 0:HasProperty | Variable | 2:Source | 0:NodeId | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:ModelReference | 2:ModelReferenceDataType | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:Mode | 2:ImportModeEnum | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:TargetDeployment | 0:NodeId | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:ImportedModel | 0:NodeId | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:BytesTransferred | 0:UInt64 | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:DigestVerified | 0:Boolean | 0:PropertyType | O |
| 0:HasComponent | Method | 2:Cancel |  |  | O |
| 0:HasProperty | Variable | 2:Registry | 0:NodeId | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AiModelManagement |  |  |  |  |  |

#### Cancel {#sec-modelimportjobtype-cancel type=ModelImportJobType method=Cancel}

Abandon the import. A partially staged artefact SHALL be discarded rather than left where a later deployment could pick it up.

**Signature**

```text
Cancel ();
```

*Table - Cancel Method Arguments* {#tbl-cancel-method-arguments}

| **Argument** | **Description** |
| --- | --- |

### InferenceJobType {#sec-inferencejobtype}

One asynchronous inference request. It exists because not every inference returns while the caller waits: a batch scored overnight and a long analysis over recorded data are ordinary industrial cases, and modelling them as a Method that blocks for hours is not.

*Table - InferenceJobType Definition* {#tbl-inferencejobtype-definition defines=InferenceJobType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:InferenceJobType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 2:AiJobType defined in [](#sec-aijobtype) |  |  |  |  |  |
| 0:HasProperty | Variable | 2:Deployment | 0:NodeId | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:RequestPayload | 0:ByteString | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:RequestContentType | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:ResponsePayload | 0:ByteString | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:ResponseContentType | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:ModelUsed | 0:NodeId | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:Usage | 2:UsageDataType | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:FinishReason | 2:FinishReasonEnum | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:SafetyAssessment | 2:SafetyAssessmentDataType[] | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:RequestUri | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:ResponseUri | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:TransferRequired | 0:Boolean | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:Transfer | 0:NodeId | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AiModelManagement |  |  |  |  |  |

### EvaluationRunType {#sec-evaluationruntype}

One measurement of a model against a dataset. It is a first-class object and not a field on the model because the same model is evaluated many times, and because the run that gated a promotion has to remain readable afterwards to answer why the promotion was allowed.

*Table - EvaluationRunType Definition* {#tbl-evaluationruntype-definition defines=EvaluationRunType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:EvaluationRunType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:BaseObjectType defined in OPC 10000-5 |  |  |  |  |  |
| 0:HasProperty | Variable | 2:RunId | 0:String | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:EvaluatedModel | 0:NodeId | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:Dataset | 0:NodeId | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:CompletedAt | 0:UtcTime | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:Metrics | 2:EvaluationMetricDataType[] | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:Passed | 0:Boolean | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:ReportUri | 0:String | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AiModelManagement |  |  |  |  |  |

### ModelCardType {#sec-modelcardtype}

What a human needs to decide whether a model may be used here: what it is for, where it stops working, and under what terms. Separate from the nameplate because a nameplate answers 'which artefact is this' and a card answers 'should this be running on my line'.

*Table - ModelCardType Definition* {#tbl-modelcardtype-definition defines=ModelCardType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:ModelCardType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:BaseObjectType defined in OPC 10000-5 |  |  |  |  |  |
| 0:HasProperty | Variable | 2:IntendedUse | 0:LocalizedText | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:Limitations | 0:LocalizedText | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:OutOfScopeUse | 0:LocalizedText | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:License | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:TrainingDataCutoff | 0:UtcTime | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:EthicalConsiderations | 0:LocalizedText | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:ContactUri | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:DeprecatedFrom | 0:UtcTime | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:SupportedUntil | 0:UtcTime | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AiModelManagement |  |  |  |  |  |

### ModelRegistryType {#sec-modelregistrytype}

A catalogue of models and the datasets they were trained on. It narrows the abstract registry's group placeholder to model publishers, so that a client browsing it knows what it will find rather than discovering it.

*Table - ModelRegistryType Definition* {#tbl-modelregistrytype-definition defines=ModelRegistryType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:ModelRegistryType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 1:RegistryType defined in OPC 99004-1 |  |  |  |  |  |
| 0:Organizes | Object | 2:<Group> |  | 2:ModelPublisherType | OP |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AiModelManagement |  |  |  |  |  |

### ModelPublisherType {#sec-modelpublishertype}

One publisher's namespace within a model registry: the organisation or project that released the models it contains. Publisher is the first element of the publisher/name/version triple by which every catalogue in practice identifies a model.

*Table - ModelPublisherType Definition* {#tbl-modelpublishertype-definition defines=ModelPublisherType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:ModelPublisherType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 1:GroupType defined in OPC 99004-1 |  |  |  |  |  |
| 0:Organizes | Object | 2:<Resource> |  | 2:AiResourceType | OP |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AiModelManagement |  |  |  |  |  |

### AiResourceType {#sec-airesourcetype}

Abstract base of everything a model registry holds. It exists so that the inherited <Resource> placeholder can be narrowed ONCE to something that admits models and datasets and nothing else - a publisher holds both, and a placeholder can be overridden only by one declaration.

*Table - AiResourceType Definition* {#tbl-airesourcetype-definition defines=AiResourceType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AiResourceType |  |  |  |  |
| IsAbstract | True |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 1:ResourceType defined in OPC 99004-1 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AiModelManagement |  |  |  |  |  |

### ModelResourceType {#sec-modelresourcetype}

One model in a catalogue. Its versions are immutable and identified by content, so a version that has been seen cannot change meaning; mutable names such as a branch or a release channel are pointers AT versions, never versions themselves. Because the base type is a FileType, a Server that holds the artefact serves it through the inherited Open, Read and Close; one that only describes it leaves those unimplemented and points at the artefact instead.

*Table - ModelResourceType Definition* {#tbl-modelresourcetype-definition defines=ModelResourceType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:ModelResourceType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 2:AiResourceType defined in [](#sec-airesourcetype) |  |  |  |  |  |
| 0:HasProperty | Variable | 2:TaskKind | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:Framework | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:Digest | 0:ByteString | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:DigestAlgorithm | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:SizeBytes | 0:UInt64 | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:Gated | 0:Boolean | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:MutableRefs | 0:String[] | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:DigestProvenance | 2:DigestProvenanceEnum | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AiModelManagement |  |  |  |  |  |

### DatasetResourceType {#sec-datasetresourcetype}

One dataset in a catalogue, a sibling of ModelResourceType rather than something beneath it: a dataset outlives the models trained on it and is cited by several.

*Table - DatasetResourceType Definition* {#tbl-datasetresourcetype-definition defines=DatasetResourceType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:DatasetResourceType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 2:AiResourceType defined in [](#sec-airesourcetype) |  |  |  |  |  |
| 0:HasProperty | Variable | 2:SourceKind | 2:DatasetSourceEnum | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:SampleCount | 0:UInt64 | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:Digest | 0:ByteString | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:DigestAlgorithm | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:SizeBytes | 0:UInt64 | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AiModelManagement |  |  |  |  |  |

### InferenceTransferType {#sec-inferencetransfertype}

One chunked inference exchange. It exists because Invoke carries its payload as a ByteString, and a ByteString is bounded by MaxByteStringLength, the negotiated MaxMessageSize and the Session's MaxResponseMessageSize - none of which the model gets to choose. An image, a point cloud or a window of high-rate samples exceeds those routinely, and a call that cannot carry the input is not a call.

Request and Response are Part 5 FileType objects: the client opens the request, writes it in chunks it selects, and closes it; after Execute the response is read the same way. Nothing here invents a transfer protocol, because OPC UA already has one and every client already implements it.

*Table - InferenceTransferType Definition* {#tbl-inferencetransfertype-definition defines=InferenceTransferType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:InferenceTransferType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:BaseObjectType defined in OPC 10000-5 |  |  |  |  |  |
| 0:HasProperty | Variable | 2:TransferId | 0:String | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:State | 2:TransferStateEnum | 0:PropertyType | M |
| 0:HasComponent | Object | 2:Request |  | 0:FileType | M |
| 0:HasComponent | Object | 2:Response |  | 0:FileType | M |
| 0:HasProperty | Variable | 2:ContentType | 0:String | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:ResponseContentType | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:ModelUsed | 0:NodeId | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:Usage | 2:UsageDataType | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:FinishReason | 2:FinishReasonEnum | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:SafetyAssessment | 2:SafetyAssessmentDataType[] | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:LastError | 0:LocalizedText | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:ExpiresAt | 0:UtcTime | 0:PropertyType | O |
| 0:HasComponent | Method | 2:Execute |  |  | M |
| 0:HasComponent | Method | 2:Abort |  |  | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AiModelManagement |  |  |  |  |  |

#### Execute {#sec-inferencetransfertype-execute type=InferenceTransferType method=Execute}

Runs inference over the written request. The Method returns as soon as the request is accepted; State and the envelope members carry the outcome, which is what lets one exchange span a payload too large to have been a single call in the first place.

**Signature**

```text
Execute (
  [out] 0:Boolean Accepted);
```

*Table - Execute Method Arguments* {#tbl-execute-method-arguments}

| **Argument** | **Description** |
| --- | --- |
| Accepted | False when the request was incomplete or already executed. |

#### Abort {#sec-inferencetransfertype-abort type=InferenceTransferType method=Abort}

Abandons the exchange and releases what it holds. A client that has stopped caring about a response SHOULD say so rather than leaving the Server to wait out ExpiresAt.

**Signature**

```text
Abort ();
```

*Table - Abort Method Arguments* {#tbl-abort-method-arguments}

| **Argument** | **Description** |
| --- | --- |

### ModelPromotedEventType {#sec-modelpromotedeventtype}

A deployment's configured UsesModel target changed. Raised on promotion, and also on a rollback or any other Server-initiated substitution, because a consumer auditing what decided a verdict cares that the model changed and not why the operator called it a promotion.

*Table - ModelPromotedEventType Definition* {#tbl-modelpromotedeventtype-definition defines=ModelPromotedEventType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:ModelPromotedEventType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:BaseEventType defined in OPC 10000-5 |  |  |  |  |  |
| 0:HasProperty | Variable | 2:Deployment | 0:NodeId | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:NewModel | 0:NodeId | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:PreviousModel | 0:NodeId | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:EvaluationRun | 0:NodeId | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:PromotedBy | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:PromotionRecord | 0:NodeId | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AiModelManagement Events |  |  |  |  |  |

### PromotionRecordType {#sec-promotionrecordtype}

Immutable, authoritative record of one successful substitution of a DeploymentType UsesModel target. The record is created atomically with the substitution, is read-only after creation, and remains available for at least the lifetime of the deployment.

*Table - PromotionRecordType Definition* {#tbl-promotionrecordtype-definition defines=PromotionRecordType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:PromotionRecordType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:BaseObjectType defined in OPC 10000-5 |  |  |  |  |  |
| 0:HasProperty | Variable | 2:RecordId | 0:String | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:Deployment | 0:NodeId | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:DeploymentId | 0:String | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:PreviousModel | 0:NodeId | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:NewModel | 0:NodeId | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:PreviousModelIdentity | 2:ModelIdentitySnapshotDataType | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:NewModelIdentity | 2:ModelIdentitySnapshotDataType | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:EvaluationRun | 0:NodeId | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:EvaluationRunId | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 2:ChangedAt | 0:UtcTime | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:ChangedBy | 0:String | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:ChangeKind | 2:ModelChangeKindEnum | 0:PropertyType | M |
| 0:HasProperty | Variable | 2:Reason | 0:LocalizedText | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AiModelManagement |  |  |  |  |  |

### InferenceLocationEnum {#sec-inferencelocationenum}

Where inference executes. The result contract is identical in every case; this property exists so a client can reason about latency, availability and the trust boundary without changing how it reads results.

*Table - InferenceLocationEnum Definition* {#tbl-inferencelocationenum-definition defines=InferenceLocationEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:InferenceLocationEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[4] | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AiModelManagement DataTypes |  |  |  |  |  |

### AcceleratorKindEnum {#sec-acceleratorkindenum}

Compute device executing the model.

*Table - AcceleratorKindEnum Definition* {#tbl-acceleratorkindenum-definition defines=AcceleratorKindEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AcceleratorKindEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[6] | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AiModelManagement DataTypes |  |  |  |  |  |

### DeploymentStateEnum {#sec-deploymentstateenum}

Runtime lifecycle state of a deployment.

*Table - DeploymentStateEnum Definition* {#tbl-deploymentstateenum-definition defines=DeploymentStateEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:DeploymentStateEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[5] | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AiModelManagement DataTypes |  |  |  |  |  |

### DatasetSourceEnum {#sec-datasetsourceenum}

Provenance of the samples in a dataset.

*Table - DatasetSourceEnum Definition* {#tbl-datasetsourceenum-definition defines=DatasetSourceEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:DatasetSourceEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[3] | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AiModelManagement DataTypes |  |  |  |  |  |

### LearningJobStateEnum {#sec-learningjobstateenum}

State of a dataset-capture, retraining and promotion cycle.

*Table - LearningJobStateEnum Definition* {#tbl-learningjobstateenum-definition defines=LearningJobStateEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:LearningJobStateEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[8] | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AiModelManagement DataTypes |  |  |  |  |  |

### FinishReasonEnum {#sec-finishreasonenum}

Why an inference call stopped producing output. A client that treats every non-error response as complete will silently accept a truncated one, which is why this is Mandatory on a response rather than a diagnostic.

*Table - FinishReasonEnum Definition* {#tbl-finishreasonenum-definition defines=FinishReasonEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:FinishReasonEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[6] | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AiModelManagement DataTypes |  |  |  |  |  |

### ApiDialectEnum {#sec-apidialectenum}

Wire contract a remote inference endpoint speaks. A Server needs this to call an endpoint it did not deploy; without it EndpointUri is a string nobody can act on. It describes the REMOTE endpoint and never affects how an OPC UA client calls this Server.

*Table - ApiDialectEnum Definition* {#tbl-apidialectenum-definition defines=ApiDialectEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:ApiDialectEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[6] | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AiModelManagement DataTypes |  |  |  |  |  |

### AuthenticationKindEnum {#sec-authenticationkindenum}

How the Server authenticates ITSELF to a remote inference endpoint. This is not how a client authenticates to this Server, which is the ordinary OPC UA Session security and is unaffected.

*Table - AuthenticationKindEnum Definition* {#tbl-authenticationkindenum-definition defines=AuthenticationKindEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:AuthenticationKindEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[5] | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AiModelManagement DataTypes |  |  |  |  |  |

### FallbackPolicyEnum {#sec-fallbackpolicyenum}

What the Server does when a deployment cannot serve. This is the question a plant asks that no cloud inference API answers, because a cloud API assumes the caller can simply wait.

*Table - FallbackPolicyEnum Definition* {#tbl-fallbackpolicyenum-definition defines=FallbackPolicyEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:FallbackPolicyEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[3] | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AiModelManagement DataTypes |  |  |  |  |  |

### VersionBindingEnum {#sec-versionbindingenum}

Whether a deployment is bound to one immutable model version or follows a moving pointer. Stated structurally rather than as an upgrade policy, because what a client needs to know is whether the artefact can change under it, not what schedule someone intends to change it on.

*Table - VersionBindingEnum Definition* {#tbl-versionbindingenum-definition defines=VersionBindingEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:VersionBindingEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[2] | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AiModelManagement DataTypes |  |  |  |  |  |

### ImportModeEnum {#sec-importmodeenum}

Whether an import job brings the model's description or its bytes.

*Table - ImportModeEnum Definition* {#tbl-importmodeenum-definition defines=ImportModeEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:ImportModeEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[3] | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AiModelManagement DataTypes |  |  |  |  |  |

### SafetySeverityEnum {#sec-safetyseverityenum}

Severity of one safety finding. The scale is the convergent industry one; what each level means for a given category is the policy's business, not this specification's.

*Table - SafetySeverityEnum Definition* {#tbl-safetyseverityenum-definition defines=SafetySeverityEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:SafetySeverityEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[4] | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AiModelManagement DataTypes |  |  |  |  |  |

### ReachabilityEnum {#sec-reachabilityenum}

Whether the Server can currently reach a deployment's execution site.

*Table - ReachabilityEnum Definition* {#tbl-reachabilityenum-definition defines=ReachabilityEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:ReachabilityEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[4] | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AiModelManagement DataTypes |  |  |  |  |  |

### TransferStateEnum {#sec-transferstateenum}

Stage of a chunked inference exchange. A client reads this rather than inferring progress from which Methods have succeeded, because a transfer that failed mid-write and one that has not started look alike from outside.

*Table - TransferStateEnum Definition* {#tbl-transferstateenum-definition defines=TransferStateEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:TransferStateEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[6] | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AiModelManagement DataTypes |  |  |  |  |  |

### DigestProvenanceEnum {#sec-digestprovenanceenum}

Where a Digest came from, or why there is none. Digest is Mandatory so that its absence is uniform and browsable rather than indistinguishable from a Server that does not implement digests - but 'empty' then carries two different meanings, and a client that must decide whether to trust an artefact needs them apart. This member is what tells them apart, and it does the same job for a digest that IS present: a value the source asserted and a value this Server computed over bytes are not the same evidence, and only one of them survives a substituted artefact.

*Table - DigestProvenanceEnum Definition* {#tbl-digestprovenanceenum-definition defines=DigestProvenanceEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:DigestProvenanceEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[4] | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AiModelManagement DataTypes |  |  |  |  |  |

### ModelChangeKindEnum {#sec-modelchangekindenum}

The trigger that caused a deployment's UsesModel reference to be substituted. Classification is by the administrative trigger, never by comparing model versions: version strings are not necessarily ordered and a rollback can target a version whose spelling sorts later.

*Table - ModelChangeKindEnum Definition* {#tbl-modelchangekindenum-definition defines=ModelChangeKindEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:ModelChangeKindEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[5] | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AiModelManagement DataTypes |  |  |  |  |  |

### TensorSignatureDataType {#sec-tensorsignaturedatatype}

Shape and element type of one model input or output tensor. This is what lets a client check that what it intends to send matches what the model expects, before it sends it.

*Table - TensorSignatureDataType Definition* {#tbl-tensorsignaturedatatype-definition defines=TensorSignatureDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:TensorSignatureDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Structure defined in OPC 10000-3 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AiModelManagement DataTypes |  |  |  |  |  |

### ModelReferenceDataType {#sec-modelreferencedatatype}

Identity of a model as a publisher, name and version triple. Every model catalogue in practice identifies a model this way, which is why an import job takes this rather than a URL: a URL says where a copy is today, the triple says which artefact is meant.

*Table - ModelReferenceDataType Definition* {#tbl-modelreferencedatatype-definition defines=ModelReferenceDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:ModelReferenceDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Structure defined in OPC 10000-3 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AiModelManagement DataTypes |  |  |  |  |  |

### UsageDataType {#sec-usagedatatype}

What one inference call consumed. Deliberately NOT named in tokens: a token is one accounting unit among several, and a model that consumes images, samples or seconds of audio needs the same accounting. UnitKind says which unit the counts are in.

*Table - UsageDataType Definition* {#tbl-usagedatatype-definition defines=UsageDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:UsageDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Structure defined in OPC 10000-3 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AiModelManagement DataTypes |  |  |  |  |  |

### CapabilityDataType {#sec-capabilitydatatype}

One capability a deployment does or does not have. An open list rather than an enumeration because the set of things a model can do is not closed, and a client that cannot recognise a capability name is no worse off than one that cannot recognise an enumeration value it has never seen.

*Table - CapabilityDataType Definition* {#tbl-capabilitydatatype-definition defines=CapabilityDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:CapabilityDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Structure defined in OPC 10000-3 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AiModelManagement DataTypes |  |  |  |  |  |

### SafetyAssessmentDataType {#sec-safetyassessmentdatatype}

One finding from a safety policy applied to an inference call. Category is a String and not an enumeration because harm categories are set by the policy an installation adopts, and an industrial taxonomy looks nothing like a consumer one.

*Table - SafetyAssessmentDataType Definition* {#tbl-safetyassessmentdatatype-definition defines=SafetyAssessmentDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:SafetyAssessmentDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Structure defined in OPC 10000-3 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AiModelManagement DataTypes |  |  |  |  |  |

### EvaluationMetricDataType {#sec-evaluationmetricdatatype}

One measured metric from an evaluation run, with the threshold it was judged against. The threshold travels with the metric because a metric without its acceptance criterion cannot be acted on, and a reviewer reading it a year later has no way to recover what 'good' meant.

*Table - EvaluationMetricDataType Definition* {#tbl-evaluationmetricdatatype-definition defines=EvaluationMetricDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:EvaluationMetricDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Structure defined in OPC 10000-3 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AiModelManagement DataTypes |  |  |  |  |  |

### RateLimitDataType {#sec-ratelimitdatatype}

Capacity a remote endpoint is currently granting. Surfaced so a client can distinguish 'the model said no' from 'the quota said no', which are different faults with different remedies.

*Table - RateLimitDataType Definition* {#tbl-ratelimitdatatype-definition defines=RateLimitDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:RateLimitDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Structure defined in OPC 10000-3 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AiModelManagement DataTypes |  |  |  |  |  |

### ModelIdentitySnapshotDataType {#sec-modelidentitysnapshotdatatype}

Durable identity of a model at the instant a deployment's UsesModel reference changed. It is copied into a promotion record rather than resolved through a retained NodeId, so the history remains complete after the ModelType instance or artefact location disappears. Digest trust provenance is retained with the digest so a later reader can tell whether it was declared, computed or verified.

*Table - ModelIdentitySnapshotDataType Definition* {#tbl-modelidentitysnapshotdatatype-definition defines=ModelIdentitySnapshotDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:ModelIdentitySnapshotDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Structure defined in OPC 10000-3 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AiModelManagement DataTypes |  |  |  |  |  |

### UsesModel {#sec-usesmodel}

Links a Deployment to the Model it executes. Clause 6.5 requires exactly one such reference per deployment so the model serving now is unambiguous. Historical result provenance uses the ModelUsed identity returned by invocation and retained by the consuming specification.

*Table - UsesModel Definition* {#tbl-usesmodel-definition defines=UsesModel}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:UsesModel |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:NonHierarchicalReferences defined in OPC 10000-5 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AiModelManagement ReferenceTypes |  |  |  |  |  |

### TrainedOn {#sec-trainedon}

Links a Model to a Dataset it was trained or validated on. A model whose training data cannot be named is a model whose behaviour cannot be explained, which is why this reference exists rather than a string.

*Table - TrainedOn Definition* {#tbl-trainedon-definition defines=TrainedOn}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:TrainedOn |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:NonHierarchicalReferences defined in OPC 10000-5 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AiModelManagement ReferenceTypes |  |  |  |  |  |

### DerivedFrom {#sec-derivedfrom}

Links a Model to the Model it was fine-tuned, distilled or quantized from. Lineage is a chain, not a field: a model three derivations from its base is answerable for all three, and a string naming the immediate parent cannot be walked.

*Table - DerivedFrom Definition* {#tbl-derivedfrom-definition defines=DerivedFrom}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:DerivedFrom |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:NonHierarchicalReferences defined in OPC 10000-5 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AiModelManagement ReferenceTypes |  |  |  |  |  |

### FallsBackTo {#sec-fallsbackto}

Links a Deployment to the Deployment that serves in its place when it cannot. Clause 9 forbids a cycle, and requires the response to say which deployment actually answered.

*Table - FallsBackTo Definition* {#tbl-fallsbackto-definition defines=FallsBackTo}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:FallsBackTo |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:NonHierarchicalReferences defined in OPC 10000-5 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AiModelManagement ReferenceTypes |  |  |  |  |  |

### ImportedFrom {#sec-importedfrom}

Links a Model to the catalogue resource an import job materialized it from. This is what makes 'where did this model come from' answerable after the fact, rather than only at the moment of import.

*Table - ImportedFrom Definition* {#tbl-importedfrom-definition defines=ImportedFrom}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:ImportedFrom |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:NonHierarchicalReferences defined in OPC 10000-5 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AiModelManagement ReferenceTypes |  |  |  |  |  |

### EvaluatedBy {#sec-evaluatedby}

Links a Model to an EvaluationRun that measured it. Optional and repeating: a model may be evaluated many times, and the run that gated its promotion is not necessarily the last one.

*Table - EvaluatedBy Definition* {#tbl-evaluatedby-definition defines=EvaluatedBy}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 2:EvaluatedBy |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:NonHierarchicalReferences defined in OPC 10000-5 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| AiModelManagement ReferenceTypes |  |  |  |  |  |
