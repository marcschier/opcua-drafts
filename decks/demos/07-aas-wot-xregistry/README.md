# Demo 7 — AAS + WoT + xRegistry

## What this shows

- An AAS V3 shell can be mapped losslessly into an OPC UA AddressSpace.
- The same shell can be catalogued as xRegistry groups, resources and versions.
- A Thing Description can carry the AAS vocabulary plus the OPC UA binding metadata.
- The registry half exists in the stack today; the AAS half lives in drafts and generated artefacts.

## What it proves

It proves the design is one asset with three projections rather than three unrelated catalogues. The shared identifier construction lets the same shell be recognized over OPC UA and over HTTP, while xRegistry adds version history that the AAS metamodel does not carry.

## Prerequisites

- The drafts repository at `D:\git\marcschier\opcua-drafts`.
- The stack checkout at `D:\git\UA-.NETStandard6` on `master` for the xRegistry implementation.
- Do not run the AAS tooling during the presentation; use the generated files and examples as evidence.

## How to present it without running it

Open these files side by side:

```powershell
code D:\git\marcschier\opcua-drafts\companion-specs\AAS\README.md
code D:\git\marcschier\opcua-drafts\companion-specs\AAS\OPC-UA-AAS.md
code D:\git\marcschier\opcua-drafts\companion-specs\AAS\xRegistry-AAS.md
code D:\git\UA-.NETStandard6\docs\XRegistry.md
```

Then show the generated examples under `companion-specs\AAS\examples\jsonld` and `companion-specs\AAS\examples\wot`.

## Step by step

1. **Start with the live AAS view.** Show `OPC-UA-AAS.md` and the generated NodeSet. Say: "The shell is browseable as OPC UA nodes; values are live and typed, and the mapping is lossless over the AAS value space."
2. **Move to the registry view.** Show `xRegistry-AAS.md` section 1.2 and 1.4. Say: "A repository entry and a descriptor are the same resource identity with different hosting, and versions are what let a client ask what the shell said last March."
3. **Show the stack half that already exists.** Open `docs\XRegistry.md`. Say: "The stack already has the abstract registry, FileType transfer, content identity, fast-path NodeIds and server/client packages. AAS would subtype this rather than inventing its own registry."
4. **Show the WoT projection.** Open one file from `examples\wot\submodels`. Say: "The Thing Description is not a second truth. It carries the AAS graph and the OPC UA type binding so a WoT runtime knows how to reach the same asset."
5. **Close on the gap.** Say: "This is a paper-and-generated-artifact walkthrough today. The registry substrate runs; the AAS server that combines all three views has not been written."

## Talking points

- AAS descriptors and repositories collapse into xRegistry's document-versus-URL distinction.
- xRegistry versions add history; AAS `administration.version` is not a history stack.
- The WoT examples are generated from the same AAS sources as the JSON-LD fixtures.
- The stack implementation is domain-neutral; AAS would be a domain registry on top.
- The AAS draft is honest about value-space losslessness, not byte-identical round trips.

## Troubleshooting

- If a file is missing, refresh the drafts checkout; the AAS work is in `companion-specs\AAS`.
- If the WoT type-binding proposal file is absent, use the AAS README and generated WoT examples; the README records that the binding was adopted in the WoT Binding draft.
- Do not imply there is an AAS sample server in the stack. There is not.
- Do not run `tools\jsonld\wot_bridge.py` live unless the corpus and Python dependencies are already prepared.

## What it would take to make this runnable

- Add an `Opc.Ua.I4AAS` model project to the stack from `Opc.Ua.I4AAS.NodeSet2.xml` and NodeIds.
- Add server node managers that materialize AAS shells, submodels and submodel elements as live nodes.
- Add an AAS domain registry that subtypes the stack's `Opc.Ua.XRegistry.Server` base managers.
- Implement the identifier construction shared by the OPC UA and xRegistry projections.
- Add a loader for AAS JSON, JSON-LD or AASX packages and persist resources through `IXRegistryResourceStore`.
- Add a client or presenter sample that browses the live shell, reads the xRegistry versioned resource and opens the matching Thing Description.
- Add tests proving AAS → OPC UA → AAS and registry identity round trips over the existing corpus.

## Links

- Draft overview: `D:\git\marcschier\opcua-drafts\companion-specs\AAS\README.md`
- OPC UA AAS draft: `D:\git\marcschier\opcua-drafts\companion-specs\AAS\OPC-UA-AAS.md`
- xRegistry AAS draft: `D:\git\marcschier\opcua-drafts\companion-specs\AAS\xRegistry-AAS.md`
- AAS package draft: `D:\git\marcschier\opcua-drafts\companion-specs\AAS\xRegistry-AAS-Packages.md`
- JSON-LD draft: `D:\git\marcschier\opcua-drafts\companion-specs\AAS\AAS-JsonLd.md`
- Stack xRegistry guide: `D:\git\UA-.NETStandard6\docs\XRegistry.md`
- Stack packages: `D:\git\UA-.NETStandard6\src\Opc.Ua.XRegistry*`

