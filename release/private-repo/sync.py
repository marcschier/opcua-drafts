#!/usr/bin/env python3
"""Report or apply drift between shared tooling and the private-repo bundle.

Default mode is report-only:

    python release/private-repo/sync.py

Apply missing or changed bundled files explicitly:

    python release/private-repo/sync.py --apply

The script is stdlib-only and has no network dependency. It intentionally does not delete
extra files from the bundle; extras are reported so a human can decide whether they are
private-only support files or stale leftovers.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
BUNDLE = BASE / 'files'
MANIFEST = BASE / 'manifest.json'
IGNORE_DIRS = {'__pycache__', '.pytest_cache'}
IGNORE_SUFFIXES = {'.pyc', '.pyo'}


def _read(rel: str) -> str:
    return (REPO / rel).read_text(encoding='utf-8')


def _bytes(text: str) -> bytes:
    return text.encode('utf-8')


# Suffixes whose bytes are stored verbatim. Everything else is normalised to LF so the
# bundle and its digests are identical whether sync.py runs on Windows or Linux, and so
# the materialised private repository does not end up with mixed line endings.
BINARY_SUFFIXES = {'.docx', '.pptx', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.pdf', '.zip'}


def _normalise(rel: str, data: bytes) -> bytes:
    if Path(rel).suffix.lower() in BINARY_SUFFIXES:
        return data
    return data.replace(b'\r\n', b'\n')


def transform_agent_task(text: str) -> str:
    pattern = re.compile(r"(?m)^env:\n  ALLOWED_PATHS: >-\n(?:    [^\n]+\n)+")
    replacement = """# Private repositories do not necessarily use the public draft repository's tree layout.
# Set the AGENT_ALLOWED_PATHS repository variable to the exact space-separated source,
# model and extras roots for this private repository. The default is intentionally narrow.
env:
  ALLOWED_PATHS: ${{ vars.AGENT_ALLOWED_PATHS || 'word-drafts/tools' }}
"""
    text, count = pattern.subn(replacement, text, count=1)
    if count != 1:
        raise ValueError("public agent-task.yml has no recognized ALLOWED_PATHS block")
    text = text.replace('the specification trees and `word-drafts/tools/`', 'the paths listed in `AGENT_ALLOWED_PATHS`')
    return text


def transform_pr_validation(text: str) -> str:
    text = text.replace("""# Only checks that run on a clean checkout are wired here. Full spec validation and the determinism
# gate additionally need untracked base data (companion NodeSets under **/tools/ref/ and the base
# PubSubBinding NodeSet), so they run their self-contained subset / skip cleanly in CI and remain a
# local gate (see CONTRIBUTING.md).
""", """# Only checks that run on a clean checkout are wired here. Full spec validation and the determinism
# gate additionally need untracked base data for some specifications, so CI runs discovered
# self-contained aggregate validators and lets determinism checks skip cleanly when their inputs are
# not present. Repository variables name any private-repo-specific roots and requirements.
""")
    text = text.replace("""      - run: python .github/scripts/check_section_refs.py
""", """      - run: python .github/scripts/check_section_refs.py
        env:
          SECTION_REF_STRICT_PREFIXES: ${{ vars.SECTION_REF_STRICT_PREFIXES }}
""")
    text = text.replace("""      - run: pip install -r extras/core-specs/requirements.txt
      - run: pip install -r source/companion-specs/AAS/requirements.txt
      # The AddressSpace figure gate re-derives each figure from the NodeSet using the
      # Word pipeline's Mermaid parser, so spec validation needs that parser installed.
      # Without it the gate skips, and a figure that contradicts its model reaches main.
      - run: pip install -r word-drafts/tools/requirements.txt
      - run: python extras/core-specs/validate_all.py --self-contained
      - run: python extras/cloud-specs/validate_all.py --self-contained
      - run: python extras/metaverse-specs/validate_all.py --self-contained
      - run: python extras/companion-specs/validate_all.py --self-contained
""", """      - name: Install validation requirements if present
        env:
          VALIDATION_REQUIREMENTS: ${{ vars.VALIDATION_REQUIREMENTS || '' }}
        run: |
          for req in $VALIDATION_REQUIREMENTS; do
            if [ -f "$req" ]; then
              pip install -r "$req"
            else
              echo "validation requirements not present: $req"
            fi
          done
      - run: pip install -r word-drafts/tools/requirements.txt
      - run: python .github/scripts/run_self_contained_validators.py
