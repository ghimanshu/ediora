"use client";
import { FormEvent, useState } from "react";
import { api } from "@/lib/api";
import type { Journal, JournalStatus } from "@/lib/journals";
export default function JournalStatusControl({ journal, onChanged }: { journal: Journal; onChanged: (journal: Journal) => void }) {
  const [status, setStatus] = useState<JournalStatus>(journal.status);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError(""); setMessage("");
    try { const updated: Journal = await api(`editor/journal/status?journal_id=${journal.id}`, { status }, "PATCH"); onChanged(updated); setStatus(updated.status); setMessage("Status updated."); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  return <div className="journal-banner-status"><form onSubmit={save}><label><span className="journal-status-label">Journal status</span><select aria-label="Journal status" disabled={busy} value={status} onChange={event => { setStatus(event.target.value as JournalStatus); setMessage(""); }}><option value="Draft">Draft</option><option value="Published">Published</option><option value="NotPublished">NotPublished</option></select></label><button type="submit" className="journal-status-save-icon" aria-label={busy ? "Saving journal status" : "Save journal status"} title={busy ? "Saving status…" : "Save status"} aria-busy={busy} disabled={busy || status === journal.status}><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h12l4 4v12a2 2 0 0 1-2 2Z" /><path d="M17 21v-8H7v8M7 3v5h9V3" /></svg></button></form>{error && <span className="journal-status-feedback error" role="alert">{error}</span>}{message && <span className="journal-status-feedback" role="status">{message}</span>}</div>;
}
