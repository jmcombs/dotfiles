#!/usr/bin/env python3
"""Generate harder TS/Py builder fixtures (edge-case rich) + validate oracles.
Each fixture: src stub, hidden test, PLAN.md, .reference. Validate: stub FAILS, ref PASSES."""
import os, shutil, subprocess, sys
from pathlib import Path

BASE = Path("/private/tmp/claude-501/-Users-jmcombs--dotfiles/"
            "696ef4f6-557a-42b6-b92f-6df58a9f637c/scratchpad/phase-bench-hard")

# ---- TypeScript fixtures: (name, stub, test, reference) ----
TS = {}

TS["interval-merge"] = (
'export function mergeIntervals(intervals: [number, number][]): [number, number][] {\n  throw new Error("todo");\n}\n',
'''import { test } from "node:test"; import assert from "node:assert";
import { mergeIntervals as m } from "../src/interval-merge.ts";
test("empty", () => assert.deepStrictEqual(m([]), []));
test("single", () => assert.deepStrictEqual(m([[1,3]]), [[1,3]]));
test("overlap", () => assert.deepStrictEqual(m([[1,3],[2,6],[8,10],[15,18]]), [[1,6],[8,10],[15,18]]));
test("touching merges", () => assert.deepStrictEqual(m([[1,4],[4,5]]), [[1,5]]));
test("unsorted", () => assert.deepStrictEqual(m([[15,18],[1,3],[8,10],[2,6]]), [[1,6],[8,10],[15,18]]));
test("nested", () => assert.deepStrictEqual(m([[1,10],[2,3],[4,5]]), [[1,10]]));
''',
'export function mergeIntervals(intervals: [number, number][]): [number, number][] {\n  if (intervals.length === 0) return [];\n  const s = [...intervals].sort((a,b)=>a[0]-b[0]);\n  const out: [number,number][] = [s[0].slice() as [number,number]];\n  for (let i=1;i<s.length;i++){ const cur=out[out.length-1]; if (s[i][0]<=cur[1]) cur[1]=Math.max(cur[1],s[i][1]); else out.push(s[i].slice() as [number,number]); }\n  return out;\n}\n')

TS["glob-match"] = (
'export function isMatch(s: string, pattern: string): boolean {\n  throw new Error("todo");\n}\n',
'''import { test } from "node:test"; import assert from "node:assert";
import { isMatch as f } from "../src/glob-match.ts";
test("exact", () => assert.strictEqual(f("abc","abc"), true));
test("question", () => assert.strictEqual(f("abc","a?c"), true));
test("star", () => assert.strictEqual(f("abcde","a*e"), true));
test("star empty", () => assert.strictEqual(f("ae","a*e"), true));
test("leading star", () => assert.strictEqual(f("abc","*c"), true));
test("only star", () => assert.strictEqual(f("","*"), true));
test("no match", () => assert.strictEqual(f("abc","a?d"), false));
test("multi star", () => assert.strictEqual(f("mississippi","m*ss*p?"), true));
test("empty pattern", () => assert.strictEqual(f("a",""), false));
''',
'export function isMatch(s: string, pattern: string): boolean {\n  const m=s.length,n=pattern.length;\n  const dp=Array.from({length:m+1},()=>new Array(n+1).fill(false));\n  dp[0][0]=true;\n  for(let j=1;j<=n;j++) if(pattern[j-1]==="*") dp[0][j]=dp[0][j-1];\n  for(let i=1;i<=m;i++) for(let j=1;j<=n;j++){\n    if(pattern[j-1]==="*") dp[i][j]=dp[i-1][j]||dp[i][j-1];\n    else if(pattern[j-1]==="?"||pattern[j-1]===s[i-1]) dp[i][j]=dp[i-1][j-1];\n  }\n  return dp[m][n];\n}\n')