""")
    text = text.replace("""      - run: pip install -r extras/core-specs/requirements.txt
      - run: python .github/scripts/check_determinism.py
""", """      - name: Install determinism requirements if present
        env:
          VALIDATION_REQUIREMENTS: ${{ vars.VALIDATION_REQUIREMENTS || '' }}
        run: |
          for req in $VALIDATION_REQUIREMENTS; do
            if [ -f "$req" ]; then
              pip install -r "$req"
            else
              echo "determinism requirements not present: $req"
            fi
          done
      - run: python .github/scripts/check_determinism.py
""")
    return text


def transform_needs_pr(text: str) -> str:
    text = text.replace('You are working in the opcua-drafts repository.', 'You are working in the private OPC UA specification drafts repository.')
    text = text.replace("""- Change the markdown specification and, where the ask is about the information
            model, the generator that produces the NodeSet — never the generated NodeSet,
            CSV or reference tables directly, and never anything under `word-drafts/`
            except `word-drafts/tools/`. Those are build outputs.""", """- Change the markdown specification and, where the ask is about the information
            model, the generator that produces the NodeSet — never the generated NodeSet,
            CSV or reference tables directly, and never anything under `word-drafts/`
            except `word-drafts/tools/`. Those are build outputs. Stay inside the
            private repository's `AGENT_ALLOWED_PATHS` allowlist.""")
    return text


def transform_word_review(text: str) -> str:
    text = text.replace('You are working in the opcua-drafts repository.', 'You are working in the private OPC UA specification drafts repository.')
    text = text.replace('run: curl -sSL -o reviewed.docx "$URL"', 'run: |\n          curl -sSL -H "Authorization: Bearer ${{ github.token }}" -o reviewed.docx "$URL"')
    text = text.replace("""- Change the markdown specification, and the *generator* where the ask is about
            the information model. Never edit a generated NodeSet, CSV, `.docx`,
            `.docmodel.json` or `.provenance.json` — they are build outputs.""", """- Change the markdown specification, and the *generator* where the ask is about
            the information model. Never edit a generated NodeSet, CSV, `.docx`,
            `.docmodel.json` or `.provenance.json` — they are build outputs. Stay inside
            the private repository's `AGENT_ALLOWED_PATHS` allowlist.""")
    return text


def transform_pr_template(text: str) -> str:
    return text


def transform_check_section_refs(text: str) -> str:
    text = text.replace("""# Trees where an unresolved reference fails the check. Elsewhere findings are printed
# as advisory notes: a reference whose qualifier sits far from it ("No change to
# OPC 10000-6 §7.2 is required. … Reverse connect (§7.1.3) …") cannot be classified from
# a bounded window, and widening the window is what makes the check miss real defects.
# Opting a tree in is a deliberate act by whoever has verified its references.
STRICT_PREFIXES = ('metaverse-specs/',)
""", """# Trees where an unresolved reference fails the check. Elsewhere findings are printed
# as advisory notes: a reference whose qualifier sits far from it ("No change to
# OPC 10000-6 §7.2 is required. … Reverse connect (§7.1.3) …") cannot be classified from
# a bounded window, and widening the window is what makes the check miss real defects.
# Opting a tree in is a deliberate act by whoever has verified its references. The private
# repository's spec roots differ from the public draft repository, so set the
# SECTION_REF_STRICT_PREFIXES repository variable to a space-separated list of roots that
# should fail the check. If unset, every unresolved reference is advisory.
_env_strict = os.environ.get('SECTION_REF_STRICT_PREFIXES', '').split()
STRICT_PREFIXES = tuple(p.strip().rstrip('/').replace('\\\\', '/') + '/'
                        for p in _env_strict if p.strip())
""")
    return text


