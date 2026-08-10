# Specification release workflow

This directory describes the lifecycle for a specification that has been submitted to the OPC Foundation for review.
While the review is active the submitted draft moves from the public repository, `marcschier/opcua-drafts`, to the private member repository, `OPCF-Members/spec-drafts`.
The move protects the review comments and the reviewed text while the Foundation process is running.
When the review is complete, the specification returns here and the private copy is removed.

The source of truth is `release/manifest.json`.
It names the public and private repositories, the shared tooling that is duplicated into the private repository, and each specification's moved paths, public holdbacks, moving closure, vendored dependencies, submission status, Word clause maps, validators and reverse references.
Do not infer a release by scanning directories.
The manifest records the decision that the workflow must apply.

## Design decisions

A release moves the requested specification with its `closure`.
`closure` means "moves with this one": both specifications were submitted for Foundation review, and both must be private while that review is active.
For example, `openusd-scene` closes over `openusd-binding`, and `wot-connectivity` closes over `wot-binding`.
Moving one part without the other would leave the public part full of broken references to the private part.

A release also exports its `vendor` dependencies to the private repository, but those dependencies stay public here.
`vendor` means "copy into the private export": the private repository needs the base model so `RequiredModel` resolves and validators can read its NodeIds CSV, while public specifications still need the same base.
For example, OpenUSD and WoT vendor `xregistry`, and Avro vendors
`observability-export-nodeset`.
Vendoring is the same design as shared tooling: duplicate and keep in step because moving the dependency would break one side.

`submitted: false` marks a shared dependency that exists in the manifest only to be vendored and cannot be released on its own.
`xregistry` and `observability-export-nodeset` are shared public bases, not submitted Foundation-review drafts.
Their files can appear in a private export, but they do not leave the public repository.

The natural release units are Avro, OpenUSD and WoT.
That is not a separate grouping field; it falls out of `closure`.
If a submitted specification that is still public closes over the requested one, the mover refuses the narrower release and names the enclosing operation instead.
`release openusd-binding` is refused in favour of `release openusd-scene`, and `release wot-binding` is refused in favour of `release wot-connectivity`.
Without that refusal, releasing Part 1 alone would gut Part 2's references while leaving Part 2 public.

`file_set()` is what leaves the public repository.
`export_set()` is what the private repository receives.
They differ by the vendored files, and that difference is the point: vendored files must be present privately for validation, but remain public because other public drafts depend on them.

Shared tooling is duplicated and kept in step rather than moved.
The public repository still needs the generators, validators and Word build for specifications that are not under review, and the private repository needs the same tooling to validate the submitted draft.
Moving the tools would break one side every time a specification changes state.

Documents targeted at xregistry.org stay public even when they live inside a folder that otherwise moves.
Those documents have their own publication target and should not disappear just because a related OPC UA draft is under Foundation review.
List them in `keepPublic` so the mover knows they are deliberate public holdbacks, not a missed file.

Public git history is accepted as-is.
This process removes the active public copy while review is in progress; it does not rewrite old commits.
Rewriting history would be more disruptive than the remaining historical visibility and would not protect review comments added after submission.

## Credentials

The workflow uses the built-in `GITHUB_TOKEN` for the public repository only.
That token is scoped to `marcschier/opcua-drafts`, so it cannot read, push to, or open pull requests in `OPCF-Members/spec-drafts`.

Create an Actions repository secret named `SPEC_DRAFTS_TOKEN` in `marcschier/opcua-drafts`.
Use a fine-grained PAT or GitHub App installation token with access only to `OPCF-Members/spec-drafts`.
Grant the private repository permissions `Contents: Read and write` and `Pull requests: Read and write`; `Metadata: Read` is implicit.
Do not use a broad classic PAT unless there is no other option, because the workflow only needs to clone the private repository, push a branch and open or update a pull request there.

The private repository also needs its bootstrap files and maintainer instructions.
Set it up from `release/private-repo/` and follow `release/private-repo/INSTRUCTIONS.md`.
That bundle is referenced here but is maintained separately.

