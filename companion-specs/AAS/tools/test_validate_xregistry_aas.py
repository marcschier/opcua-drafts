#!/usr/bin/env python3
"""Regression tests for the xRegistry AAS semantic validator."""

from __future__ import annotations

import base64
import copy
import hashlib
import ipaddress
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
        del referrers["attributes"]["layermediatype"]
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
            any("referrers.layermediatype: must be required" in error for error in errors),
            errors,
        )
        self.assertTrue(
            any("referrer-only Opaque/1.0" in error for error in errors),
            errors,
        )

    def test_referrer_subject_metadata_must_remain_only_an_index_hint(self) -> None:
        mutated = copy.deepcopy(self.model)
        subject = (
            mutated["groups"]["aasxregistries"]["resources"]["referrers"]
            ["attributes"]["subjectmanifestdigest"]
        )
        subject["description"] = "The authoritative package association."
        errors = validator.validate_model(mutated)
        self.assertTrue(
            any("non-authoritative index hint" in error for error in errors),
            errors,
        )

    def test_routing_metadata_requires_resolver_egress_policy(self) -> None:
        mutations = (
            (
                "submodel resource",
                ("groups", "shells", "resources", "submodels"),
            ),
            (
                "event endpoint",
                ("groups", "shells", "attributes", "eventendpoint"),
            ),
            (
                "package registry",
                ("groups", "aasxregistries", "attributes", "registryurl"),
            ),
        )
        for name, path in mutations:
            with self.subTest(name=name):
                mutated = copy.deepcopy(self.model)
                definition = mutated
                for component in path:
                    definition = definition[component]
                definition["description"] = "A routing URL."
                errors = validator.validate_model(mutated)
                self.assertTrue(
                    any("egress policy" in error for error in errors),
                    errors,
                )

    def test_registry_url_requires_ipv6_transition_address_controls(self) -> None:
        for phrase in (
            "configured RFC 6052 NAT64-prefix",
            "both ISATAP-marker",
            "unconditional metadata-address denial",
            "special-use rejection before global acceptance",
        ):
            with self.subTest(phrase=phrase):
                mutated = copy.deepcopy(self.model)
                registry_url = (
                    mutated["groups"]["aasxregistries"]["attributes"]["registryurl"]
                )
                registry_url["description"] = registry_url["description"].replace(
                    phrase,
                    "generic address filtering",
                    1,
                )
                errors = validator.validate_model(mutated)
                self.assertTrue(
                    any("normalize configured NAT64" in error for error in errors),
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
            base64.b64decode(validator.OCI_REFERRER_MANIFEST_BASE64),
            base64.b64decode(example["attestationbase64"]),
            example["digestalg"],
            example["digest"],
            example["artifacttype"],
            example["layermediatype"],
            True,
            validator.extract_cosign_statement_subject(
                base64.b64decode(example["attestationbase64"])
            ),
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
            base64.b64decode(validator.OCI_REFERRER_MANIFEST_BASE64),
            base64.b64decode(example["attestationbase64"]),
            example["digestalg"],
            example["digest"],
            example["artifacttype"],
            example["layermediatype"],
            True,
            validator.extract_cosign_statement_subject(
                base64.b64decode(example["attestationbase64"])
            ),
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

    def test_verified_referrer_manifest_and_statement_bind_selected_package(self) -> None:
        example = validator.OCI_REFERRER_EXAMPLE
        manifest_bytes = base64.b64decode(validator.OCI_REFERRER_MANIFEST_BASE64)
        attestation_blob = base64.b64decode(example["attestationbase64"])
        self.assertEqual(
            example["manifestdigest"].split(":", 1)[1],
            hashlib.sha256(manifest_bytes).hexdigest(),
        )
        self.assertEqual(
            example["digest"],
            hashlib.sha256(attestation_blob).hexdigest(),
        )
        self.assertEqual(
            example["statementsubject"],
            validator.extract_cosign_statement_subject(attestation_blob),
        )
        manifest = validator.verify_oci_attestation_binding(
            selected_package_manifest_digest=example["subjectmanifestdigest"],
            indexed_subject_manifest_digest=example["subjectmanifestdigest"],
            referrer_manifest_digest=example["manifestdigest"],
            referrer_manifest_bytes=manifest_bytes,
            surfaced_artifact_type=example["artifacttype"],
            surfaced_layer_media_type=example["layermediatype"],
            surfaced_digest_algorithm=example["digestalg"],
            surfaced_blob_digest=example["digest"],
            attestation_blob=attestation_blob,
            signature_valid=True,
            statement_subject_manifest_digest=
                validator.extract_cosign_statement_subject(attestation_blob),
        )
        self.assertEqual(
            example["subjectmanifestdigest"],
            manifest["subject"]["digest"],
        )

    def test_valid_benign_attestation_cannot_be_rebound_to_malicious_package(self) -> None:
        example = validator.OCI_REFERRER_EXAMPLE
        malicious_package = validator.OCI_EXAMPLES[1]["manifestdigest"]
        with self.assertRaisesRegex(ValueError, "manifest subject"):
            validator.verify_oci_attestation_binding(
                selected_package_manifest_digest=malicious_package,
                indexed_subject_manifest_digest=malicious_package,
                referrer_manifest_digest=example["manifestdigest"],
                referrer_manifest_bytes=base64.b64decode(
                    validator.OCI_REFERRER_MANIFEST_BASE64
                ),
                surfaced_artifact_type=example["artifacttype"],
                surfaced_layer_media_type=example["layermediatype"],
                surfaced_digest_algorithm=example["digestalg"],
                surfaced_blob_digest=example["digest"],
                attestation_blob=base64.b64decode(example["attestationbase64"]),
                signature_valid=True,
                statement_subject_manifest_digest=
                    validator.extract_cosign_statement_subject(
                        base64.b64decode(example["attestationbase64"])
                    ),
            )

    def test_referrer_surface_and_statement_mutations_are_rejected(self) -> None:
        example = validator.OCI_REFERRER_EXAMPLE
        base_arguments = {
            "selected_package_manifest_digest": example["subjectmanifestdigest"],
            "indexed_subject_manifest_digest": example["subjectmanifestdigest"],
            "referrer_manifest_digest": example["manifestdigest"],
            "referrer_manifest_bytes": base64.b64decode(
                validator.OCI_REFERRER_MANIFEST_BASE64
            ),
            "surfaced_artifact_type": example["artifacttype"],
            "surfaced_layer_media_type": example["layermediatype"],
            "surfaced_digest_algorithm": example["digestalg"],
            "surfaced_blob_digest": example["digest"],
            "attestation_blob": base64.b64decode(example["attestationbase64"]),
            "signature_valid": True,
            "statement_subject_manifest_digest":
                validator.extract_cosign_statement_subject(
                    base64.b64decode(example["attestationbase64"])
                ),
        }
        mutations = (
            (
                "index hint",
                {"indexed_subject_manifest_digest": validator.OCI_EXAMPLES[1]["manifestdigest"]},
            ),
            ("artifacttype", {"surfaced_artifact_type": "application/example"}),
            ("layermediatype", {"surfaced_layer_media_type": "application/example"}),
            ("blob digest", {"surfaced_blob_digest": "0" * 64}),
            ("signature", {"signature_valid": False}),
            (
                "statement subject",
                {
                    "statement_subject_manifest_digest":
                        validator.OCI_EXAMPLES[1]["manifestdigest"]
                },
            ),
        )
        for expected_error, mutation in mutations:
            with self.subTest(mutation=expected_error):
                arguments = dict(base_arguments)
                arguments.update(mutation)
                with self.assertRaisesRegex(ValueError, expected_error):
                    validator.verify_oci_attestation_binding(**arguments)


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


class FederationSecurityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.public_hop = {
            "url": "https://registry.example/resource",
            "dns_addresses": ["93.184.216.34"],
            "connected_address": "93.184.216.34",
        }
        self.policy = {
            "allowed_schemes": {"https"},
            "allowed_hosts": {"registry.example"},
            "allowed_ports": {443},
            "response_size": 128,
            "max_response_size": 1024,
            "elapsed_seconds": 0.1,
            "max_elapsed_seconds": 2.0,
        }

    @staticmethod
    def _rfc6052_address(prefix: str, embedded_ipv4: str) -> str:
        network = ipaddress.ip_network(prefix, strict=True)
        address = bytearray(network.network_address.packed)
        ipv4 = ipaddress.IPv4Address(embedded_ipv4).packed
        if network.prefixlen == 96:
            address[12:16] = ipv4
        else:
            prefix_octets = network.prefixlen // 8
            before_u_octets = 8 - prefix_octets
            address[prefix_octets:8] = ipv4[:before_u_octets]
            address[8] = 0
            address[9:9 + 4 - before_u_octets] = ipv4[before_u_octets:]
        return str(ipaddress.IPv6Address(bytes(address)))

    @staticmethod
    def _isatap_address(marker: str, embedded_ipv4: str) -> str:
        address = bytearray(
            ipaddress.IPv6Address("2606:4700:1234:5678::").packed
        )
        address[8:12] = bytes.fromhex(marker)
        address[12:16] = ipaddress.IPv4Address(embedded_ipv4).packed
        return str(ipaddress.IPv6Address(bytes(address)))

    def _assert_release_blocked(
        self,
        address: str,
        expected_error: str | None = None,
        **policy_updates: object,
    ) -> None:
        hop = dict(self.public_hop)
        hop["dns_addresses"] = [address]
        hop["connected_address"] = address
        policy = dict(self.policy)
        policy.update(policy_updates)
        content = b"internal-service-secret"
        with self.assertRaises(ValueError) as failure:
            validator.release_federated_content(content, [hop], **policy)
        self.assertNotIn(content.decode(), str(failure.exception))
        if expected_error is not None:
            self.assertRegex(str(failure.exception), expected_error)

    def test_allowlisted_public_target_is_accepted(self) -> None:
        validator.validate_federated_resolution(
            [self.public_hop],
            **self.policy,
        )

    def test_private_metadata_and_special_addresses_are_rejected(self) -> None:
        for address in (
            "127.0.0.1",
            "10.0.0.10",
            "169.254.169.254",
            "fe80::1",
        ):
            with self.subTest(address=address):
                hop = dict(self.public_hop)
                hop["dns_addresses"] = [address]
                hop["connected_address"] = address
                with self.assertRaises(ValueError):
                    validator.validate_federated_resolution(
                        [hop],
                        **self.policy,
                    )

    def test_ipv6_embedded_ipv4_and_site_local_bypasses_are_rejected(self) -> None:
        addresses = (
            "64:ff9b::a9fe:a9fe",
            "::ffff:169.254.169.254",
            "::ffff:10.0.0.10",
            "::a9fe:a9fe",
            "::a00:1",
            "fec0::1",
        )
        for address in addresses:
            with self.subTest(address=address):
                hop = dict(self.public_hop)
                hop["dns_addresses"] = [address]
                hop["connected_address"] = address
                with self.assertRaises(ValueError):
                    validator.validate_federated_resolution(
                        [hop],
                        **self.policy,
                    )

    def test_valid_global_ipv6_target_is_accepted(self) -> None:
        address = "2606:2800:220:1:248:1893:25c8:1946"
        hop = dict(self.public_hop)
        hop["dns_addresses"] = [address]
        hop["connected_address"] = address
        validator.validate_federated_resolution([hop], **self.policy)

    def test_trusted_network_override_requires_explicit_embedded_network(self) -> None:
        address = "64:ff9b::a00:1"
        hop = dict(self.public_hop)
        hop["dns_addresses"] = [address]
        hop["connected_address"] = address

        outer_only_policy = dict(self.policy)
        outer_only_policy["trusted_networks"] = ("64:ff9b::/96",)
        with self.assertRaisesRegex(ValueError, "embeds an untrusted"):
            validator.validate_federated_resolution(
                [hop],
                **outer_only_policy,
            )

        fully_trusted_policy = dict(self.policy)
        fully_trusted_policy["trusted_networks"] = (
            "64:ff9b::/96",
            "10.0.0.0/8",
        )
        validator.validate_federated_resolution(
            [hop],
            **fully_trusted_policy,
        )

    def test_metadata_address_cannot_be_enabled_by_trusted_networks(self) -> None:
        address = "64:ff9b::a9fe:a9fe"
        hop = dict(self.public_hop)
        hop["dns_addresses"] = [address]
        hop["connected_address"] = address
        policy = dict(self.policy)
        policy["trusted_networks"] = (
            "64:ff9b::/96",
            "169.254.0.0/16",
        )
        with self.assertRaisesRegex(ValueError, "metadata service"):
            validator.validate_federated_resolution([hop], **policy)

    def test_rfc6052_configured_prefix_lengths_are_decoded(self) -> None:
        for prefix_length in sorted(validator.RFC6052_PREFIX_LENGTHS):
            prefix = f"2606:4700::/{prefix_length}"
            with self.subTest(prefix=prefix, embedded="public"):
                address = self._rfc6052_address(prefix, "8.8.8.8")
                hop = dict(self.public_hop)
                hop["dns_addresses"] = [address]
                hop["connected_address"] = address
                policy = dict(self.policy)
                policy["nat64_prefixes"] = (prefix,)
                validator.validate_federated_resolution([hop], **policy)
            with self.subTest(prefix=prefix, embedded="private"):
                self._assert_release_blocked(
                    self._rfc6052_address(prefix, "10.1.2.3"),
                    nat64_prefixes=(prefix,),
                )

    def test_invalid_rfc6052_prefix_configuration_is_rejected(self) -> None:
        for prefix in (
            "2606:4700::/33",
            "2606:4700::/65",
            "2606:4700::/95",
            "2606:4700::1/96",
            "192.0.2.0/24",
        ):
            with self.subTest(prefix=prefix):
                policy = dict(self.policy)
                policy["nat64_prefixes"] = (prefix,)
                with self.assertRaisesRegex(ValueError, "NAT64 prefix"):
                    validator.validate_federated_resolution(
                        [self.public_hop],
                        **policy,
                    )

    def test_nonzero_rfc6052_u_octet_is_rejected(self) -> None:
        prefix = "2606:4700:1234::/48"
        address_bytes = bytearray(
            ipaddress.IPv6Address(
                self._rfc6052_address(prefix, "8.8.8.8")
            ).packed
        )
        address_bytes[8] = 1
        address = str(ipaddress.IPv6Address(bytes(address_bytes)))
        hop = dict(self.public_hop)
        hop["dns_addresses"] = [address]
        hop["connected_address"] = address
        policy = dict(self.policy)
        policy["nat64_prefixes"] = (prefix,)
        with self.assertRaisesRegex(ValueError, "non-zero u octet"):
            validator.validate_federated_resolution([hop], **policy)

    def test_release_blocks_isatap_and_nat64_wrapped_special_addresses(self) -> None:
        custom_prefix = "2606:4700:1234::/48"
        cases = (
            (
                "isatap-zero-metadata",
                self._isatap_address("00005efe", "169.254.169.254"),
                {},
            ),
            (
                "isatap-universal-metadata",
                self._isatap_address("02005efe", "169.254.169.254"),
                {},
            ),
            (
                "isatap-private",
                self._isatap_address("00005efe", "10.1.2.3"),
                {},
            ),
            (
                "isatap-shared",
                self._isatap_address("02005efe", "100.64.1.2"),
                {},
            ),
            (
                "local-nat64-metadata",
                self._rfc6052_address(
                    str(validator.NAT64_LOCAL_USE_NETWORK),
                    "169.254.169.254",
                ),
                {},
            ),
            (
                "custom-nat64-metadata",
                self._rfc6052_address(custom_prefix, "169.254.169.254"),
                {"nat64_prefixes": (custom_prefix,)},
            ),
            (
                "custom-nat64-private",
                self._rfc6052_address(custom_prefix, "10.1.2.3"),
                {"nat64_prefixes": (custom_prefix,)},
            ),
            (
                "custom-nat64-shared",
                self._rfc6052_address(custom_prefix, "100.64.1.2"),
                {"nat64_prefixes": (custom_prefix,)},
            ),
        )
        for name, address, policy_updates in cases:
            with self.subTest(name=name, address=address):
                self._assert_release_blocked(address, **policy_updates)

    def test_alibaba_metadata_is_unconditional_in_wrapped_forms(self) -> None:
        alibaba_metadata = "100.100.100.200"
        custom_prefix = "2606:4700:1234::/48"
        cases = (
            ("direct", alibaba_metadata, {}),
            ("mapped", f"::ffff:{alibaba_metadata}", {}),
            (
                "well-known-nat64",
                self._rfc6052_address(
                    str(validator.NAT64_WELL_KNOWN_NETWORK),
                    alibaba_metadata,
                ),
                {},
            ),
            (
                "custom-nat64",
                self._rfc6052_address(custom_prefix, alibaba_metadata),
                {"nat64_prefixes": (custom_prefix,)},
            ),
            (
                "isatap-zero",
                self._isatap_address("00005efe", alibaba_metadata),
                {},
            ),
            (
                "isatap-universal",
                self._isatap_address("02005efe", alibaba_metadata),
                {},
            ),
        )
        for name, address, policy_updates in cases:
            with self.subTest(name=name, address=address):
                self._assert_release_blocked(
                    address,
                    expected_error="metadata service",
                    trusted_networks=("100.64.0.0/10",),
                    **policy_updates,
                )

    def test_dns_rebinding_and_redirect_targets_are_revalidated(self) -> None:
        rebound = dict(self.public_hop)
        rebound["connected_address"] = "1.1.1.1"
        with self.assertRaisesRegex(ValueError, "DNS rebinding"):
            validator.validate_federated_resolution(
                [rebound],
                **self.policy,
            )

        redirect = {
            "url": "https://internal.example/resource",
            "dns_addresses": ["93.184.216.34"],
            "connected_address": "93.184.216.34",
        }
        with self.assertRaisesRegex(ValueError, "redirects are disabled"):
            validator.validate_federated_resolution(
                [self.public_hop, redirect],
                **self.policy,
            )
        redirect_policy = dict(self.policy)
        redirect_policy.update({"allow_redirects": True, "max_redirects": 1})
        with self.assertRaisesRegex(ValueError, "host is not allowlisted"):
            validator.validate_federated_resolution(
                [self.public_hop, redirect],
                **redirect_policy,
            )

    def test_ambient_credentials_and_resource_bounds_are_rejected(self) -> None:
        credentials_policy = dict(self.policy)
        credentials_policy["forwarded_headers"] = {
            "Authorization": "Bearer inbound-token"
        }
        with self.assertRaisesRegex(ValueError, "ambient credentials"):
            validator.validate_federated_resolution(
                [self.public_hop],
                **credentials_policy,
            )

        for name, value, error in (
            ("response_size", 2048, "size limit"),
            ("elapsed_seconds", 3.0, "time limit"),
        ):
            with self.subTest(bound=name):
                bounded_policy = dict(self.policy)
                bounded_policy[name] = value
                with self.assertRaisesRegex(ValueError, error):
                    validator.validate_federated_resolution(
                        [self.public_hop],
                        **bounded_policy,
                    )

    def test_opcua_certificate_and_application_uri_are_required(self) -> None:
        hop = {
            "url": "opc.tcp://opcua.example:4840",
            "dns_addresses": ["10.0.0.10"],
            "connected_address": "10.0.0.10",
            "certificate_trusted": True,
            "certificate_application_uri": "urn:example:server",
            "server_application_uri": "urn:example:server",
            "configured_peer_application_uri": "urn:example:server",
        }
        policy = {
            "allowed_schemes": {"opc.tcp"},
            "allowed_hosts": {"opcua.example"},
            "allowed_ports": {4840},
            "trusted_networks": ("10.0.0.0/24",),
            "response_size": 128,
            "max_response_size": 1024,
            "elapsed_seconds": 0.1,
            "max_elapsed_seconds": 2.0,
        }
        validator.validate_federated_resolution([hop], **policy)

        for mutation, error in (
            ({"certificate_trusted": False}, "certificate is not trusted"),
            (
                {"certificate_application_uri": "urn:example:attacker"},
                "ApplicationUri",
            ),
        ):
            with self.subTest(mutation=mutation):
                invalid_hop = dict(hop)
                invalid_hop.update(mutation)
                with self.assertRaisesRegex(ValueError, error):
                    validator.validate_federated_resolution(
                        [invalid_hop],
                        **policy,
                    )

    def test_failed_resolution_never_releases_internal_content(self) -> None:
        secret = b"internal-service-secret"
        hop = dict(self.public_hop)
        hop["dns_addresses"] = ["169.254.169.254"]
        hop["connected_address"] = "169.254.169.254"
        with self.assertRaises(ValueError) as failure:
            validator.release_federated_content(
                secret,
                [hop],
                **self.policy,
            )
        self.assertNotIn(secret.decode(), str(failure.exception))


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

    def test_security_requirements_cannot_be_removed_from_prose(self) -> None:
        registry_spec = validator.REGISTRY_SPEC_PATH.read_text(encoding="utf-8")
        package_spec = validator.PACKAGE_SPEC_PATH.read_text(encoding="utf-8")
        mutations = (
            (
                "resolver allowlist",
                registry_spec.replace(
                    "allowlist of schemes, hosts and ports",
                    "list of destinations",
                    1,
                ),
                package_spec,
            ),
            (
                "IPv6 embedded IPv4 inspection",
                registry_spec.replace(
                    "6to4, Teredo, NAT64 and ISATAP forms",
                    "transition-network",
                    1,
                ),
                package_spec,
            ),
            (
                "ISATAP variants",
                registry_spec.replace(
                    "`0000:5efe` and `0200:5efe`",
                    "an ISATAP marker",
                    1,
                ),
                package_spec,
            ),
            (
                "configured RFC6052 prefix",
                registry_spec.replace(
                    "deployment-specific RFC 6052 prefix",
                    "deployment-specific translation prefix",
                    1,
                ),
                package_spec,
            ),
            (
                "Alibaba metadata rejection",
                registry_spec.replace(
                    "Alibaba Cloud `100.100.100.200`",
                    "a cloud endpoint",
                    1,
                ),
                package_spec,
            ),
            (
                "CGNAT trust cannot override metadata",
                registry_spec.replace(
                    "MUST NOT override this metadata denial",
                    "normally does not override this metadata denial",
                    1,
                ),
                package_spec,
            ),
            (
                "attestation subject authority",
                registry_spec,
                package_spec.replace(
                    "It is an index hint,\n  never an authority",
                    "It identifies the package",
                    1,
                ),
            ),
        )
        for name, mutated_registry, mutated_package in mutations:
            with self.subTest(name=name):
                errors = validator.validate_documents(
                    mutated_registry,
                    mutated_package,
                )
                self.assertTrue(
                    any("missing normative phrase" in error for error in errors),
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
