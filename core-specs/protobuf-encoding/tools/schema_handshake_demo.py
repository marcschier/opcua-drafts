from __future__ import annotations

import importlib
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from google.protobuf import descriptor_pb2, descriptor_pool, message_factory

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, os.path.abspath(HERE / ".." / ".." / "_common"))
from opcua_enc import corpus, fingerprint, types as t  # noqa: E402
from opcua_enc.values import canonical_equal, is_single_float_type  # noqa: E402
import build_schemas  # noqa: E402
import protobuf_codec  # noqa: E402


@dataclass(frozen=True)
class Frame:
    kind: str
    schema_id: bytes
    message_name: str = ""
    body: bytes = b""
    fds: bytes = b""


def _safe_name(name: str) -> str:
    s = re.sub(r"[^A-Za-z0-9_]", "_", name)
    if not s or s[0].isdigit():
        s = "_" + s
    return s


def _module_for_struct(st: t.Struct) -> Any:
    return importlib.import_module(f"{_safe_name(st.name).lower()}_pb2")


def _file_proto(file_desc: Any) -> descriptor_pb2.FileDescriptorProto:
    out = descriptor_pb2.FileDescriptorProto()
    out.ParseFromString(file_desc.serialized_pb)
    out.ClearField("source_code_info")
    return out


def _canonical_bytes(file_desc_or_proto: Any) -> bytes:
    if isinstance(file_desc_or_proto, descriptor_pb2.FileDescriptorSet):
        fds = file_desc_or_proto
    elif isinstance(file_desc_or_proto, descriptor_pb2.FileDescriptorProto):
        fds = descriptor_pb2.FileDescriptorSet()
        fds.file.append(file_desc_or_proto)
    else:
        fds = _collect_files(file_desc_or_proto)
    return fds.SerializeToString(deterministic=True)


def _schema_id(file_desc_or_proto: Any) -> bytes:
    return fingerprint.sha256_id(_canonical_bytes(file_desc_or_proto))


def _collect_files(file_desc: Any, override: descriptor_pb2.FileDescriptorProto | None = None) -> descriptor_pb2.FileDescriptorSet:
    seen: set[str] = set()
    ordered: list[descriptor_pb2.FileDescriptorProto] = []

    def visit(fd: Any) -> None:
        if fd.name in seen:
            return
        for dep in sorted(fd.dependencies, key=lambda d: d.name):
            visit(dep)
        seen.add(fd.name)
        if override is not None and override.name == fd.name:
            ordered.append(override)
        else:
            ordered.append(_file_proto(fd))

    visit(file_desc)
    fds = descriptor_pb2.FileDescriptorSet()
    fds.file.extend(ordered)
    return fds


def _descriptor_for_type(ty: t.Type) -> Any:
    if isinstance(ty, t.Struct):
        return getattr(_module_for_struct(ty), _safe_name(ty.name)).DESCRIPTOR
    import opcua_builtins_pb2 as pb
    return pb.Value.DESCRIPTOR


def _message_name(ty: t.Type) -> str:
    if isinstance(ty, t.Struct):
        return f"opcua.protobuf.generated.{_safe_name(ty.name)}"
    return "opcua.protobuf.v1.Value"


class Encoder:
    def __init__(self) -> None:
        self.announced: set[bytes] = set()

    def send(self, ty: t.Type, value: Any, override: descriptor_pb2.FileDescriptorProto | None = None) -> list[Frame]:
        desc = _descriptor_for_type(ty)
        file_desc = desc.file
        fds = _collect_files(file_desc, override)
        schema_id = _schema_id(fds)
        body = protobuf_codec.encode(ty, value)
        frames: list[Frame] = []
        if schema_id not in self.announced:
            frames.append(Frame("schema", schema_id, fds=fds.SerializeToString(deterministic=True)))
            self.announced.add(schema_id)
        frames.append(Frame("data", schema_id, _message_name(ty), body))
        return frames


