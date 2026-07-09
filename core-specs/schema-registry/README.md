# OPC UA Schema Registry

This folder contains the generated NodeSet companion extension for an in-server OPC UA Schema Registry.

The model is isomorphic to the xRegistry Schema Registry shape (`registry` → `schemagroups` → `schemas` → `versions`) and is exposed as a well-known `SchemaRegistry` Object under Part 14 `PublishSubscribe` (`i=14443`). Each schema Version document is also addressable at runtime by an Opaque NodeId in the Schema Registry namespace whose Identifier bytes are the raw on-wire `SchemaId` fingerprint.

Generated artifacts:

- `Opc.Ua.SchemaRegistry.NodeSet2.xml`
- `Opc.Ua.SchemaRegistry.NodeIds.csv`
- `tools/model-reference.md`

Regenerate and validate:

```powershell
python core-specs\schema-registry\tools\build_model.py
python core-specs\schema-registry\tools\validate_local.py
python core-specs\extras\validate_all.py
```

Draft numeric NodeIds use the provisional `62000+` block in `http://opcfoundation.org/UA/SchemaRegistry/`; final NodeIds are assigned by the OPC Foundation.