def private_copilot_instructions() -> str:
    source = _read('.github/copilot-instructions.md')
    tail = source[source.index('## Voice and tense'):]
    head = """# Copilot instructions — private OPC UA specification drafts

This private repository carries specifications that have already been submitted for OPC Foundation review. It uses the same contribution model as the public draft repository, but it may not use the same top-level specification trees. Do not assume `core-specs/`, `cloud-specs/` or `metaverse-specs/` exist unless they are present in this repository.

Most specifications are generated from a single source of truth, so the prose, the NodeSet, the NodeId CSV and the Annex tables cannot drift apart. The most common way to break this repository is to hand-edit a generated file.

## Commands

```powershell
# one-time
pip install -r extras/core-specs/requirements.txt
pip install -r word-drafts/tools/requirements.txt

# advisory checks used by PR validation
npx markdownlint-cli2 "**/*.md"
python .github/scripts/check_links.py
python .github/scripts/check_section_refs.py
python .github/scripts/check_yaml_json.py
python .github/scripts/run_self_contained_validators.py
python .github/scripts/check_determinism.py

# Word rendering: replace <spec-id> with a config in word-drafts/tools/specs/
python word-drafts/tools/build_docx.py word-drafts/tools/specs/<spec-id>.json
python word-drafts/tools/validate_docx.py word-drafts/tools/specs/<spec-id>.json
python word-drafts/tools/test_validate_docx.py word-drafts/tools/specs/<spec-id>.json
pwsh word-drafts/tools/finalize_word.ps1 -Path word-drafts/<document>.docx
```

`run_self_contained_validators.py` discovers aggregate `validate_all.py` entrypoints and runs them with `--self-contained`. If a submitted specification has only a per-extension `validate_local.py`, run that directly. Full validation may require untracked base data; keep those local gates documented next to the specification that needs them.

## Architecture

The active specification roots are a repository-specific allowlist. Keep these in step:

- the `AGENT_ALLOWED_PATHS` repository variable used by `.github/workflows/agent-task.yml`;
- the `SECTION_REF_STRICT_PREFIXES` repository variable used by section-reference validation;
- the `VALIDATION_REQUIREMENTS` repository variable if validators need requirements outside `word-drafts/tools/requirements.txt`;
- the `word-drafts/tools/specs/*.json` Word configs and `word-drafts/tools/specs/batch.json` inventory.

`word-drafts/` holds submission-ready Word documents built into the official OPC Foundation companion specification template. `templates/` holds the template cloned by the Word build. `skills/` holds agent instructions that operate on the drafts.

**Normative / tooling split.** A spec folder holds only the normative documents and generated base artifacts; secondary tooling, descriptors and examples live under `extras/<group>/<spec>/`, unless the specification already owns them under `source/`. Shared core helpers live under `extras/core-specs/_common/`, and group aggregate validators live at `extras/<group>/validate_all.py`.

**Validation is per-extension.** Each extension owns a validator. Aggregate `validate_all.py` files cover one group each; `.github/scripts/run_self_contained_validators.py` discovers all of them.

"""
    return head + tail


RUN_VALIDATORS = r'''#!/usr/bin/env python3
"""Discover and run self-contained aggregate validators.

The private review repository can hold a different set of specification trees than the
public draft repository. This script avoids hard-coding that set: it walks the repository
for aggregate ``validate_all.py`` entrypoints and runs each with ``--self-contained``.
Per-extension ``validate_local.py`` checks remain local, targeted commands.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXTRAS = ROOT / "extras"


def validators():
    return sorted(
        (path.relative_to(ROOT) for path in EXTRAS.glob("*-specs/validate_all.py")),
        key=lambda path: path.as_posix(),
    )


def main():
    found = validators()
    if not found:
        print('run_self_contained_validators: SKIP - no validate_all.py entrypoints found')
        return 0
    expected = {
        Path("extras/core-specs/validate_all.py"),
        Path("extras/cloud-specs/validate_all.py"),
        Path("extras/metaverse-specs/validate_all.py"),
        Path("extras/wot-specs/validate_all.py"),
    }
    missing = expected - set(found)
    if missing:
        print("run_self_contained_validators: ERROR - missing aggregate validators:")
        for rel in sorted(missing, key=lambda path: path.as_posix()):
            print(f"  {rel.as_posix()}")
        return 1
    failed = []
    for rel in found:
        print(f'=== {rel.as_posix()} --self-contained ===')
        code = subprocess.call([sys.executable, str(ROOT / rel), '--self-contained'], cwd=ROOT)
        if code:
            failed.append((rel, code))
    if failed:
        print('run_self_contained_validators: failures:')
        for rel, code in failed:
            print(f'  {rel.as_posix()}: exit {code}')
        return 1
    print(f'run_self_contained_validators: OK ({len(found)} aggregate validator(s))')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
'''

