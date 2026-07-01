# Phase 1 — LRU cache
### Actionable TODOs
- [ ] Implement generic `class LRUCache<K,V>` in `src/lru.ts`: `constructor(capacity)`, `get`, `put` with LRU eviction; `get` and `put` count as use.
### Testing Gates
| Criterion | Command | Expected |
|---|---|---|
| lru | `node --test test/lru.test.ts` | exit 0; all pass |
