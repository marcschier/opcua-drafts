"""Round-trip the corpus NodeId / ExpandedNodeId values through the Avro `string`
form (*OPC UA — Apache Avro DataEncoding* §5.2.1).

Each value is converted to its canonical OPC UA textual form, written and read
back through a real Avro `string` schema with fastavro, then parsed back to a
value and compared for canonical equality. Run standalone; the process exits
non-zero if any assertion fails.
"""
from __future__ import annotations

import os
import sys
from io import BytesIO

from fastavro import parse_schema, schemaless_reader, schemaless_writer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_common")))

from nodeid_text import (  # noqa: E402
    expandednodeid_from_text,
    expandednodeid_to_text,
    nodeid_from_text,
    nodeid_to_text,
)
from opcua_enc import types as t  # noqa: E402
from opcua_enc.corpus import build_corpus  # noqa: E402
from opcua_enc.values import canonical_equal  # noqa: E402

# A NodeId/ExpandedNodeId field declared as Avro `string` (§5.2.1). The nullable
# variant is the ["null", "string"] union; a plain string is used here.
STRING_FIELD = parse_schema({
    "type": "record",
    "name": "TextualNodeId",
    "namespace": "org.opcfoundation.ua.avro",
    "fields": [{"name": "value", "type": "string"}],
})


def _roundtrip_string(text: str) -> str:
    buf = BytesIO()
    schemaless_writer(buf, STRING_FIELD, {"value": text})
    buf.seek(0)
    return schemaless_reader(buf, STRING_FIELD)["value"]


def main() -> int:
    cases = [c for c in build_corpus() if c.type in (t.NODEID, t.EXPANDEDNODEID)]
    assert cases, "no NodeId/ExpandedNodeId corpus cases found"
    seen_index_and_uri = False
    for case in cases:
        if case.type is t.NODEID:
            text = nodeid_to_text(case.value)
            back = nodeid_from_text(_roundtrip_string(text))
        else:
            text = expandednodeid_to_text(case.value)
            e = case.value
            if e.namespace_uri is not None and e.node_id.namespace != 0:
                seen_index_and_uri = True
            back = expandednodeid_from_text(_roundtrip_string(text))
        assert canonical_equal(case.value, back), (
            f"{case.name}: text={text!r} did not round-trip"
        )
        # The on-wire form is a single Avro string, never a record.
        assert isinstance(text, str) and "=" in text, text

    assert seen_index_and_uri, "corpus lacks an ExpandedNodeId with both index and URI"
    print(f"nodeid_string_demo: cases={len(cases)} index+uri=ok; ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
