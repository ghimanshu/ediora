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
  function renderIssue(issue, index, kind) {
    var section = element("section");
    section.className = "journal-feed-issue";
    var articles = Array.isArray(issue.articles) ? issue.articles : [];
    var header = element("div");
    header.className = "journal-page-heading";
    header.appendChild(element(index === 0 ? "h1" : "h2", index === 0 ? (kind === "current" ? "Current" : "Archives") : "Volume"));
    var info = element("div");
    info.className = "journal-volume-inline";
    info.setAttribute("aria-label", "Volume information");
    info.appendChild(element("strong", issue.title));
    var details = [];
    if (issue.volume) details.push("Vol. " + issue.volume);
    if (issue.number) details.push("No. " + issue.number);
    info.appendChild(element("span", details.join(" ")));
    var date = element("time", new Date(issue.published_at).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric", timeZone: "UTC" }));
    date.setAttribute("datetime", issue.published_at);
    info.appendChild(date);
    header.appendChild(info);
    section.appendChild(header);
    var articleHeader = element("div");
    articleHeader.className = "journal-list-header";
    var heading = element("h2", "Articles ");
    heading.appendChild(element("span", "(" + articles.length + ")"));
    articleHeader.appendChild(heading);
    section.appendChild(articleHeader);
    if (!articles.length) section.appendChild(element("p", "No published articles in this volume yet."));
    articles.forEach(function (article) {
      var item = element("article");
      item.className = "journal-feed-article journal-article-row";
      var info = element("div");
      info.appendChild(element("h4", article.title));
      var authors = element("p", Array.isArray(article.authors) ? article.authors.join(", ") : "");
      authors.className = "journal-article-authors";
      info.appendChild(authors);
      if (article.how_to_cite) {
        var citation = element("details"); citation.className = "article-citation";
        citation.appendChild(element("summary", "How to Cite"));
        citation.appendChild(element("p", article.how_to_cite));
        info.appendChild(citation);
      }
      item.appendChild(info);
      var url = safeLink(article.article_url);
      if (url) {
        var link = element("a", "PDF");
        var icon = document.createElementNS("http://www.w3.org/2000/svg", "svg");
        var attributes = { width: "16", height: "16", viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", "stroke-width": "1.8", "stroke-linecap": "round", "stroke-linejoin": "round", "aria-hidden": "true" };
        Object.keys(attributes).forEach(function (key) { icon.setAttribute(key, attributes[key]); });
        var path = document.createElementNS("http://www.w3.org/2000/svg", "path");
        path.setAttribute("d", "M15 3h6v6M10 14 21 3M21 14v5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5");
        icon.appendChild(path);
        link.appendChild(icon);
        link.className = "journal-pdf-link";
        link.href = url;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.setAttribute("aria-label", "View PDF: " + article.title + " (opens in a new tab)");
        item.appendChild(link);
      }
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
        if (!issues.length) results.appendChild(element("h1", kind === "current" ? "Current" : "Archives"));
        issues.forEach(function (issue, index) { results.appendChild(renderIssue(issue, index, kind)); });
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
