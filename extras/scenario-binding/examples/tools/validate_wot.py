#!/usr/bin/env python3
"""Validate generated WoT Thing Descriptions for Scenario Binding examples."""
import json
import os
import re
import subprocess
import sys


HERE = os.path.dirname(os.path.abspath(__file__))
EX = os.path.dirname(HERE)
TD_FILES = [
    os.path.join(EX, "pumps", "Opc.Ua.Pumps.ScenarioBinding.td.json"),
    os.path.join(EX, "robotics", "Opc.Ua.Robotics.ScenarioBinding.td.json"),
]
SOURCES = [
    os.path.join(EX, "pumps", "Pumps.ScenarioBinding.json"),
    os.path.join(EX, "robotics", "Robotics.ScenarioBinding.json"),
]
WOT_TD_CONTEXT = "https://www.w3.org/2019/wot/td/v1"
UAV = "http://opcfoundation.org/UA/WoT-Binding/"
SB = "http://opcfoundation.org/UA/ScenarioBinding/WoT/"
DATASET_CLASS_ID = re.compile(r"^urn:uuid:[0-9a-f-]{36}$")
ALLOWED_OPS = {
    "readproperty",
    "writeproperty",
    "observeproperty",
    "invokeaction",
    "subscribeevent",
    "unobserveproperty",
    "unsubscribeevent",
}

errors = []


def err(path, message):
    errors.append(f"{os.path.relpath(path, EX)}: {message}")


def load_document(path):
    with open(path, "r", encoding="utf-8") as f:
        doc = json.load(f)
    if isinstance(doc, dict):
        return doc, [doc]
    if isinstance(doc, list):
        things = [x for x in doc if isinstance(x, dict)]
        if len(things) != len(doc):
            err(path, "TD collection contains non-object entries")
        return doc, things
    err(path, "TD root must be an object or an array")
    return doc, []


def has_context_prefix(context, prefix, uri):
    if not isinstance(context, list):
        return False
    for item in context[1:]:
        if isinstance(item, dict) and item.get(prefix) == uri:
            return True
    return False


def non_empty(value):
    return bool(value)


def as_ops(value):
    if isinstance(value, str):
        return [value]
    if isinstance(value, list) and value and all(isinstance(x, str) for x in value):
        return value
    return None


def id_portion(href):
    marker = "?id="
    pos = href.find(marker)
    if pos < 0:
        return None
    return href[pos + len(marker):]


def validate_form(path, thing_title, section, name, index, form):
    where = f"{thing_title} {section}.{name} form[{index}]"
    if not isinstance(form, dict):
        err(path, f"{where}: form must be an object")
        return 0
    ops = as_ops(form.get("op"))
    if not ops:
        err(path, f"{where}: op must be a non-empty string or string array")
    else:
        for op in ops:
            if op not in ALLOWED_OPS:
                err(path, f"{where}: invalid op {op!r}")
    href = form.get("href")
    if not isinstance(href, str) or not href:
        err(path, f"{where}: href must be a non-empty string")
        return 1
    if href.startswith("/?id=") or (href.startswith("opc.tcp://") and "?id=" in href):
        node_id = id_portion(href)
        if node_id is None:
            err(path, f"{where}: OPC UA href missing ?id=")
        elif "#" in node_id or "&" in node_id:
            err(path, f"{where}: raw # or & in id portion of href")
    return 1


def validate_affordances(path, thing, section):
    values = thing.get(section)
    if values is None:
        return 0, 0
    if not isinstance(values, dict):
        err(path, f"{thing.get('title', '<untitled>')} {section}: must be an object")
        return 0, 0
    form_count = 0
    for name, affordance in values.items():
        if not isinstance(affordance, dict):
            err(path, f"{thing.get('title', '<untitled>')} {section}.{name}: must be an object")
            continue
        forms = affordance.get("forms")
        if not isinstance(forms, list) or not forms:
            err(path, f"{thing.get('title', '<untitled>')} {section}.{name}: forms must be a non-empty array")
            continue
        for i, form in enumerate(forms):
            form_count += validate_form(path, thing.get("title", "<untitled>"), section, name, i, form)
    return len(values), form_count


def validate_dataset_class_ids(path, value, trail="$"):
    if isinstance(value, dict):
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            if key == "sb:dataSetClassId":
                validate_dataset_value(path, child, child_trail)
            else:
                validate_dataset_class_ids(path, child, child_trail)
    elif isinstance(value, list):
        for i, child in enumerate(value):
            validate_dataset_class_ids(path, child, f"{trail}[{i}]")


