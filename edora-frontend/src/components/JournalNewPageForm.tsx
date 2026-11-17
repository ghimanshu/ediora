"use client";
import { FormEvent, useState } from "react";
import RichTextEditor from "@/components/RichTextEditor";
export type NewJournalPage = { key: string; title: string; slug: string; content_html: string };
export default function JournalNewPageForm({ initial, existingSlugs, onSave, onCancel, busy = false, saveLabel = "Add to journal draft", description = "This draft is added only to your journal and is saved to the database when you create the journal." }: { initial: NewJournalPage; existingSlugs: string[]; onSave: (page: NewJournalPage) => void | Promise<void>; onCancel: () => void; busy?: boolean; saveLabel?: string; description?: string }) {
  const [draft, setDraft] = useState(initial);
  const [customSlug, setCustomSlug] = useState(!!initial.slug);
  const [error, setError] = useState("");
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError("");
    if (!draft.title.trim()) { setError("Enter a page title."); return; }
    if (existingSlugs.includes(draft.slug)) { setError("This URL slug is already used by another page in your journal."); return; }
    const text = new DOMParser().parseFromString(draft.content_html, "text/html").body.textContent?.replace(/\u200b/g, "").trim();
    if (!text) { setError("Add some page content before saving."); return; }
    if (draft.content_html.length > 100000) { setError("Page HTML must not exceed 100,000 characters."); return; }
    try { await onSave({ ...draft, title: draft.title.trim() }); }
    catch (e) { setError((e as Error).message); }
  }
  return <section className="journal-new-page-form"><h3>{initial.title ? "Edit new page" : "Create a private page"}</h3><p className="template-help">{description}</p>{error && <p className="message error" role="alert">{error}</p>}<form onSubmit={save}><fieldset className="template-fieldset" disabled={busy}><div className="fields"><label>Page title<input autoFocus required maxLength={150} value={draft.title} onChange={e => { const title = e.target.value; const slug = title.toLowerCase().normalize("NFKD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 150).replace(/-$/, ""); setDraft({ ...draft, title, slug: customSlug ? draft.slug : slug }); }} /></label><label>URL slug<input required maxLength={150} pattern="[a-z0-9]+(-[a-z0-9]+)*" title="Use lowercase letters, numbers, and hyphens" value={draft.slug} onChange={e => { setCustomSlug(true); setDraft({ ...draft, slug: e.target.value }); }} /></label></div><RichTextEditor initialContent={initial.content_html} disabled={busy} onChange={html => setDraft(current => ({ ...current, content_html: html }))} /><div className="admin-actions template-save-actions"><button type="submit" disabled={busy}>{busy ? "Saving…" : saveLabel}</button><button type="button" className="secondary" onClick={() => { if (window.confirm("Discard unsaved page changes?")) onCancel(); }}>Cancel</button><span>{draft.content_html.length.toLocaleString()} / 100,000 HTML characters</span></div></fieldset></form></section>;
}
