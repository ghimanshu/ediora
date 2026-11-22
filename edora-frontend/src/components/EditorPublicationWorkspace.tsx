"use client";
import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import { api } from "@/lib/api";
const ArticleManager = dynamic(() => import("@/components/ArticleManager"), { loading: () => <p role="status">Loading articles…</p> });
const VolumeManager = dynamic(() => import("@/components/VolumeManager"), { loading: () => <p role="status">Loading volumes…</p> });
import type { JournalChoice, PublicationFilters, ArticleStatus } from "@/lib/publications";
export default function EditorPublicationWorkspace({ mode }: { mode: "articles" | "volumes" }) {
  const [journals, setJournals] = useState<JournalChoice[]>([]);
  const [search, setSearch] = useState("");
  const [articleStatus, setArticleStatus] = useState<"" | ArticleStatus>("");
  const [status, setStatus] = useState<"" | "Published" | "UnPublished" | "Archived">("");
  const [journal, setJournal] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [filters, setFilters] = useState<PublicationFilters>({ journal: "", from: "", to: "" });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    let live = true;
    api("editor/journals").then(items => { if (live) { setJournals(items); } }).catch(e => { if (live) setError(e.message); }).finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
  }, []);
  function apply(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (from && to && from > to) { setError("Created from must not be later than created to."); return; }
    setError(""); setFilters({ journal, from, to });
  }
  function clear() { setArticleStatus(""); setSearch(""); setStatus(""); setJournal(""); setFrom(""); setTo(""); setError(""); setFilters({ journal: "", from: "", to: "" }); }
  if (loading) return <p role="status">Loading journals…</p>;
  if (error && !journals.length) return <p className="message error" role="alert">{error}</p>;
  if (!journals.length) return <div className="admin-panel admin-empty-state"><h2>Create a journal first</h2><p>Articles and volumes belong to a journal.</p><Link className="button" href="/dashboard/journal/new">Create journal</Link></div>;
  const filterPanel = <section className={`admin-panel publication-filters volume-workspace-filters ${mode === "articles" ? "article-workspace-filters" : "volume-only-filters"}`}><form onSubmit={apply}>{mode === "articles" && <label>Search articles<input type="search" value={search} onChange={e => setSearch(e.target.value)} placeholder="Heading, journal, author or volume" /></label>}{mode === "articles" && <label>Filter by status<select value={articleStatus} onChange={e => setArticleStatus(e.target.value as "" | ArticleStatus)}><option value="">All statuses</option><option value="Submitted">Submitted</option><option value="Published">Published</option><option value="UnPublished">UnPublished</option></select></label>}{mode === "volumes" && <label>Filter by status<select value={status} onChange={e => setStatus(e.target.value as typeof status)}><option value="">All statuses</option><option value="Published">Published</option><option value="UnPublished">UnPublished</option><option value="Archived">Archived</option></select></label>}<label>Filter by journal<select value={journal} onChange={e => setJournal(e.target.value)}><option value="">All journals</option>{journals.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label>Created from (UTC)<input type="date" value={from} max={to || undefined} onChange={e => setFrom(e.target.value)} /></label><label>Created to (UTC)<input type="date" value={to} min={from || undefined} onChange={e => setTo(e.target.value)} /></label><div className="admin-actions"><button>Apply</button><button type="button" className="secondary" onClick={clear}>Clear</button></div></form></section>;
  return <>{error && <p className="message error" role="alert">{error}</p>}{mode === "articles" ? <ArticleManager journals={journals} filters={filters} search={search} statusFilter={articleStatus} filterPanel={filterPanel} /> : <VolumeManager journals={journals} filters={filters} statusFilter={status} filterPanel={filterPanel} />}</>;
}
