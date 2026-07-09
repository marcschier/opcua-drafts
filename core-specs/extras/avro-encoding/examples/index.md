# Avro example payloads

The `.hex.txt` files contain schemaless Avro payload bytes generated from the shared CORPUS.

- `bool_true.hex.txt` — `Builtin` descriptor, 1 bytes
- `uint64_max.hex.txt` — `Builtin` descriptor, 1 bytes
- `double_nan.hex.txt` — `Builtin` descriptor, 8 bytes
- `string_unicode.hex.txt` — `Builtin` descriptor, 21 bytes
- `nodeid_guid.hex.txt` — `Builtin` descriptor, 23 bytes
- `array_string_with_nulls.hex.txt` — `Array` descriptor, 9 bytes
- `matrix_double_2x2_special.hex.txt` — `Matrix` descriptor, 43 bytes
- `struct_person_min.hex.txt` — `Struct` descriptor, 7 bytes
- `union_point.hex.txt` — `Struct` descriptor, 26 bytes
- `envelope.hex.txt` — `Struct` descriptor, 55 bytes
- `variant_matrix_int.hex.txt` — `Builtin` descriptor, 17 bytes
- `variant_extobj.hex.txt` — `Builtin` descriptor, 30 bytes
- `datavalue_full.hex.txt` — `Builtin` descriptor, 19 bytes
- `diaginfo_nested.hex.txt` — `Builtin` descriptor, 34 bytes

Schema-exchange message examples are schemaless Avro payload bytes generated from the published `.avsc` files.

- `avro_schema_announcement.hex.txt` — `AvroSchemaAnnouncement` record, 804 bytes
- `avro_schema_request.hex.txt` — `AvroSchemaRequest` record, 35 bytes
