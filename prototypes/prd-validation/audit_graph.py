import json, re, sys

PRD = "国家在线业务管理平台V2_Beta_PRD_20260811.md"
GRAPH = "国家在线业务管理平台V2_Beta_PRD_20260811_功能点图谱.json"

doc = open(PRD, encoding="utf-8").read()
g = json.load(open(GRAPH, encoding="utf-8"))

ids = [n["id"] for n in g["nodes"]]
assert len(ids) == len(set(ids)), "node id duplicated"
idset = set(ids)

errors, warnings = [], []
quote_re = re.compile(r'"([^"]+)"')

non_contains = 0
cert_count = {}
for i, e in enumerate(g["edges"]):
    if e["source"] not in idset or e["target"] not in idset:
        errors.append(f"edge#{i} endpoint missing: {e['source']}->{e['target']}")
    t = e["type"]
    if t == "contains":
        continue
    non_contains += 1
    cert_count[e["certainty"]] = cert_count.get(e["certainty"], 0) + 1
    if e["source"] == e["target"] and "note" not in e:
        errors.append(f"edge#{i} self-loop without note")
    ev = e.get("evidence", "")
    if not ev:
        errors.append(f"edge#{i} ({t}) missing evidence")
        continue
    quotes = quote_re.findall(ev)
    if not quotes:
        errors.append(f"edge#{i} ({t}) no ASCII-quoted phrase in evidence")
    for q in quotes:
        if q not in doc:
            errors.append(f"edge#{i} ({t}) quote NOT FOUND: {q[:40]}...")

if set(cert_count) == {"high"}:
    warnings.append("all non-contains edges are high (violates certainty distribution rule)")

print(f"nodes={len(ids)} edges={len(g['edges'])} non_contains={non_contains} certainty={cert_count}")
if warnings:
    print("WARNINGS:"); [print(" -", w) for w in warnings]
if errors:
    print(f"FAILED: {len(errors)} errors"); [print(" -", e) for e in errors]; sys.exit(1)
print("AUDIT PASS: all quoted evidence found in source doc")
