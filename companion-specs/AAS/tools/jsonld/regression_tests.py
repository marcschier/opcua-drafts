#!/usr/bin/env python3
"""Focused JSON-LD/WoT regressions and negative controls."""
from __future__ import annotations

import base64
import hashlib
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from authored import FOREIGN, add_foreign, author, load_context, lower_graph, read_back  # noqa: E402
from context_security import (  # noqa: E402
    ContextPolicy,
    ContextSecurityError,
    NetworkResponse,
)
from lift import AAS, Lifter, Ontology, Schema, serialize  # noqa: E402
from lower import Lowerer, parse_nt  # noqa: E402
import validate_examples  # noqa: E402
import wot_bridge  # noqa: E402

ONTOLOGY = Ontology()
SCHEMA = Schema()


def graph_of(source):
    sink = Lifter(ONTOLOGY, "linked", schema=SCHEMA).lift(source)
    core = serialize(sink, with_graphs=False)
    order = "\n".join(f"{s} {p} {o} ." for s, p, o, _ in sink.quads)
    return core, order


def subject_collision():
    irdi = "0173-1#02-AAO677#002"
    old_hash_style = (
        "https://w3id.org/aas-jsonld/id/"
        "4a508ebd70e19917cd187073e2ff250e75d464260868f755e40ccb04d95948ca")
    source = {
        "submodels": [
            {"modelType": "Submodel", "id": irdi, "idShort": "IRDI"},
            {"modelType": "Submodel", "id": old_hash_style, "idShort": "HashStyleIRI"},
        ]
    }
    core, order = graph_of(source)
    def encoded(value):
        payload = base64.urlsafe_b64encode(value.encode("utf-8")).decode("ascii").rstrip("=")
        return "https://w3id.org/aas-jsonld/subject/v1/" + payload
    subjects = {
        subject for subject, predicate, _ in parse_nt(core)
        if predicate == f"<{AAS}Identifiable/id>"
    }
    if subjects != {f"<{encoded(irdi)}>", f"<{encoded(old_hash_style)}>"}:
        raise AssertionError(f"root subjects merged or were not uniformly encoded: {subjects}")
    authored = author(core, order, load_context())
    recovered_core, recovered_order = read_back(authored)
    recovered = lower_graph(recovered_core, recovered_order, seed=11)
    ids = sorted(node["id"] for node in recovered["submodels"])
    if ids != sorted((irdi, old_hash_style)):
        raise AssertionError(f"subject collision lost a submodel: {ids}")
    print("  passed: IRDI and old hash-style absolute IRI remain two submodels")


def foreign_vocabulary():
    source = {
        "submodels": [{
            "modelType": "Submodel",
            "id": "https://example.org/submodels/foreign",
            "idShort": "AASValue",
        }]
    }
    core, order = graph_of(source)
    augmented = add_foreign(core)
    doc_text = author(augmented, order, load_context())
    recovered_core, recovered_order = read_back(doc_text)
    lowerer = Lowerer(ONTOLOGY, SCHEMA)
    lowerer.load(parse_nt(recovered_core), parse_nt(recovered_order))
    recovered = lowerer.lower()
    if recovered["submodels"][0]["idShort"] != "AASValue":
        raise AssertionError("foreign idShort overwrote aas:Referable/idShort")
    foreign = {
        (predicate, obj)
        for _, predicate, obj in parse_nt(recovered_core)
        if predicate.startswith(f"<{FOREIGN}")
    }
    expected = {
        (f"<{FOREIGN}reviewedBy>", "<https://example.org/people/1>"),
        (f"<{FOREIGN}idShort>", '"foreign local-name collision"'
                                  '^^<http://www.w3.org/2001/XMLSchema#string>'),
    }
    if foreign != expected:
        raise AssertionError(f"foreign terms were not preserved exactly: {foreign}")
    preserved = {
        (predicate, obj)
        for _, predicate, obj in lowerer.foreign_triples
        if predicate.startswith(f"<{FOREIGN}")
    }
    if preserved != expected:
        raise AssertionError(f"lowerer did not preserve foreign residue: {preserved}")
    print("  passed: reviewedBy and colliding foreign idShort survive; AAS is unchanged")