TS["toposort"] = (
'export function topoSort(n: number, edges: [number, number][]): number[] | null {\n  throw new Error("todo");\n}\n',
'''import { test } from "node:test"; import assert from "node:assert";
import { topoSort as t } from "../src/toposort.ts";
function valid(order: number[]|null, n: number, edges: [number,number][]) {
  if (order===null) return false;
  if (order.length!==n) return false;
  const pos=new Map(order.map((v,i)=>[v,i]));
  return edges.every(([a,b])=>pos.get(a)! < pos.get(b)!);
}
test("linear", () => assert.ok(valid(t(3,[[0,1],[1,2]]),3,[[0,1],[1,2]])));
test("cycle -> null", () => assert.strictEqual(t(2,[[0,1],[1,0]]), null));
test("no edges", () => { const r=t(3,[]); assert.ok(r&&r.length===3); });
test("diamond", () => assert.ok(valid(t(4,[[0,1],[0,2],[1,3],[2,3]]),4,[[0,1],[0,2],[1,3],[2,3]])));
test("self loop -> null", () => assert.strictEqual(t(1,[[0,0]]), null));
''',
'export function topoSort(n: number, edges: [number, number][]): number[] | null {\n  const adj: number[][]=Array.from({length:n},()=>[]); const indeg=new Array(n).fill(0);\n  for(const [a,b] of edges){ adj[a].push(b); indeg[b]++; }\n  const q:number[]=[]; for(let i=0;i<n;i++) if(indeg[i]===0) q.push(i);\n  const out:number[]=[];\n  while(q.length){ const u=q.shift()!; out.push(u); for(const v of adj[u]){ if(--indeg[v]===0) q.push(v); } }\n  return out.length===n?out:null;\n}\n')

TS["expr-eval"] = (
'export function evaluate(expr: string): number {\n  throw new Error("todo");\n}\n',
'''import { test } from "node:test"; import assert from "node:assert";
import { evaluate as e } from "../src/expr-eval.ts";
test("add", () => assert.strictEqual(e("1+2"), 3));
test("prec", () => assert.strictEqual(e("2+3*4"), 14));
test("parens", () => assert.strictEqual(e("(2+3)*4"), 20));
test("sub div", () => assert.strictEqual(e("10-6/2"), 7));
test("whitespace", () => assert.strictEqual(e(" 2 * ( 3 + 4 ) "), 14));
test("unary minus", () => assert.strictEqual(e("-3+5"), 2));
test("nested", () => assert.strictEqual(e("((1+2)*(3+4))"), 21));
''',
'''export function evaluate(expr: string): number {
  let i=0; const s=expr.replace(/\\s+/g,"");
  function parseExpr(): number { let v=parseTerm(); while(s[i]==="+"||s[i]==="-"){ const op=s[i++]; const t=parseTerm(); v=op==="+"?v+t:v-t; } return v; }
  function parseTerm(): number { let v=parseFactor(); while(s[i]==="*"||s[i]==="/"){ const op=s[i++]; const f=parseFactor(); v=op==="*"?v*f:v/f; } return v; }
  function parseFactor(): number { if(s[i]==="-"){ i++; return -parseFactor(); } if(s[i]==="("){ i++; const v=parseExpr(); i++; return v; } let j=i; while(j<s.length&&/[0-9.]/.test(s[j])) j++; const n=parseFloat(s.slice(i,j)); i=j; return n; }
  return parseExpr();
}
''')

TS["csv-parse"] = (
'export function parseCSV(text: string): string[][] {\n  throw new Error("todo");\n}\n',
'''import { test } from "node:test"; import assert from "node:assert";
import { parseCSV as p } from "../src/csv-parse.ts";
test("simple", () => assert.deepStrictEqual(p("a,b,c"), [["a","b","c"]]));
test("rows", () => assert.deepStrictEqual(p("a,b\\nc,d"), [["a","b"],["c","d"]]));
test("quoted comma", () => assert.deepStrictEqual(p('a,"b,c",d'), [["a","b,c","d"]]));
test("escaped quote", () => assert.deepStrictEqual(p('"a""b"'), [['a"b']]));
test("newline in quotes", () => assert.deepStrictEqual(p('"a\\nb",c'), [["a\\nb","c"]]));
test("empty fields", () => assert.deepStrictEqual(p("a,,c"), [["a","","c"]]));
''',
'''export function parseCSV(text: string): string[][] {
  const rows: string[][]=[]; let row: string[]=[]; let field=""; let inq=false; let i=0;
  while(i<text.length){ const c=text[i];
    if(inq){ if(c==='"'){ if(text[i+1]==='"'){ field+='"'; i+=2; continue; } inq=false; i++; continue; } field+=c; i++; continue; }
    if(c==='"'){ inq=true; i++; continue; }
    if(c===","){ row.push(field); field=""; i++; continue; }
    if(c==="\\n"){ row.push(field); rows.push(row); row=[]; field=""; i++; continue; }
    field+=c; i++;
  }
  row.push(field); rows.push(row); return rows;
}
''')

