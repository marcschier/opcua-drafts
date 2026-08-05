# Bootstrap `OPCF-Members/spec-drafts`

This bundle prepares the empty private review repository with the same contribution model as `marcschier/opcua-drafts`: advisory PR validation, issue-to-PR agent runs, Word review ingest, and Word draft refresh PRs. It is stored inertly because this bundle lives inside a working public repository.

## 1. Storage model

Do **not** copy `release/private-repo/files/` by directory shape. The stored files use neutral paths and a `.bundle` suffix so repo-wide tools in the public repository cannot interpret them as live configuration.

The authoritative mapping is `release/private-repo/manifest.json`:

```text
stored path under files/ -> destination path in OPCF-Members/spec-drafts
```

Use `release/private-repo/expand_bundle.py`; it consumes the manifest, verifies every stored file's SHA-256, and materializes the real private-repo paths. Reviewers can inspect `manifest.json` to see exactly where every stored file lands.

Validate the stored bundle before use:

```powershell
python release\private-repo\validate_bundle.py
python release\private-repo\sync.py
```

`validate_bundle.py` parses every stored JSON/YAML file according to its destination extension, so an inert stored workflow cannot silently ship broken YAML.

## 2. What the bundle materializes

Included as-is from the public draft repository:

- GitHub workflows for PR validation, issue-to-PR, Word review, Word draft refresh, and the reusable agent task;
- advisory scripts for links, Mermaid, YAML/JSON, determinism, and section references;
- issue and pull-request templates, Copilot instructions, Puppeteer config, and markdownlint config;
- `skills/`;
- the OPC Foundation Word template in `templates/`;
- `word-drafts/tools/`, excluding the public repository's specification configs.

Included with private-repo adaptations:

- `agent-task.yml` reads `AGENT_ALLOWED_PATHS` instead of hard-coding public spec trees.
- `pr-validation.yml` discovers aggregate validators with `.github/scripts/run_self_contained_validators.py` instead of naming `core-specs`, `cloud-specs`, and `metaverse-specs` directly.
- `needs-pr.yml` and `word-review.yml` use private-repo prompts and remind the agent to stay inside `AGENT_ALLOWED_PATHS`.
- `word-review.yml` downloads issue attachments with the workflow token because this repository is private.
- `check_section_refs.py` reads `SECTION_REF_STRICT_PREFIXES`; if unset, unresolved references are advisory notes only.
- The private Copilot instructions keep the public repo's editorial/model rules but remove the assumption that the public tree layout exists.
- The pull-request template refers to discovered validators rather than public tree names.
- `word-drafts/tools/specs/batch.json` starts empty; add one config per submitted private specification.

## 3. Admin decisions before materializing

Decide these values first; they are security boundaries, not cosmetics.

1. **Default branch**: use `main` unless OPCF-Members has a conflicting policy. The workflows assume `main` in triggers and PR bases.
2. **Specification roots**: choose the top-level directories the private repo will actually contain. Do not copy the public list blindly.
3. **Agent allowlist** (`AGENT_ALLOWED_PATHS`): set this to the exact space-separated roots the coding agent may change, plus `word-drafts/tools` if the agent may fix Word tooling. Keep workflow/configuration paths and generated Word outputs out of this list.
4. **Strict section-reference roots** (`SECTION_REF_STRICT_PREFIXES`): set this to the roots whose unresolved `§` references should fail the advisory check. Usually this is the same spec-source list, excluding tooling-only roots.
5. **Validation requirements** (`VALIDATION_REQUIREMENTS`): space-separated requirement files to install before aggregate spec validation. Leave unset until there is a real requirements file.
6. **Word specs**: add private `word-drafts/tools/specs/<spec-id>.json` configs and list committed renderings in `word-drafts/tools/specs/batch.json`. The public configs are intentionally not bundled because they name public repo paths.
7. **Branch protection strictness**: decide whether advisory validation remains advisory, or whether selected checks become required after the first green run.