PRIVATE_DETERMINISM = r'''#!/usr/bin/env python3
"""Determinism / "generated files are up to date" check.

Regenerates the deterministic encoding artifacts and fails if that produces any change under
version control — i.e. a generated file was hand-edited or a source change was not regenerated.

The private repository regenerates the submitted Avro schemas and the OpenUSD artifact
catalog. Both inputs are available in a clean checkout; the OpenUSD domain model is fetched
from its commit-pinned, hash-verified upstream URL.

Usage (from repo root):  python .github/scripts/check_determinism.py
Exit code: 0 = clean or skipped, 1 = generated files drifted, 2 = a generator errored.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE_NODESET = os.path.join(
    ROOT, "model", "cloud-specs", "observability-export",
    "Opc.Ua.ObservabilityExport.NodeSet2.xml")

GENERATORS = [
    "extras/core-specs/avro-encoding/tools/build_schemas.py",
    "extras/metaverse-specs/openusd-artifacts/tools/build_catalog.py",
]


def main():
    if not os.path.exists(BASE_NODESET):
        print("check_determinism: SKIP - base NodeSet not present "
              "(model/cloud-specs/observability-export/"
              "Opc.Ua.ObservabilityExport.NodeSet2.xml)")
        return 0
    for rel in GENERATORS:
        print(f"=== regenerate {rel} ===")
        proc = subprocess.run([sys.executable, os.path.join(ROOT, *rel.split("/"))], cwd=ROOT)
        if proc.returncode != 0:
            print(f"check_determinism: ERROR - generator failed: {rel}")
            return 2
    diff = subprocess.run(["git", "diff", "--stat", "--exit-code"], cwd=ROOT)
    if diff.returncode != 0:
        print("check_determinism: generated files drifted - regenerate and commit "
              "(do not hand-edit generated artifacts)")
        return 1
    print("check_determinism: OK (regeneration produced no changes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

PRIVATE_WORD_README = '''# Word drafts

The submission-ready Word renderings of the specifications under OPC Foundation review, built
into the official OPC Foundation companion specification template.

**Word is the review format.** These are the documents to review, and reviewing one is a
complete contribution — you never have to touch git or markdown.

## These files are generated — please do not edit them

Every `.docx` here is built from the specification markdown and its UANodeSet by
`tools/build_docx.py`. The build is pure Python and byte-reproducible, so a rebuild of
unchanged sources produces an identical file. Editing a committed document is pointless: the
next build discards it silently. To change what a document says, change the markdown or the
model and regenerate.

Marking up a **downloaded copy** is a different thing entirely, and is exactly the intended
workflow.

Beside each document are two committed artifacts:

| File | What it is |
|---|---|
| `*.docmodel.json` | The intermediate representation the document was rendered from. Committed **because a `.docx` diff is unreadable** — review this instead. |
| `*.provenance.json` | What each paragraph was rendered from. This is what lets a marked-up copy be turned back into a change to the source. |

`figures/*.pptx` is the editable PowerPoint behind each figure, embedded in the document as an
OLE object; `figures/*.png` is the preview image Word displays for it.

## Sending a review back

Download the document, turn on track changes, and mark it up — edits as tracked changes,
questions and objections as comments. Then open an issue, attach the marked-up file, and ask a
maintainer to add the `word-review` label.

Your tracked changes become the diff of a pull request against the specification source, and
your comments become a review on that pull request, anchored to the text they were written
against.

**Every paragraph knows where it came from.** The build stamps a deterministic `w14:paraId` on
each paragraph and `*.provenance.json` maps those ids to source addresses, so a mark is traced
to the markdown that produced it rather than matched by text or guessed at by position. A
paragraph with an unknown id is one you created.

**Not every mark belongs in the markdown.** Each is routed to its real owner:

| Marked content | Owner | What happens |
|---|---|---|
| Prose rendered from markdown | that `.md` | applied |
| Node tables | the UANodeSet / `build_model.py` | reported as a model change request |
| Clause 4.1, use cases, Annex A identity | `tools/specs/<spec>.json` | reported |
| Clause and caption numbers, cross-references | Word fields | reported — numbering is not authored |
| Retained template regions | the OPC 20020 template | reported, and flagged as a deviation |