TS["flatten"] = (
'export function flatten(arr: any[]): number[] {\n  throw new Error("todo");\n}\n',
'''import { test } from "node:test"; import assert from "node:assert";
import { flatten as f } from "../src/flatten.ts";
test("flat", () => assert.deepStrictEqual(f([1,2,3]), [1,2,3]));
test("nested", () => assert.deepStrictEqual(f([1,[2,[3,[4]]]]), [1,2,3,4]));
test("empty inner", () => assert.deepStrictEqual(f([1,[],[2,[]],3]), [1,2,3]));
test("deep", () => assert.deepStrictEqual(f([[[[[5]]]]]), [5]));
test("mixed", () => assert.deepStrictEqual(f([0,[1,2],3,[4,[5,6]]]), [0,1,2,3,4,5,6]));
''',
'export function flatten(arr: any[]): number[] {\n  const out: number[]=[];\n  for(const x of arr){ if(Array.isArray(x)) out.push(...flatten(x)); else out.push(x); }\n  return out;\n}\n')

TS["base-convert"] = (
'export function convert(num: string, fromBase: number, toBase: number): string {\n  throw new Error("todo");\n}\n',
'''import { test } from "node:test"; import assert from "node:assert";
import { convert as c } from "../src/base-convert.ts";
test("bin to dec", () => assert.strictEqual(c("1010",2,10), "10"));
test("dec to hex", () => assert.strictEqual(c("255",10,16), "ff"));
test("hex to dec", () => assert.strictEqual(c("ff",16,10), "255"));
test("dec to bin", () => assert.strictEqual(c("10",10,2), "1010"));
test("zero", () => assert.strictEqual(c("0",10,2), "0"));
test("base36", () => assert.strictEqual(c("z",36,10), "35"));
test("roundtrip", () => assert.strictEqual(c(c("12345",10,16),16,10), "12345"));
''',
'export function convert(num: string, fromBase: number, toBase: number): string {\n  let v=0; for(const ch of num.toLowerCase()){ v=v*fromBase+parseInt(ch,36); }\n  if(v===0) return "0";\n  let out=""; const digits="0123456789abcdefghijklmnopqrstuvwxyz";\n  while(v>0){ out=digits[v%toBase]+out; v=Math.floor(v/toBase); }\n  return out;\n}\n')

# ---- Python fixtures ----
PY = {}

PY["dijkstra"] = (
'def shortest_path(n, edges, start, end):\n    raise NotImplementedError\n',
'''import sys, os, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from dijkstra import shortest_path as sp
class T(unittest.TestCase):
    def test_direct(self): self.assertEqual(sp(2, [(0,1,5)], 0, 1), 5)
    def test_path(self): self.assertEqual(sp(4, [(0,1,1),(1,2,2),(2,3,3),(0,3,10)], 0, 3), 6)
    def test_unreachable(self): self.assertEqual(sp(3, [(0,1,1)], 0, 2), -1)
    def test_same(self): self.assertEqual(sp(1, [], 0, 0), 0)
    def test_cheaper_indirect(self): self.assertEqual(sp(3, [(0,1,1),(1,2,1),(0,2,5)], 0, 2), 2)
if __name__ == "__main__": unittest.main()
''',
'''import heapq
def shortest_path(n, edges, start, end):
    adj = [[] for _ in range(n)]
    for a,b,w in edges: adj[a].append((b,w)); adj[b].append((a,w))
    dist = [float("inf")]*n; dist[start]=0
    pq=[(0,start)]
    while pq:
        d,u=heapq.heappop(pq)
        if d>dist[u]: continue
        if u==end: return d
        for v,w in adj[u]:
            if d+w<dist[v]: dist[v]=d+w; heapq.heappush(pq,(d+w,v))
    return dist[end] if dist[end]!=float("inf") else -1
''')