## 4. Repository settings

In GitHub UI or with `gh`, set:

- **Visibility**: private (already true).
- **Default branch**: `main` after the first commit creates it.
- **Actions**: enabled. Allow GitHub-owned actions (`actions/checkout`, `actions/setup-python`, `actions/setup-node`, `actions/upload-artifact`, `actions/download-artifact`) and outbound installs used by the workflows (`pip`, `npm`, `curl` for pinned actionlint). If the org restricts Actions, explicitly allow these.
- **Copilot CLI policy for the organization**: enable it under the organization's Copilot policies. This is what lets `copilot-requests: write` on the built-in token succeed, and it is what keeps Copilot spend with the organization rather than an individual — see *Secrets and tokens* below. Nothing in the repository can substitute for it.
- **Workflow permissions**: `Read and write permissions`; allow GitHub Actions to create pull requests if the organization has that switch. The workflows still request least-privilege job permissions individually.
- **Fork pull-request approval**: require approval before workflows run for fork PRs. Private repositories often have no public forks, but do not relax this if private forks are enabled.
- **Branch protection for `main`**: require PRs, at least one approval, conversation resolution, and no direct pushes except by maintainers/release automation the admin explicitly trusts. Initially do not require the advisory checks until they have run once in the private repo; then optionally require selected checks by exact name.
- **Labels**: create `needs pr`, `word-review`, and `feedback` if they do not exist. The agent workflows are deliberately label-gated.

Suggested variables:

```powershell
gh variable set AGENT_ALLOWED_PATHS --repo OPCF-Members/spec-drafts --body "<spec-root-1> <spec-root-2> word-drafts/tools"
gh variable set SECTION_REF_STRICT_PREFIXES --repo OPCF-Members/spec-drafts --body "<spec-root-1> <spec-root-2>"
# Only once a real requirements file exists:
gh variable set VALIDATION_REQUIREMENTS --repo OPCF-Members/spec-drafts --body "<path/to/requirements.txt>"
```

## 5. Secrets and tokens

No permanent secret is required if GitHub accepts `GITHUB_TOKEN` with `permissions: copilot-requests: write`.

**Who pays.** Copilot usage on the built-in token is billed to the account that owns the repository, so in `OPCF-Members/spec-drafts` it is billed to the OPC Foundation. Usage on a personal access token is billed to whoever owns that token. The built-in path is therefore not merely the simpler one — it is the one that keeps the cost with the organization, and the setting that makes it work is an organization policy, not a repository secret.

Before reaching for a token, check that `OPCF-Members` has **Copilot CLI** enabled in its Copilot policies. An authentication or entitlement failure almost always means that policy is off, and adding a personal PAT "fixes" it by quietly moving the bill to one person. Organization-level billing requires Copilot Business or Enterprise.

Optional fallback secret:

- `COPILOT_GITHUB_TOKEN`: only for `agent-task.yml`'s read-only `think` job, and only once the organization policy above has been confirmed on. Use a fine-grained PAT owned by a **service account that holds an organization-assigned Copilot seat** — never a maintainer's personal account, because the requests are billed to the account that owns the token. Restrict it to `OPCF-Members/spec-drafts` with the minimum available **Copilot Requests** permission. Do not grant contents write, pull-request write, or issue write to this PAT; publishing is done by the job-scoped `GITHUB_TOKEN` in a separate job that never reads the prompt.

After the first agent run, confirm the usage appears under the organization at **Settings → Billing → Copilot**. That is the only direct evidence that attribution is what you intended.

Built-in `GITHUB_TOKEN` job permissions used by workflows:

- `pr-validation.yml`: `contents: read`.
- `needs-pr.yml`: reads/issues in the `read` job, then calls `agent-task.yml` with `contents`, `pull-requests`, `issues`, and `copilot-requests` as declared.
- `word-review.yml`: `contents`, `pull-requests`, `issues`, and `copilot-requests` to ingest a reviewed `.docx`, open/update a PR, comment on the issue, and optionally run the agent for judgment calls.
- `word-drafts-refresh.yml`: `contents: write` and `pull-requests: write` to maintain the standing Word-refresh PR.
- `agent-task.yml`: the `think` job has only `contents: read` plus `copilot-requests: write`; the `publish` job has write permissions but never reads the prompt.

