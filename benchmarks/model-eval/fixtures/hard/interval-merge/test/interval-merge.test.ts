import { test } from "node:test"; import assert from "node:assert";
import { mergeIntervals as m } from "../src/interval-merge.ts";
test("empty", () => assert.deepStrictEqual(m([]), []));
test("single", () => assert.deepStrictEqual(m([[1,3]]), [[1,3]]));
test("overlap", () => assert.deepStrictEqual(m([[1,3],[2,6],[8,10],[15,18]]), [[1,6],[8,10],[15,18]]));
test("touching merges", () => assert.deepStrictEqual(m([[1,4],[4,5]]), [[1,5]]));
test("unsorted", () => assert.deepStrictEqual(m([[15,18],[1,3],[8,10],[2,6]]), [[1,6],[8,10],[15,18]]));
test("nested", () => assert.deepStrictEqual(m([[1,10],[2,3],[4,5]]), [[1,10]]));
