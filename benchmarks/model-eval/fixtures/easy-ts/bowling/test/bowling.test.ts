import { test } from "node:test";
import assert from "node:assert";
import { BowlingGame } from "../src/bowling.ts";
function many(g: BowlingGame, n: number, p: number) { for (let i=0;i<n;i++) g.roll(p); }
test("gutter game", () => { const g=new BowlingGame(); many(g,20,0); assert.strictEqual(g.score(),0); });
test("all ones", () => { const g=new BowlingGame(); many(g,20,1); assert.strictEqual(g.score(),20); });
test("one spare", () => { const g=new BowlingGame(); g.roll(5);g.roll(5);g.roll(3); many(g,17,0); assert.strictEqual(g.score(),16); });
test("one strike", () => { const g=new BowlingGame(); g.roll(10);g.roll(3);g.roll(4); many(g,16,0); assert.strictEqual(g.score(),24); });
test("perfect game", () => { const g=new BowlingGame(); many(g,12,10); assert.strictEqual(g.score(),300); });
