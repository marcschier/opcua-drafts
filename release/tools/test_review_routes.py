"""Regression checks for working-group routing and content-only handoff."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import manifest as manifest_module
import prepare_private_release
import release_spec
from review_routes import (
    checked_path, cleanup_file_map, closure_routes, public_file_map, relative_path, review_file_map,
    require_review_repository, route_for, translated_content,
)


class ReviewRouteTests(unittest.TestCase):
    def setUp(self):
        self.manifest = manifest_module.load()

    def test_every_specification_has_the_correct_owner(self):
        expected = {
            "wot-binding": "OPC10100-WoT", "wot-connectivity": "OPC10100-WoT",
            "openusd-binding": "OPC12000-Metaverse", "openusd-scene": "OPC12000-Metaverse",
            "vision": "OPC12000-Metaverse", "robot-intent": "OPC12000-Metaverse",
            "ai-model-management": "OPC12000-Metaverse",
            "avro-encoding": "OPC30450-CloudInitiative", "xregistry": "OPC30450-CloudInitiative",
            "schema-registry": "OPC30450-CloudInitiative", "observability-export": "OPC30450-CloudInitiative",
            "data-channels": "spec-drafts",
        }
        self.assertEqual(set(expected), set(self.manifest.spec_ids()))
        for spec, repository in expected.items():
            with self.subTest(spec=spec):
                self.assertEqual(route_for(self.manifest, spec).repository, "OPCF-Members/" + repository)
        route = route_for(self.manifest, "xregistry")
        self.assertEqual((route.group, route.submodule), ("CloudIntegration", "OPC30450-CloudIntegration"))

    def test_specific_source_tool_and_model_mappings_roundtrip(self):
        cases = (
            ("wot-connectivity", "source/wot-specs/WoT-Connectivity/tools/build_model.py",
             "extras/WoT-Connectivity/tools/build_model.py"),
            ("wot-binding", "source/wot-specs/WoT-Binding/examples/new.jsonld",
             "source/WoT-Binding/examples/new.jsonld"),
            ("xregistry", "model/core-specs/xregistry/Opc.Ua.XRegistry.NodeSet2.xml",
             "model/Opc.Ua.XRegistry.NodeSet2.xml"),
            ("vision", "source/metaverse-specs/vision/research.md", "extras/vision/research.md"),
            ("openusd-binding", "model/metaverse-specs/openusd-binding/Opc.Ua.Pumps.OpenUsd.NodeSet2.xml",
             "model/dependencies/Opc.Ua.Pumps.OpenUsd.NodeSet2.xml"),
        )
        for spec, public, review in cases:
            with self.subTest(spec=spec, public=public):
                route = route_for(self.manifest, spec)
                self.assertEqual(route.translate(public), review)
                self.assertEqual(route.translate(review, reverse=True), public)

    def test_core_layout_remains_unchanged(self):
        route = route_for(self.manifest, "data-channels")
        path = "source/core-specs/data-channels/spec.md"
        self.assertEqual(route.translate(path), path)
        self.assertEqual(translated_content(self.manifest, "data-channels", path, path, b"unchanged"), b"unchanged")

    def test_cross_working_group_closure_is_rejected(self):
        data = copy.deepcopy(self.manifest._data)
        data["specs"]["wot-binding"]["closure"] = ["xregistry"]
        invalid = manifest_module.Manifest(data, self.manifest._path)
        with self.assertRaisesRegex(ValueError, "cannot cross"):
            closure_routes(invalid, "wot-binding")

    def test_return_inventory_uses_review_checkout_not_absent_public_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for path in ("source/WoT-Binding/spec.md", "source/WoT-Binding/new-clause.md",
                         "extras/WoT-Binding/tools/validate_local.py", "model/dependencies/base.xml",
                         ".github/workflows/publish.yml", "AUTHORING.md"):
                file = root.joinpath(*path.split("/"))
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text("fixture", encoding="utf-8")
            files = review_file_map(self.manifest, "wot-binding", root)
            self.assertEqual(files, {
                "source/wot-specs/WoT-Binding/spec.md": "source/WoT-Binding/spec.md",
                "source/wot-specs/WoT-Binding/new-clause.md": "source/WoT-Binding/new-clause.md",
                "source/wot-specs/WoT-Binding/tools/validate_local.py": "extras/WoT-Binding/tools/validate_local.py",
            })

    def test_legacy_word_is_excluded_and_infrastructure_is_rejected(self):
        files = ["source/wot-specs/WoT-Binding/spec.md", "word-drafts/OPC-UA-WoT-Binding.docx"]
        self.assertEqual(public_file_map(self.manifest, "wot-binding", files),
                         {files[0]: "source/WoT-Binding/spec.md"})
        for path in (".github/workflows/publish.yml", ".config/dotnet-tools.json", "AUTHORING.md",
                     "source/agreement-of-use.md", "source/figures/palette.xml", "word-drafts/build.py"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                route_for(self.manifest, "wot-binding").require_content(path)

    def test_paths_cannot_escape_the_repository(self):
        for value in ("../spec.md", "source/../../secrets", "/absolute", "C:\\absolute", "source//file"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                relative_path(value)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(checked_path(root, "source\\spec.md"), root / "source" / "spec.md")

    def test_wrong_repository_and_spoofed_remote_are_rejected(self):
        for url in (
                "https://github.com/another/repo.git",
                "https://elsewhere.example/github.com/OPCF-Members/OPC10100-WoT",
                "file:///OPCF-Members/OPC10100-WoT"):
            with self.subTest(url=url), patch("review_routes.subprocess.run",
                    return_value=SimpleNamespace(returncode=0, stdout=url)):
                with self.assertRaisesRegex(ValueError, "does not belong"):
                    require_review_repository(Path("."), "OPCF-Members/OPC10100-WoT")
        for url in ("https://github.com/OPCF-Members/OPC10100-WoT.git",
                    "git@github.com:OPCF-Members/OPC10100-WoT.git"):
            with patch("review_routes.subprocess.run", return_value=SimpleNamespace(returncode=0, stdout=url)):
                require_review_repository(Path("."), "OPCF-Members/OPC10100-WoT")

    def test_prepare_preserves_infrastructure_and_rejects_all_conflicts_before_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            root, export = Path(directory) / "review", Path(directory) / "export"
            existing = root / "source" / "WoT-Binding" / "spec.md"
            existing.parent.mkdir(parents=True)
            existing.write_bytes(b"reviewed destination edit")
            infrastructure = root / "AUTHORING.md"
            infrastructure.write_bytes(b"Foundation owned")
            incoming = export / "source" / "wot-specs" / "WoT-Binding"
            incoming.mkdir(parents=True)
            (incoming / "spec.md").write_bytes(b"conflicting source")
            (incoming / "new.md").write_bytes(b"new content")
            with self.assertRaisesRegex(RuntimeError, "reconcile"):
                prepare_private_release.prepare("wot-binding", root, export, self.manifest)
            self.assertEqual(existing.read_bytes(), b"reviewed destination edit")
            self.assertEqual(infrastructure.read_bytes(), b"Foundation owned")
            self.assertFalse((existing.parent / "new.md").exists())
            (incoming / "spec.md").write_bytes(existing.read_bytes())
            changed = prepare_private_release.prepare("wot-binding", root, export, self.manifest)
            self.assertEqual(set(changed), {"source/WoT-Binding/spec.md", "source/WoT-Binding/new.md"})
            self.assertEqual((existing.parent / "new.md").read_bytes(), b"new content")
            self.assertEqual(infrastructure.read_bytes(), b"Foundation owned")

    def test_return_preflight_does_not_overwrite_public_edits(self):
        with tempfile.TemporaryDirectory() as directory:
            root, review = Path(directory) / "public", Path(directory) / "review"
            root.mkdir()
            review.mkdir()
            (root / "one.md").write_bytes(b"public edit")
            (review / "one.md").write_bytes(b"review edit")
            (review / "two.md").write_bytes(b"new")
            with patch.object(release_spec, "REPO", root), self.assertRaisesRegex(RuntimeError, "overwrite"):
                release_spec.copy_from_import(["one.md", "two.md"], review)
            self.assertEqual((root / "one.md").read_bytes(), b"public edit")
            self.assertFalse((root / "two.md").exists())

    def test_manifest_and_cross_repo_links_are_routed_without_reassigning_model_identity(self):
        source = "source/core-specs/xregistry/manifest.json"
        document = {
            "identity": {"docNumber": "OPC 99004-1", "namespaceUri": "urn:model", "version": "0.7.0"},
            "model": {"nodeset": "model/core-specs/xregistry/Opc.Ua.XRegistry.NodeSet2.xml"},
            "output": {},
        }
        routed = json.loads(translated_content(self.manifest, "xregistry", source,
                                              "source/xregistry/manifest.json", json.dumps(document).encode()))
        self.assertEqual(routed["identity"], {"docNumber": "OPC 30452", "namespaceUri": "urn:model", "version": "0.7.0"})
        self.assertEqual(routed["model"]["nodeset"], "model/Opc.Ua.XRegistry.NodeSet2.xml")
        restored = json.loads(translated_content(self.manifest, "xregistry", "source/xregistry/manifest.json",
                                                source, json.dumps(routed).encode(), reverse=True))
        self.assertEqual(restored["model"], document["model"])
        link = b"[base](../../core-specs/xregistry/spec.md#sec-registrytype)"
        converted = translated_content(self.manifest, "wot-binding", "source/wot-specs/WoT-Binding/spec.md",
                                       "source/WoT-Binding/spec.md", link)
        self.assertIn(b"OPCF-Members/OPC30450-CloudInitiative/blob/main/source/xregistry/spec.md#sec-registrytype", converted)

    def test_each_closure_manifest_keeps_its_own_assigned_number(self):
        content = {"identity": {"docNumber": "old"}, "model": {
            "nodeset": "model/metaverse-specs/ai-model-management/Opc.Ua.AiModelManagement.NodeSet2.xml"}}
        routed = json.loads(translated_content(
            self.manifest, "vision", "source/metaverse-specs/ai-model-management/manifest.json",
            "source/ai-model-management/manifest.json", json.dumps(content).encode()))
        self.assertEqual(routed["identity"]["docNumber"], "OPC 12001-5")

    def test_literal_examples_and_binary_models_are_not_rewritten(self):
        link = "[base](../../core-specs/xregistry/spec.md)"
        text = f"{link}\n\n`{link}`\n\n```text\n{link}\n```\n"
        result = translated_content(
            self.manifest, "wot-binding", "source/wot-specs/WoT-Binding/spec.md",
            "source/WoT-Binding/spec.md", text.encode()).decode()
        self.assertIn(f"`{link}`", result)
        self.assertIn(f"```text\n{link}\n```", result)
        self.assertEqual(result.count("https://github.com/"), 1)
        payload = b"\x00\xffmodel"
        self.assertEqual(translated_content(self.manifest, "xregistry",
            "model/core-specs/xregistry/Opc.Ua.XRegistry.NodeSet2.xml",
            "model/Opc.Ua.XRegistry.NodeSet2.xml", payload), payload)

    def test_cleanup_keeps_a_required_model_until_a_dependency_snapshot_exists(self):
        namespace = "http://opcfoundation.org/UA/2011/03/UANodeSet.xsd"
        registry = f'<UANodeSet xmlns="{namespace}"><Models><Model ModelUri="urn:xreg"/></Models></UANodeSet>'
        schema = (f'<UANodeSet xmlns="{namespace}"><Models><Model ModelUri="urn:schema">'
                  '<RequiredModel ModelUri="urn:xreg"/></Model></Models></UANodeSet>')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = root / "model"
            model.mkdir()
            (model / "Opc.Ua.XRegistry.NodeSet2.xml").write_text(registry, encoding="utf-8")
            (model / "Opc.Ua.SchemaRegistry.NodeSet2.xml").write_text(schema, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "still required"):
                cleanup_file_map(self.manifest, "xregistry", root)
            (model / "dependencies").mkdir()
            (model / "dependencies" / "xregistry.xml").write_text(registry, encoding="utf-8")
            files = cleanup_file_map(self.manifest, "xregistry", root)
            self.assertEqual(list(files.values()), ["model/Opc.Ua.XRegistry.NodeSet2.xml"])


if __name__ == "__main__":
    unittest.main()
