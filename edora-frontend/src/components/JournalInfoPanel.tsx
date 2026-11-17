"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import JournalStatusBadge from "@/components/JournalStatusBadge";
import type { Journal, JournalStatus } from "@/lib/journals";
export default function JournalInfoPanel({ journal, onChanged }: { journal: Journal; onChanged: (journal: Journal) => void }) {
  const [status, setStatus] = useState<JournalStatus>(journal.status);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const date = (value: string) => new Date(value).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
  async function saveStatus() {
    setBusy(true); setError(""); setMessage("");
    try { const updated: Journal = await api(`editor/journal/status?journal_id=${journal.id}`, { status }, "PATCH"); onChanged(updated); setStatus(updated.status); setMessage("Journal status updated."); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  async function copyLink() {
    try { await navigator.clipboard.writeText(new URL(journal.preview_path, window.location.origin).href); setMessage("Preview link copied."); }
    catch { setMessage("Could not copy the link. Use Open website to view its address."); }
  }
  return <section className="admin-panel journal-info-panel"><div className="journal-panel-heading"><div><h2>Journal information</h2><p>Key details for your journal website.</p></div><span className="journal-private-badge">Your workspace</span></div>{error && <p className="message error" role="alert">{error}</p>}<div className="journal-status-control"><div><h3>Journal status</h3><p>Choose the status for this journal.</p><JournalStatusBadge status={journal.status} /></div><div className="admin-actions"><label>Status<select aria-label="Journal status" disabled={busy} value={status} onChange={event => setStatus(event.target.value as JournalStatus)}><option value="Draft">Draft</option><option value="Published">Published</option><option value="NotPublished">NotPublished</option></select></label><button disabled={busy || status === journal.status} onClick={() => void saveStatus()}>{busy ? "Saving…" : "Save status"}</button></div></div><dl className="journal-info-grid">{[["Journal name", journal.name], ["Website slug", journal.slug], ["Editor code", journal.editor_code], ["Personal template", journal.template_name], ["Journal pages", String(journal.pages.length)], ["Menu placement", journal.template_layout.menu_position], ["Created", date(journal.created_at)], ["Last updated", date(journal.updated_at)]].map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl><div className="journal-address-card"><div><span className="eyebrow">Website address</span><code>{journal.preview_path}</code></div><div className="admin-actions"><button type="button" className="small secondary" onClick={() => void copyLink()}>Copy link</button><a className="button small" href={journal.preview_path} target="_blank" rel="noopener noreferrer">Open website ↗</a></div></div>{message && <p className="template-help" role="status">{message}</p>}<p className="journal-isolation-note">Your template and pages are independent copies. Changes here apply only to your journal.</p></section>;
}