class Decoder:
    def __init__(self) -> None:
        self.cache: dict[bytes, descriptor_pool.DescriptorPool] = {}
        self.announcements = 0
        self.decoded = 0

    def receive(self, frame: Frame) -> bytes | None:
        if frame.kind == "schema":
            fds = descriptor_pb2.FileDescriptorSet()
            fds.ParseFromString(frame.fds)
            if _schema_id(fds) != frame.schema_id:
                raise ValueError(f"SchemaId mismatch for announcement {frame.schema_id.hex()}")
            pool = descriptor_pool.DescriptorPool()
            for fdp in fds.file:
                try:
                    pool.Add(fdp)
                except TypeError:
                    # Well-known descriptors may already exist in some runtimes.
                    pass
            self.cache[frame.schema_id] = pool
            self.announcements += 1
            return None
        if frame.schema_id not in self.cache:
            raise KeyError(f"unknown SchemaId {frame.schema_id.hex()}")
        desc = self.cache[frame.schema_id].FindMessageTypeByName(frame.message_name)
        cls = message_factory.GetMessageClass(desc)
        msg = cls()
        msg.ParseFromString(frame.body)
        self.decoded += 1
        return msg.SerializeToString(deterministic=True)


def _changed_person_descriptor() -> descriptor_pb2.FileDescriptorProto:
    desc = _descriptor_for_type(corpus.PERSON).file
    fdp = _file_proto(desc)
    person = next(m for m in fdp.message_type if m.name == "Person")
    field = person.field.add()
    field.name = "schema_epoch"
    field.number = 100
    field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    field.type = descriptor_pb2.FieldDescriptorProto.TYPE_UINT32
    return fdp


def run_demo() -> dict[str, int]:
    build_schemas.main()
    protobuf_codec.reload_generated()
    cases = [c for c in corpus.CORPUS if c.name in ("struct_person_one_opt", "struct_person_min", "envelope")]
    enc = Encoder()
    dec = Decoder()

    frames: list[tuple[Frame, Any]] = []
    for case in cases:
        for frame in enc.send(case.type, case.value):
            frames.append((frame, case))
    initial_announcements = sum(1 for f, _ in frames if f.kind == "schema")
    if initial_announcements != 2:  # Person and Envelope
        raise AssertionError(f"expected two initial schema announcements, got {initial_announcements}")

    changed = _changed_person_descriptor()
    person_file = _descriptor_for_type(corpus.PERSON).file
    old_id = _schema_id(_collect_files(person_file))
    new_id = _schema_id(_collect_files(person_file, changed))
    if old_id == new_id:
        raise AssertionError("schema change did not change SchemaId")
    changed_case = next(c for c in cases if c.name == "struct_person_min")
    changed_frames = enc.send(changed_case.type, changed_case.value, changed)
    if sum(1 for f in changed_frames if f.kind == "schema") != 1:
        raise AssertionError("changed schema was not re-announced exactly once")
    frames.extend((f, changed_case) for f in changed_frames)

    for frame, case in frames:
        decoded_bytes = dec.receive(frame)
        if decoded_bytes is None:
            continue
        if decoded_bytes != frame.body:
            raise AssertionError(f"dynamic decode drift for {case.name}")
        static_value = protobuf_codec.decode(case.type, frame.body)
        if not canonical_equal(case.value, static_value, single_float=is_single_float_type(case.type)):
            raise AssertionError(f"static decode mismatch for {case.name}")

    late = Decoder()
    late_case = next(c for c in cases if c.name == "envelope")
    late_frames = enc.send(late_case.type, late_case.value)
    if late_frames[0].kind != "data":
        raise AssertionError("encoder re-announced already announced schema")
    try:
        late.receive(late_frames[0])
    except KeyError:
        pass
    else:
        raise AssertionError("late joiner decoded without a schema")
    recovery = _collect_files(_descriptor_for_type(late_case.type).file)
    sid = _schema_id(recovery)
    late.receive(Frame("schema", sid, fds=recovery.SerializeToString(deterministic=True)))
    recovered = late.receive(late_frames[0])
    if recovered != late_frames[0].body:
        raise AssertionError("late joiner recovery failed")

    return {"announcements": dec.announcements, "decoded": dec.decoded, "schema_ids": len(enc.announced)}


def main() -> int:
    stats = run_demo()
    print(
        "schema_handshake_demo: "
        f"announcements={stats['announcements']} decoded={stats['decoded']} schema_ids={stats['schema_ids']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
