import { test } from "node:test";
import assert from "node:assert";
import { toRoman, fromRoman } from "../src/roman.ts";
test("toRoman", () => {
  assert.strictEqual(toRoman(4), "IV");
  assert.strictEqual(toRoman(9), "IX");
  assert.strictEqual(toRoman(40), "XL");
  assert.strictEqual(toRoman(90), "XC");
  assert.strictEqual(toRoman(1994), "MCMXCIV");
  assert.strictEqual(toRoman(3888), "MMMDCCCLXXXVIII");
});
test("fromRoman", () => {
  assert.strictEqual(fromRoman("IV"), 4);
  assert.strictEqual(fromRoman("MCMXCIV"), 1994);
});
test("roundtrip", () => {
  for (const n of [1, 49, 444, 2023]) assert.strictEqual(fromRoman(toRoman(n)), n);
});