The workflow stages the private checkout and export under `node_modules/spec-release-work`.
`node_modules/` is ignored deliberately.
The workflow still excludes that path when staging the public pull request, but the ignore rule is a second barrier against committing a private checkout into the public repository.

## Dry runs

Dry-run is the default and should be the first run for every release or return.
It runs the mover with `--dry-run` and opens no pull requests.

From the GitHub CLI:

```powershell
gh workflow run spec-release.yml --repo marcschier/opcua-drafts --ref main -f spec-id=<spec-id> -f direction=release -f dry-run=true
gh workflow run spec-release.yml --repo marcschier/opcua-drafts --ref main -f spec-id=<spec-id> -f direction=return -f dry-run=true
```

The equivalent local checks are:

```powershell
python release/tools/release_spec.py status
python release/tools/release_spec.py release <spec-id> --dry-run
python release/tools/release_spec.py return <spec-id> --dry-run
```

## Releasing a specification for review

Run the dry run first.
Read the log and fix every reported repair that needs a human.
The mover exits non-zero when it cannot safely repair the public tree, and the workflow treats that as a hard stop.

When the dry run is clean, start the real release:

```powershell
gh workflow run spec-release.yml --repo marcschier/opcua-drafts --ref main -f spec-id=<spec-id> -f direction=release -f dry-run=false
```

For a real release, the mover command is equivalent to:

```powershell
python release/tools/release_spec.py release <spec-id> --export node_modules\spec-release-work\export
```

The export directory preserves repository-relative paths.
The export contains the moving `file_set()`, the vendored `export_set()` additions and shared tooling.
The workflow copies that export into a branch in `OPCF-Members/spec-drafts`, verifies that files were exported, commits the private branch and opens or updates the private pull request.
Only after the private pull request exists does it push the public branch and open or update the public pull request that removes the submitted draft and applies the repairs.
Merge the private pull request first, then merge the public removal pull request.

Before either pull request is opened, the workflow runs the repair gates that can execute in CI: internal links, section references, YAML/JSON parsing and every discovered `validate_all.py --self-contained`.
These are blocking here because a half-repaired release is worse than a red advisory check on an ordinary draft pull request.

This order prevents the dangerous half-completed release: the public side should never remove a specification before the private side has received it.
If the workflow fails before the private pull request is opened, no repository has been changed.
If it fails after the private pull request is opened but before the public pull request is opened, either fix the public-side error and rerun the workflow, or close the private pull request and delete its branch.
Do not merge the public removal unless the private pull request exists and contains the exported file set.

## Returning a specification after review

Run the dry run first:

```powershell
gh workflow run spec-release.yml --repo marcschier/opcua-drafts --ref main -f spec-id=<spec-id> -f direction=return -f dry-run=true
```

When it is clean, start the real return:

```powershell
gh workflow run spec-release.yml --repo marcschier/opcua-drafts --ref main -f spec-id=<spec-id> -f direction=return -f dry-run=false
```

For a real return, the workflow checks out `OPCF-Members/spec-drafts` and uses that checkout as the import directory.
The mover command is equivalent to:

```powershell
python release/tools/release_spec.py return <spec-id> --import node_modules\spec-release-work\private
```

Locally, the `spec-drafts/` submodule is already a checkout of the private repository, so it can be the import source directly — update it first so it is not importing a stale commit:

```powershell
git submodule update --remote spec-drafts
python release/tools/release_spec.py return <spec-id> --import spec-drafts --dry-run
```

The mover skips any directory carrying its own `.git`, so the submodule is never scanned for references to repair and a release can never rewrite files inside it.

The public return pull request is opened first, because it restores the reviewed text to the public repository.
After that pull request exists, the workflow opens a private cleanup pull request that removes the returned specification's manifest file set from `OPCF-Members/spec-drafts`:

```powershell
python release/tools/private_cleanup.py <spec-id> --root node_modules\spec-release-work\private
```

