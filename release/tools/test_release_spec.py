#!/usr/bin/env python3
"""Regression tests for release grouping and SpecificationPublisher batch repair."""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / ".github/scripts"))

import check_section_refs  # noqa: E402
import manifest as manifest_module  # noqa: E402
import release_spec  # noqa: E402


class ReleaseSpecTests(unittest.TestCase):
    def setUp(self):
        self.manifest = manifest_module.load()
        current_batch = (
            REPO / "word-drafts/tools/specs/batch.json"
        ).read_text(encoding="utf-8")
        self.batch_text, _ = release_spec.repair_word_batch_return(
            current_batch, self.manifest, self.manifest.spec_ids()
        )

    def test_vision_and_ai_are_one_symmetric_release_group(self):
        self.assertEqual(
            set(self.manifest.closure("vision")),
            {"vision", "ai-model-management"},
        )
        self.assertEqual(
            set(self.manifest.closure("ai-model-management")),
            {"vision", "ai-model-management"},
        )
        self.assertEqual(release_spec.public_dependency_blockers(self.manifest, "vision"), [])
        self.assertEqual(
            release_spec.public_dependency_blockers(self.manifest, "ai-model-management"), []
        )

    def test_vision_review_readme_moves_but_external_mapping_stays_public(self):
        vision = self.manifest.spec("vision")
        moved = {release_spec.norm(path) for path in vision["move"]}
        self.assertIn("source/metaverse-specs/README.md", moved)
        self.assertNotIn(
            "source/metaverse-specs/vision-ai-external-result-mapping.md",
            moved,
        )
        self.assertIn(
            "source/metaverse-specs/vision-ai-external-result-mapping.md",
            vision["reverseRefs"],
        )
        self.assertIn(
            "source/metaverse-specs/vision-ai-external-result-mapping.md",
            self.manifest.spec("ai-model-management")["reverseRefs"],
        )

    def test_release_and_return_restore_migrated_batch(self):
        closure = self.manifest.closure("vision")
        released, removed = release_spec.repair_word_batch_release(
            self.batch_text, self.manifest, closure
        )
        released_ids = {
            entry["spec"] for entry in json.loads(released)["migrated"]
        }
        self.assertEqual(removed, 2)
        self.assertNotIn("vision", released_ids)
        self.assertNotIn("ai-model-management", released_ids)

        returned, restored = release_spec.repair_word_batch_return(
            released, self.manifest, closure
        )
        self.assertEqual(restored, 2)
        self.assertEqual(json.loads(returned), json.loads(self.batch_text))

    def test_schema_release_removes_only_schema_batch_entry(self):
        released, removed = release_spec.repair_word_batch_release(
            self.batch_text, self.manifest, ["schema-registry"]
        )
        before = {
            entry["spec"] for entry in json.loads(self.batch_text)["migrated"]
        }
        after = {entry["spec"] for entry in json.loads(released)["migrated"]}
        self.assertEqual(removed, 1)
        self.assertEqual(before - after, {"schema-registry"})

    def test_private_document_labels_distinguish_guides(self):
        self.assertEqual(
            release_spec.private_document_label(
                "extras/metaverse-specs/ai-model-management/examples/index.md"
            ),
            "Guides",
        )
        self.assertEqual(
            release_spec.private_document_label(
                "source/metaverse-specs/ai-model-management/spec.md"
            ),
            "Specification",
        )

    def test_private_inventory_row_rewrites_retained_guide_link(self):
        text = (
            "| Specification | Why | Version | Status | Documents |\n"
            "|---|---|---|---|---|\n"
            "| AI | Eleven [implementation guides]"
            "(extras/metaverse-specs/ai-model-management/examples/index.md) | "
            "0.6.0 | public | [Specification]"
            "(source/metaverse-specs/ai-model-management/spec.md) |\n"
        )
        released, count = release_spec.repair_markdown_table_rows_release(
            text,
            {"extras/metaverse-specs/ai-model-management/"},
            "README.md",
            {
                "extras/metaverse-specs/ai-model-management/examples/index.md",
                "source/metaverse-specs/ai-model-management/spec.md",
            },
            [
                "extras/metaverse-specs/ai-model-management",
                "source/metaverse-specs/ai-model-management",
            ],
            "UNDER REVIEW",
            self.manifest,
        )
        self.assertEqual(count, 1)
        self.assertNotIn(
            "](extras/metaverse-specs/ai-model-management/examples/index.md)",
            released,
        )
        self.assertIn(
            "OPCF-Members/spec-drafts/blob/main/"
            "extras/metaverse-specs/ai-model-management/examples/index.md",
            released,
        )

    def test_reverse_reference_list_item_is_capsuled_before_link_repair(self):
        text = (
            "- [`source/metaverse-specs/vision/`](../source/metaverse-specs/vision/) "
            "— Vision tooling and prose.\n"
        )
        released, count = release_spec.repair_markdown_reverse_lines_release(
            text,
            {"vision"},
            "metaverse-specs/README.md",
            {"source/metaverse-specs/vision/spec.md"},
            ["source/metaverse-specs/vision"],
            "UNDER REVIEW",
        )
        self.assertEqual(count, 1)
        self.assertIn("UNDER REVIEW", released)
        self.assertIn("release-spec-link:", released)

    def test_duplicate_publisher_ids_are_rejected(self):
        data = json.loads(Path(manifest_module.DEFAULT_MANIFEST).read_text(encoding="utf-8"))
        broken = copy.deepcopy(data)
        broken["specs"]["robot-intent"]["publisherSpecs"][0]["spec"] = "vision"
        problems = manifest_module.Manifest(broken, manifest_module.DEFAULT_MANIFEST).validate()
        self.assertTrue(
            any("publisher spec id 'vision'" in problem for problem in problems),
            problems,
        )

    def test_duplicate_publisher_fields_are_rejected_within_one_release(self):
        data = json.loads(Path(manifest_module.DEFAULT_MANIFEST).read_text(encoding="utf-8"))
        broken = copy.deepcopy(data)
        broken["specs"]["vision"]["publisherSpecs"].append(
            copy.deepcopy(broken["specs"]["vision"]["publisherSpecs"][0])
        )
        problems = manifest_module.Manifest(broken, manifest_module.DEFAULT_MANIFEST).validate()
        self.assertTrue(
            any("publisher spec id 'vision'" in problem for problem in problems),
            problems,
        )
        self.assertTrue(
            any("publisher markdown" in problem for problem in problems),
            problems,
        )
        self.assertTrue(
            any("publisher document number 'OPC 99011-1'" in problem for problem in problems),
            problems,
        )

    def test_publisher_heading_numbers_follow_template_insertions(self):
        text = """\
## Scope {#sec-scope}
### Scope detail {#sec-scope-detail}
## Overview {#sec-overview}
### Overview detail {#sec-overview-detail}
## Information model {#sec-information-model}
## Information model reference {#anx-a annex=normative}
### Annex detail {#sec-annex-detail}
"""
        numbers = check_section_refs.clause_numbers(text)
        self.assertEqual(
            numbers,
            {"1", "1.1", "4", "4.1", "5", "A", "A.1"},
        )
        mutated = text.replace(
            "### Overview detail {#sec-overview-detail}",
            "#### Overview detail {#sec-overview-detail}",
        )
        self.assertNotIn("4.1", check_section_refs.clause_numbers(mutated))
        self.assertEqual(check_section_refs.annex_letters(text), {"A"})


if __name__ == "__main__":
    unittest.main()
