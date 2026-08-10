#!/usr/bin/env python3
"""Regression tests for the xRegistry AAS semantic validator."""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_xregistry_aas as validator


class SymbolicIdentifierTests(unittest.TestCase):
    def test_published_examples(self) -> None:
        for source, expected in validator.IDENTIFIER_EXAMPLES.items():
            with self.subTest(source=source):
                actual = validator.symbolic_identifier(source)
                self.assertEqual(expected, actual)
                self.assertTrue(
                    actual.endswith(hashlib.sha256(source.encode("utf-8")).hexdigest())
                )

    def test_singleton_collision_and_reversed_order_are_identical(self) -> None:
        first, second = validator.COLLIDING_PREFIX_SOURCES
        self.assertEqual(
            validator.readable_prefix(first),
            validator.readable_prefix(second),
        )

        singleton = {first: validator.symbolic_identifier(first)}
        forward = {
            source: validator.symbolic_identifier(source)
            for source in (first, second)
        }
        reverse = {
            source: validator.symbolic_identifier(source)
            for source in (second, first)
        }

        self.assertEqual(singleton[first], forward[first])
        self.assertEqual(forward, reverse)
        self.assertNotEqual(forward[first].casefold(), forward[second].casefold())

    def test_full_xid_uses_parent_and_resource_source_identities(self) -> None:
        group_source = "https://example.com/aas/one"
        resource_source = "https://example.com/submodels/nameplate"
        xid = validator.resource_xid(
            "shells",
            group_source,
            "submodels",
            resource_source,
        )
        self.assertEqual(
            xid,
            f"/shells/{validator.symbolic_identifier(group_source)}"
            f"/submodels/{validator.symbolic_identifier(resource_source)}",
        )

    def test_malformed_uri_like_sources_use_free_form_fallback(self) -> None:
        expectations = {
            "http://[": "http",
            "https://[broken": "https.broken",
            "custom://[bad/path": "custom.bad.path",
        }
        for source, expected_prefix in expectations.items():
            with self.subTest(source=source):
                identifier = validator.symbolic_identifier(source)
                self.assertTrue(identifier.startswith(f"{expected_prefix}."))
                self.assertTrue(
                    identifier.endswith(
                        hashlib.sha256(source.encode("utf-8")).hexdigest()
                    )
                )
                self.assertRegex(identifier, validator.ID_RE)

    def test_legal_uri_still_uses_authority_path_algorithm(self) -> None:
        self.assertEqual(
            "com.example.templates.nameplate",
            validator.readable_prefix(
                "https://example.com/templates/nameplate?ignored=yes#ignored"
            ),
        )

    def test_invalid_authorities_use_free_form_fallback(self) -> None:
        expectations = {
            "https://example.com:bad/path": "https.example.com-bad.path",
            "https://example.com:65536/path": "https.example.com-65536.path",
            "https://[2001:db8::zz]:443/path": "https.2001-db8-zz-443.path",
        }
        for source, expected_prefix in expectations.items():
            with self.subTest(source=source):
                self.assertEqual(
                    expected_prefix,
                    validator.readable_prefix(source),
                )

    def test_valid_ports_and_ipv6_use_authority_path_algorithm(self) -> None:
        expectations = {
            "https://example.com:443/path": "com.example.443.path",
            "https://[2001:db8::1]:8443/path": "2001-db8-1.8443.path",
            "https://example.com:65535/path": "com.example.65535.path",
        }
        for source, expected_prefix in expectations.items():
            with self.subTest(source=source):
                self.assertEqual(
                    expected_prefix,
                    validator.readable_prefix(source),
                )

    def test_control_characters_use_free_form_fallback(self) -> None:
        source = "https://example.com/pa\nth"
        identifier = validator.symbolic_identifier(source)
        self.assertTrue(identifier.startswith("https.example.com.pa-th."))
        self.assertTrue(
            identifier.endswith(hashlib.sha256(source.encode("utf-8")).hexdigest())
        )

    def test_leading_and_trailing_whitespace_use_exact_free_form_source(self) -> None:
        valid = "https://example.com/path"
        self.assertEqual("com.example.path", validator.readable_prefix(valid))

        for source in (f" {valid}", f"{valid} "):
            with self.subTest(source=source):
                identifier = validator.symbolic_identifier(source)
                self.assertEqual(
                    "https.example.com.path",
                    validator.readable_prefix(source),
                )
                self.assertTrue(
                    identifier.endswith(
                        hashlib.sha256(source.encode("utf-8")).hexdigest()
                    )
                )
                self.assertNotEqual(
                    validator.symbolic_identifier(valid),
                    identifier,
                )

    def test_long_source_identity_stays_within_xregistry_limit(self) -> None:
        identifier = validator.symbolic_identifier("x" * 2048)
        self.assertEqual(128, len(identifier))
        self.assertRegex(identifier, validator.ID_RE)


class ModelValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with validator.MODEL_PATH.open(encoding="utf-8") as stream:
            cls.model = json.load(stream)

    def test_current_model_passes(self) -> None:
        self.assertEqual([], validator.validate_model(self.model))

    def test_missing_group_source_identities_are_rejected(self) -> None:
        expectations = {
            "submodeltemplates": "templatenamespace",
            "conceptdictionaries": "dictionaryidentifier",
            "aasxregistries": "storeidentifier",
        }
        for group_name, attribute_name in expectations.items():
            with self.subTest(group=group_name):
                mutated = copy.deepcopy(self.model)
                del mutated["groups"][group_name]["attributes"][attribute_name]
                errors = validator.validate_model(mutated)
                self.assertTrue(
                    any(attribute_name in error for error in errors),
                    errors,
                )

    def test_non_retaining_history_policy_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.model)
        submodels = mutated["groups"]["shells"]["resources"]["submodels"]
        submodels["maxversions"] = 1
        submodels["metaattributes"]["historypolicy"]["default"] = "latest-only"
        errors = validator.validate_model(mutated)
        self.assertTrue(any("maxversions" in error for error in errors), errors)
        self.assertTrue(any("historypolicy" in error for error in errors), errors)

    def test_history_policy_requires_strict_true(self) -> None:
        for mutation in ("false", "missing"):
            with self.subTest(mutation=mutation):
                mutated = copy.deepcopy(self.model)
                policy = (
                    mutated["groups"]["shells"]["resources"]["submodels"]
                    ["metaattributes"]["historypolicy"]
                )
                if mutation == "false":
                    policy["strict"] = False
                else:
                    del policy["strict"]
                errors = validator.validate_model(mutated)
                self.assertTrue(
                    any("historypolicy: strict must be true" in error for error in errors),
                    errors,
                )

    def test_domain_metadata_must_not_use_reserved_resourceattributes(self) -> None:
        for name in ("historypolicy", "tags"):
            with self.subTest(name=name):
                mutated = copy.deepcopy(self.model)
                if name == "historypolicy":
                    resource = mutated["groups"]["shells"]["resources"]["submodels"]
                else:
                    resource = (
                        mutated["groups"]["aasxregistries"]["resources"]["packages"]
                    )
                definition = resource["metaattributes"].pop(name)
                resource.setdefault("resourceattributes", {})[name] = definition
                errors = validator.validate_model(mutated)
                self.assertTrue(
                    any(
                        name in error and "must be defined in metaattributes" in error
                        for error in errors
                    ),
                    errors,
                )

    def test_referrers_must_not_be_package_metadata(self) -> None:
        mutated = copy.deepcopy(self.model)
        packages = mutated["groups"]["aasxregistries"]["resources"]["packages"]
        packages["metaattributes"]["referrers"] = {
            "name": "referrers",
            "type": "array",
        }
        errors = validator.validate_model(mutated)
        self.assertTrue(
            any("referrers must be separate Resources" in error for error in errors),
            errors,
        )

    def test_ambiguous_package_digest_model_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.model)
        packages = mutated["groups"]["aasxregistries"]["resources"]["packages"]
        packages["attributes"]["digest"]["required"] = False
        errors = validator.validate_model(mutated)
        self.assertTrue(any("blob verification" in error for error in errors), errors)

    def test_tag_aliases_must_be_lossless_array_entries(self) -> None:
        mutated = copy.deepcopy(self.model)
        packages = mutated["groups"]["aasxregistries"]["resources"]["packages"]
        packages["metaattributes"]["tags"] = {
            "name": "tags",
            "type": "map",
            "item": {"type": "string"},
            "description": "Mutable tags map.",
        }
        errors = validator.validate_model(mutated)
        self.assertTrue(any("lossless alias entries" in error for error in errors), errors)
        self.assertTrue(any("tags.tag: must be required" in error for error in errors), errors)
        self.assertTrue(
            any("tags.manifestdigest: must be required" in error for error in errors),
            errors,
        )

    def test_digest_algorithm_requires_exact_case_metadata(self) -> None:
        resources = {
            "submodels": ("shells", "submodels"),
            "packages": ("aasxregistries", "packages"),
            "referrers": ("aasxregistries", "referrers"),
        }
        for resource_name, (group_name, model_name) in resources.items():
            for mutation in ("false", "missing"):
                with self.subTest(resource=resource_name, mutation=mutation):
                    mutated = copy.deepcopy(self.model)
                    digest_algorithm = (
                        mutated["groups"][group_name]["resources"]
                        [model_name]["attributes"]["digestalg"]
                    )
                    if mutation == "false":
                        digest_algorithm["matchcase"] = False
                    else:
                        del digest_algorithm["matchcase"]
                    errors = validator.validate_model(mutated)
                    self.assertTrue(
                        any(
                            f"{resource_name}.digestalg" in error
                            and "case" in error
                            for error in errors
                        ),
                        errors,
                    )

    def test_digest_algorithm_enum_spelling_is_exact(self) -> None:
        resources = {
            "submodels": ("shells", "submodels"),
            "packages": ("aasxregistries", "packages"),
            "referrers": ("aasxregistries", "referrers"),
        }
        for resource_name, (group_name, model_name) in resources.items():
            with self.subTest(resource=resource_name):
                mutated = copy.deepcopy(self.model)
                digest_algorithm = (
                    mutated["groups"][group_name]["resources"]
                    [model_name]["attributes"]["digestalg"]
                )
                digest_algorithm["enum"] = ["sha256", "Sha384", "Sha512"]
                errors = validator.validate_model(mutated)
                self.assertTrue(
                    any(
                        f"{resource_name}.digestalg" in error
                        and "exactly Sha256" in error
                        for error in errors
                    ),
                    errors,
                )

    def test_attestations_require_separate_referrer_resources(self) -> None:
        mutated = copy.deepcopy(self.model)
        packages = mutated["groups"]["aasxregistries"]["resources"]["packages"]
        packages["attributes"]["attestations"] = {
            "name": "attestations",
            "type": "array",
            "item": {"type": "string"},
        }
        packages["attributes"]["subject"] = {
            "name": "subject",
            "type": "string",
        }
        packages["attributes"]["format"]["enum"].append("Opaque/1.0")
        referrers = mutated["groups"]["aasxregistries"]["resources"]["referrers"]
        referrers["maxversions"] = 0
        del referrers["attributes"]["subjectmanifestdigest"]
        errors = validator.validate_model(mutated)
        self.assertTrue(
            any("attestations must not be package Version attributes" in error for error in errors),
            errors,
        )
        self.assertTrue(
            any("referrers.subjectmanifestdigest: must be required" in error for error in errors),
            errors,
        )
        self.assertTrue(
            any("maxversions must be 1" in error for error in errors),
            errors,
        )
        self.assertTrue(
            any("referrer-only Opaque/1.0" in error for error in errors),
            errors,
        )


