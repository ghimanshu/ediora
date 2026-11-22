"use client";
import { FormEvent, useEffect, useState } from "react";
import { api } from "@/lib/api";
import RichTextEditor from "@/components/RichTextEditor";
type PageSummary = { menu_group: "" | "Ethics" | "For Authors"; id: number; title: string; slug: string; created_at: string; updated_at: string };
type PageRecord = PageSummary & { content_html: string };
type PageDraft = Pick<PageRecord, "title" | "slug" | "content_html" | "menu_group">;
function slugify(title: string) { return title.toLowerCase().normalize("NFKD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 150).replace(/-$/, ""); }
export default function PageManagement() {
  const [pages, setPages] = useState<PageSummary[]>([]);
  const [draft, setDraft] = useState<PageDraft | null>(null);
  const [initialHtml, setInitialHtml] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editorKey, setEditorKey] = useState(0);
  const [customSlug, setCustomSlug] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [menuFilter, setMenuFilter] = useState<string>("all");
  const [search, setSearch] = useState("");
  const [preview, setPreview] = useState<PageRecord | null>(null);
  async function load() {
    setLoading(true); setError("");
    try { setPages(await api("admin/pages")); }
    catch (e) { setError((e as Error).message); }
    finally { setLoading(false); }
  }
  useEffect(() => { void load(); }, []);
  function mayDiscard() { return !draft || window.confirm("Discard unsaved page changes?"); }
  async function open(page?: PageSummary, previewOnly = false) {
    if (!previewOnly && !mayDiscard()) return;
    setBusy(true); setError(""); setMessage("");
    try {
      const record: PageRecord | null = page ? await api(`admin/pages/${page.id}`) : null;
      if (previewOnly && record) { setPreview(record); return; }
      setDraft(record ? { menu_group: record.menu_group, title: record.title, slug: record.slug, content_html: record.content_html } : { menu_group: "", title: "", slug: "", content_html: "<p></p>" });
      setInitialHtml(record?.content_html ?? "<p></p>"); setEditingId(record?.id ?? null); setCustomSlug(!!record); setEditorKey(key => key + 1); setPreview(null);
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!draft) return;
    setBusy(true); setError(""); setMessage("");
    try {
      const saved: PageRecord = await api(editingId ? `admin/pages/${editingId}` : "admin/pages", draft, editingId ? "PATCH" : "POST");
      setPages(current => editingId ? current.map(page => page.id === saved.id ? saved : page) : [saved, ...current]);
      setDraft(null); setEditingId(null); setPreview(null); setMessage("Page saved successfully.");
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  async function remove(page: PageSummary) {
    if (!window.confirm(`Permanently delete "${page.title}"? This cannot be undone.${editingId === page.id ? " Unsaved edits will be discarded." : ""}`)) return;
    setBusy(true); setError(""); setMessage("");
    try {
      await api(`admin/pages/${page.id}`, undefined, "DELETE");
      setPages(current => current.filter(item => item.id !== page.id));
      if (editingId === page.id) { setDraft(null); setEditingId(null); }
      if (preview?.id === page.id) setPreview(null);
      setMessage("Page deleted.");
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  const filtered = pages.filter(page => (menuFilter === "all" || page.menu_group === menuFilter) && `${page.title} ${page.slug}`.toLowerCase().includes(search.toLowerCase()));
  return <>
    <div className="template-library-toolbar"><span>{pages.length} saved pages</span><div className="admin-actions"><button className="secondary" disabled={busy || loading || !!draft} onClick={() => void load()}>Refresh</button><button disabled={busy || loading} onClick={() => void open()}>+ Add page</button></div></div>
    {error && <p className="message error" role="alert">{error}</p>}{message && <p className="message" role="status">{message}</p>}
    {draft && <section className="admin-panel page-form-panel"><h2>{editingId ? "Edit page" : "Add page"}</h2><form onSubmit={save}><fieldset className="template-fieldset" disabled={busy}><div className="fields"><label>Page title<input autoFocus required maxLength={150} value={draft.title} onChange={e => { const title = e.target.value; setDraft({ ...draft, title, slug: customSlug ? draft.slug : slugify(title) }); }} /></label><label>URL slug<input required maxLength={150} pattern="[a-z0-9]+(-[a-z0-9]+)*" title="Use lowercase letters, numbers, and hyphens" value={draft.slug} onChange={e => { setCustomSlug(true); setDraft({ ...draft, slug: e.target.value }); }} /><small>For example: about-us</small></label></div><label>Menu item<select value={draft.menu_group} onChange={e => setDraft({ ...draft, menu_group: e.target.value as PageDraft["menu_group"] })}><option value="">Main menu</option><option value="Ethics">Ethics</option><option value="For Authors">For Authors</option></select></label><label className="page-content-label">Page content</label><RichTextEditor key={editorKey} initialContent={initialHtml} disabled={busy} onChange={html => setDraft(current => current && ({ ...current, content_html: html }))} /><p className="template-help page-content-help">Supports headings, paragraphs, lists, quotes, code, and links. Scripts, embeds, and unsupported HTML are removed when saved.</p><details className="page-html-source"><summary>View generated HTML</summary><textarea aria-label="Generated page HTML" readOnly value={draft.content_html} rows={6} /></details><div className="admin-actions template-save-actions"><button disabled={busy || draft.content_html.length > 100000}>{busy ? "Saving…" : "Save page"}</button><button type="button" className="secondary" onClick={() => { if (mayDiscard()) { setDraft(null); setEditingId(null); } }}>Cancel</button><span>{draft.content_html.length.toLocaleString()} / 100,000 HTML characters</span></div></fieldset></form></section>}
    {preview && <section className="admin-panel page-preview-panel"><div className="template-card-heading"><h2>{preview.title}</h2><button className="small secondary" onClick={() => setPreview(null)}>Close preview</button></div><iframe title={`Preview: ${preview.title}`} sandbox="" referrerPolicy="no-referrer" srcDoc={`<!doctype html><html><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'"><style>body{font:14px/1.7 system-ui;color:#243b36;padding:20px;overflow-wrap:anywhere}pre{white-space:pre-wrap;background:#f4f6f5;padding:12px}blockquote{border-left:3px solid #8bac99;padding-left:16px}a{color:#276749}</style></head><body>${preview.content_html}</body></html>`} /></section>}
    <section className="admin-panel"><div className="page-menu-tabs" role="group" aria-label="Filter by menu item">{[["all", "All pages"], ["", "Main menu"], ["Ethics", "Ethics"], ["For Authors", "For Authors"]].map(([value, label]) => <button type="button" key={value} className="small secondary" aria-pressed={menuFilter === value} onClick={() => setMenuFilter(value)}>{label}</button>)}</div><label className="page-search">Search pages<input type="search" value={search} maxLength={150} placeholder="Title or URL slug" onChange={e => setSearch(e.target.value)} /></label>{loading ? <p role="status">Loading pages…</p> : <><div className="table-scroll"><table><thead><tr><th>Page title</th><th>URL slug</th><th>Menu item</th><th>Updated</th><th>Actions</th></tr></thead><tbody>{filtered.map(page => <tr key={page.id}><td>{page.title}</td><td><code>{page.slug}</code></td><td>{page.menu_group || "Main menu"}</td><td>{new Date(page.updated_at).toLocaleDateString()}</td><td><div className="admin-actions"><button className="small secondary" disabled={busy} onClick={() => void open(page, true)}>Preview</button><button className="small" disabled={busy} onClick={() => void open(page)}>Edit</button><button className="small danger" disabled={busy} aria-label={`Delete page ${page.title}`} onClick={() => void remove(page)}>Delete</button></div></td></tr>)}</tbody></table></div>{!filtered.length && <p>{search ? "No matching pages." : "No pages yet. Add your first web page."}</p>}</>}</section>
  </>;
}
