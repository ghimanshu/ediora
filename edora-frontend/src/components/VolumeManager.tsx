"use client";
import { type ReactNode, FormEvent, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { publicationQuery, type JournalChoice, type PublicationFilters, type ManagedArticle, type ManagedVolume } from "@/lib/publications";
type VolumeStatus = "Published" | "UnPublished" | "Archived";
type Draft = { status: VolumeStatus; journal_id: number; id?: number; title: string; volume: string; number: string; published_at: string; article_ids: number[] };
function localDateTime(value: string) {
  const date = new Date(value);
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
}
export default function VolumeManager({ journals, filters, statusFilter, filterPanel }: { journals: JournalChoice[]; filters: PublicationFilters; statusFilter: "" | VolumeStatus; filterPanel: ReactNode }) {
  const requestVersion = useRef(0);
  const activeFilters = useRef(filters);
  activeFilters.current = filters;
  const [volumes, setVolumes] = useState<ManagedVolume[]>([]);
  const [articles, setArticles] = useState<ManagedArticle[]>([]);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  async function load() {
    const version = ++requestVersion.current;
    setLoading(true);
    try { const query = publicationQuery(activeFilters.current); const [volumeList, articleList] = await Promise.all([api(`editor/volumes${query ? `?${query}` : ""}`), api("editor/articles")]); if (version === requestVersion.current) { setVolumes(volumeList); setArticles(articleList); } }
    catch (e) { if (version === requestVersion.current) setError((e as Error).message); }
    finally { if (version === requestVersion.current) setLoading(false); }
  }
  useEffect(() => { void load(); }, [filters]);
  function open(volume?: ManagedVolume) {
    if (draft && !window.confirm("Discard unsaved volume changes?")) return;
    setDraft(volume ? { status: volume.is_archived && volume.is_published ? "Archived" : volume.is_published ? "Published" : "UnPublished", journal_id: volume.journal_id, id: volume.id, title: volume.title, volume: volume.volume, number: volume.number, published_at: volume.published_at ? localDateTime(volume.published_at) : "", article_ids: [...volume.article_ids] } : { status: "UnPublished", journal_id: Number(filters.journal) || 0, title: "", volume: "", number: "", published_at: "", article_ids: [] });
    setError(""); setMessage("");
  }
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!draft) return;
    setBusy(true); setError(""); setMessage("");
    try {
      if (!draft.journal_id) throw new Error("Choose a journal for this volume");
      await api(`editor/volumes${draft.id ? `/${draft.id}` : ""}?journal_id=${draft.journal_id}`, { status: draft.status, title: draft.title, volume: draft.volume, number: draft.number, published_at: draft.status !== "UnPublished" && draft.published_at ? new Date(draft.published_at).toISOString() : null, article_ids: draft.article_ids }, draft.id ? "PATCH" : "POST");
      setDraft(null); setMessage("Volume saved."); await load();
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  async function remove(volume: ManagedVolume) {
    if (!window.confirm(`Delete "${volume.title}"? Articles and PDFs will remain and become unassigned.`)) return;
    setBusy(true); setError(""); setMessage("");
    try { await api(`editor/volumes/${volume.id}?journal_id=${volume.journal_id}`, undefined, "DELETE"); if (draft?.id === volume.id) setDraft(null); setMessage("Volume deleted. Its articles remain available."); await load(); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  const visibleVolumes = volumes.filter(volume => !statusFilter || (volume.is_published ? (volume.is_archived ? "Archived" : "Published") : "UnPublished") === statusFilter);
  return <><div className="admin-page-heading volume-workspace-heading"><div><span className="eyebrow">Journal publishing</span><h1>Manage volumes</h1><p>Group articles into volumes for your journal.</p></div><button disabled={busy || loading} onClick={() => open()}>+ New volume</button></div>{filterPanel}{error && <p className="message error" role="alert">{error}</p>}{message && <p className="message" role="status">{message}</p>}{draft && <section className="admin-panel publication-editor"><form onSubmit={save}><fieldset className="template-fieldset" disabled={busy}><div className="publication-status-row"><h2>{draft.id ? "Edit volume" : "New volume"}</h2><label>Volume status<select value={draft.status} onChange={e => setDraft({ ...draft, status: e.target.value as VolumeStatus })}><option value="Published">Published</option><option value="UnPublished">UnPublished</option><option value="Archived">Archived</option></select></label></div><div className="fields"><label className="wide">Journal<select required disabled={!!draft.id} value={draft.journal_id} onChange={e => setDraft({ ...draft, journal_id: Number(e.target.value), article_ids: [] })}><option value={0} disabled>Choose one journal</option>{journals.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select><small>A volume and its articles must belong to the same journal. The journal cannot change after creation.</small></label><label className="wide">Volume title<input required maxLength={200} value={draft.title} onChange={e => setDraft({ ...draft, title: e.target.value })} /></label><label>Volume number<input required maxLength={40} value={draft.volume} onChange={e => setDraft({ ...draft, volume: e.target.value })} /></label><label>Issue number (optional)<input maxLength={40} value={draft.number} onChange={e => setDraft({ ...draft, number: e.target.value })} /></label></div><label>Publication date and time (your local time, optional)<input type="datetime-local" disabled={draft.status === "UnPublished"} value={draft.published_at} onChange={e => setDraft({ ...draft, published_at: e.target.value })} /><small>Leave empty to publish now. Future dates schedule the volume; it stays hidden until that time.</small></label><h3>Articles in this volume</h3><p className="template-help">Each article can belong to one volume only. Remove it from its existing volume before assigning it here. Selection order sets article order.</p><div className="journal-page-choices">{articles.filter(article => article.journal_id === draft.journal_id).map(article => { const unavailable = article.volume_id !== null && article.volume_id !== draft.id; return <label className="journal-page-choice" key={article.id}><input type="checkbox" disabled={unavailable} checked={draft.article_ids.includes(article.id)} onChange={e => setDraft({ ...draft, article_ids: e.target.checked ? [...draft.article_ids, article.id] : draft.article_ids.filter(id => id !== article.id) })} /><span><strong>{article.title}</strong><small>{article.authors.join(", ")}{unavailable ? ` · Assigned to ${article.volume_title}` : article.is_published ? " · Published" : " · Draft"}</small></span>{draft.article_ids.includes(article.id) && <span className="admin-access-badge">{draft.article_ids.indexOf(article.id) + 1}</span>}</label>; })}</div>{!articles.some(article => article.journal_id === draft.journal_id) && <p>{draft.journal_id ? "No articles in this journal. Create articles from the Articles menu first." : "Choose a journal to see its articles."}</p>}<div className="admin-actions template-save-actions"><button disabled={busy}>{busy ? "Saving…" : "Save volume"}</button><button type="button" className="secondary" onClick={() => { if (window.confirm("Discard unsaved volume changes?")) setDraft(null); }}>Cancel</button><span>{draft.article_ids.length} articles selected</span></div></fieldset></form></section>}
    <section className="admin-panel"><div className="volume-list-summary" role="status">{loading ? "Loading volumes..." : `${visibleVolumes.length} of ${volumes.length} volumes`}</div>{loading ? <p role="status">Loading volumes…</p> : <><div className="table-scroll"><table><thead><tr><th>Volume</th><th>Journal</th><th>Created</th><th>Number</th><th>Articles</th><th>Status</th><th>Actions</th></tr></thead><tbody>{visibleVolumes.map(volume => <tr key={volume.id}><td>{volume.title}</td><td>{volume.journal_name}</td><td>{new Date(volume.created_at).toLocaleDateString(undefined, { timeZone: "UTC" })}</td><td>{volume.volume}{volume.number ? ` / ${volume.number}` : ""}</td><td>{volume.article_ids.length}</td><td>{volume.is_published ? (volume.is_archived ? "Archived" : "Published") : "UnPublished"}</td><td><div className="admin-actions"><button className="small" disabled={busy} onClick={() => open(volume)}>Edit / manage articles</button><button className="small danger" disabled={busy} onClick={() => void remove(volume)}>Delete</button></div></td></tr>)}</tbody></table></div>{!visibleVolumes.length && <p>{volumes.length ? "No volumes match the selected status." : "No volumes found for the selected filters."}</p>}</>}</section></>;
}
