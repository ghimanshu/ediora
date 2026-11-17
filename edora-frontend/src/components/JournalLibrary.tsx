"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import JournalStatusBadge from "@/components/JournalStatusBadge";
import type { JournalStatus } from "@/lib/journals";
import { api } from "@/lib/api";
type JournalTile = { status: JournalStatus; id: number; name: string; slug: string; template_name: string; page_count: number; updated_at: string };
export default function JournalLibrary() {
  const [journals, setJournals] = useState<JournalTile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  async function load() {
    setLoading(true); setError("");
    try { setJournals(await api("editor/journals")); }
    catch (e) { setError((e as Error).message); }
    finally { setLoading(false); }
  }
  useEffect(() => { void load(); }, []);
  return <><div className="journal-library-toolbar"><span>{loading ? "Your journal collection" : `${journals.length} ${journals.length === 1 ? "journal" : "journals"}`}</span></div>{error && <div className="message error" role="alert">{error} <button className="small secondary" onClick={() => void load()}>Try again</button></div>}{loading ? <div className="admin-panel journal-section-loading" role="status">Loading journals…</div> : <div className="journal-library-grid">{journals.map(journal => <Link className="journal-library-tile" href={`/dashboard/journal/${journal.id}`} key={journal.id} aria-label={`Manage ${journal.name}`}><div className="journal-tile-top"><span className="journal-tile-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><rect x="4" y="2" width="16" height="20" rx="2" /><path d="M8 7h8M8 11h8M8 15h5" /></svg></span><JournalStatusBadge status={journal.status} /><span className="journal-tile-arrow" aria-hidden="true">↗</span></div><h2>{journal.name}</h2><p>{journal.template_name}</p><div className="journal-tile-meta"><span>{journal.page_count} {journal.page_count === 1 ? "page" : "pages"}</span><span>Updated {new Date(journal.updated_at).toLocaleDateString()}</span></div><div className="journal-tile-open">Manage journal <span aria-hidden="true">→</span></div></Link>)}</div>}{!loading && !error && journals.length === 0 && <div className="admin-panel admin-empty-state"><h2>Your journals belong here</h2><p>Create your first journal, then manage its template, pages, and preview from its tile.</p><Link className="button" href="/dashboard/journal/new">Create your first journal</Link></div>}</>;
}
