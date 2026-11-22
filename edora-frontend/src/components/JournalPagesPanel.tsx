"use client";
import { FormEvent, useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { api } from "@/lib/api";
import type { Journal, JournalPage, PageChoice } from "@/lib/journals";
import type { NewJournalPage } from "@/components/JournalNewPageForm";
const RichTextEditor = dynamic(() => import("@/components/RichTextEditor"), { ssr: false, loading: () => <p role="status">Loading editor…</p> });
const JournalNewPageForm = dynamic(() => import("@/components/JournalNewPageForm"), { ssr: false, loading: () => <p role="status">Loading page form…</p> });
export default function JournalPagesPanel({ journal, onChanged }: { journal: Journal; onChanged: (journal: Journal) => void }) {
  const [library, setLibrary] = useState<PageChoice[]>([]);
  const [libraryLoading, setLibraryLoading] = useState(true);
  const [libraryError, setLibraryError] = useState("");
  useEffect(() => {
    let mounted = true;
    setLibraryLoading(true); setLibraryError("");
    api("editor/pages").then((pages: PageChoice[]) => { if (mounted) setLibrary(pages); })
      .catch((e: Error) => { if (mounted) setLibraryError(e.message); })
      .finally(() => { if (mounted) setLibraryLoading(false); });
    return () => { mounted = false; };
  }, [journal.id]);
  const availablePages = library.filter(page => !journal.pages.some(copy => copy.slug === page.slug));
  const readOnlySlugs = ["current", "archives", "archive", "submission", "submissions"];
  const systemPages = [{ title: "Current", slug: "current" }, { title: "Archives", slug: "archives" }, { title: "Submission", slug: "submission" }].filter(page => !journal.pages.some(item => item.slug === page.slug || (page.slug === "submission" && item.slug === "submissions")));
  const rows: (JournalPage | { id: string; title: string; slug: string; source_type?: "admin" | "editor"; is_active?: boolean })[] = [...journal.pages, ...systemPages.map(page => ({ ...page, id: page.slug }))];
  const savedOrder = journal.menu_order ?? [];
  const orderedSlugs = [...new Set([...savedOrder, ...rows.map(page => page.slug)])];
  rows.sort((a, b) => orderedSlugs.indexOf(a.slug) - orderedSlugs.indexOf(b.slug));
  const [adding, setAdding] = useState<NewJournalPage | null>(null);
  const [orderValues, setOrderValues] = useState<Record<string, string>>({});
  const [editing, setEditing] = useState<JournalPage | null>(null);
  const [initialHtml, setInitialHtml] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const orderDirty = rows.some((item, index) => (orderValues[item.id] ?? String(index + 1)) !== String(index + 1));
  async function removePage(page: JournalPage) {
    if (!window.confirm(`Permanently delete "${page.title}" from this journal? This cannot be undone.`)) return;
    setBusy(true); setError(""); setMessage("");
    try {
      onChanged(await api(`editor/journal/pages/${page.id}?journal_id=${journal.id}`, undefined, "DELETE"));
      setOrderValues({}); setMessage("Your page has been deleted.");
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  async function togglePage(page: JournalPage) {
    setBusy(true); setError(""); setMessage("");
    try {
      onChanged(await api(`editor/journal/pages/${page.id}/status?journal_id=${journal.id}`, { is_active: !page.is_active }, "PATCH"));
      setOrderValues({}); setMessage(page.is_active ? "Page deactivated. It is hidden from your journal website." : "Page activated. It is visible on your journal website.");
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  async function activateLibraryPage(page: PageChoice) {
    setBusy(true); setError(""); setMessage("");
    try {
      onChanged(await api(`editor/journal/pages/library/${page.id}?journal_id=${journal.id}`, {}));
      setOrderValues({}); setMessage("Admin page copied to your journal and activated.");
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  async function savePage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!editing) return;
    setBusy(true); setError(""); setMessage("");
    try { onChanged(await api(`editor/journal/pages/${editing.id}?journal_id=${journal.id}`, { title: editing.title, slug: editing.slug, content_html: editing.content_html }, "PATCH")); setEditing(null); setMessage("Your page copy has been saved."); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  async function saveOrder() {
    const ordered = rows.map((item, index) => ({ id: item.id, order: Number(orderValues[item.id] ?? index + 1) }));
    if (ordered.some(item => !Number.isInteger(item.order) || item.order < 1 || item.order > rows.length) || new Set(ordered.map(item => item.order)).size !== ordered.length) {
      setError(`Use each order number from 1 to ${rows.length} exactly once.`); return;
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
    {libraryError && <p className="message error" role="alert">Unable to load new admin pages: {libraryError}</p>}
    {message && <p className="message" role="status">{message}</p>}
    {!editing && <section className="admin-panel"><div className="template-card-heading"><h2>Journal pages</h2><button disabled={busy || !!editing || !!adding || orderDirty || journal.pages.length >= 100} onClick={() => { setError(""); setMessage(""); setAdding({ key: crypto.randomUUID(), title: "", slug: "", content_html: "<p></p>" }); }}>+ Add page</button></div><p className="template-help">Use each order number from 1 to {rows.length} once, then save. Activate new admin pages to add a personal copy. Delete your own pages or deactivate admin copies. Inactive pages stay here but are hidden from your website.</p><div className="table-scroll journal-pages-table"><table><thead><tr><th>Order</th><th>Page</th><th>Slug</th><th>Source</th><th>Status</th><th>Actions</th></tr></thead><tbody>{rows.map((item, index) => <tr key={item.id}><td><input className="journal-order-input" type="number" min={1} max={rows.length} step={1} aria-label={`Order for ${item.title}`} value={orderValues[item.id] ?? index + 1} disabled={busy || !!editing || !!adding} onChange={e => setOrderValues(current => ({ ...current, [item.id]: e.target.value }))} /></td><td>{item.title}</td><td>{item.slug}</td><td>{typeof item.id === "string" ? "Built-in" : item.source_type === "admin" ? "Admin copy" : "My page"}</td><td><span className={item.is_active === false ? "journal-page-inactive" : "admin-access-badge"}>{item.is_active === false ? "Inactive" : "Active"}</span></td><td><div className="admin-actions">{item.is_active !== false && <a className="button small secondary" href={`/${journal.editor_code}/${journal.slug}/${item.slug}`} target="_blank" rel="noopener noreferrer">Preview ↗</a>}{typeof item.id === "number" && !readOnlySlugs.includes(item.slug) && <button className="small" disabled={busy || !!editing || !!adding || orderDirty} onClick={() => { setEditing({ ...item } as JournalPage); setInitialHtml((item as JournalPage).content_html); setError(""); setMessage(""); }}>Edit my copy</button>}{typeof item.id === "number" && item.source_type === "editor" && <button type="button" className="small danger" disabled={busy || !!editing || !!adding || orderDirty} onClick={() => void removePage(item as JournalPage)}>Delete</button>}{typeof item.id === "number" && item.source_type === "admin" && <button type="button" role="switch" aria-checked={item.is_active !== false} aria-label={`Active status for ${item.title}`} className="journal-page-switch" disabled={busy || !!editing || !!adding || orderDirty} onClick={() => void togglePage(item as JournalPage)}><span aria-hidden="true" />{item.is_active === false ? "Inactive" : "Active"}</button>}</div></td></tr>)}{availablePages.map(page => <tr key={`library-${page.id}`}><td><span className="template-help">&mdash;</span></td><td>{page.title}{page.menu_group && <small className="template-help"> ? {page.menu_group}</small>}</td><td>{page.slug}</td><td>Admin library</td><td><span className="journal-page-inactive">Not added</span></td><td><button type="button" role="switch" aria-checked={false} aria-label={`Active status for ${page.title}`} className="journal-page-switch" disabled={busy || !!adding || orderDirty || journal.pages.length >= 100} onClick={() => void activateLibraryPage(page)}><span aria-hidden="true" />Inactive</button></td></tr>)}</tbody></table></div><div className="admin-actions"><button disabled={!orderDirty || busy || !!editing || !!adding} onClick={() => void saveOrder()}>{busy && orderDirty ? "Saving…" : "Save order"}</button><button className="secondary" disabled={!orderDirty || busy} onClick={() => { setOrderValues({}); setError(""); }}>Reset order</button></div>{libraryLoading && <p className="template-help" role="status">Checking for new admin pages...</p>}{journal.pages.length >= 100 && <p className="template-help">Your journal has reached the 100-page limit.</p>}
      {adding && <JournalNewPageForm key={adding.key} initial={adding} existingSlugs={journal.pages.map(item => item.slug)} busy={busy} saveLabel="Save page to my journal" description="This page will be saved only to your journal and will appear in its website menu. It will not be added to the admin page library." onSave={addPage} onCancel={() => setAdding(null)} />}
    </section>}
    {editing && <section className="admin-panel page-form-panel journal-page-editor"><h2>Edit my page copy</h2><form onSubmit={savePage}><fieldset className="template-fieldset" disabled={busy}><div className="fields"><label>Page title<input required maxLength={150} value={editing.title} onChange={e => setEditing({ ...editing, title: e.target.value })} /></label><label>URL slug<input required pattern="[a-z0-9]+(-[a-z0-9]+)*" maxLength={150} value={editing.slug} onChange={e => setEditing({ ...editing, slug: e.target.value })} /></label></div><RichTextEditor key={editing.id} initialContent={initialHtml} disabled={busy} onChange={html => setEditing(current => current && ({ ...current, content_html: html }))} /><div className="admin-actions template-save-actions"><button disabled={busy || editing.content_html.length > 100000}>{busy ? "Saving…" : "Save my page"}</button><button className="secondary" type="button" onClick={() => { if (window.confirm("Discard unsaved page changes?")) { setEditing(null); setError(""); setMessage(""); } }}>Cancel</button><span>{editing.content_html.length.toLocaleString()} / 100,000 HTML characters</span></div></fieldset></form></section>}
  </>;
}
