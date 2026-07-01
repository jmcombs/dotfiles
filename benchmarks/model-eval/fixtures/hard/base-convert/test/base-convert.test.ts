import { test } from "node:test"; import assert from "node:assert";
import { convert as c } from "../src/base-convert.ts";
test("bin to dec", () => assert.strictEqual(c("1010",2,10), "10"));
test("dec to hex", () => assert.strictEqual(c("255",10,16), "ff"));
test("hex to dec", () => assert.strictEqual(c("ff",16,10), "255"));
test("dec to bin", () => assert.strictEqual(c("10",10,2), "1010"));
test("zero", () => assert.strictEqual(c("0",10,2), "0"));
test("base36", () => assert.strictEqual(c("z",36,10), "35"));
test("roundtrip", () => assert.strictEqual(c(c("12345",10,16),16,10), "12345"));
