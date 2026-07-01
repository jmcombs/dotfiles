import { test } from "node:test";
import assert from "node:assert";
import { LRUCache } from "../src/lru.ts";
test("basic get/put", () => {
  const c = new LRUCache<string, number>(2);
  c.put("a", 1); c.put("b", 2);
  assert.strictEqual(c.get("a"), 1);
  assert.strictEqual(c.get("b"), 2);
});
test("evicts least-recently-used", () => {
  const c = new LRUCache<string, number>(2);
  c.put("a", 1); c.put("b", 2);
  c.get("a");
  c.put("c", 3);
  assert.strictEqual(c.get("b"), undefined);
  assert.strictEqual(c.get("a"), 1);
  assert.strictEqual(c.get("c"), 3);
});
test("overwrite updates value and recency", () => {
  const c = new LRUCache<string, number>(2);
  c.put("a", 1); c.put("b", 2); c.put("a", 10);
  c.put("c", 3);
  assert.strictEqual(c.get("b"), undefined);
  assert.strictEqual(c.get("a"), 10);
});
