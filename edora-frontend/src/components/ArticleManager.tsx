"use client";
import { type ReactNode, FormEvent, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { pdfBase64, publicationQuery, type JournalChoice, type PublicationFilters, type ManagedArticle, type ArticleStatus } from "@/lib/publications";
type Draft = { journal_id: number; id?: number; title: string; authors: string; abstract: string; status: ArticleStatus; has_pdf: boolean };
export default function ArticleManager({ journals, filters, search, filterPanel }: { journals: JournalChoice[]; filters: PublicationFilters; search: string; filterPanel: ReactNode }) {
  const requestVersion = useRef(0);
  const activeFilters = useRef(filters);
  activeFilters.current = filters;
  const [formVersion, setFormVersion] = useState(0);
  const [articles, setArticles] = useState<ManagedArticle[]>([]);
  const [draft, setDraft] = useState<Draft | null>(null);
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
  function open(article?: ManagedArticle) {
    if (draft && !window.confirm("Discard unsaved article changes?")) return;
    setDraft(article ? { journal_id: article.journal_id, id: article.id, title: article.title, authors: article.authors.join("\n"), abstract: article.abstract, status: article.status, has_pdf: article.has_pdf } : { journal_id: Number(filters.journal) || 0, title: "", authors: "", abstract: "", status: "UnPublished", has_pdf: false });
    setFormVersion(version => version + 1); setFile(null); setError(""); setMessage("");
  }
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!draft) return;
    setBusy(true); setError(""); setMessage("");
    try {
      if (!draft.journal_id) throw new Error("Choose a journal for this article");
      if (!file && !draft.has_pdf) throw new Error("Upload a PDF for this article");
      const body = { title: draft.title, authors: draft.authors.split("\n").map(name => name.trim()).filter(Boolean), abstract: draft.abstract, status: draft.status, ...(file ? { pdf_base64: await pdfBase64(file) } : {}) };
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
  const filtered = articles.filter(article => [article.title, article.journal_name, ...article.authors, article.volume_title ?? ""].some(value => value.toLowerCase().includes(searchTerm)));
  return <><div className="admin-page-heading volume-workspace-heading"><div><span className="eyebrow">Journal publishing</span><h1>Manage articles</h1><p>Create articles with multiple authors and a PDF document.</p></div><button disabled={loading || busy} onClick={() => open()}>+ New article</button></div>{filterPanel}{error && <p className="message error" role="alert">{error}</p>}{message && <p className="message" role="status">{message}</p>}{draft && <section className="admin-panel publication-editor"><form onSubmit={save}><fieldset className="template-fieldset" disabled={busy}><div className="publication-status-row"><h2>{draft.id ? "Edit article" : "New article"}</h2><label>Article status<select value={draft.status} onChange={e => setDraft({ ...draft, status: e.target.value as ArticleStatus })}><option value="Submitted">Submitted</option><option value="Published">Published</option><option value="UnPublished">UnPublished</option></select></label></div><div className="fields"><label className="wide">Journal<select required disabled={!!draft.id} value={draft.journal_id} onChange={e => setDraft({ ...draft, journal_id: Number(e.target.value) })}><option value={0} disabled>Choose one journal</option>{journals.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select><small>Each article belongs to one journal. Its journal cannot be changed after creation.</small></label><label className="wide">Article heading<input required maxLength={300} value={draft.title} onChange={e => setDraft({ ...draft, title: e.target.value })} /></label><label>Author names (one per line)<textarea required rows={4} value={draft.authors} onChange={e => setDraft({ ...draft, authors: e.target.value })} placeholder="First author
Second author" /></label><label>PDF document (maximum 10 MB)<input key={formVersion} type="file" accept=".pdf,application/pdf" required={!draft.has_pdf} onChange={e => setFile(e.target.files?.[0] ?? null)} /><small>{draft.has_pdf ? "Leave empty to retain the existing PDF." : "Upload a PDF document."}</small></label><label className="wide">Abstract (optional)<textarea maxLength={10000} value={draft.abstract} onChange={e => setDraft({ ...draft, abstract: e.target.value })} /></label></div><div className="admin-actions template-save-actions"><button disabled={busy}>{busy ? "Saving PDF…" : "Save article"}</button><button type="button" className="secondary" onClick={() => { if (window.confirm("Discard unsaved article changes?")) setDraft(null); }}>Cancel</button></div></fieldset></form></section>}
    <section className="admin-panel"><div className="volume-list-summary" role="status">{loading ? "Loading articles..." : `${filtered.length} of ${articles.length} articles`}</div>{loading ? <p role="status">Loading articles…</p> : <><div className="table-scroll"><table><thead><tr><th>Heading</th><th>Journal</th><th>Created</th><th>Authors</th><th>Volume</th><th>Status</th><th>Actions</th></tr></thead><tbody>{filtered.map(article => <tr key={article.id}><td>{article.title}</td><td>{article.journal_name}</td><td>{new Date(article.created_at).toLocaleDateString(undefined, { timeZone: "UTC" })}</td><td>{article.authors.join(", ")}{article.submitter_email && <small className="article-submitter">Submitted by {article.submitter_name}<br /><a href={`mailto:${article.submitter_email}`}>{article.submitter_email}</a></small>}</td><td>{article.volume_title ?? "Unassigned"}</td><td>{article.status}</td><td><div className="admin-actions">{article.has_pdf && <><a className="button small secondary" href={`/api/editor/articles/${article.id}/pdf?journal_id=${article.journal_id}&inline=true`} target="_blank" rel="noopener noreferrer">View article ↗</a><a className="button small secondary" href={`/api/editor/articles/${article.id}/pdf?journal_id=${article.journal_id}`} target="_blank" rel="noopener noreferrer">Download PDF</a></>}<button className="small" disabled={busy} onClick={() => open(article)}>Edit</button><button className="small danger" disabled={busy} onClick={() => void remove(article)}>Delete</button></div></td></tr>)}</tbody></table></div>{!filtered.length && <p>No articles found for the selected filters.</p>}</>}</section></>;
}