def control_free_nodeids():
    component_cases = {
        "line\nfeed": "line%0Afeed",
        "nul\x00byte": "nul%00byte",
        "nel\x85byte": "nel%C2%85byte",
        "literal%percent": "literal%25percent",
    }
    for raw, encoded in component_cases.items():
        if validate_examples.encode_nodeid_component(raw) != encoded:
            raise AssertionError(
                f"control-free component encoding differs for {raw!r}")
        if validate_examples.decode_nodeid_component(encoded) != raw:
            raise AssertionError(
                f"control-free component decoding differs for {encoded!r}")

    namespace = "https://example.org/aas/instances/"
    owner = "owner%\x00\x85"
    path = "op.\x1f[%]"
    expected = (
        "nsu=https://example.org/aas/instances/;"
        "s=i4aas3:E:17:11:owner%25%00%C2%85op.%1F[%25]"
    )
    actual = validate_examples.expected_node_id(owner, path, namespace)
    bridge = wot_bridge.expanded_node_id(owner, path, namespace)
    if actual != expected or bridge != expected:
        raise AssertionError(
            f"control-free NodeId encoding differs: validator={actual!r}, bridge={bridge!r}")
    if validate_examples.parse_expanded_node_id(actual, "regression") != (
            namespace, "E", owner, path):
        raise AssertionError("control-free NodeId did not decode to its exact components")
    try:
        validate_examples.decode_i4aas_identifier("i4aas3:S:\u0661:x")
    except AssertionError:
        pass
    else:
        raise AssertionError("Arabic-Indic NodeId length prefix was accepted")
    print("  passed: independent control-free NodeId encoding is canonical and reversible")


def operation_value_requires_idshort():
    source_path = HERE.parent / "fixtures" / "every-element-type.json"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    operation = next(
        element
        for element in source["submodels"][0]["submodelElements"]
        if element.get("modelType") == "Operation"
    )
    operation["inputVariables"][0]["value"].pop("idShort")
    try:
        wot_bridge.generate(source, "attype")
    except ValueError as exc:
        if "idShort" not in str(exc):
            raise AssertionError(
                f"missing Operation value idShort failed for the wrong reason: {exc}") from exc
    else:
        raise AssertionError("Operation variable value without idShort was accepted")
    print("  passed: Operation variable value without idShort is rejected")


def nested_reference_order_survives_shuffle():
    source_path = HERE.parent / "fixtures" / "ordering-and-nesting.json"
    td_path = (
        HERE.parent.parent / "examples" / "wot"
        / "ordering-and-nesting.td.jsonld"
    )
    source = json.loads(source_path.read_text(encoding="utf-8"))
    documents = validate_examples.load_projection_bundle(td_path)
    datasets = [
        (path, validate_examples.process_jsonld(doc, path))
        for path, doc in documents
    ]
    dataset = validate_examples.merge_document_datasets(datasets)
    core_text, order_text = validate_examples.dataset_text(dataset)
    key_predicate = f"<{AAS}Reference/keys>"
    key_triples = [
        triple for triple in parse_nt(core_text)
        if triple[1] == key_predicate
    ]
    if len(key_triples) != 2 or key_triples[0][0] != key_triples[1][0]:
        raise AssertionError(
            f"expected one two-key Reference, got {key_triples}")
    other_triples = [
        triple for triple in parse_nt(core_text)
        if triple[1] != key_predicate
    ]
    random.Random(20260810).shuffle(other_triples)
    shuffled_core = other_triples + list(reversed(key_triples))
    shuffled_order = parse_nt(order_text)
    random.Random(1082026).shuffle(shuffled_order)

    with_order = Lowerer(ONTOLOGY, SCHEMA)
    with_order.load(shuffled_core, shuffled_order)
    recovered = with_order.lower()
    operation = next(
        element
        for element in recovered["submodels"][0]["submodelElements"]
        if element.get("idShort") == "OrderMatters"
    )
    actual_keys = operation["semanticId"]["keys"]
    expected_element = next(
        element
        for element in source["submodels"][0]["submodelElements"]
        if element.get("idShort") == "OrderMatters"
    )
    expected_keys = expected_element["semanticId"]["keys"]
    if actual_keys != expected_keys:
        raise AssertionError(
            f"Reference.keys order was not reconstructed: {actual_keys}")

    without_order = Lowerer(ONTOLOGY, SCHEMA)
    without_order.load(shuffled_core)
    unordered = without_order.lower()
    unordered_element = next(
        element
        for element in unordered["submodels"][0]["submodelElements"]
        if element.get("idShort") == "OrderMatters"
    )
    if unordered_element["semanticId"]["keys"] == expected_keys:
        raise AssertionError(
            "Reference.keys shuffle did not make the ordering graph load-bearing")
    print("  passed: shuffled Reference.keys are restored from nested ordering occurrences")


