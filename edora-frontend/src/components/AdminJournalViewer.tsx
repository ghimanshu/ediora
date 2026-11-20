"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { journalPreviewDocument, type Journal } from "@/lib/journals";
import JournalStatusBadge from "@/components/JournalStatusBadge";
import TemplatePreview from "@/components/TemplatePreview";
type Inspection = Journal & { editor_id: number; editor_name: string; editor_email: string };
export default function AdminJournalViewer({ journalId }: { journalId: number }) {
  const [journal, setJournal] = useState<Inspection | null>(null);
  const [activePage, setActivePage] = useState(0);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let live = true;
    setLoading(true); setError("");
    api(`admin/editor-journals/${journalId}`).then(data => { if (live) { setJournal(data); setActivePage(data.pages[0]?.id ?? 0); } }).catch(e => { if (live) setError(e.message); }).finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
  }, [journalId]);
  if (loading) return <p role="status">Loading read-only journal…</p>;
  if (error) return <p className="message error" role="alert">{error}</p>;
  if (!journal) return null;
  const page = journal.pages.find(item => item.id === activePage) ?? journal.pages[0];
  return <><Link className="journal-back-link" href="/admin/editor-journals">← All Editor Journals</Link><div className="journal-manager-banner"><div className="journal-banner-info"><div className="journal-banner-title"><h2>{journal.name}</h2><JournalStatusBadge status={journal.status} /></div><p><span>{journal.editor_name}</span><span>{journal.editor_email}</span></p></div><span className="journal-private-badge">Read-only journal</span></div><section className="admin-panel"><div className="journal-panel-heading"><div><h2>Editor’s personal template</h2><p>{journal.template_name} · {journal.pages.length} journal pages</p></div><span className="admin-access-badge">View only</span></div><div className="journal-template-overview"><div><h3>{journal.template_name}</h3><p>{journal.template_description}</p><p className="journal-isolation-note">This is the editor’s independent template copy. Admin viewing does not change the template, pages, or journal status.</p></div><TemplatePreview layout={journal.template_layout} /></div></section>{page && <section className="admin-panel page-preview-panel admin-journal-viewer"><div className="journal-panel-heading"><div><h2>Journal website</h2><p>Read the saved pages using the editor’s template.</p></div><label>Viewing page<select value={page.id} onChange={e => setActivePage(Number(e.target.value))}>{journal.pages.map(item => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label></div><div className="admin-journal-page-links" role="group" aria-label="View journal pages">{journal.pages.map(item => <button className="small secondary" aria-pressed={item.id === page.id} key={item.id} onClick={() => setActivePage(item.id)}>{item.title}</button>)}</div><iframe title={`Read-only: ${journal.name} — ${page.title}`} sandbox="" referrerPolicy="no-referrer" srcDoc={journalPreviewDocument(journal, page)} /></section>}</>;
}
