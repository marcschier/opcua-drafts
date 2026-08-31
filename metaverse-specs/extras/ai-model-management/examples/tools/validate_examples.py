#!/usr/bin/env python3
"""
Validator for the vendor implementation guides beside this file.

    python metaverse-specs/extras/ai-model-management/examples/tools/validate_examples.py

The guides map real systems onto the information model, which means every one of them
cites member names, enumeration literals and conformance units. Those citations are the
part that rots: a member renamed in the model leaves a guide quietly describing something
that no longer exists, and nothing about a markdown file fails when it does.

Everything here is re-derived from Opc.Ua.AiModelManagement.NodeSet2.xml and from the
specification. Nothing is read from the guides and compared against a second copy of
itself, because a checker that asks the guides what the guides say validates nothing.

Checks:

  * Every model identifier a guide cites in backticks exists in the NodeSet. A backticked
    PascalCase token that is neither a NodeSet name nor a listed vendor term is a typo or
    a renamed member, and both are reported. known-terms.txt is what lets a guide say
    `InvokeModel` without that becoming a hole big enough for `EgressPermited` to fit
    through - adding a term is a deliberate act, visible in a diff.
  * Every ApiDialectEnum and AuthenticationKindEnum literal is exercised by at least one
    guide. The index claims the set is complete; this is that claim, checked. A dialect
    nobody can show an example of is a literal worth reconsidering.
  * Every conformance unit a guide names exists in the specification.
  * Every guide cites the specification by relative path. This is load-bearing beyond
    navigation: check_section_refs.py resolves a bare section reference against any
    document cited by relative path, metaverse-specs/ is a strict tree, and a guide
    without the link fails that check for every section reference it makes.
  * The index lists every guide, every guide is listed by the index, and the dialect the
    index attributes to a guide is one that guide actually assigns.

Exit code 0 when everything holds, 1 otherwise.
"""

import os
import re
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
EXAMPLES = os.path.dirname(HERE)
EXTRAS = os.path.dirname(EXAMPLES)
REPO = os.path.normpath(os.path.join(HERE, "..", "..", "..", "..", ".."))
MODEL = os.path.join(REPO, "model", "metaverse-specs", "ai-model-management")

NODESET = os.path.join(MODEL, "Opc.Ua.AiModelManagement.NodeSet2.xml")
SPEC = os.path.join(
    REPO, "source", "metaverse-specs", "ai-model-management", "spec.md")
INDEX = os.path.join(EXAMPLES, "index.md")
KNOWN_TERMS = os.path.join(HERE, "known-terms.txt")

UA = "{http://opcfoundation.org/UA/2011/03/UANodeSet.xsd}"
UAX = "{http://opcfoundation.org/UA/2008/02/Types.xsd}"

ERRORS: list[str] = []


def err(msg: str) -> None:
    ERRORS.append(msg)


def load_nodeset_names() -> set[str]:
    """Every BrowseName, enumeration literal, structure field and Method argument.

    Method argument names live in the Value of an InputArguments or OutputArguments
    Variable rather than in a BrowseName, so a guide naming `PayloadUri` is naming
    something the model genuinely declares. Reading them here keeps the check honest
    in both directions: a guide may cite an argument, and a typo in one still fails.
    """
    root = ET.parse(NODESET).getroot()
    names: set[str] = set()

    for node in root:
        browse = node.get("BrowseName")
        if browse:
            names.add(browse.split(":", 1)[-1])

        definition = node.find(f"{UA}Definition")
        if definition is not None:
            for field in definition.findall(f"{UA}Field"):
                field_name = field.get("Name")
                if field_name:
                    names.add(field_name)

        if browse and browse.split(":", 1)[-1] in ("InputArguments", "OutputArguments"):
            for arg_name in node.iter(f"{UAX}Name"):
                if arg_name.text:
                    names.add(arg_name.text)

    if not names:
        err("the NodeSet yielded no names; the parse is wrong, not the guides")

    return names


