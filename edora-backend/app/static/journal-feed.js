(function () {
  "use strict";
  var config = window.EDORA_JOURNAL;
  var roots = document.querySelectorAll("[data-journal-feed]");
  function element(tag, text) {
    var node = document.createElement(tag);
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }
  function safeLink(value) {
    try {
      var url = new URL(value);
      return (url.protocol === "https:" || url.protocol === "http:") && !url.username && !url.password ? url.href : null;
    } catch (_) { return null; }
  }
  function renderIssue(issue) {
    var section = element("section");
    section.className = "journal-feed-issue";
    section.appendChild(element("h3", issue.title));
    var details = [];
    if (issue.volume) details.push("Volume " + issue.volume);
    if (issue.number) details.push("Issue " + issue.number);
    if (issue.published_at) details.push(new Date(issue.published_at).toLocaleDateString());
    section.appendChild(element("p", details.join(" · ")));
    var articles = Array.isArray(issue.articles) ? issue.articles : [];
    if (!articles.length) section.appendChild(element("p", "No published articles in this issue yet."));
    articles.forEach(function (article) {
      var item = element("article");
      item.className = "journal-feed-article";
      var heading = element("h4");
      var url = safeLink(article.article_url);
      if (url) {
        var link = element("a", article.title);
        link.href = url;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        heading.appendChild(link);
      } else heading.textContent = article.title || "Untitled article";
      item.appendChild(heading);
      if (Array.isArray(article.authors) && article.authors.length) item.appendChild(element("p", article.authors.join(", ")));
      if (article.abstract) item.appendChild(element("p", article.abstract));
      section.appendChild(item);
    });
    return section;
  }
  Array.prototype.forEach.call(roots, function (root) {
    var kind = root.getAttribute("data-journal-feed");
    if (kind !== "current" && kind !== "archives") return;
    var status = element("p", "Loading published journal data…");
    status.setAttribute("role", "status");
    var results = element("div");
    var controls = element("div");
    controls.className = "journal-feed-controls";
    var retry = element("button", "Retry");
    var previous = element("button", "Previous issues");
    var next = element("button", "Next issues");
    [retry, previous, next].forEach(function (button) { button.type = "button"; button.hidden = true; controls.appendChild(button); });
    root.appendChild(status); root.appendChild(results); root.appendChild(controls);
    var offset = 0;
    var limit = 10;
    async function load() {
      retry.hidden = true; previous.hidden = true; next.hidden = true;
      status.textContent = "Loading published journal data…";
      status.setAttribute("role", "status");
      results.replaceChildren();
      try {
        if (!config || !config.api_origin || !config.editor_code || !config.journal_slug) throw new Error("Missing journal configuration");
        var base = new URL(config.api_origin);
        if (base.protocol !== "http:" && base.protocol !== "https:") throw new Error("Invalid API origin");
        var url = new URL("/api/journal/" + kind, base);
        url.searchParams.set("editor_code", config.editor_code);
        url.searchParams.set("journal_slug", config.journal_slug);
        if (kind === "archives") { url.searchParams.set("offset", String(offset)); url.searchParams.set("limit", String(limit)); }
        var response = await fetch(url.href, { credentials: "omit", cache: "no-store", headers: { Accept: "application/json" }, signal: AbortSignal.timeout(20000) });
        var data = await response.json();
        if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Feed unavailable");
        if (data.editor_code !== config.editor_code || data.journal_slug !== config.journal_slug) throw new Error("The API returned data for another journal");
        var issues = kind === "current" ? (data.issue ? [data.issue] : []) : data.items;
        if (!Array.isArray(issues)) throw new Error("Invalid issue data");
        issues.forEach(function (issue) { results.appendChild(renderIssue(issue)); });
        status.textContent = issues.length ? (kind === "current" ? "Current published issue" : "Showing " + issues.length + " of " + data.total + " archived issues") : (kind === "current" ? "No current issue has been published yet." : "No archived issues have been published yet.");
        if (kind === "archives") { previous.hidden = offset === 0; next.hidden = offset + limit >= data.total; }
      } catch (error) {
        status.setAttribute("role", "alert");
        status.textContent = "Could not load journal data. Check your internet connection and the API origin in assets/journal-config.js. " + error.message;
        retry.hidden = false;
      }
    }
    retry.addEventListener("click", load);
    previous.addEventListener("click", function () { offset = Math.max(0, offset - limit); load(); });
    next.addEventListener("click", function () { offset += limit; load(); });
    load();
  });
}());
