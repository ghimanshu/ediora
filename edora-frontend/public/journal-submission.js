(function () {
  "use strict";
  function node(tag, text) { var el = document.createElement(tag); if (text) el.textContent = text; return el; }
  function mount(root, config) {
    if (root.dataset.submissionReady === "true") return;
    root.dataset.submissionReady = "true";
    var form = node("form"); form.className = "journal-submission-form";
    var intro = node("p", "Complete the details below and attach your manuscript as a PDF. Your submission will be sent to the journal editor.");
    var fields = node("fieldset"); var grid = node("div"); grid.className = "submission-fields";
    function field(name, title, type, max, wide) {
      var label = node("label", title); if (wide) label.className = "submission-wide";
      var input = node(type === "textarea" ? "textarea" : "input");
      input.name = name; input.required = true;
      if (type !== "textarea") input.type = type;
      else { input.rows = 4; input.minLength = 10; }
      if (max) input.maxLength = max;
      if (name === "full_name") input.autocomplete = "name";
      if (name === "email") input.autocomplete = "email";
      label.appendChild(input); grid.appendChild(label); return input;
    }
    field("full_name", "Full name", "text", 150);
    field("email", "Email address", "email", 254);
    field("title", "Article heading", "text", 300, true);
    field("authors", "Author names", "text", 2000, true);
    field("abstract", "Abstract / message", "textarea", 10000, true);
    var citation = field("how_to_cite", "How to Cite (optional)", "textarea", 2000, true); citation.required = false; citation.minLength = 0; citation.rows = 2;
    var pdf = field("pdf", "Manuscript PDF (maximum 10 MB)", "file", null, true); pdf.accept = ".pdf,application/pdf";
    fields.appendChild(grid);
    var captchaBox = node("div"); captchaBox.className = "submission-captcha";
    var image = node("img"); image.alt = "CAPTCHA code. Enter the characters shown, or request a new code."; image.width = 190; image.height = 55;
    var refresh = node("button", "New code"); refresh.type = "button"; refresh.className = "secondary small";
    var codeLabel = node("label", "Enter the verification code"); var answer = node("input"); answer.required = true; answer.maxLength = 12; answer.autocomplete = "off"; answer.spellcheck = false; answer.autocapitalize = "characters";
    codeLabel.appendChild(answer); captchaBox.appendChild(image); captchaBox.appendChild(refresh); captchaBox.appendChild(codeLabel); fields.appendChild(captchaBox);
    var send = node("button", "Submit manuscript"); send.type = "submit"; send.disabled = true;
    fields.appendChild(send); form.appendChild(intro); form.appendChild(fields);
    var status = node("p"); status.setAttribute("aria-live", "polite"); status.className = "submission-status"; form.appendChild(status); root.appendChild(form);
    var captchaId = ""; var busy = false;
    function endpoint(suffix) { var url = new URL("/api/journal/submission" + suffix, config.api_origin || location.origin); url.searchParams.set("editor_code", config.editor_code); url.searchParams.set("journal_slug", config.journal_slug); return url.href; }
    async function responseData(response) { var data; try { data = await response.json(); } catch (_) { throw new Error("The service returned an invalid response. Please try again."); } if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Check the form details and try again."); return data; }
    async function loadCaptcha() {
      captchaId = ""; send.disabled = true; refresh.disabled = true; answer.value = "";
      try {
        var data = await responseData(await fetch(endpoint("/captcha"), { credentials: "omit", cache: "no-store", signal: AbortSignal.timeout(20000) }));
        if (!/^data:image\/svg\+xml;base64,/.test(data.image)) throw new Error("Unable to load verification code.");
        image.src = data.image; captchaId = data.captcha_id; send.disabled = busy;
      } catch (error) { status.textContent = error.message; status.setAttribute("role", "alert"); }
      finally { refresh.disabled = false; }
    }
    refresh.addEventListener("click", function () { if (!busy) { status.textContent = ""; loadCaptcha(); } });
    form.addEventListener("submit", async function (event) {
      event.preventDefault(); if (busy || !captchaId) return;
      var file = pdf.files && pdf.files[0];
      if (!file || file.size > 10 * 1024 * 1024) { status.textContent = "Choose a PDF no larger than 10 MB."; status.setAttribute("role", "alert"); return; }
      busy = true; fields.disabled = true; send.textContent = "Submitting..."; status.textContent = "";
      try {
        var bytes = new Uint8Array(await file.arrayBuffer()); var parts = [];
        for (var i = 0; i < bytes.length; i += 32768) parts.push(String.fromCharCode.apply(null, bytes.subarray(i, i + 32768)));
        var payload = { full_name: form.elements.full_name.value, email: form.elements.email.value, title: form.elements.title.value, authors: form.elements.authors.value, abstract: form.elements.abstract.value, how_to_cite: form.elements.how_to_cite.value, pdf_base64: btoa(parts.join("")), captcha_id: captchaId, captcha_answer: answer.value };
        var data = await responseData(await fetch(endpoint(""), { method: "POST", credentials: "omit", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload), signal: AbortSignal.timeout(40000) }));
        form.reset(); status.setAttribute("role", "status"); status.textContent = data.message + " Reference: " + data.reference;
      } catch (error) { status.setAttribute("role", "alert"); status.textContent = error.message; }
      finally { busy = false; fields.disabled = false; send.textContent = "Submit manuscript"; await loadCaptcha(); }
    });
    loadCaptcha();
  }
  window.EdoraSubmission = { mount: mount };
  document.querySelectorAll("[data-journal-submission]").forEach(function (root) { mount(root, window.EDORA_JOURNAL || { api_origin: location.origin, editor_code: root.dataset.editorCode, journal_slug: root.dataset.journalSlug }); });
}());
