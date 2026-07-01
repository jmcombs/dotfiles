import { test } from "node:test"; import assert from "node:assert";
import { parseCSV as p } from "../src/csv-parse.ts";
test("simple", () => assert.deepStrictEqual(p("a,b,c"), [["a","b","c"]]));
test("rows", () => assert.deepStrictEqual(p("a,b\nc,d"), [["a","b"],["c","d"]]));
test("quoted comma", () => assert.deepStrictEqual(p('a,"b,c",d'), [["a","b,c","d"]]));
test("escaped quote", () => assert.deepStrictEqual(p('"a""b"'), [['a"b']]));
test("newline in quotes", () => assert.deepStrictEqual(p('"a\nb",c'), [["a\nb","c"]]));
test("empty fields", () => assert.deepStrictEqual(p("a,,c"), [["a","","c"]]));
