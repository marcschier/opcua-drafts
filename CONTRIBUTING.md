# Contributing

Thanks for helping improve these **OPC UA specification drafts**. This repository is an intentionally informal scratch pad (see the [README](README.md)) — nothing here is normative, official, or final, so early feedback, questions, and half-formed ideas are all welcome.

The most important thing to know: **you don't have to write the specification yourself.** You can leave feedback, notes, or annotations, and the maintainers use **AI agents** to turn that feedback into concrete specification text, information-model (NodeSet / NodeId CSV) updates, and regenerated artifacts. Your job is to point at *what* should change and *why*; the drafting, modelling, and regeneration are handled for you.

## Ways to contribute

- **Raise feedback** — open an issue using the *Spec feedback or annotation* template. Describe what you would change or what you observed. A concrete suggestion is welcome but not required.
- **Annotate a draft** — open a pull request that adds inline comments, margin notes, or `<!-- … -->` annotations to a draft document. You do not need to resolve them; they become the agenda for discussion.
- **Propose a concrete change** — edit the specification or model source and open a pull request.

All three land in the same place: a thread where maintainers, contributors, and AI iterate on the draft together.

## How it works

Changes are accepted through **forks and pull requests** — the `main` branch is protected, so every change is proposed, discussed, and merged via a PR.

1. **Fork** `marcschier/opcua-drafts` to your account — on GitHub, or with `gh repo fork marcschier/opcua-drafts --clone`.
2. **Clone** your fork and **create a topic branch** with a short, descriptive name:

   ```bash
   git clone https://github.com/<you>/opcua-drafts.git
   cd opcua-drafts
   git checkout -b observability-export-metric-units
   ```

3. **Make your changes or annotations.** Edit the draft document, add annotations, or — for model changes — edit the **source** (a descriptor or a `tools/build_model.py` generator), never the generated NodeSet / CSV / Annex by hand (see [Working with generated content](#working-with-generated-content)).
4. **Regenerate and validate** if you touched a generated specification (see [Validating your change](#validating-your-change)). Documentation-only or annotation-only changes do not need this.
5. **Commit and push** to your fork, then **open a pull request** against `marcschier/opcua-drafts` `main` (for example `gh pr create --repo marcschier/opcua-drafts`).
6. **Discuss.** Maintainers and other contributors review and discuss in the pull request (and any linked issues).
7. **AI updates the draft from the feedback.** Based on the discussion, a maintainer runs an AI agent that applies the agreed changes to the specification text and model, regenerates every derived artifact, and re-runs validation. The PR is updated with the result for another round of review.
8. **Merge.** Once the thread converges and validation is green, the PR is merged.

You are welcome to stop after step 5 — or after just filing an issue. Turning rough feedback into a polished, validated change is exactly what the AI-assisted flow is for.

## Working with generated content

Most specifications here are **generated from a single source of truth**, so that the prose, the NodeSet, the NodeId CSV, and the Annex tables can never drift apart. For those:

- **Do not hand-edit** generated files (`*.NodeSet2.xml`, `*.NodeIds.csv`, generated Annex tables, per-spec addenda). Edit the **source** — the specification document, the JSON descriptor, or the `tools/build_model.py` / `build_*.py` generator — and **regenerate**.
- Each `core-specs/<extension>/` folder holds only the normative documents and the base schema; its tooling, descriptors, and examples live under the mirrored `core-specs/extras/<extension>/` tree.
- Generators are **deterministic** — regenerating without a source change produces byte-identical output, so a clean diff confirms your change is exactly what you intended.

If you are unsure which file is the source, say so in the issue or PR and a maintainer (or the AI agent) will find it — this is precisely the kind of thing the assisted flow handles.

## Validating your change

Install the prerequisites once, then run the validation gate from the repository root:

```powershell
# one-time
pip install -r core-specs/extras/requirements.txt

# validate every extension
python core-specs/extras/validate_all.py

# or a single extension
python core-specs/extras/<extension>/tools/validate_local.py
```

A green run (`ALL EXTENSIONS VALIDATED OK`) is the acceptance gate; please include it in the PR for model or tooling changes. Feedback-only and annotation-only pull requests do not need to pass validation.

## Conventions

- **Branch names** — short and descriptive of the change (for example `avro-action-response-fields`).
- **Commit messages** — a concise, imperative summary line; add a body explaining *why* for anything non-trivial.
- **Markdown** — wrap prose at logical / paragraph boundaries (roughly one line per paragraph), not at a fixed column; code snippets are exempt.
- **NodeIds are provisional** — numeric NodeIds in these drafts are placeholders drawn from a currently-unused block; final IDs are assigned by the OPC Foundation. Do not rely on their exact values.
- **No secrets** — never commit credentials, tokens, or private data.

## Ground rules

These drafts are **experimental and non-normative**. They are not affiliated with, reviewed by, or endorsed by the OPC Foundation, and the use of `opcfoundation.org` namespace URIs is for prototyping only. By contributing you agree that your contributions may be edited (including by AI agents), regenerated, reorganized, or removed as the drafts evolve.
