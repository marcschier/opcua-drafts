# Pinned OPC 10100-1 v1.02 sources

These files are the **pinned authoring sources** for the published OPC 10100-1 v1.02 WoT Connectivity model. They are a **source input** to `../tools/build_model.py`, which parses them and incorporates the 1.02 nodes into the combined `Opc.Ua.WoTCon.NodeSet2.xml` at their exact published NodeIds — they are **not** hand-copied output.

- `WotConnection.xml` — the UA ModelDesign for the 1.02 model (type bases, method signatures, references).
- `WotConnection.csv` — the authoritative NodeId / NodeClass table (`SymbolicName,NodeId,NodeClass`) for every published node `1..172`, including reserved (`Unspecified`) ids.

Do not edit these files to change the generated model; they pin the published baseline. `../tools/validate_local.py` proves the preservation by comparing the first 172 rows of the generated CSV against `WotConnection.csv` byte-for-byte and checking that every concrete legacy id appears in the NodeSet with its pinned NodeClass.

Origin: `src/Opc.Ua.WotCon/Design/WotConnection.{xml,csv}` in the WoT Connectivity model assembly.