def derived_identifiable_browse_name_is_safe():
    source_path = HERE.parent / "fixtures" / "identifiable-without-idshort.json"
    td_path = (
        HERE.parent.parent / "examples" / "wot"
        / "identifiable-without-idshort.td.jsonld"
    )
    source = json.loads(source_path.read_text(encoding="utf-8"))
    td = json.loads(td_path.read_text(encoding="utf-8"))
    expected = validate_examples.expected_identifiable_browse_names(source)[
        ("submodels", 0)
    ]
    if td.get("title") != expected:
        raise AssertionError(
            f"derived TD title expected {expected!r}, got {td.get('title')!r}")
    browse = td.get("uav:browseName")
    if browse != wot_bridge.browse_name(expected):
        raise AssertionError(
            f"derived BrowseName expected {expected!r}, got {browse!r}")
    if any(ord(character) <= 0x1F or 0x7F <= ord(character) <= 0x9F
           for character in browse):
        raise AssertionError("derived BrowseName contains a control character")
    validate_examples.validate_bytes(
        td_path, td_path.read_text(encoding="utf-8"),
        td=True, source=source, projection=True)

    control_ids = (
        "urn:example:submodel\nwith-lf",
        "urn:example:submodel\x00with-nul",
        "urn:example:submodel\x85with-c1",
    )
    control_source = {
        "submodels": [
            {
                "modelType": "Submodel",
                "id": identifier,
                "submodelElements": [],
            }
            for identifier in control_ids
        ],
    }
    expected_controls = validate_examples.expected_identifiable_browse_names(
        control_source)
    control_tds = wot_bridge.generate(control_source, "attype")
    escaped_controls = ("%0A", "%00", "%C2%85")
    for index, (identifier, td, escaped) in enumerate(
            zip(control_ids, control_tds, escaped_controls)):
        expected_name = expected_controls[("submodels", index)]
        direct_name = (
            "Submodel_"
            + hashlib.sha256(identifier.encode("utf-8")).hexdigest())
        if expected_name != direct_name:
            raise AssertionError(
                f"independent BrowseName digest altered {identifier!r}")
        digest = expected_name.removeprefix("Submodel_")
        if (
                td.get("title") != expected_name
                or td.get("uav:browseName") != wot_bridge.browse_name(expected_name)
                or len(digest) != 64
                or any(character not in "0123456789abcdef" for character in digest)):
            raise AssertionError(
                f"control identifier {identifier!r} did not produce a safe "
                f"derived BrowseName: {td.get('title')!r}")
        if identifier in expected_name:
            raise AssertionError("raw control identifier was used as a BrowseName")
        if escaped not in td["uav:id"]:
            raise AssertionError(
                f"control identifier {identifier!r} was not escaped in its NodeId")
        if escaped.replace("%", "%25") not in td["forms"][0]["href"]:
            raise AssertionError(
                f"control identifier {identifier!r} was not URI-layer escaped")
        namespace, kind, owner, path = validate_examples.parse_expanded_node_id(
            td["uav:id"], "control identifier regression")
        if (
                namespace != wot_bridge.INSTANCE_NS
                or kind != "S"
                or owner != identifier
                or path is not None):
            raise AssertionError(
                f"control identifier NodeId did not decode exactly: {td['uav:id']!r}")
        validate_examples.validate_td(td)
        validate_examples.validate_node_class_domains(td)
        validate_examples.validate_object_form(td)
    print("  passed: LF, NUL and C1 identifiers have safe, schema-valid BrowseNames")