## 6. Materialize in the private checkout

After admin approval, from a clean working directory:

```powershell
# 1. Clone the empty private repo.
gh repo clone OPCF-Members/spec-drafts spec-drafts
Set-Location spec-drafts

# 2. Create main if the repository is still empty.
git switch --orphan main

# 3. Materialize the inert bundle here, using your own checkout of the public
#    drafts repository in place of $public.
$public = "<path-to>\opcua-drafts"
python "$public\release\private-repo\expand_bundle.py" --target .

# 4. Add the submitted specification sources, generated artifacts, committed Word drafts,
#    and private word-drafts/tools/specs/<spec-id>.json configs approved for review.
#    Keep batch.json in step with the committed Word renderings.

# 5. Review before committing.
git status --short
git add .
git commit -m "Bootstrap private specification review repository"
```

Do not push until the admin confirms the diff and variables.

## 7. Verification before the first push

Run in the private checkout:

```powershell
python .github\scripts\check_yaml_json.py
python .github\scripts\check_links.py
python .github\scripts\check_section_refs.py
python .github\scripts\run_self_contained_validators.py
python word-drafts\tools\build_all.py --list
python word-drafts\tools\test_ingest.py
```

If Node/Python dependencies are missing:

```powershell
pip install -r word-drafts\tools\requirements.txt
pip install pyyaml
npm --version
```

For any committed Word rendering, verify one concrete spec:

```powershell
python word-drafts\tools\build_docx.py word-drafts\tools\specs\<spec-id>.json
python word-drafts\tools\validate_docx.py word-drafts\tools\specs\<spec-id>.json
```

## 8. First push and workflow verification

After approval:

```powershell
git push -u origin main
gh workflow list --repo OPCF-Members/spec-drafts
gh workflow run "PR validation" --repo OPCF-Members/spec-drafts --ref main
gh workflow run "Refresh Word drafts" --repo OPCF-Members/spec-drafts --ref main
```

Then verify the agent flows with disposable test inputs:

1. Open a test issue in the private repo.
2. Add `needs pr`; confirm the workflow either opens a PR or comments that no concrete change was needed.
3. Attach a reviewed `.docx` built from a committed rendering, add `word-review`, and confirm tracked changes become a PR and comments become a review.
4. If the agent job fails with Copilot authentication/entitlement, add `COPILOT_GITHUB_TOKEN` and rerun only after confirming the token has no write scopes.

## 9. Keeping the bundle in sync

From the public draft repository checkout:

```powershell
python release\private-repo\sync.py
```

The default is report-only. To refresh changed/missing bundle files and `manifest.json` after reviewing the drift:

```powershell
python release\private-repo\sync.py --apply
python release\private-repo\validate_bundle.py
```

`sync.py`, `expand_bundle.py`, and `validate_bundle.py` are deterministic. `sync.py` reports extra stored files but does not delete them.

## 10. Private-repository caveats

- GitHub-hosted Actions minutes and storage are billed/limited differently for private repositories.
- Anonymous raw-content assumptions were avoided for Word review attachments by adding an authorization header. The pinned public `actionlint` download, npm, and pip installs still require outbound internet access from Actions runners.
- The agent security boundary depends on `AGENT_ALLOWED_PATHS`. A too-narrow list drops legitimate agent edits; a too-wide list can let untrusted prompts modify files that execute later. Decide it explicitly.
- Public `word-drafts/tools/specs/*.json` files were not bundled because they name public paths and documents. Private specs need their own configs.
- Workflow/configuration paths remain outside the agent allowlist by design. Workflow changes should be normal human-reviewed PRs, not agent output.
