# Model artifacts

Repository-owned model artifacts mirror their specification under
`model/<group>/<spec>/`. For example, the model for
`source/core-specs/xregistry/` is in `model/core-specs/xregistry/`.

`model/dependencies/` remains flat because the specification publisher uses that
directory for downloaded external dependencies. A model defined by this repository is
not an external dependency and belongs in its specification's mirrored directory.

Pass `--nodesets model` to `Opc.Ua.SpecificationPublisher build` so dependency
resolution searches the complete mirrored tree.

The generators are the source of truth. Do not hand-edit a generated `NodeSet2.xml` or
`NodeIds.csv` file.