def derived_identifiable_browse_name_collisions():
    digest = "ab" * 32
    base = f"Submodel_{digest}"
    identifiers = (
        "urn:example:submodel:e\u0301",
        "urn:example:submodel:\u00e9",
    )
    byte_order = sorted(identifiers, key=lambda value: value.encode("utf-8"))

    raw_source = {
        "submodels": [{
            "modelType": "Submodel",
            "id": identifiers[0],
            "submodelElements": [],
        }],
    }
    raw_td = wot_bridge.generate(raw_source, "attype")[0]
    raw_name = (
        "Submodel_"
        + hashlib.sha256(identifiers[0].encode("utf-8")).hexdigest())
    normalized_name = (
        "Submodel_"
        + hashlib.sha256(identifiers[1].encode("utf-8")).hexdigest())
    if raw_name == normalized_name or raw_td["title"] != raw_name:
        raise AssertionError(
            "derived BrowseName did not hash exact non-normalized UTF-8 bytes")

    def constant_digest(_):
        return digest

    def assignments(source):
        expected = validate_examples.expected_identifiable_browse_names(
            source, digest_function=constant_digest)
        expected_by_id = {
            submodel["id"]: expected[("submodels", index)]
            for index, submodel in enumerate(source["submodels"])
        }
        tds = wot_bridge.generate(
            source, "attype", digest_function=constant_digest)
        actual_by_id = {
            submodel["id"]: td["title"]
            for submodel, td in zip(source["submodels"], tds)
        }
        shared = wot_bridge.rt.identifiable_browse_names(
            source, digest_function=constant_digest)
        shared_by_id = {
            submodel["id"]: shared[("submodels", index)]
            for index, submodel in enumerate(source["submodels"])
        }
        for submodel, td in zip(source["submodels"], tds):
            if td["uav:browseName"] != wot_bridge.browse_name(
                    actual_by_id[submodel["id"]]):
                raise AssertionError("forced-collision BrowseName is inconsistent")
            validate_examples.validate_td(td)
            validate_examples.validate_node_class_domains(td)
            validate_examples.validate_object_form(td)
        if actual_by_id != expected_by_id:
            raise AssertionError(
                "emitter and independent forced-collision assignments differ: "
                f"{actual_by_id!r} != {expected_by_id!r}")
        if actual_by_id != shared_by_id:
            raise AssertionError(
                "JSON/WoT and OPC forced-collision assignments differ: "
                f"{actual_by_id!r} != {shared_by_id!r}")
        return actual_by_id

    without_authored = {
        "submodels": [
            {
                "modelType": "Submodel",
                "id": identifier,
                "submodelElements": [],
            }
            for identifier in reversed(identifiers)
        ],
    }
    first = assignments(without_authored)
    without_authored["submodels"].reverse()
    second = assignments(without_authored)
    expected_without_authored = {
        byte_order[0]: base,
        byte_order[1]: f"{base}_0",
    }
    if first != expected_without_authored or second != expected_without_authored:
        raise AssertionError(
            "derived collision was not assigned in exact UTF-8 identifier "
            f"byte order: {first!r}, {second!r}")

    with_authored = {
        "submodels": [
            {
                "modelType": "Submodel",
                "id": identifier,
                "submodelElements": [],
            }
            for identifier in reversed(identifiers)
        ],
        "conceptDescriptions": [{
            "modelType": "ConceptDescription",
            "id": "urn:example:concept:authored-collision",
            "idShort": base,
        }],
    }
    first = assignments(with_authored)
    with_authored["submodels"].reverse()
    second = assignments(with_authored)
    expected_with_authored = {
        byte_order[0]: f"{base}_0",
        byte_order[1]: f"{base}_1",
    }
    if first != expected_with_authored or second != expected_with_authored:
        raise AssertionError(
            "authored collision did not use zero-based ASCII suffixes in "
            f"UTF-8 byte order: {first!r}, {second!r}")
    for invalid in ("", None):
        source = {
            "submodels": [{
                "modelType": "Submodel",
                "id": "urn:example:submodel:invalid-id-short",
                "idShort": invalid,
                "submodelElements": [],
            }],
        }
        for label, implementation in (
                ("JSON/WoT emitter",
                 lambda environment: wot_bridge.generate(
                     environment, "attype")),
                ("independent validator",
                 validate_examples.expected_identifiable_browse_names),
                ("OPC materializer",
                 wot_bridge.rt.identifiable_browse_names)):
            try:
                implementation(source)
            except (AssertionError, ValueError):
                pass
            else:
                raise AssertionError(
                    f"{label} accepted invalid idShort {invalid!r}")
    print("  passed: forced BrowseName collisions use deterministic _0 suffixes")


