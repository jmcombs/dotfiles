import json, sys
from collections import Counter
path = sys.argv[1]
events = []
with open(path) as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except Exception as e:
            print("UNPARSEABLE:", line[:100])

print("total events:", len(events))
types = Counter(e.get('type', e.get('role', '?')) for e in events)
print("event types:", dict(types))
print()
# Show keys per distinct type (first occurrence)
seen = set()
for e in events:
    t = e.get('type', e.get('role', '?'))
    if t in seen:
        continue
    seen.add(t)
    print(f"--- first '{t}' --- keys={list(e.keys())}")
    s = json.dumps(e)
    print("   sample:", s[:400])
print()
# Look for tool calls and final result/usage
print("=== tool-call-ish events ===")
for e in events:
    blob = json.dumps(e).lower()
    if 'tool' in blob and ('name' in e or 'tool' in e or e.get('type','').find('tool')>=0):
        nm = e.get('name') or e.get('tool') or (e.get('toolCall') or {}).get('name')
        print(f"  type={e.get('type')} name={nm} keys={list(e.keys())[:6]}")
print()
print("=== last event (final result/usage) ===")
print(json.dumps(events[-1], indent=2)[:1500])
