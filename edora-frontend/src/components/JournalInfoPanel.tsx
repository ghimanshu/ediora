"use client";
import { type FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { JournalInfo, Journal } from "@/lib/journals";
const infoFields = [["editor_in_chief", "EiC", "Narjess ALOUI"], ["frequency", "Frequency", "Four iss./ year"], ["final_decision", "Final decision", "75 days"], ["acceptance_rate", "Acceptance rate", "15%"], ["plagiarism", "Plagiarism", "<10%"], ["language", "Language", "English"], ["review_process", "Review process", "Single-blind"], ["open_access", "Open access", "Yes"], ["copyright", "Copyright", "CC-BY 4.0"], ["eissn", "eISSN", "2323-5233"]] as const;
export default function JournalInfoPanel({ journal, onChanged }: { journal: Journal; onChanged: (journal: Journal) => void }) {
  const router = useRouter();
  const [info, setInfo] = useState<JournalInfo>(journal.journal_info);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => { setInfo(journal.journal_info); }, [journal.id, journal.journal_info]);
  async function saveInfo(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError(""); setMessage("");
    try {
      const updated = await api(`editor/journal/info?journal_id=${journal.id}`, info, "PATCH");
      onChanged(updated); setMessage("Journal information saved.");
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  async function deleteJournal() {
    if (!window.confirm(`Permanently delete "${journal.name}"? This deletes its pages, personal template, volumes, articles and PDFs. This cannot be undone.`)) return;
    setBusy(true); setError(""); setMessage("");
    try {
      await api(`editor/journal?journal_id=${journal.id}`, undefined, "DELETE");
      router.replace("/dashboard/journal"); router.refresh();
    } catch (e) { setError((e as Error).message); setBusy(false); }
  }
  const [message, setMessage] = useState("");
  const date = (value: string) => new Date(value).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
  async function copyLink() {
    try { await navigator.clipboard.writeText(new URL(journal.preview_path, window.location.origin).href); setMessage("Preview link copied."); }
    catch { setMessage("Could not copy the link. Use Open website to view its address."); }
  }
  return <section className="admin-panel journal-info-panel"><div className="journal-panel-heading"><div><h2>Journal information</h2><p>Key details for your journal website.</p></div><span className="journal-private-badge">Your workspace</span></div><dl className="journal-info-grid">{[["Journal name", journal.name], ["Website slug", journal.slug], ["Editor code", journal.editor_code], ["Personal template", journal.template_name], ["Journal pages", String(journal.pages.length)], ["Menu placement", journal.template_layout.menu_position], ["Created", date(journal.created_at)], ["Last updated", date(journal.updated_at)]].map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl><form onSubmit={saveInfo} className="journal-metadata-form"><h2>Editorial &amp; publishing details</h2><p className="template-help">Set these details for this journal. All fields are optional.</p><fieldset className="template-fieldset" disabled={busy}><div className="fields">{infoFields.map(([key, label, example]) => <label key={key}>{label}<input maxLength={150} value={info?.[key] ?? ""} placeholder={example} onChange={event => setInfo(current => ({ ...current, [key]: event.target.value }))} /></label>)}</div><div className="admin-actions"><button disabled={busy}>{busy ? "Saving..." : "Save journal information"}</button></div></fieldset>{error && <p className="message error" role="alert">{error}</p>}</form><div className="journal-address-card"><div><span className="eyebrow">Website address</span><code>{journal.preview_path}</code></div><div className="admin-actions"><button type="button" className="small secondary" onClick={() => void copyLink()}>Copy link</button><a className="button small" href={journal.preview_path} target="_blank" rel="noopener noreferrer">Open website ↗</a></div></div>{message && <p className="template-help" role="status">{message}</p>}<p className="journal-isolation-note">Your template and pages are independent copies. Changes here apply only to your journal.</p><div className="journal-delete-section"><div><h3>Delete journal</h3><p>Permanently remove this journal and all its pages, volumes, articles and PDFs.</p></div><button type="button" className="small danger" disabled={busy} onClick={() => void deleteJournal()}>Delete journal</button></div></section>;
}
