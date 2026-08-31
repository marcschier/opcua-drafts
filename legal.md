<!-- Written by `Opc.Ua.SpecificationPublisher upgrade`, which refreshes it when a new version
     of the tool ships a new copy. Edit it and it becomes yours; delete it and run
     `upgrade --write` to take the current copy back. -->

# Legal

`source/agreement-of-use.md`, `source/logo-left.*` and `source/logo-right.*` are not authored in
this repository. `upgrade --write` downloads them from the OPC Foundation's shared repository of
partner agreements and logos, at `https://opcfoundation.org/specification-common/<organization>/`,
and overwrites whatever is on disk with what it fetched. Editing those files by hand accomplishes
nothing beyond the next `upgrade --write`, which is the point: it is the Foundation's legal text
and the Foundation's and partner's marks, not a document a working group edits, and this way every
repository stays in step with whatever the Foundation currently publishes rather than with
whatever a Word document happened to say on the day someone copy-pasted it.

`<organization>` is the line below. Leave it blank, or delete this file, and the Foundation
publishes alone: `agreement-of-use.md` and `logo-left.*` are still fetched from the `OPC` folder,
and any `source/logo-right.*` left over from an earlier joint work is deleted rather than fetched.
Name a co-publisher - `VDMA`, `VDW`, and so on, matching a folder in that shared repository - and
the joint text and both logos are fetched instead.

A failed fetch (no network, or no folder for the name below) is reported and does not stop the
rest of `upgrade`; it is retried on the next `upgrade --write`.

Partner organization:
