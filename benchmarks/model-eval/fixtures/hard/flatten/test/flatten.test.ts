import { test } from "node:test"; import assert from "node:assert";
import { flatten as f } from "../src/flatten.ts";
test("flat", () => assert.deepStrictEqual(f([1,2,3]), [1,2,3]));
test("nested", () => assert.deepStrictEqual(f([1,[2,[3,[4]]]]), [1,2,3,4]));
test("empty inner", () => assert.deepStrictEqual(f([1,[],[2,[]],3]), [1,2,3]));
test("deep", () => assert.deepStrictEqual(f([[[[[5]]]]]), [5]));
test("mixed", () => assert.deepStrictEqual(f([0,[1,2],3,[4,[5,6]]]), [0,1,2,3,4,5,6]));