The cleanup tool calls `manifest.file_set()` instead of re-reading `release/manifest.json`.
That matters for two reasons.
First, vendored files are in the private export but do not leave the public repository, so cleanup must remove only the files that actually moved.
Second, a moved directory can have public holdback files, so cleanup must remove exactly the files the manifest API says were moved, not a directory approximation that can delete files which never left the public side.
Merge the public return pull request first, then merge the private cleanup pull request.

If the workflow fails before the public return pull request is opened, no public change exists and the private copy remains authoritative.
If it fails after the public return pull request is opened but before the private cleanup pull request is opened, rerun the workflow after fixing the error or remove the private copy manually in a reviewed private pull request.
That failure leaves a duplicate copy, not a lost one, so it is safer than the release-side failure.

## Adding a newly submitted specification

Add the specification to `release/manifest.json`.
Use a stable `<spec-id>`; the workflow uses it in branch names and commands.

Set `title` to the human-readable document title and `state` to `public` before the first release.
Set `submitted` to `true` for a specification that was submitted for Foundation review.
Set `submitted` to `false` only for a shared dependency that appears in the manifest so other submitted specifications can vendor it.
An unsubmitted dependency can be copied into the private repository, but it cannot be the target of a release.

List every path that moves in `move`.
Include the specification folder, its `extras/` mirror if it has one, the clause map, **and the committed Word rendering** — the `.docx`, its `.docmodel.json` and `.provenance.json`, and each figure declared by the clause map's `figures` array, both the `.pptx` source and the generated `.png`.
Word is the review format, so the `.docx` is the artifact under review; leaving it behind would keep the reviewed document publicly downloadable while only its markdown source went private.
Take the figure list from the clause map rather than from a filename prefix: the clause map is the declared source of truth, and a prefix is a guess that silently drags a sibling specification's figures along with it.
A vendored specification contributes no Word rendering, because it is not under review.
List public holdbacks in `keepPublic`, especially documents that are targeted at xregistry.org even though they sit inside a folder that moves.
List every submitted specification that must travel with this one in `closure`; include only specification ids from the same manifest.
Use `closure` when the dependency was itself submitted for Foundation review and must become private at the same time.
Use `vendor` when the dependency is needed by the private copy but must stay public here.
The test is the submission boundary, not whether the model has a `RequiredModel` edge: a submitted Part 2 belongs in `closure`, while a public base model belongs in `vendor`.
List Word clause-map descriptors in `wordSpecs`.
Set `validateAll` to the aggregate validator path that must be repaired, or `null` if there is no aggregate.
List public files that reverse-reference this specification in `reverseRefs` so the mover can repair or report them.
A reverse reference is a path, relative link, validator entry or Word batch entry that breaks when the target moves.
A citation by name or label is not a reverse reference, and a file's own location is never a reference to itself.
Do not list a holdback merely because it lives under a moving directory, and do not list a bibliography entry or `foreignAnchors` entry that intentionally names an external document.

Run:

```powershell
python release/tools/release_spec.py status
python release/tools/release_spec.py release <spec-id> --dry-run
python .github/scripts/check_yaml_json.py
```

The dry run must be clean before the real release.
If the mover says a repair needs a human, fix the manifest or the source text; do not work around the failure in the workflow.

## Recovery rules

Never push directly to `main` in either repository as a recovery shortcut.
Open or update pull requests so a maintainer can compare the public and private sides before anything merges.

For a failed release, check which pull requests exist.
If the private PR does not exist, rerun after fixing the failure.
If the private PR exists but the public PR does not, either rerun to create the public PR or close the private PR and delete its branch.
If both exist, merge the private PR first.

For a failed return, check which pull requests exist.
If the public PR does not exist, rerun after fixing the failure.
If the public PR exists but the private cleanup PR does not, rerun to create the cleanup PR or open an equivalent private PR by hand.
If both exist, merge the public PR first.

The workflow's own YAML/JSON check is blocking.
The repository's ordinary PR checks remain advisory after the pull requests are opened, because that is how this repository reviews draft changes, but this workflow must stop before publishing a half-repaired move.