def load_enum_literals(name: str) -> list[str]:
    """The literals of one enumeration, in declaration order."""
    root = ET.parse(NODESET).getroot()

    for node in root.findall(f"{UA}UADataType"):
        if (node.get("BrowseName") or "").split(":", 1)[-1] != name:
            continue
        definition = node.find(f"{UA}Definition")
        if definition is None:
            break
        return [f.get("Name") or "" for f in definition.findall(f"{UA}Field")]

    err(f"{name} is not an enumeration in the NodeSet")
    return []


def load_conformance_units() -> set[str]:
    """Every conformance unit the specification declares."""
    with open(SPEC, encoding="utf-8") as handle:
        text = handle.read()
    return set(re.findall(r"\*\*(AI-[A-Za-z]+)\*\*", text))


def load_profiles() -> set[str]:
    """Every profile the specification's profile table declares.

    Read from the leading column of the clause 13.3 table rather than from prose, so a
    profile a guide claims is checked against the one place that defines it. A guide that
    names a Server shape the specification does not define is claiming something no test
    lab can assess, which is the same failure a misspelled facet would be.
    """
    with open(SPEC, encoding="utf-8") as handle:
        text = handle.read()
    return set(re.findall(r"^\|\s*\*\*((?:AI|Robot) [^*|]*Server)\*\*\s*\|", text, re.M))


def check_profiles(text_by_guide: dict[str, str]) -> None:
    """A guide may name a profile only if the specification defines it.

    This checks the NAME, not the claim. Whether a guide's reachable facets actually
    cover the profile it names is a judgement over prose, and a checker that guessed at
    it would fail on wording rather than on substance. What this does catch is the
    failure that matters mechanically: a profile that does not exist, whether from a
    typo or from an author inventing a Server shape the specification never defined.
    """
    declared = load_profiles()
    if not declared:
        err("no profiles parsed from the specification; the parse is wrong, not the guides")
        return

    for rel, text in text_by_guide.items():
        for claimed in re.findall(r"\*\*((?:AI|Robot) [^*]*Server)\*\*", strip_fences(text)):
            if claimed not in declared:
                err(f"{rel}: `{claimed}` is not a profile the specification defines")


def load_known_terms() -> set[str]:
    """Backticked PascalCase tokens the guides may cite that this model does not declare."""
    if not os.path.exists(KNOWN_TERMS):
        err("known-terms.txt is missing; every vendor identifier would be reported")
        return set()

    terms: set[str] = set()
    with open(KNOWN_TERMS, encoding="utf-8") as handle:
        for line in handle:
            line = line.split("#", 1)[0].strip()
            if line:
                terms.add(line)
    return terms


def guides() -> list[str]:
    """Every guide beside the index."""
    found = []
    for name in sorted(os.listdir(EXAMPLES)):
        if name.endswith(".md") and name != "index.md":
            found.append(os.path.join(EXAMPLES, name))
    return found


# A backticked token. Fenced blocks are stripped first so that sample payloads do not
# masquerade as citations.
BACKTICKED = re.compile(r"`([^`\n]+)`")

# The shape of a model identifier: PascalCase with at least one lower-case letter, so
# that `AI-Base`, `application/json`, `stop` and `POST /v1/models` are not candidates.
IDENTIFIER = re.compile(r"^[A-Z][A-Za-z0-9]*[a-z][A-Za-z0-9]*$")


