const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const path = require("node:path");
const { test } = require("node:test");
const vm = require("node:vm");
const ts = require("typescript");
const { NextRequest } = require("next/server");

// Execute the actual TypeScript modules with a mocked fetch; no backend or data changes.
function loadModule(relativePath, fetch) {
  const filename = path.join(__dirname, "..", relativePath);
  const source = ts.transpileModule(readFileSync(filename, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const module = { exports: {} };
  vm.runInNewContext(source, {
    module, exports: module.exports, require, fetch: async (url, options) => {
      if (relativePath === "src/app/api/[...path]/route.ts" && String(url).endsWith("/api/v1/auth/me") && options?.headers?.Authorization) return Response.json({ public_code: "ab12cd34" });
      return fetch(url, options);
    }, Buffer, AbortSignal, process, URL, URLSearchParams,
  }, { filename });
  return module.exports;
}
process.env.INTERNAL_API_KEY = "test-internal-key";
// Existing forwarding tests use an authenticated website request for dashboard mutations.
function testRequest(url, init) {
  const request = new NextRequest(url, init);
  if (request.method !== "GET" && /\/api\/(?:editor\/|admin\/|website\/template|auth\/logout)/.test(url) && !request.cookies.has("edora_session")) request.cookies.set("edora_session", "test-session");
  return request;
}
const context = (route) => ({ params: Promise.resolve({ path: route.split("/") }) });

test("proxy preserves JSON null for editors without a journal", async () => {
  const { GET } = loadModule("src/app/api/[...path]/route.ts", async () => new Response("null", { status: 200 }));
  const result = await GET(testRequest("http://localhost:3000/api/editor/journal"), context("editor/journal"));
  assert.equal(result.status, 200);
  assert.equal(result.headers.get("cache-control"), "no-store");
  assert.equal(await result.text(), "null");
});

test("proxy and browser helper load an editor's empty-journal response together", async () => {
  const { GET } = loadModule("src/app/api/[...path]/route.ts", async () => new Response("null", { status: 200 }));
  const { api } = loadModule("src/lib/api.ts", () => GET(testRequest("http://localhost:3000/api/editor/journal"), context("editor/journal")));
  assert.equal(await api("editor/journal"), null);
});

test("proxy keeps successful delete responses bodyless", async () => {
  const { DELETE } = loadModule("src/app/api/[...path]/route.ts", async () => new Response(null, { status: 204 }));
  const origin = process.env.APP_ORIGIN ?? "http://localhost:3000";
  const result = await DELETE(testRequest(`${origin}/api/admin/templates/1`, { method: "DELETE", headers: { origin } }), context("admin/templates/1"));
  assert.equal(result.status, 204);
  assert.equal(await result.text(), "");
});

test("proxy preserves JSON objects and backend errors", async () => {
  for (const [status, data] of [[200, { id: 1, name: "Journal" }], [403, { detail: "Editor account required" }]]) {
    const { GET } = loadModule("src/app/api/[...path]/route.ts", async () => Response.json(data, { status }));
    const result = await GET(testRequest("http://localhost:3000/api/editor/journal"), context("editor/journal"));
    assert.equal(result.status, status);
    assert.deepEqual(await result.json(), data);
  }
});

test("browser helper explains empty and non-JSON responses instead of exposing parsing errors", async () => {
  for (const [body, status, expected] of [["", 200, /empty response/], ["", 502, /HTTP 502/], ["<html>Error</html>", 200, /invalid response/], ["<html>Error</html>", 502, /HTTP 502/]]) {
    const { api } = loadModule("src/lib/api.ts", async () => new Response(body, { status }));
    await assert.rejects(() => api("editor/journal"), expected);
  }
});

test("browser helper retains no-content success and validation messages", async () => {
  const { api: remove } = loadModule("src/lib/api.ts", async () => new Response(null, { status: 204 }));
  assert.equal(Object.keys(await remove("admin/templates/1", undefined, "DELETE")).length, 0);
  const { api } = loadModule("src/lib/api.ts", async () => Response.json({ detail: [{ loc: ["body", "name"], msg: "Required" }] }, { status: 422 }));
  await assert.rejects(() => api("editor/journal"), /name: Required/);
});


test("journal creation forwards custom HTML pages larger than the old 20KB limit", async () => {
  let forwarded;
  const { POST } = loadModule("src/app/api/[...path]/route.ts", async (_url, options) => {
    forwarded = JSON.parse(options.body);
    return Response.json({ id: 1 }, { status: 201 });
  });
  const origin = process.env.APP_ORIGIN ?? "http://localhost:3000";
  const payload = { name: "My Journal", template_id: 1, page_ids: [], new_pages: [{ title: "Research", slug: "research", content_html: "<p>" + "x".repeat(30000) + "</p>" }] };
  const result = await POST(testRequest(`${origin}/api/editor/journal`, { method: "POST", headers: { origin, "content-type": "application/json" }, body: JSON.stringify(payload) }), context("editor/journal"));
  assert.equal(result.status, 201);
  assert.deepEqual(forwarded, payload);
});


test("public journal reads use the allowlisted internal proxy without a session", async () => {
  let upstreamUrl;
  const { GET } = loadModule("src/app/api/[...path]/route.ts", async (url) => {
    upstreamUrl = url;
    return Response.json({ name: "My Journal", pages: [] });
  });
  const result = await GET(testRequest("http://localhost:3000/api/public/journals/ab12cd34/my-journal"), context("public/journals/ab12cd34/my-journal"));
  assert.equal(result.status, 200);
  assert.ok(upstreamUrl.endsWith("/api/v1/public/journals/ab12cd34/my-journal"));
  assert.equal((await result.json()).name, "My Journal");
});


test("private journal page creation and reordering forward through internal routes", async () => {
  const origin = process.env.APP_ORIGIN ?? "http://localhost:3000";
  for (const [method, route, payload, status] of [
    ["POST", "editor/journal/pages", { title: "Private", slug: "private", content_html: "<p>" + "x".repeat(30000) + "</p>" }, 201],
    ["PATCH", "editor/journal/pages/order", { page_ids: [3, 1, 2] }, 200],
  ]) {
    let forwarded;
    const handlers = loadModule("src/app/api/[...path]/route.ts", async (_url, options) => {
      forwarded = { method: options.method, body: JSON.parse(options.body) };
      return Response.json({ pages: [] }, { status });
    });
    const response = await handlers[method](testRequest(`${origin}/api/${route}`, { method, headers: { origin, "content-type": "application/json" }, body: JSON.stringify(payload) }), context(route));
    assert.equal(response.status, status);
    assert.deepEqual(forwarded, { method, body: payload });
  }
});


test("journal list and selected journal IDs are forwarded through the internal API", async () => {
  let upstream;
  const handlers = loadModule("src/app/api/[...path]/route.ts", async (url) => { upstream = url; return Response.json([]); });
  let response = await handlers.GET(testRequest("http://localhost:3000/api/editor/journals"), context("editor/journals"));
  assert.equal(response.status, 200);
  assert.ok(upstream.endsWith("/api/v1/editor/journals"));
  response = await handlers.GET(testRequest("http://localhost:3000/api/editor/journal?journal_id=7"), context("editor/journal"));
  assert.equal(response.status, 200);
  assert.ok(upstream.endsWith("/api/v1/editor/journal?journal_id=7"));
});


test("journal status updates preserve the selected journal ID", async () => {
  const origin = process.env.APP_ORIGIN ?? "http://localhost:3000";
  let forwarded;
  const { PATCH } = loadModule("src/app/api/[...path]/route.ts", async (url, options) => {
    forwarded = { url, body: JSON.parse(options.body) };
    return Response.json({ id: 7, status: "Published" });
  });
  const response = await PATCH(testRequest(`${origin}/api/editor/journal/status?journal_id=7`, { method: "PATCH", headers: { origin, "content-type": "application/json" }, body: JSON.stringify({ status: "Published" }) }), context("editor/journal/status"));
  assert.equal(response.status, 200);
  assert.ok(forwarded.url.endsWith("/api/v1/editor/journal/status?journal_id=7"));
  assert.deepEqual(forwarded.body, { status: "Published" });
});


test("admin editor-journal inspection forwards filters and rejects write methods", async () => {
  const origin = process.env.APP_ORIGIN ?? "http://localhost:3000";
  let url;
  const handlers = loadModule("src/app/api/[...path]/route.ts", async (upstream) => { url = upstream; return Response.json({ items: [], total: 0 }); });
  const response = await handlers.GET(testRequest(`${origin}/api/admin/editor-journals?editor_id=2&date_from=2026-11-01&date_to=2026-11-20&limit=20&offset=0`), context("admin/editor-journals"));
  assert.equal(response.status, 200);
  assert.ok(url.includes("editor_id=2&date_from=2026-11-01&date_to=2026-11-20"));
  for (const method of ["PATCH", "DELETE", "POST"]) {
    const blocked = await handlers[method](testRequest(`${origin}/api/admin/editor-journals/1`, { method, headers: { origin } }), context("admin/editor-journals/1"));
    assert.equal(blocked.status, 405);
  }
});


test("admin ZIP export forwards bytes and download headers without JSON parsing", async () => {
  const bytes = new Uint8Array([80, 75, 3, 4, 0, 255, 128, 1]);
  const { GET } = loadModule("src/app/api/[...path]/route.ts", async () => new Response(bytes, { headers: { "content-type": "application/zip", "content-disposition": 'attachment; filename="journal-website.zip"' } }));
  const result = await GET(testRequest("http://localhost:3000/api/admin/editor-journals/1/export"), context("admin/editor-journals/1/export"));
  assert.equal(result.status, 200);
  assert.equal(result.headers.get("content-type"), "application/zip");
  assert.equal(result.headers.get("cache-control"), "no-store");
  assert.equal(result.headers.get("content-disposition"), 'attachment; filename="journal-website.zip"');
  assert.deepEqual(new Uint8Array(await result.arrayBuffer()), bytes);
});

test("admin ZIP export preserves permission and publication errors as JSON", async () => {
  for (const status of [401, 403, 409]) {
    const { GET } = loadModule("src/app/api/[...path]/route.ts", async () => Response.json({ detail: "Export denied" }, { status }));
    const result = await GET(testRequest("http://localhost:3000/api/admin/editor-journals/1/export"), context("admin/editor-journals/1/export"));
    assert.equal(result.status, status);
    assert.equal((await result.json()).detail, "Export denied");
  }
});


test("Current and Archives feed APIs validate editor/journal scope and support static-site CORS", async () => {
  for (const kind of ["current", "archives", "info"]) {
    let called;
    const module = loadModule("src/lib/journal-feed-proxy.ts", async (url, options) => {
      called = { url, options };
      return Response.json({ editor_code: "ab12cd34", journal_slug: "research", issue: null, items: [] });
    });
    const handler = module.journalFeedProxy(kind);
    let result = await handler(testRequest(`https://portal.example.com/api/journal/${kind}?editor_code=ab12cd34&journal_slug=research&limit=5&offset=10`, { headers: { origin: "null", authorization: "not-forwarded" } }));
    assert.equal(result.status, 200);
    assert.equal(result.headers.get("access-control-allow-origin"), "*");
    assert.equal(result.headers.get("cache-control"), "no-store");
    assert.ok(called.url.includes(`/api/v1/public/journals/ab12cd34/research/${kind}`));
    assert.equal(called.options.headers.Authorization, undefined);
    if (kind === "archives") assert.ok(called.url.includes("offset=10&limit=5"));
    result = await handler(testRequest(`https://portal.example.com/api/journal/${kind}?editor_code=invalid&journal_slug=research`));
    assert.equal(result.status, 422);
    result = await handler(testRequest(`https://portal.example.com/api/journal/${kind}?editor_code=ab12cd34`));
    assert.equal(result.status, 422);
    assert.equal(module.feedOptions().status, 204);
  }
});

test("feed APIs keep backend errors readable across origins", async () => {
  for (const status of [404, 422]) {
    const { journalFeedProxy } = loadModule("src/lib/journal-feed-proxy.ts", async () => Response.json({ detail: "Unavailable" }, { status }));
    const result = await journalFeedProxy("current")(testRequest("https://portal.example.com/api/journal/current?editor_code=ab12cd34&journal_slug=research"));
    assert.equal(result.status, status);
    assert.equal(result.headers.get("access-control-allow-origin"), "*");
  }
});


test("article upload and volume management use editor internal routes", async () => {
  const origin = process.env.APP_ORIGIN ?? "http://localhost:3000";
  for (const route of ["editor/articles", "editor/volumes"]) {
    let forwarded;
    const handlers = loadModule("src/app/api/[...path]/route.ts", async (url, options) => { forwarded = { url, body: options.body }; return Response.json({ id: 1 }, { status: 201 }); });
    const payload = route.endsWith("articles") ? { title: "Article", authors: ["A", "B"], pdf_base64: "A".repeat(30000) } : { title: "Volume", volume: "1", article_ids: [1, 2] };
    const response = await handlers.POST(testRequest(`${origin}/api/${route}?journal_id=7`, { method: "POST", headers: { origin, "content-type": "application/json" }, body: JSON.stringify(payload) }), context(route));
    assert.equal(response.status, 201);
    assert.ok(forwarded.url.endsWith(`${route}?journal_id=7`));
    assert.deepEqual(JSON.parse(forwarded.body), payload);
  }
});

test("private PDF downloads forward bytes with the editor session", async () => {
  const bytes = new TextEncoder().encode("%PDF-1.4\n%%EOF");
  let auth;
  const { GET } = loadModule("src/app/api/[...path]/route.ts", async (_url, options) => { auth = options.headers.Authorization; return new Response(bytes, { headers: { "content-type": "application/pdf" } }); });
  const result = await GET(testRequest("http://localhost:3000/api/editor/articles/1/pdf?journal_id=7", { headers: { cookie: "edora_session=test-session" } }), context("editor/articles/1/pdf"));
  assert.equal(result.status, 200);
  assert.equal(result.headers.get("content-type"), "application/pdf");
  assert.equal(auth, "Bearer test-session");
  assert.deepEqual(new Uint8Array(await result.arrayBuffer()), bytes);
});


test("article and volume filters default to all journals and preserve journal/date queries", async () => {
  const { publicationQuery } = loadModule("src/lib/publications.ts", async () => { throw new Error("Unexpected fetch"); });
  assert.equal(publicationQuery({ journal: "", from: "", to: "" }), "");
  assert.equal(publicationQuery({ journal: "3", from: "2026-11-01", to: "2026-11-20" }), "journal_id=3&date_from=2026-11-01&date_to=2026-11-20");
  for (const route of ["editor/articles", "editor/volumes"]) {
    let url;
    const { GET } = loadModule("src/app/api/[...path]/route.ts", async upstream => { url = upstream; return Response.json([]); });
    let response = await GET(testRequest(`http://localhost:3000/api/${route}`), context(route));
    assert.equal(response.status, 200);
    assert.ok(url.endsWith(`/api/v1/${route}`));
    response = await GET(testRequest(`http://localhost:3000/api/${route}?journal_id=3&date_from=2026-11-01&date_to=2026-11-20`), context(route));
    assert.equal(response.status, 200);
    assert.ok(url.endsWith("journal_id=3&date_from=2026-11-01&date_to=2026-11-20"));
  }
});

test("journal info updates use the internal proxy with the selected journal", async () => {
  const origin = process.env.APP_ORIGIN ?? "http://localhost:3000";
  let forwarded;
  const { PATCH } = loadModule("src/app/api/[...path]/route.ts", async (url, options) => {
    forwarded = { url, body: JSON.parse(options.body) };
    return Response.json({ id: 7, journal_info: { language: "English" } });
  });
  const response = await PATCH(testRequest(`${origin}/api/editor/journal/info?journal_id=7`, { method: "PATCH", headers: { origin, "content-type": "application/json" }, body: JSON.stringify({ language: "English" }) }), context("editor/journal/info"));
  assert.equal(response.status, 200);
  assert.ok(forwarded.url.endsWith("/api/v1/editor/journal/info?journal_id=7"));
  assert.deepEqual(forwarded.body, { language: "English" });
});

test("journal deletion uses the internal API and preserves a bodyless response", async () => {
  const origin = process.env.APP_ORIGIN ?? "http://localhost:3000";
  let forwarded;
  const { DELETE } = loadModule("src/app/api/[...path]/route.ts", async (url, options) => {
    forwarded = { url, method: options.method };
    return new Response(null, { status: 204 });
  });
  const response = await DELETE(testRequest(`${origin}/api/editor/journal?journal_id=7`, { method: "DELETE", headers: { origin } }), context("editor/journal"));
  assert.equal(response.status, 204);
  assert.equal(await response.text(), "");
  assert.ok(forwarded.url.endsWith("/api/v1/editor/journal?journal_id=7"));
  assert.equal(forwarded.method, "DELETE");
});

test("public submissions proxy scopes CAPTCHA and manuscript delivery without session credentials", async () => {
  let upstream;
  const { submissionProxy } = loadModule("src/lib/journal-submission-proxy.ts", async (url, options) => {
    upstream = { url, options };
    return Response.json({ reference: 12, message: "Submitted" }, { status: 201 });
  });
  const url = "https://portal.example.com/api/journal/submission?editor_code=ab12cd34&journal_slug=research";
  const data = { title: "Research", captcha_id: "challenge", captcha_answer: "ABC123" };
  const result = await submissionProxy()(testRequest(url, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(data) }));
  assert.equal(result.status, 201);
  assert.ok(upstream.url.endsWith("/api/v1/public/journals/ab12cd34/research/submission"));
  assert.equal(upstream.options.headers.Authorization, undefined);
  assert.deepEqual(JSON.parse(upstream.options.body), data);
  assert.equal(result.headers.get("access-control-allow-origin"), "*");
  await submissionProxy(true)(testRequest(url));
  assert.ok(upstream.url.endsWith("/submission/captcha"));
  const invalid = await submissionProxy(true)(testRequest("https://portal.example.com/api/journal/submission?editor_code=invalid&journal_slug=research"));
  assert.equal(invalid.status, 422);
});

test("dashboard mutations reject anonymous requests and bind the editor code to the session", async () => {
  const origin=process.env.APP_ORIGIN ?? "http://localhost:3000";
  let forwarded;
  const { PATCH }=loadModule("src/app/api/[...path]/route.ts",async (url,options)=> { forwarded={url,options}; return Response.json({id:7}); });
  const url=`${origin}/api/editor/journal/status?journal_id=7`;
  const body=JSON.stringify({status:"Published"});
  const anonymous=await PATCH(new NextRequest(url,{method:"PATCH",headers:{origin,"content-type":"application/json"},body}),context("editor/journal/status"));
  assert.equal(anonymous.status,401);
  const wrongCode=await PATCH(testRequest(url+"&editor_code=zzzzzzzz",{method:"PATCH",headers:{origin,"content-type":"application/json"},body}),context("editor/journal/status"));
  assert.equal(wrongCode.status,403);
  const wrongOrigin=await PATCH(testRequest(url,{method:"PATCH",headers:{origin:"https://untrusted.example","content-type":"application/json"},body}),context("editor/journal/status"));
  assert.equal(wrongOrigin.status,403);
  const valid=await PATCH(testRequest(url,{method:"PATCH",headers:{origin,"content-type":"application/json"},body}),context("editor/journal/status"));
  assert.equal(valid.status,200);
  assert.equal(forwarded.options.headers["X-Editor-Code"],"ab12cd34");
  assert.equal(forwarded.options.headers["X-Internal-API-Key"],"test-internal-key");
  assert.equal(forwarded.options.headers.Authorization,"Bearer test-session");
});
