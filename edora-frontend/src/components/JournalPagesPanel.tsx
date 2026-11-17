"use client";
import { FormEvent, useState } from "react";
import dynamic from "next/dynamic";
import { api } from "@/lib/api";
import type { Journal, JournalPage } from "@/lib/journals";
import type { NewJournalPage } from "@/components/JournalNewPageForm";
const RichTextEditor = dynamic(() => import("@/components/RichTextEditor"), { ssr: false, loading: () => <p role="status">Loading editor…</p> });
const JournalNewPageForm = dynamic(() => import("@/components/JournalNewPageForm"), { ssr: false, loading: () => <p role="status">Loading page form…</p> });
export default function JournalPagesPanel({ journal, onChanged }: { journal: Journal; onChanged: (journal: Journal) => void }) {
  const [adding, setAdding] = useState<NewJournalPage | null>(null);
  const [orderValues, setOrderValues] = useState<Record<number, string>>({});
  const [editing, setEditing] = useState<JournalPage | null>(null);
  const [initialHtml, setInitialHtml] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const orderDirty = journal.pages.some((item, index) => (orderValues[item.id] ?? String(index + 1)) !== String(index + 1));
  async function savePage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!editing) return;
    setBusy(true); setError(""); setMessage("");
    try { onChanged(await api(`editor/journal/pages/${editing.id}?journal_id=${journal.id}`, { title: editing.title, slug: editing.slug, content_html: editing.content_html }, "PATCH")); setEditing(null); setMessage("Your page copy has been saved."); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  async function saveOrder() {
    const ordered = journal.pages.map((item, index) => ({ id: item.id, order: Number(orderValues[item.id] ?? index + 1) }));
    if (ordered.some(item => !Number.isInteger(item.order) || item.order < 1 || item.order > journal.pages.length) || new Set(ordered.map(item => item.order)).size !== ordered.length) {
      setError(`Use each order number from 1 to ${journal.pages.length} exactly once.`); return;
    }
    setBusy(true); setError(""); setMessage("");
    try {
      const updated = await api(`editor/journal/pages/order?journal_id=${journal.id}`, { page_ids: ordered.sort((a, b) => a.order - b.order).map(item => item.id) }, "PATCH");
      onChanged(updated); setOrderValues({}); setMessage("Page order saved. Your website menu now uses this order.");
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  async function addPage(draft: NewJournalPage) {
    setBusy(true); setError(""); setMessage("");
    try {
      onChanged(await api(`editor/journal/pages?journal_id=${journal.id}`, { title: draft.title, slug: draft.slug, content_html: draft.content_html }));
      setAdding(null); setOrderValues({}); setMessage("Page added to your journal only.");
    } catch (e) { setError((e as Error).message); throw e; }
    finally { setBusy(false); }
  }
  return <>
    {error && <p className="message error" role="alert">{error}</p>}
    {message && <p className="message" role="status">{message}</p>}
    <section className="admin-panel"><div className="template-card-heading"><h2>Journal pages</h2><button disabled={busy || !!editing || !!adding || orderDirty || journal.pages.length >= 100} onClick={() => { setError(""); setMessage(""); setAdding({ key: crypto.randomUUID(), title: "", slug: "", content_html: "<p></p>" }); }}>+ Add page</button></div><p className="template-help">Use each order number from 1 to {journal.pages.length} once, then save. New pages are added only to your journal.</p><div className="table-scroll"><table><thead><tr><th>Order</th><th>Page</th><th>Slug</th><th>Actions</th></tr></thead><tbody>{journal.pages.map((item, index) => <tr key={item.id}><td><input className="journal-order-input" type="number" min={1} max={journal.pages.length} step={1} aria-label={`Order for ${item.title}`} value={orderValues[item.id] ?? index + 1} disabled={busy || !!editing || !!adding} onChange={e => setOrderValues(current => ({ ...current, [item.id]: e.target.value }))} /></td><td>{item.title}</td><td>{item.slug}</td><td><div className="admin-actions"><a className="button small secondary" href={`/${journal.editor_code}/${journal.slug}/${item.slug}`} target="_blank" rel="noopener noreferrer">Preview ↗</a><button className="small" disabled={busy || !!editing || !!adding || orderDirty} onClick={() => { setEditing({ ...item }); setInitialHtml(item.content_html); setError(""); setMessage(""); }}>Edit my copy</button></div></td></tr>)}</tbody></table></div><div className="admin-actions"><button disabled={!orderDirty || busy || !!editing || !!adding} onClick={() => void saveOrder()}>{busy && orderDirty ? "Saving…" : "Save order"}</button><button className="secondary" disabled={!orderDirty || busy} onClick={() => { setOrderValues({}); setError(""); }}>Reset order</button></div>{journal.pages.length >= 100 && <p className="template-help">Your journal has reached the 100-page limit.</p>}
      {adding && <JournalNewPageForm key={adding.key} initial={adding} existingSlugs={journal.pages.map(item => item.slug)} busy={busy} saveLabel="Save page to my journal" description="This page will be saved only to your journal and will appear in its website menu. It will not be added to the admin page library." onSave={addPage} onCancel={() => setAdding(null)} />}
    </section>
    {editing && <section className="admin-panel page-form-panel journal-page-editor"><h2>Edit my page copy</h2><form onSubmit={savePage}><fieldset className="template-fieldset" disabled={busy}><div className="fields"><label>Page title<input required maxLength={150} value={editing.title} onChange={e => setEditing({ ...editing, title: e.target.value })} /></label><label>URL slug<input required pattern="[a-z0-9]+(-[a-z0-9]+)*" maxLength={150} value={editing.slug} onChange={e => setEditing({ ...editing, slug: e.target.value })} /></label></div><RichTextEditor key={editing.id} initialContent={initialHtml} disabled={busy} onChange={html => setEditing(current => current && ({ ...current, content_html: html }))} /><div className="admin-actions template-save-actions"><button disabled={busy || editing.content_html.length > 100000}>{busy ? "Saving…" : "Save my page"}</button><button className="secondary" type="button" onClick={() => { if (window.confirm("Discard unsaved page changes?")) setEditing(null); }}>Cancel</button><span>{editing.content_html.length.toLocaleString()} / 100,000 HTML characters</span></div></fieldset></form></section>}
  </>;
}
