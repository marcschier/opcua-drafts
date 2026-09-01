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

import manifest as manifest_module  # noqa: E402
import release_spec  # noqa: E402


class ReleaseSpecTests(unittest.TestCase):
    def setUp(self):
        self.manifest = manifest_module.load()
        self.batch_text = (
            REPO / "word-drafts/tools/specs/batch.json"
        ).read_text(encoding="utf-8")

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

    def test_duplicate_publisher_ids_are_rejected(self):
        data = json.loads(Path(manifest_module.DEFAULT_MANIFEST).read_text(encoding="utf-8"))
        broken = copy.deepcopy(data)
        broken["specs"]["robot-intent"]["publisherSpecs"][0]["spec"] = "vision"
        problems = manifest_module.Manifest(broken, manifest_module.DEFAULT_MANIFEST).validate()
        self.assertTrue(
            any("publisher spec id 'vision'" in problem for problem in problems),
            problems,
        )


if __name__ == "__main__":
    unittest.main()
