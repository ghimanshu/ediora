(function () {
  "use strict";
  var config = window.EDORA_JOURNAL;
  var roots = document.querySelectorAll("[data-journal-info]");
  var contacts = document.querySelectorAll("[data-journal-editor-email]");
  if (!roots.length && !contacts.length) return;
  var fields = [["editor_in_chief", "EiC"], ["frequency", "Frequency"], ["final_decision", "Final decision"], ["acceptance_rate", "Acceptance rate"], ["plagiarism", "Plagiarism"], ["language", "Language"], ["review_process", "Review process"], ["open_access", "Open access"], ["copyright", "Copyright"], ["eissn", "eISSN"]];
  function node(tag, text) { var item = document.createElement(tag); item.textContent = text; return item; }
  function valid(data) { return data && data.editor_code === config.editor_code && data.journal_slug === config.journal_slug && data.journal_info && typeof data.journal_info === "object" && !Array.isArray(data.journal_info) && typeof data.editor_email === "string"; }
  function render(data) {
    roots.forEach(function (root) {
      var target = root.querySelector("[data-journal-info-fields]"); if (!target) return;
      var list = document.createElement("dl");
      fields.forEach(function (field) {
        var value = data.journal_info[field[0]];
        if (typeof value !== "string" || !value.trim()) return;
        var row = document.createElement("div"); row.appendChild(node("dt", field[1])); row.appendChild(node("dd", value)); list.appendChild(row);
      });
      target.replaceChildren(list.children.length ? list : node("p", "Journal details will appear here."));
    });
    contacts.forEach(function (link) { if (/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(data.editor_email)) { link.textContent = data.editor_email; link.href = "mailto:" + encodeURIComponent(data.editor_email); } });
  }
  var cached = null;
  var key;
  try {
    if (!config || !config.editor_code || !config.journal_slug) throw new Error("Missing configuration");
    var origin = new URL(config.api_origin);
    if (origin.protocol !== "https:" && origin.protocol !== "http:") throw new Error("Invalid API origin");
    key = "edora:journal-info:v1:" + origin.origin + ":" + config.editor_code + ":" + config.journal_slug;
    try {
      cached = JSON.parse(localStorage.getItem(key));
      if (!cached || !valid(cached.data) || !Number.isFinite(cached.saved_at) || cached.saved_at > Date.now()) cached = null;
    } catch (_) { cached = null; }
    if (cached && Date.now() - cached.saved_at < 5 * 60 * 1000) { render(cached.data); return; }
    var url = new URL("/api/journal/info", origin);
    url.searchParams.set("editor_code", config.editor_code); url.searchParams.set("journal_slug", config.journal_slug);
    fetch(url.href, { credentials: "omit", cache: "no-store", headers: { Accept: "application/json" }, signal: AbortSignal.timeout(20000) }).then(async function (response) {
      if (response.status === 404 || response.status === 403) {
        cached = null; try { localStorage.removeItem(key); } catch (_) {}
        roots.forEach(function (root) { var target = root.querySelector("[data-journal-info-fields]"); if (target) target.replaceChildren(node("p", "Journal information is currently unavailable.")); });
        contacts.forEach(function (link) { link.hidden = true; });
        return;
      }
      if (!response.ok) throw new Error("Journal info unavailable");
      var data = await response.json(); if (!valid(data)) throw new Error("Unexpected journal data");
      render(data);
      try { localStorage.setItem(key, JSON.stringify({ saved_at: Date.now(), data: data })); } catch (_) {}
    }).catch(function () {
      if (cached) render(cached.data);
      roots.forEach(function (root) { var target = root.querySelector("[data-journal-info-fields]"); if (target) { var note = node("p", "Showing last available details. Connect to the internet to refresh."); note.className = "journal-info-cache-note"; target.appendChild(note); } });
    });
  } catch (_) { /* Keep the exported snapshot if storage or configuration is unavailable. */ }
}());