class OciProjectionTests(unittest.TestCase):
    def test_tag_movement_retains_distinct_immutable_versions(self) -> None:
        versions: dict[str, dict[str, str]] = {}
        tags: list[dict[str, str]] = []

        first = validator.OCI_EXAMPLES[0]
        first_id = validator.apply_oci_tag(
            versions,
            tags,
            "Release_2026.08",
            first["manifestdigest"],
            base64.b64decode(first["packagebase64"]),
            "Sha256",
            first["digest"],
        )
        retained_first = copy.deepcopy(versions[first_id])

        second = validator.OCI_EXAMPLES[1]
        second_id = validator.apply_oci_tag(
            versions,
            tags,
            "Release_2026.08",
            second["manifestdigest"],
            base64.b64decode(second["packagebase64"]),
            "Sha256",
            second["digest"],
        )

        self.assertNotEqual(first_id, second_id)
        self.assertEqual(2, len(versions))
        self.assertEqual(retained_first, versions[first_id])
        self.assertEqual(
            [{"tag": "Release_2026.08", "manifestdigest": second["manifestdigest"]}],
            tags,
        )

    def test_raw_oci_tags_are_preserved_as_values(self) -> None:
        versions: dict[str, dict[str, str]] = {}
        tags: list[dict[str, str]] = []
        example = validator.OCI_EXAMPLES[0]
        blob = base64.b64decode(example["packagebase64"])

        for tag in validator.OCI_TAG_EXAMPLES:
            validator.apply_oci_tag(
                versions,
                tags,
                tag,
                example["manifestdigest"],
                blob,
                "Sha256",
                example["digest"],
            )

        self.assertEqual(128, len(validator.OCI_TAG_EXAMPLES[-1]))
        self.assertEqual(list(validator.OCI_TAG_EXAMPLES), [entry["tag"] for entry in tags])
        for tag in validator.OCI_TAG_EXAMPLES:
            self.assertRegex(tag, validator.OCI_TAG_RE)

    def test_invalid_oci_tags_are_rejected(self) -> None:
        example = validator.OCI_EXAMPLES[0]
        blob = base64.b64decode(example["packagebase64"])
        for tag in ("", "release/name", "x" * 129):
            with self.subTest(tag=tag):
                with self.assertRaisesRegex(ValueError, "invalid OCI tag"):
                    validator.apply_oci_tag(
                        {},
                        [],
                        tag,
                        example["manifestdigest"],
                        blob,
                        "Sha256",
                        example["digest"],
                    )

    def test_returned_package_bytes_verify_against_blob_digest(self) -> None:
        for example in validator.OCI_EXAMPLES:
            with self.subTest(manifest=example["manifestdigest"]):
                blob = base64.b64decode(example["packagebase64"])
                self.assertEqual(
                    example["digest"],
                    hashlib.sha256(blob).hexdigest(),
                )

    def test_descriptor_digest_algorithm_is_verified_and_retained(self) -> None:
        blob = b"AASX package bytes for digest algorithm coverage"
        versions: dict[str, dict[str, str]] = {}
        tags: list[dict[str, str]] = []
        for index, algorithm in enumerate(("Sha256", "Sha384", "Sha512"), start=1):
            with self.subTest(algorithm=algorithm):
                manifest_digest = f"sha256:{index:064x}"
                package_digest = validator.digest_bytes(blob, algorithm)
                version_id = validator.apply_oci_tag(
                    versions,
                    tags,
                    algorithm,
                    manifest_digest,
                    blob,
                    algorithm,
                    package_digest,
                )
                self.assertEqual(algorithm, versions[version_id]["digestalg"])
                self.assertEqual(package_digest, versions[version_id]["digest"])

    def test_unsupported_descriptor_digest_algorithm_is_rejected(self) -> None:
        versions: dict[str, dict[str, str]] = {}
        tags: list[dict[str, str]] = []
        with self.assertRaisesRegex(ValueError, "unsupported digest algorithm"):
            validator.apply_oci_tag(
                versions,
                tags,
                "unsupported",
                validator.OCI_EXAMPLES[0]["manifestdigest"],
                b"package",
                "Blake3",
                "not-used",
            )
        self.assertEqual({}, versions)
        self.assertEqual([], tags)

    def test_digest_algorithm_enum_is_case_sensitive(self) -> None:
        for algorithm in ("sha256", "SHA256", "sha384", "sha512"):
            with self.subTest(algorithm=algorithm):
                with self.assertRaisesRegex(
                    ValueError,
                    "unsupported digest algorithm",
                ):
                    validator.digest_bytes(b"package", algorithm)

    def test_blob_digest_mismatch_is_rejected(self) -> None:
        example = validator.OCI_EXAMPLES[0]
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            validator.apply_oci_tag(
                {},
                [],
                "Release_2026.08",
                example["manifestdigest"],
                b"modified package bytes",
                "Sha256",
                example["digest"],
            )

    def test_existing_manifest_version_cannot_be_mutated(self) -> None:
        example = validator.OCI_EXAMPLES[0]
        versions: dict[str, dict[str, str]] = {}
        tags: list[dict[str, str]] = []
        blob = base64.b64decode(example["packagebase64"])
        validator.apply_oci_tag(
            versions,
            tags,
            "Release_2026.08",
            example["manifestdigest"],
            blob,
            "Sha256",
            example["digest"],
        )
        mutated_digest = validator.digest_bytes(b"different bytes", "Sha256")
        with self.assertRaisesRegex(ValueError, "immutable"):
            validator.apply_oci_tag(
                versions,
                tags,
                "Release_2026.08",
                example["manifestdigest"],
                b"different bytes",
                "Sha256",
                mutated_digest,
            )

    def test_later_attestation_is_separate_and_preserves_package_default(self) -> None:
        versions: dict[str, dict[str, str]] = {}
        tags: list[dict[str, str]] = []
        for example in validator.OCI_EXAMPLES:
            validator.apply_oci_tag(
                versions,
                tags,
                "Release_2026.08",
                example["manifestdigest"],
                base64.b64decode(example["packagebase64"]),
                "Sha256",
                example["digest"],
            )
        default_before = next(reversed(versions))
        package_resource = {
            "defaultversionid": default_before,
            "versions": versions,
        }
        before = copy.deepcopy(package_resource)
        referrers: dict[str, dict[str, object]] = {}
        example = validator.OCI_REFERRER_EXAMPLE

        referrer_id = validator.add_oci_referrer_resource(
            package_resource["versions"],
            referrers,
            example["subjectmanifestdigest"],
            example["manifestdigest"],
            base64.b64decode(example["attestationbase64"]),
            example["digestalg"],
            example["digest"],
            example["artifacttype"],
            example["signer"],
        )

        self.assertEqual(before, package_resource)
        self.assertEqual(default_before, package_resource["defaultversionid"])
        self.assertNotIn(referrer_id, package_resource["versions"])
        self.assertEqual(referrer_id, referrers[referrer_id]["defaultversionid"])
        self.assertEqual(
            [referrer_id],
            list(referrers[referrer_id]["versions"]),
        )
        referrer_version = referrers[referrer_id]["versions"][referrer_id]
        self.assertEqual(example["manifestdigest"], referrer_version["manifestdigest"])
        self.assertEqual(
            example["subjectmanifestdigest"],
            referrer_version["subjectmanifestdigest"],
        )
        self.assertEqual(example["digest"], referrer_version["digest"])

    def test_referrer_resource_cannot_be_mutated(self) -> None:
        package = validator.OCI_EXAMPLES[0]
        package_versions: dict[str, dict[str, str]] = {}
        validator.apply_oci_tag(
            package_versions,
            [],
            "Release_2026.08",
            package["manifestdigest"],
            base64.b64decode(package["packagebase64"]),
            "Sha256",
            package["digest"],
        )
        referrers: dict[str, dict[str, object]] = {}
        example = validator.OCI_REFERRER_EXAMPLE
        arguments = (
            package_versions,
            referrers,
            example["subjectmanifestdigest"],
            example["manifestdigest"],
            base64.b64decode(example["attestationbase64"]),
            example["digestalg"],
            example["digest"],
            example["artifacttype"],
        )
        validator.add_oci_referrer_resource(
            *arguments,
            signer=example["signer"],
        )
        with self.assertRaisesRegex(ValueError, "immutable OCI referrer"):
            validator.add_oci_referrer_resource(
                *arguments,
                signer="did:example:other",
            )


