# Secondary tooling and examples

Specification prose lives under `source/<group>/<spec>/`, generated repository-owned models live
under `model/<group>/<spec>/`, and secondary generators, validators, examples, descriptors and
research tooling live here under `extras/<group>/<spec>/`.

Group-level support files remain directly under `extras/<group>/`. In particular, each populated
group has a `validate_all.py` aggregate, and shared encoding support is
`extras/core-specs/_common/`.

Run an aggregate from the repository root, for example:

```powershell
python extras/core-specs/validate_all.py --self-contained
python extras/cloud-specs/validate_all.py --self-contained
python extras/metaverse-specs/validate_all.py --self-contained
python extras/companion-specs/validate_all.py --self-contained
```

Some specifications own their generator directly under `source/<group>/<spec>/tools/`; those
tools stay with their specification rather than being duplicated here.
