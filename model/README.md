# Model artifacts

Repository-owned model artifacts mirror their specification under
`model/<group>/<spec>/`. For example, the model for
`source/companion-specs/Generators/` is in `model/companion-specs/Generators/`.

`model/dependencies/` remains flat because the specification publisher uses that
directory for external dependencies. The released xRegistry model is kept there because
its authoritative specification is under review in `OPCF-Members/spec-drafts`; a model
defined by this repository belongs in its specification's mirrored directory.

Pass `--nodesets model` to `Opc.Ua.SpecificationPublisher build` so dependency
resolution searches the complete mirrored tree.

The generators are the source of truth. Do not hand-edit a generated `NodeSet2.xml` or
`NodeIds.csv` file.