def strip_fences(text: str) -> str:
    out, fenced = [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if not fenced:
            out.append(line)
    return "\n".join(out)


def citations(text: str) -> set[str]:
    """Backticked tokens shaped like a model identifier.

    A two-part dotted citation - `RateLimit.RetryAfter`, `Usage.InputUnits` - is checked
    part by part, because that form is how a guide names a field of a structure and a typo
    in the second half is exactly as wrong as one in the first. Both halves have to look
    like identifiers for the token to be read that way, which is what keeps a package name
    such as `Microsoft.AI.Foundry.Local` from being mistaken for one.
    """
    found = set()
    for token in BACKTICKED.findall(strip_fences(text)):
        token = token.strip()

        if IDENTIFIER.match(token):
            found.add(token)
            continue

        parts = token.split(".")
        if len(parts) == 2 and all(IDENTIFIER.match(p) for p in parts):
            found.update(parts)

    return found


def check_identifiers(names: set[str], known: set[str]) -> None:
    for path in guides() + [INDEX]:
        rel = os.path.basename(path)
        with open(path, encoding="utf-8") as handle:
            text = handle.read()

        for token in sorted(citations(text)):
            if token not in names and token not in known:
                err(
                    f"{rel}: `{token}` is neither declared by this model nor "
                    f"listed in known-terms.txt"
                )


def check_enum_coverage(text_by_guide: dict[str, str]) -> None:
    for enum in ("ApiDialectEnum", "AuthenticationKindEnum"):
        for literal in load_enum_literals(enum):
            if not literal:
                continue
            if not any(f"`{literal}`" in text for text in text_by_guide.values()):
                err(
                    f"no guide exercises {enum}.{literal}; the index claims every literal "
                    f"is covered"
                )


def check_conformance_units(text_by_guide: dict[str, str]) -> None:
    declared = load_conformance_units()

    for rel, text in text_by_guide.items():
        for unit in sorted(set(re.findall(r"\*\*(AI-[A-Za-z]+)\*\*", text))):
            if unit not in declared:
                err(f"{rel}: **{unit}** is not a conformance unit the specification declares")


def check_spec_link(text_by_guide: dict[str, str]) -> None:
    for rel, text in text_by_guide.items():
        if "source/metaverse-specs/ai-model-management/spec.md" not in text:
            err(
                f"{rel}: does not cite the specification by relative path, so every "
                f"section reference in it resolves against nothing"
            )


def check_index(text_by_guide: dict[str, str]) -> None:
    with open(INDEX, encoding="utf-8") as handle:
        index_text = handle.read()

    linked = set(re.findall(r"\]\((?!http)([a-z0-9-]+\.md)\)", index_text))
    present = set(os.path.basename(p) for p in guides())

    for missing in sorted(present - linked):
        err(f"index.md: does not link {missing}")
    for dangling in sorted(linked - present):
        err(f"index.md: links {dangling}, which does not exist")

    # The dialect the index attributes to a guide has to be one that guide assigns.
    for line in index_text.splitlines():
        if not line.startswith("| ["):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 3:
            continue
        match = re.search(r"\]\(([a-z0-9-]+\.md)\)", cells[0])
        if not match:
            continue
        guide = match.group(1)
        text = text_by_guide.get(guide)
        if text is None:
            continue
        for literal in re.findall(r"`([A-Za-z]+)`", cells[2]):
            if f"`{literal}`" not in text:
                err(
                    f"index.md: attributes `{literal}` to {guide}, which does not "
                    f"mention it"
                )


def main() -> int:
    for required in (NODESET, SPEC, INDEX):
        if not os.path.exists(required):
            print(f"FAIL: {required} is missing")
            return 1

    found = guides()
    if not found:
        print("FAIL: no guides found beside the index")
        return 1

    text_by_guide = {}
    for path in found:
        with open(path, encoding="utf-8") as handle:
            text_by_guide[os.path.basename(path)] = handle.read()

    names = load_nodeset_names()
    known = load_known_terms()

    check_identifiers(names, known)
    check_enum_coverage(text_by_guide)
    check_conformance_units(text_by_guide)
    check_profiles(text_by_guide)
    check_spec_link(text_by_guide)
    check_index(text_by_guide)

    if ERRORS:
        print(f"FAIL: {len(ERRORS)} problem(s) in the vendor guides")
        for problem in ERRORS:
            print(f"  - {problem}")
        return 1

    print(
        f"OK: {len(found)} vendor guide(s) agree with "
        f"Opc.Ua.AiModelManagement.NodeSet2.xml"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