PY["ini_parse"] = (
'def parse_ini(text):\n    raise NotImplementedError\n',
'''import sys, os, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from ini_parse import parse_ini as p
class T(unittest.TestCase):
    def test_basic(self): self.assertEqual(p("[a]\\nx=1"), {"a":{"x":"1"}})
    def test_multi(self): self.assertEqual(p("[a]\\nx=1\\ny=2\\n[b]\\nz=3"), {"a":{"x":"1","y":"2"},"b":{"z":"3"}})
    def test_comments(self): self.assertEqual(p("; c\\n[a]\\n# c2\\nx=1"), {"a":{"x":"1"}})
    def test_whitespace(self): self.assertEqual(p("[a]\\n  x =  1  "), {"a":{"x":"1"}})
    def test_equals_in_value(self): self.assertEqual(p("[a]\\nx=1=2"), {"a":{"x":"1=2"}})
if __name__ == "__main__": unittest.main()
''',
'''def parse_ini(text):
    result={}; section=None
    for line in text.splitlines():
        line=line.strip()
        if not line or line[0] in ";#": continue
        if line.startswith("[") and line.endswith("]"):
            section=line[1:-1].strip(); result[section]={}
        elif "=" in line and section is not None:
            k,v=line.split("=",1); result[section][k.strip()]=v.strip()
    return result
''')

PY["lcs"] = (
'def lcs_length(a, b):\n    raise NotImplementedError\n',
'''import sys, os, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from lcs import lcs_length as f
class T(unittest.TestCase):
    def test_basic(self): self.assertEqual(f("abcde","ace"), 3)
    def test_none(self): self.assertEqual(f("abc","def"), 0)
    def test_empty(self): self.assertEqual(f("","abc"), 0)
    def test_same(self): self.assertEqual(f("abc","abc"), 3)
    def test_classic(self): self.assertEqual(f("AGGTAB","GXTXAYB"), 4)
if __name__ == "__main__": unittest.main()
''',
'''def lcs_length(a, b):
    m,n=len(a),len(b)
    dp=[[0]*(n+1) for _ in range(m+1)]
    for i in range(1,m+1):
        for j in range(1,n+1):
            dp[i][j]=dp[i-1][j-1]+1 if a[i-1]==b[j-1] else max(dp[i-1][j],dp[i][j-1])
    return dp[m][n]
''')

def write_fixture(name, lang, stub, test, ref):
    d=BASE/name;
    if d.exists(): shutil.rmtree(d)
    (d/"src").mkdir(parents=True); (d/"test").mkdir(parents=True)
    ext="ts" if lang=="ts" else "py"
    (d/"src"/f"{name}.{ext}").write_text(stub)
    if lang=="ts":
        (d/"test"/f"{name}.test.ts").write_text(test); gate=f"node --test test/{name}.test.ts"
    else:
        (d/"test"/f"{name}_test.py").write_text(test); gate=f"python3 test/{name}_test.py"
    (d/".reference."+ext if False else d/f".reference.{ext}").write_text(ref)
    (d/"PLAN.md").write_text(f"# PLAN\n## Phase 1 — {name}\n### Actionable TODOs\n- [ ] Implement the function(s) in `src/{name}.{ext}` per the test contract.\n### Testing Gates\n| Criterion | Command | Expected |\n|---|---|---|\n| {name} | `{gate}` | exit 0; all tests pass |\n")
    return d, ext, gate

def validate(name, lang, d, ext, gate):
    src=d/"src"/f"{name}.{ext}"
    stub=src.read_text(); ref=(d/f".reference.{ext}").read_text()
    def run():
        return subprocess.run(gate.split(), cwd=d, capture_output=True, text=True, timeout=60).returncode
    stub_rc=run()
    src.write_text(ref); ref_rc=run(); src.write_text(stub)
    ok = stub_rc!=0 and ref_rc==0
    print(f"  {name:<16}({lang}) stub_rc={stub_rc} ref_rc={ref_rc}  {'OK' if ok else 'BAD!!'}")
    return ok

if __name__=="__main__":
    BASE.mkdir(parents=True, exist_ok=True)
    allok=True
    print("=== TypeScript fixtures ===")
    for name,(stub,test,ref) in TS.items():
        d,ext,gate=write_fixture(name,"ts",stub,test,ref); allok &= validate(name,"ts",d,ext,gate)
    print("=== Python fixtures ===")
    for name,(stub,test,ref) in PY.items():
        d,ext,gate=write_fixture(name,"py",stub,test,ref); allok &= validate(name,"py",d,ext,gate)
    print(f"\n{'ALL OK' if allok else 'SOME ORACLES INVALID — fix before running'}  ({len(TS)} TS + {len(PY)} Py = {len(TS)+len(PY)})")