def adopted_type_binding_forms():
    source = {
        "submodels": [{
            "modelType": "Submodel",
            "id": "urn:example:type-binding",
            "idShort": "TypeBinding",
            "submodelElements": [],
        }],
    }
    expected = wot_bridge.expected(source)
    for form in ("attype", "link", "both"):
        documents = wot_bridge.generate(source, form)
        actual = wot_bridge.project(
            documents, honour_type_binding=True, form=form)
        missing, extra, differing = wot_bridge.compare(expected, actual)
        if missing or extra or differing:
            raise AssertionError(
                f"{form} type binding did not project identically: "
                f"{missing!r}, {extra!r}, {differing!r}")
    documents = wot_bridge.generate(source, "both")
    validate_examples.validate_published_type_binding(documents[0])
    links = [
        link for link in documents[0]["links"]
        if link.get("rel") == "ua:HasTypeDefinition"
    ]
    links[0]["href"] = wot_bridge.TYPE_NODEIDS["AASPropertyType"]
    try:
        wot_bridge.project(documents, honour_type_binding=True, form="both")
    except ValueError:
        pass
    else:
        raise AssertionError("disagreeing type-binding forms were accepted")
    print("  passed: both adopted type-binding forms are independently sufficient")


def context_resolution_security() -> int:
    caught = 0

    def expect(label, action, text=None):
        nonlocal caught
        try:
            action()
        except Exception as exc:
            messages = []
            cause = exc
            while cause is not None:
                messages.append(str(cause))
                cause = cause.__cause__
            message = "\n".join(messages)
            if text is not None and text not in message:
                raise AssertionError(
                    f"{label} failed for the wrong reason: {exc}") from exc
            print(f"  caught: {label} ({type(exc).__name__}: {exc})")
            caught += 1
        else:
            raise AssertionError(f"{label}: unsafe context was accepted")

    expect(
        "default loader rejects an unapproved remote context",
        lambda: read_back(json.dumps({
            "@context": "https://contexts.example/unapproved.jsonld",
            "@id": "urn:example:context-security",
        })),
        "network JSON-LD context loading is disabled",
    )

    transport_calls = []

    def forbidden_transport(url, addresses, timeout, max_bytes):
        transport_calls.append(url)
        raise AssertionError("network transport was invoked")

    address_map = {
        "localhost": ("127.0.0.1",),
        "169.254.169.254": ("169.254.169.254",),
        "shared.example": ("100.100.100.200",),
        "site-local.example": ("fec0::1",),
        "mapped-shared.example": ("::ffff:100.100.100.200",),
        "compatible-shared.example": ("::100.100.100.200",),
        "nat64-shared.example": ("64:ff9b::100.100.100.200",),
        "contexts.example": ("93.184.216.34",),
        "mapped-global.example": ("::ffff:93.184.216.34",),
    }

    def resolver(host, port):
        return address_map[host]

    pins = {
        "https://localhost/context": "0" * 64,
        "https://169.254.169.254/latest/meta-data": "0" * 64,
        "https://shared.example/context": "0" * 64,
        "https://site-local.example/context": "0" * 64,
        "https://mapped-shared.example/context": "0" * 64,
        "https://compatible-shared.example/context": "0" * 64,
        "https://nat64-shared.example/context": "0" * 64,
    }
    guarded = ContextPolicy(
        network_enabled=True,
        allowlisted_origins=frozenset(
            url.rsplit("/", 1)[0] for url in pins),
        network_sha256=pins,
        resolver=resolver,
        transport=forbidden_transport,
    )
    for label, url in (
            ("localhost context is rejected before transport",
             "https://localhost/context"),
            ("metadata context is rejected before transport",
             "https://169.254.169.254/latest/meta-data"),
            ("CGNAT/shared context is rejected before transport",
             "https://shared.example/context"),
            ("deprecated IPv6 site-local context is rejected before transport",
             "https://site-local.example/context"),
            ("IPv4-mapped shared context is rejected before transport",
             "https://mapped-shared.example/context"),
            ("IPv4-compatible shared context is rejected before transport",
             "https://compatible-shared.example/context"),
            ("NAT64-embedded shared context is rejected before transport",
             "https://nat64-shared.example/context")):
        expect(label, lambda url=url: guarded.loader()(url), "prohibited address")
    if transport_calls:
        raise AssertionError(
            f"prohibited targets reached network transport: {transport_calls}")

    unpinned = ContextPolicy(
        network_enabled=True,
        allowlisted_origins=frozenset({"https://contexts.example"}),
        resolver=resolver,
        transport=forbidden_transport,
    )
    expect(
        "allowlisted but unpinned external context is rejected before transport",
        lambda: unpinned.loader()(
            "https://contexts.example/unpinned.jsonld"),
        "not content-hash pinned",
    )
    if transport_calls:
        raise AssertionError(
            f"unpinned context reached network transport: {transport_calls}")

    pinned_url = "https://contexts.example/pinned.jsonld"
    pinned_body = b'{"@context":{"safe":"urn:example:safe"}}'
    pinned_calls = []

    def pinned_transport(url, addresses, timeout, max_bytes):
        pinned_calls.append((url, addresses))
        return NetworkResponse(200, {}, pinned_body)

    pinned = ContextPolicy(
        network_enabled=True,
        allowlisted_origins=frozenset({"https://contexts.example"}),
        network_sha256={
            pinned_url: hashlib.sha256(pinned_body).hexdigest(),
        },
        resolver=resolver,
        transport=pinned_transport,
    )
    loaded = pinned.loader()(pinned_url)
    if (
            loaded["document"] != {"@context": {"safe": "urn:example:safe"}}
            or pinned_calls != [(pinned_url, ("93.184.216.34",))]):
        raise AssertionError(
            f"pinned allowlisted context was not loaded exactly: {loaded!r}")
    print("  passed: allowlisted HTTPS context is loaded only by pinned bytes")

    mapped_url = "https://mapped-global.example/pinned.jsonld"
    mapped_calls = []

    def mapped_transport(url, addresses, timeout, max_bytes):
        mapped_calls.append((url, addresses))
        return NetworkResponse(200, {}, pinned_body)

    mapped = ContextPolicy(
        network_enabled=True,
        allowlisted_origins=frozenset({"https://mapped-global.example"}),
        network_sha256={
            mapped_url: hashlib.sha256(pinned_body).hexdigest(),
        },
        resolver=resolver,
        transport=mapped_transport,
    )
    mapped_loaded = mapped.loader()(mapped_url)
    if (
            mapped_loaded["document"] != loaded["document"]
            or mapped_calls != [
                (mapped_url, ("93.184.216.34",)),
            ]):
        raise AssertionError(
            "IPv4-mapped global address was not normalized and allowed: "
            f"{mapped_calls!r}")
    print("  passed: IPv4-mapped valid global address remains allowed")

    mismatched = ContextPolicy(
        network_enabled=True,
        allowlisted_origins=frozenset({"https://contexts.example"}),
        network_sha256={pinned_url: "0" * 64},
        resolver=resolver,
        transport=pinned_transport,
    )
    expect(
        "network context with a mismatched content hash is rejected",
        lambda: mismatched.loader()(pinned_url),
        "context hash mismatch",
    )

    initial = "https://contexts.example/start.jsonld"
    redirect_calls = []

    def private_redirect(url, addresses, timeout, max_bytes):
        redirect_calls.append(url)
        return NetworkResponse(
            302,
            {"Location": "https://169.254.169.254/latest/meta-data"},
            b"",
        )

    redirected = ContextPolicy(
        network_enabled=True,
        allowlisted_origins=frozenset({
            "https://contexts.example",
            "https://169.254.169.254",
        }),
        network_sha256={initial: "0" * 64},
        resolver=resolver,
        transport=private_redirect,
    )
    expect(
        "redirect target is revalidated and metadata is rejected",
        lambda: redirected.loader()(initial),
        "prohibited address",
    )
    if redirect_calls != [initial]:
        raise AssertionError(
            f"redirect validation made unexpected requests: {redirect_calls}")

    loop_calls = []

    def redirect_loop(url, addresses, timeout, max_bytes):
        loop_calls.append(url)
        return NetworkResponse(302, {"Location": "/loop.jsonld"}, b"")

    limited = ContextPolicy(
        network_enabled=True,
        allowlisted_origins=frozenset({"https://contexts.example"}),
        network_sha256={initial: "0" * 64},
        max_redirects=1,
        resolver=resolver,
        transport=redirect_loop,
    )
    expect(
        "context redirect limit is enforced",
        lambda: limited.loader()(initial),
        "redirect limit exceeded",
    )
    if len(loop_calls) != 2:
        raise AssertionError(
            f"redirect limit expected two bounded requests, got {loop_calls}")

    expect(
        "ambient credentials in a context URL are rejected",
        lambda: ContextPolicy(
            network_enabled=True,
            allowlisted_origins=frozenset({"https://contexts.example"}),
            network_sha256={
                "https://user:password@contexts.example/context": "0" * 64,
            },
            resolver=resolver,
            transport=forbidden_transport,
        ).loader()("https://user:password@contexts.example/context"),
        "must not contain ambient credentials",
    )
    expect(
        "context count bound is enforced",
        lambda: ContextPolicy(max_contexts=2).loader({
            "@context": [{}, {}, {}],
        }),
        "context count exceeds",
    )
    expect(
        "context byte bound is enforced",
        lambda: ContextPolicy(max_context_bytes=32).loader({
            "@context": {"large": "urn:" + ("x" * 64)},
        }),
        "context bytes exceed",
    )

    nested = {"leaf": "urn:example:leaf"}
    for index in range(4):
        nested = {
            f"level{index}": {
                "@id": f"urn:example:level{index}",
                "@context": nested,
            },
        }
    expect(
        "context nesting bound is enforced",
        lambda: ContextPolicy(max_context_depth=2).loader({
            "@context": nested,
        }),
        "context nesting exceeds",
    )
    return caught + 2


def projection_mutations():
    caught = validate_examples.mutation_test()
    if caught != 31:
        raise AssertionError(f"expected 31 caught mutations, got {caught}")
    return caught


def main():
    subject_collision()
    foreign_vocabulary()
    control_free_nodeids()
    operation_value_requires_idshort()
    nested_reference_order_survives_shuffle()
    derived_identifiable_browse_name_is_safe()
    derived_identifiable_browse_name_collisions()
    adopted_type_binding_forms()
    security_controls = context_resolution_security()
    mutations = projection_mutations()
    print(f"regressions and mutations: {8 + security_controls + mutations} passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
