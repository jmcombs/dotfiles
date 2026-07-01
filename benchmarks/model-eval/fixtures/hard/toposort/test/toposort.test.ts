import { test } from "node:test"; import assert from "node:assert";
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
