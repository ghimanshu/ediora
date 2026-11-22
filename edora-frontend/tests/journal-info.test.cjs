const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const script = fs.readFileSync(path.join(__dirname, "../../edora-backend/app/static/journal-info.js"), "utf8");
function element(tag, text = "") { return { tag, textContent: text, children: [], appendChild(child) { this.children.push(child); }, replaceChildren(...children) { this.children = children; } }; }
function contents(el) { return el.textContent + el.children.map(contents).join(" "); }
async function run({ storage = new Map(), code = "ab12cd34", slug = "research", now = 1000000, offline = false, denied = false, blocked = false, language = "French" } = {}) {
  let calls = 0;
  const target = element("div"); target.appendChild(element("p", "Snapshot"));
  const contact = element("a");
  const config = { api_origin: "https://portal.example.com", editor_code: code, journal_slug: slug };
  class Clock extends Date { static now() { return now; } }
  const context = { window: { EDORA_JOURNAL: config }, URL, Date: Clock, Number, JSON, AbortSignal,
    document: { createElement: tag => element(tag), querySelectorAll: selector => selector === "[data-journal-info]" ? [{ querySelector: () => target }] : [contact] },
    localStorage: { getItem(key) { if (blocked) throw Error("Blocked"); return storage.get(key) || null; }, setItem(key, value) { if (blocked) throw Error("Blocked"); storage.set(key, value); }, removeItem(key) { storage.delete(key); } },
    fetch: async () => { calls++; if (offline) throw Error("Offline"); return { status: denied ? 404 : 200, ok: !denied, json: async () => ({ editor_code: code, journal_slug: slug, journal_info: { language, plagiarism: "<10%" }, editor_email: "editor@example.com" }) }; },
  };
  vm.runInNewContext(script, context);
  await new Promise(setImmediate);
  return { calls, target, contact, storage };
}
test("journal information fetches once and is reused between exported pages", async () => {
  const first = await run();
  assert.equal(first.calls, 1); assert.match(contents(first.target), /French/); assert.match(contents(first.target), /<10%/);
  const next = await run({ storage: first.storage });
  assert.equal(next.calls, 0); assert.match(contents(next.target), /French/);
  assert.equal(next.contact.href, "mailto:editor%40example.com");
});
test("expired journal information cache refreshes from the internal API", async () => {
  const first = await run();
  const next = await run({ storage: first.storage, now: 1300001, language: "English" });
  assert.equal(next.calls, 1); assert.match(contents(next.target), /English/);
});
test("journal cache is scoped separately for each journal", async () => {
  const first = await run();
  const next = await run({ storage: first.storage, slug: "another-journal", language: "Spanish" });
  assert.equal(next.calls, 1); assert.match(contents(next.target), /Spanish/); assert.equal(next.storage.size, 2);
});
test("blocked storage still loads live journal details and offline mode keeps cached data", async () => {
  const blocked = await run({ blocked: true }); assert.equal(blocked.calls, 1); assert.match(contents(blocked.target), /French/);
  const first = await run();
  const offline = await run({ storage: first.storage, now: 1300001, offline: true });
  assert.match(contents(offline.target), /French/); assert.match(contents(offline.target), /last available/);
});
test("unavailable journals clear expired cached data", async () => {
  const first = await run();
  const hidden = await run({ storage: first.storage, now: 1300001, denied: true });
  assert.equal(hidden.storage.size, 0); assert.doesNotMatch(contents(hidden.target), /French/); assert.equal(hidden.contact.hidden, true);
});