def validate_dataset_value(path, value, trail):
    values = value if isinstance(value, list) else [value]
    if not isinstance(value, (str, list)):
        err(path, f"{trail}: uav:dataSetClassId must be a string or array")
        return
    for item in values:
        if not isinstance(item, str) or not DATASET_CLASS_ID.match(item):
            err(path, f"{trail}: invalid uav:dataSetClassId {item!r}")


def contains_key(value, wanted):
    if isinstance(value, dict):
        if wanted in value:
            return True
        return any(contains_key(child, wanted) for child in value.values())
    if isinstance(value, list):
        return any(contains_key(child, wanted) for child in value)
    return False


def validate_thing(path, thing):
    title = thing.get("title")
    thing_name = title if isinstance(title, str) and title else "<untitled>"
    context = thing.get("@context")
    if not (isinstance(context, list) and context and context[0] == WOT_TD_CONTEXT):
        err(path, f"{thing_name}: @context must start with {WOT_TD_CONTEXT}")
    if not has_context_prefix(context, "uav", UAV):
        err(path, f"{thing_name}: @context missing uav mapping")
    if not has_context_prefix(context, "sb", SB):
        err(path, f"{thing_name}: @context missing sb (Scenario Bindings extension) mapping")
    if not isinstance(title, str) or not title:
        err(path, f"{thing_name}: title must be a non-empty string")
    if not non_empty(thing.get("security")):
        err(path, f"{thing_name}: security must be non-empty")
    if not non_empty(thing.get("securityDefinitions")):
        err(path, f"{thing_name}: securityDefinitions must be non-empty")
    base = thing.get("base")
    if not isinstance(base, str) or not base.startswith("opc.tcp://"):
        err(path, f"{thing_name}: base must start with opc.tcp://")
    if not any(thing.get(x) for x in ("properties", "actions", "events")):
        err(path, f"{thing_name}: expected at least one of properties/actions/events")

    counts = {}
    total_forms = 0
    for section in ("properties", "actions", "events"):
        count, forms = validate_affordances(path, thing, section)
        counts[section] = count
        total_forms += forms
    return counts["properties"], counts["actions"], counts["events"], total_forms


def validate_file(path):
    doc, things = load_document(path)
    validate_dataset_class_ids(path, doc)
    if not contains_key(doc, "uav:browsePath"):
        err(path, "uav:browsePath not found anywhere in document")
    if not contains_key(doc, "uav:browseName"):
        err(path, "uav:browseName not found anywhere in document")

    totals = {"properties": 0, "actions": 0, "events": 0, "forms": 0}
    for thing in things:
        p, a, e, f = validate_thing(path, thing)
        totals["properties"] += p
        totals["actions"] += a
        totals["events"] += e
        totals["forms"] += f
    print(f"{os.path.relpath(path, EX)}: {len(things)} Things, "
          f"{totals['properties']} properties, {totals['actions']} actions, "
          f"{totals['events']} events, {totals['forms']} forms")


def read_bytes(paths):
    data = {}
    for path in paths:
        with open(path, "rb") as f:
            data[path] = f.read()
    return data


def run_generator(source):
    cmd = [sys.executable, os.path.join(HERE, "build_wot_td.py"), source]
    return subprocess.call(cmd, cwd=EX, stdout=subprocess.DEVNULL)


def check_determinism():
    before = read_bytes(TD_FILES)
    for pass_no in (1, 2):
        for source in SOURCES:
            rc = run_generator(source)
            if rc:
                err(source, f"generator failed with exit code {rc} on determinism pass {pass_no}")
        after = read_bytes(TD_FILES)
        for path in TD_FILES:
            if before[path] != after[path]:
                err(path, f"not byte-identical after regeneration pass {pass_no}")
    print("determinism: regenerated both TDs twice; byte-identical")


def main():
    determinism = False
    args = []
    for arg in sys.argv[1:]:
        if arg == "--determinism":
            determinism = True
        else:
            args.append(arg)
    if args:
        sys.exit(f"usage: {os.path.basename(sys.argv[0])} [--determinism]")
    for path in TD_FILES:
        if not os.path.exists(path):
            err(path, "file not found")
        else:
            validate_file(path)
    if determinism:
        check_determinism()
    print(f"\nERRORS: {len(errors)}")
    for e in errors[:40]:
        print("  ", e)
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