**A change that cannot be placed exactly is refused.** What you see is not the markdown —
inline markup is gone, cross-references have become numbers, BrowseNames have been resolved —
so an edit is applied only where the text it replaces occurs exactly once in that paragraph's
own source lines. Ambiguity is reported, never guessed at.

**And then it is checked.** The markdown is patched, the document is rebuilt, and every applied
edit must read the way you wrote it. One that does not is reported as unapplied and blocks the
pull request.

What the ingest refuses is not a failure but a different kind of work — a comment that states a
problem rather than supplying text, a mark that belongs in the information model, an edit made
unplaceable because the prose around it was rewritten. That remainder goes to the coding agent,
on the branch the ingest already built, and it is given the **report, not the document**, so it
cannot revert or re-apply your exact edits. It is told that changing nothing is a valid outcome,
because the branch already carries your marks and a guessed interpretation is worse than none.

Mechanical where it is exact, agentic where it needs judgement, and never both on the same text.

## Commands

```powershell
# one-time
pip install -r word-drafts/tools/requirements.txt

# markdown + NodeSet -> .docx  (pure Python, cross-platform, byte-reproducible)
python word-drafts/tools/build_docx.py word-drafts/tools/specs/<spec-id>.json
python word-drafts/tools/validate_docx.py word-drafts/tools/specs/<spec-id>.json
python word-drafts/tools/test_validate_docx.py word-drafts/tools/specs/<spec-id>.json

# the whole batch: build, validate and mutation-test every converted specification
python word-drafts/tools/build_all.py

# which renderings have fallen behind their sources
python word-drafts/tools/stale_specs.py

# update the table of contents, the table of figures and every cross-reference, so the
# committed file opens fully paginated  (needs Word; Windows only)
pwsh word-drafts/tools/finalize_word.ps1 -Path word-drafts/<document>.docx
```

`.github/workflows/word-drafts-refresh.yml` keeps the renderings in step with the markdown on
`main`, collecting the result on one standing pull request.

## The clause map

`tools/specs/<spec-id>.json` drives **both** the Word build and the markdown restructure, so the
document and its source cannot drift into different structures. The node tables are generated
from the UANodeSet, so the document cannot drift from the model either.