class XrefConversionTests(unittest.TestCase):
    def test_local_history_cannot_be_converted_to_xref(self) -> None:
        resource = {
            "versions": {
                "v1": {"document": "original"},
                "v2": {"document": "corrected"},
            }
        }
        before = copy.deepcopy(resource)
        with self.assertRaisesRegex(ValueError, "retained local history"):
            validator.convert_resource_to_xref(resource, "/shells/remote")
        self.assertEqual(before, resource)

    def test_xref_can_be_established_before_local_history(self) -> None:
        resource = {"versions": {}}
        validator.convert_resource_to_xref(resource, "/shells/remote")
        self.assertEqual("/shells/remote", resource["xref"])
        self.assertEqual({}, resource["versions"])


class RepositoryValidationTests(unittest.TestCase):
    def test_documents_and_model_are_aligned(self) -> None:
        self.assertEqual([], validator.validate_repository())

    def test_top_level_domain_metadata_examples_are_rejected(self) -> None:
        registry_spec = validator.REGISTRY_SPEC_PATH.read_text(encoding="utf-8")
        package_spec = validator.PACKAGE_SPEC_PATH.read_text(encoding="utf-8")
        mutations = (
            ("historypolicy", '```json\n{"historypolicy": "retain-all"}\n```', True),
            ("tags", '```json\n{"tags": []}\n```', False),
        )
        for name, block, mutate_registry in mutations:
            with self.subTest(name=name):
                errors = validator.validate_documents(
                    registry_spec + ("\n" + block if mutate_registry else ""),
                    package_spec + ("" if mutate_registry else "\n" + block),
                )
                self.assertTrue(
                    any("outside meta" in error for error in errors),
                    errors,
                )

    def test_package_referrer_versions_and_metadata_are_rejected(self) -> None:
        registry_spec = validator.REGISTRY_SPEC_PATH.read_text(encoding="utf-8")
        package_spec = validator.PACKAGE_SPEC_PATH.read_text(encoding="utf-8")
        for obsolete in (
            "`meta.referrers`",
            "own immutable `package` Version",
        ):
            with self.subTest(obsolete=obsolete):
                errors = validator.validate_documents(
                    registry_spec,
                    package_spec + "\n" + obsolete,
                )
                self.assertTrue(
                    any("obsolete OCI mapping" in error for error in errors),
                    errors,
                )


if __name__ == "__main__":
    unittest.main()
