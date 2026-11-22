"use client";
import { type ReactNode, FormEvent, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { api } from "@/lib/api";
import { pdfBase64, publicationQuery, type JournalChoice, type PublicationFilters, type ManagedArticle, type ArticleStatus, type ManagedVolume } from "@/lib/publications";
type Draft = { how_to_cite: string; volume_id: number | null; journal_id: number; id?: number; title: string; authors: string; abstract: string; status: ArticleStatus; has_pdf: boolean };
function ArticleActionIcon({ action }: { action: "view" | "download" | "edit" | "delete" }) {
  return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{action === "view" ? <><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z" /><circle cx="12" cy="12" r="3" /></> : action === "download" ? <><path d="M12 3v12m-5-5 5 5 5-5M4 16v4h16v-4" /></> : action === "edit" ? <><path d="m16 3 5 5-12 12-6 1 1-6L16 3Zm-2 2 5 5" /></> : <><path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7m4-7v7" /></>}</svg>;
}
export default function ArticleManager({ journals, filters, search, statusFilter, filterPanel }: { journals: JournalChoice[]; filters: PublicationFilters; search: string; statusFilter: "" | ArticleStatus; filterPanel: ReactNode }) {
  const [topbarActions, setTopbarActions] = useState<HTMLElement | null>(null);
  useEffect(() => { setTopbarActions(document.getElementById("article-topbar-actions")); }, []);
  const requestVersion = useRef(0);
  const activeFilters = useRef(filters);
  activeFilters.current = filters;
  const [formVersion, setFormVersion] = useState(0);
  const [articles, setArticles] = useState<ManagedArticle[]>([]);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [volumes, setVolumes] = useState<ManagedVolume[]>([]);
  const [volumesLoading, setVolumesLoading] = useState(false);
  const [volumeError, setVolumeError] = useState("");
  const [volumeRetry, setVolumeRetry] = useState(0);
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  async function load() {
    const version = ++requestVersion.current;
    setLoading(true);
    try { const query = publicationQuery(activeFilters.current); const items = await api(`editor/articles${query ? `?${query}` : ""}`); if (version === requestVersion.current) setArticles(items); }
    catch (e) { if (version === requestVersion.current) setError((e as Error).message); }
    finally { if (version === requestVersion.current) setLoading(false); }
  }
  useEffect(() => { void load(); }, [filters]);
  useEffect(() => {
    let live = true;
    const journalId = draft?.journal_id;
    setVolumes([]); setVolumeError("");
    if (!journalId) { setVolumesLoading(false); return; }
    setVolumesLoading(true);
    api(`editor/volumes?journal_id=${journalId}`).then(items => { if (live) setVolumes(items); }).catch(e => { if (live) setVolumeError(e.message); }).finally(() => { if (live) setVolumesLoading(false); });
    return () => { live = false; };
  }, [draft?.journal_id, volumeRetry]);
  function open(article?: ManagedArticle) {
    if (draft && !window.confirm("Discard unsaved article changes?")) return;
    setDraft(article ? { how_to_cite: article.how_to_cite ?? "", volume_id: article.volume_id, journal_id: article.journal_id, id: article.id, title: article.title, authors: article.authors.join("\n"), abstract: article.abstract, status: article.status, has_pdf: article.has_pdf } : { how_to_cite: "", volume_id: null, journal_id: Number(filters.journal) || 0, title: "", authors: "", abstract: "", status: "UnPublished", has_pdf: false });
    setFormVersion(version => version + 1); setFile(null); setError(""); setMessage("");
  }
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!draft) return;
    setBusy(true); setError(""); setMessage("");
    try {
      if (!draft.journal_id) throw new Error("Choose a journal for this article");
      if (!file && !draft.has_pdf) throw new Error("Upload a PDF for this article");
      const body = { how_to_cite: draft.how_to_cite, volume_id: draft.volume_id, title: draft.title, authors: draft.authors.split("\n").map(name => name.trim()).filter(Boolean), abstract: draft.abstract, status: draft.status, ...(file ? { pdf_base64: await pdfBase64(file) } : {}) };
      await api(`editor/articles${draft.id ? `/${draft.id}` : ""}?journal_id=${draft.journal_id}`, body, draft.id ? "PATCH" : "POST");
      setDraft(null); setFile(null); setMessage("Article saved."); await load();
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  async function remove(article: ManagedArticle) {
    if (!window.confirm(`Delete "${article.title}" and its PDF? It will also be removed from its volume.`)) return;
    setBusy(true); setError(""); setMessage("");
    try { await api(`editor/articles/${article.id}?journal_id=${article.journal_id}`, undefined, "DELETE"); if (draft?.id === article.id) setDraft(null); setMessage("Article deleted."); await load(); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  const searchTerm = search.trim().toLowerCase();
  const filtered = articles.filter(article => (!statusFilter || article.status === statusFilter) && [article.title, article.journal_name, ...article.authors, article.volume_title ?? ""].some(value => value.toLowerCase().includes(searchTerm)));
  return <>{topbarActions && createPortal(<button className="small" disabled={loading || busy} onClick={() => open()}>+ New article</button>, topbarActions)}{filterPanel}{error && <p className="message error" role="alert">{error}</p>}{message && <p className="message" role="status">{message}</p>}{draft && <section className="admin-panel publication-editor"><form onSubmit={save}><fieldset className="template-fieldset" disabled={busy}><div className="publication-status-row"><h2>{draft.id ? "Edit article" : "New article"}</h2><label>Article status<select value={draft.status} onChange={e => setDraft({ ...draft, status: e.target.value as ArticleStatus })}><option value="Submitted">Submitted</option><option value="Published">Published</option><option value="UnPublished">UnPublished</option></select></label></div><div className="fields"><label className="wide">Journal<select required disabled={!!draft.id} value={draft.journal_id} onChange={e => setDraft({ ...draft, journal_id: Number(e.target.value), volume_id: null })}><option value={0} disabled>Choose one journal</option>{journals.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select><small>Each article belongs to one journal. Its journal cannot be changed after creation.</small></label><label className="wide">Volume<select value={draft.volume_id ?? ""} disabled={!draft.journal_id || volumesLoading || !!volumeError} onChange={e => setDraft({ ...draft, volume_id: e.target.value ? Number(e.target.value) : null })}><option value="">{volumesLoading ? "Loading volumes..." : "Unassigned"}</option>{volumes.filter(volume => volume.journal_id === draft.journal_id).map(volume => <option key={volume.id} value={volume.id}>{volume.title} - Vol. {volume.volume}{volume.number ? ` No. ${volume.number}` : ""}</option>)}</select><small>Only this journal's volumes are available. Selecting another volume moves the article out of its current volume.</small>{volumeError && <span role="alert">{volumeError} <button type="button" className="small secondary" onClick={() => setVolumeRetry(value => value + 1)}>Retry</button></span>}</label><label className="wide">Article heading<input required maxLength={300} value={draft.title} onChange={e => setDraft({ ...draft, title: e.target.value })} /></label><label>Author names (one per line)<textarea required rows={4} value={draft.authors} onChange={e => setDraft({ ...draft, authors: e.target.value })} placeholder="First author
Second author" /></label><label>PDF document (maximum 10 MB)<input key={formVersion} type="file" accept=".pdf,application/pdf" required={!draft.has_pdf} onChange={e => setFile(e.target.files?.[0] ?? null)} /><small>{draft.has_pdf ? "Leave empty to retain the existing PDF." : "Upload a PDF document."}</small></label><label className="wide">How to Cite (optional)<textarea rows={3} maxLength={2000} value={draft.how_to_cite} onChange={e => setDraft({ ...draft, how_to_cite: e.target.value })} placeholder="Author(s). (Year). Article title. Journal name, volume(issue), pages. DOI or URL." /><small>Provide the citation readers should use for this article.</small></label><label className="wide">Abstract (optional)<textarea maxLength={10000} value={draft.abstract} onChange={e => setDraft({ ...draft, abstract: e.target.value })} /></label></div><div className="admin-actions template-save-actions"><button disabled={busy || volumesLoading || !!volumeError}>{busy ? "Saving PDF…" : "Save article"}</button><button type="button" className="secondary" onClick={() => { if (window.confirm("Discard unsaved article changes?")) setDraft(null); }}>Cancel</button></div></fieldset></form></section>}
    <section className="admin-panel"><div className="volume-list-summary" role="status">{loading ? "Loading articles..." : `${filtered.length} of ${articles.length} articles`}</div>{loading ? <p role="status">Loading articles…</p> : <><div className="table-scroll article-table-scroll"><table className="article-management-table"><thead><tr><th>Heading</th><th>Journal</th><th>Created</th><th>Authors</th><th>Submitted by</th><th>Volume</th><th>Status</th><th>PDF</th><th>Actions</th></tr></thead><tbody>{filtered.map(article => <tr key={article.id}><td data-label="Heading">{article.title}{article.how_to_cite && <details className="article-citation"><summary>How to Cite</summary><p>{article.how_to_cite}</p></details>}</td><td data-label="Journal">{article.journal_name}</td><td data-label="Created">{new Date(article.created_at).toLocaleDateString(undefined, { timeZone: "UTC" })}</td><td data-label="Authors">{article.authors.join(", ")}</td><td data-label="Submitted by">{article.submitter_name || article.submitter_email ? <>{article.submitter_name}{article.submitter_email && <><br /><a href={`mailto:${article.submitter_email}`}>{article.submitter_email}</a></>}</> : <span className="template-help">Not provided</span>}</td><td data-label="Volume">{article.volume_title ?? "Unassigned"}</td><td data-label="Status">{article.status}</td><td data-label="PDF"><div className="admin-actions article-row-icons">{article.has_pdf && <><a className="button small secondary article-icon-action" title="View PDF" aria-label={`View PDF: ${article.title}`} href={`/api/editor/articles/${article.id}/pdf?journal_id=${article.journal_id}&inline=true`} target="_blank" rel="noopener noreferrer"><ArticleActionIcon action="view" /></a><a className="button small secondary article-icon-action" title="Download PDF" aria-label={`Download PDF: ${article.title}`} href={`/api/editor/articles/${article.id}/pdf?journal_id=${article.journal_id}`} target="_blank" rel="noopener noreferrer"><ArticleActionIcon action="download" /></a></>}{!article.has_pdf && <span className="template-help">No PDF</span>}</div></td><td data-label="Actions"><div className="admin-actions article-row-icons"><button className="small article-icon-action" title="Edit article" aria-label={`Edit article: ${article.title}`} disabled={busy} onClick={() => open(article)}><ArticleActionIcon action="edit" /></button><button className="small danger article-icon-action" title="Delete article" aria-label={`Delete article: ${article.title}`} disabled={busy} onClick={() => void remove(article)}><ArticleActionIcon action="delete" /></button></div></td></tr>)}</tbody></table></div>{!filtered.length && <p>No articles found for the selected filters.</p>}</>}</section></>;
}