Add one config per specification, and list it in `tools/specs/batch.json` once its rendering is
committed.
'''


PRIVATE_BATCH = b'''{
  "_comment": "Private repository conversion batch. Add one <spec-id>.json per submitted specification and list converted ids here once the committed Word rendering exists.",
  "converted": [],
  "ready": [],
  "notAFit": []
}
'''


def transform_gitignore(text: str) -> str:
    """Drop the release-workflow scratch rule, which has no private-side meaning.

    The public repository ignores ``node_modules/`` because the release workflow stages
    the private checkout there. The private repository never stages anything, so carrying
    the rule would only invite someone to wonder what it protects.
    """
    marker = '# Scratch area used by the specification release workflow.'
    if marker in text:
        text = text[: text.index(marker)].rstrip() + '\n'
    return text


def desired_files() -> dict[Path, bytes]:
    out: dict[Path, bytes] = {}

    def add(rel: str, data: bytes | str | None = None) -> None:
        if data is None:
            data = (REPO / rel).read_bytes()
        if isinstance(data, str):
            data = _bytes(data)
        out[Path(rel)] = _normalise(rel, data)

    add('.markdownlint-cli2.yaml')
    add('.gitignore', transform_gitignore(_read('.gitignore')))
    add('.github/puppeteer-config.json')
    add('.github/ISSUE_TEMPLATE/spec-feedback.yml')
    add('.github/pull_request_template.md', transform_pr_template(_read('.github/pull_request_template.md')))
    add('.github/copilot-instructions.md', private_copilot_instructions())
    add('.github/workflows/agent-task.yml', transform_agent_task(_read('.github/workflows/agent-task.yml')))
    add('.github/workflows/pr-validation.yml', transform_pr_validation(_read('.github/workflows/pr-validation.yml')))
    add('.github/workflows/needs-pr.yml', transform_needs_pr(_read('.github/workflows/needs-pr.yml')))
    add('.github/workflows/word-review.yml', transform_word_review(_read('.github/workflows/word-review.yml')))
    add('.github/workflows/word-drafts-refresh.yml')

    for script in sorted((REPO / '.github' / 'scripts').glob('*.py')):
        rel = script.relative_to(REPO)
        key = rel.as_posix()
        if key == '.github/scripts/check_section_refs.py':
            add(key, transform_check_section_refs(_read(key)))
        elif key == '.github/scripts/check_determinism.py':
            add(key, PRIVATE_DETERMINISM)
        else:
            add(key)
    add('.github/scripts/run_self_contained_validators.py', RUN_VALIDATORS)

    for base in ('skills', 'templates', 'word-drafts/tools'):
        for p in sorted((REPO / base).rglob('*')):
            rel = p.relative_to(REPO)
            if p.is_dir() or any(part in IGNORE_DIRS for part in rel.parts) or p.suffix in IGNORE_SUFFIXES:
                continue
            if base == 'word-drafts/tools' and len(rel.parts) >= 4 and rel.parts[:3] == ('word-drafts', 'tools', 'specs'):
                continue
            add(rel.as_posix())
    out[Path('word-drafts/tools/specs/batch.json')] = PRIVATE_BATCH
    out[Path('word-drafts/README.md')] = _bytes(PRIVATE_WORD_README)
    return out


def stored_for(destination: Path) -> Path:
    parts = [('dot-' + part[1:]) if part.startswith('.') else part
             for part in destination.parts]
    return Path('payload').joinpath(*parts).with_name(parts[-1] + '.bundle')


def desired_manifest(desired: dict[Path, bytes]) -> dict:
    files = []
    for destination, data in sorted(desired.items(), key=lambda item: item[0].as_posix()):
        stored = stored_for(destination)
        files.append({
            'stored': stored.as_posix(),
            'destination': destination.as_posix(),
            'sha256': hashlib.sha256(data).hexdigest(),
        })
    return {'version': 1, 'files': files}


def existing_files() -> set[Path]:
    if not BUNDLE.exists():
        return set()
    found = set()
    for p in BUNDLE.rglob('*'):
        rel = p.relative_to(BUNDLE)
        if p.is_dir() or any(part in IGNORE_DIRS for part in rel.parts):
            continue
        found.add(rel)
    return found


def write_file(rel: Path, data: bytes) -> None:
    dest = BUNDLE / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)


def write_manifest(manifest: dict) -> None:
    MANIFEST.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')


def manifest_matches(manifest: dict) -> bool:
    if not MANIFEST.exists():
        return False
    try:
        current = json.loads(MANIFEST.read_text(encoding='utf-8'))
    except json.JSONDecodeError:
        return False
    return current == manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='write missing and changed bundle files and manifest')
    args = parser.parse_args(argv)

    desired = desired_files()
    manifest = desired_manifest(desired)
    existing = existing_files()
    desired_stored = {stored_for(dest): (dest, data) for dest, data in desired.items()}
    statuses = []

    for stored, (destination, data) in sorted(desired_stored.items(), key=lambda item: item[0].as_posix()):
        path = BUNDLE / stored
        label = f'{stored.as_posix()} -> {destination.as_posix()}'
        if not path.exists():
            statuses.append(('MISSING', label))
            if args.apply:
                write_file(stored, data)
        elif path.read_bytes() != data:
            statuses.append(('DIFF', label))
            if args.apply:
                write_file(stored, data)
        else:
            statuses.append(('OK', label))

    for rel in sorted(existing - set(desired_stored), key=lambda p: p.as_posix()):
        statuses.append(('EXTRA', rel.as_posix()))

    if not manifest_matches(manifest):
        statuses.append(('DIFF', 'manifest.json'))
        if args.apply:
            write_manifest(manifest)

    drift = [s for s in statuses if s[0] != 'OK']
    for status, label in statuses:
        if status != 'OK' or not drift:
            print(f'{status:7} {label}')
    if args.apply:
        print(f'Applied bundle updates; extras are not removed.')
    elif drift:
        print('\nRun with --apply to update missing/different files. Review EXTRA files manually.')
    else:
        print(f'Bundle is in sync ({len(statuses)} item(s), including manifest).')
    return 1 if drift and not args.apply else 0


if __name__ == '__main__':
    raise SystemExit(main())
