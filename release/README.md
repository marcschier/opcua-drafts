# Specification release and return routing

`release/manifest.json` records each specification's review owner, release closure, public holdbacks, publication identity and reversible content-path mappings. The mover never infers ownership from a directory scan.

| Working group | Review repository | Local submodule |
| --- | --- | --- |
| Core | `OPCF-Members/spec-drafts` | `spec-drafts` |
| WoT | `OPCF-Members/OPC10100-WoT` | `OPC10100-WoT` |
| Metaverse | `OPCF-Members/OPC12000-Metaverse` | `OPC12000-Metaverse` |
| CloudIntegration | `OPCF-Members/OPC30450-CloudInitiative` | `OPC30450-CloudIntegration` |

The CloudIntegration working group owns xRegistry. The repository URL retains its existing `CloudInitiative` spelling; this is not a request to rename the repository.

## Inspecting a route

```powershell
python release\tools\release_spec.py status
python release\tools\release_spec.py route wot-connectivity
python release\tools\release_spec.py route xregistry
```

`route` returns JSON containing the repository, submodule, working-group name and layout mode. The release workflow uses this output for its checkout, permission preflight and PR target rather than hard-coding `spec-drafts`.

Core retains its existing grouped layout. WG specifications use the destination's `source/<spec>`, flat `model` files, and `extras/<spec>` support layout. More specific mappings cover generators formerly under `source`, informative research, example overlays, and allocation ledgers. Reverse mappings enumerate the actual review checkout, so destination-only additions are included even when the public source directory no longer exists.

## Safety boundaries

Only explicitly mapped content may enter a WG repository. Existing official workflows, tool pins, legal/authoring files, shared front matter, installer scripts, templates and other infrastructure are protected. The mover does not invoke `expand_bundle.py`, install the old Word infrastructure, or modify repository settings.

Legacy `word-drafts` content is excluded from WG transfers. The official Publisher generates the review repository's Word, HTML and STS outputs. An allocation CSV in `model` is not interchangeable with a documentation CSV in `artifacts`.

Every transfer is preflighted before writing. If a target file contains different bytes, preparation fails and names the conflict; it does not overwrite the destination's edits or choose a merge side. Reconcile those differences on the topic branch using the source/import baseline and current destination, then regenerate and validate. The same protection applies to differing public files during a return.

Publication manifests and relative Markdown links are translated with the content paths; assigned document numbers and model namespace/version identities are preserved. Executable generators and normative decisions are not rewritten by a generic text replacement. Their destination validators must pass before the workflow opens the receipt PR; layout-sensitive code needs an explicit reviewed adaptation.

Review and cleanup commands verify the checkout's `origin` against the selected repository. Absolute paths, traversal, linked paths escaping the checkout, collisions and cross-WG release closures are rejected.

## Closures and dependencies

`closure` means specifications that move together. OpenUSD Scene closes over OpenUSD Binding; WoT Connectivity closes over WoT Binding. A symmetric `releaseGroup`, such as Vision/AI, moves together regardless of the requested member.

A closure must have one review owner. A cross-WG relationship is a dependency, not permission to move the other WG's specification.

WG repositories maintain their own explicit, pinned dependency snapshots. A WG export does not copy an entire vendored specification or overwrite shared tooling merely because the public manifest lists a dependency. Core's existing shared-tooling export behavior is retained. Required inputs are checked by the destination validators; missing or incompatible inputs must be resolved before publication.

Public holdbacks (`keepPublic`) are excluded from removal. Cleanup inventories include only the selected mapped content, never sibling specifications, global CI/tooling, or unrelated dependency snapshots.

## Credentials

The public workflow token is scoped to `marcschier/opcua-drafts`; it cannot access the member repositories.

The existing `SPEC_DRAFTS_TOKEN` secret is used for the selected review repository. Its historical name does not determine the destination. A maintainer must provision access to the intended repository with only the necessary Contents and Pull requests permissions. The workflow verifies repository access before preparing changes. It does not broaden permissions, read or print secrets, or alter Foundation repository settings.

Scratch exports and checkouts live under the gitignored `node_modules/spec-release-work` directory. Repository scans exclude scratch directories and nested Git repositories, preventing private export contents from being treated as public files to repair or commit.

## Dry runs

Dry-run is the workflow default and opens no PRs.

```powershell
python release\tools\release_spec.py release <spec-id> --dry-run
python release\tools\release_spec.py return schema-registry --import OPC30450-CloudIntegration --dry-run
python release\tools\release_spec.py return openusd-scene --import OPC12000-Metaverse --dry-run
```

Use `route <spec-id>` to obtain the correct import submodule. Fetch and inspect the chosen review revision before a real return; do not update or reset a dirty checkout.

```powershell
gh workflow run spec-release.yml --repo marcschier/opcua-drafts --ref main -f spec-id=<spec-id> -f direction=release -f dry-run=true
```

## Release for review

The real release exports the selected public content, repairs public references, and prepares the routed private checkout:

```powershell
python release\tools\release_spec.py release <spec-id> --export node_modules\spec-release-work\export
python release\tools\prepare_private_release.py <spec-id> --root node_modules\spec-release-work\private --export node_modules\spec-release-work\export
```

The export retains public-relative paths; preparation applies the explicit review mappings. It neither bootstraps the repository nor replaces reviewed content.

The workflow validates the repaired public tree and the relocated private validators, opens the private receipt PR first, and then opens the public removal PR. Merge the green, reviewed receipt before the public removal. A failure leaves the authoritative remote source in place; do not force an incomplete handoff through.

## Return after review

A real return must explicitly name the correct checkout:

```powershell
python release\tools\release_spec.py return <spec-id> --import <review-submodule>
```

The mover maps the review file inventory back to the public layout, including new destination-authored files, and repairs public navigation and publication inventories. It refuses to overwrite differing public files.

The public return PR is opened first. The separate private cleanup PR removes the returned file inventory from the routed repository:

```powershell
python release\tools\private_cleanup.py <spec-id> --root <review-submodule> --dry-run
```

Review the exact removal list and merge the public return before the private cleanup. Infrastructure and dependencies not owned by the return stay in the review repository.

## The WG split is a separate handoff

Do not use a release or return operation to delete the migrated material from `spec-drafts` during the WG split. That cleanup requires all WG receipts and parent integration to pass CI and merge, followed by fresh explicit user confirmation of the file-exact deletion inventory.

## Regression checks

```powershell
python -m unittest discover -s release\tools -p "test_*.py"
python .github\scripts\check_yaml_json.py
python .github\scripts\check_links.py
```

The routing tests cover every review owner, both layout directions, actual-checkout inventories, closure boundaries, retained destination/public edits, publication identities, path escapes, infrastructure exclusions and legacy Word exclusions. They use isolated fixtures and perform no live release, return or cleanup.
