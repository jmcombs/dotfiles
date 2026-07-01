import { test } from "node:test"; import assert from "node:assert";
import { evaluate as e } from "../src/expr-eval.ts";
test("add", () => assert.strictEqual(e("1+2"), 3));
test("prec", () => assert.strictEqual(e("2+3*4"), 14));
test("parens", () => assert.strictEqual(e("(2+3)*4"), 20));
test("sub div", () => assert.strictEqual(e("10-6/2"), 7));
test("whitespace", () => assert.strictEqual(e(" 2 * ( 3 + 4 ) "), 14));
test("unary minus", () => assert.strictEqual(e("-3+5"), 2));
test("nested", () => assert.strictEqual(e("((1+2)*(3+4))"), 21));
