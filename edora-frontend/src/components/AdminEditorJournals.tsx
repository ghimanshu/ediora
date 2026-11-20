"use client";
import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { downloadWebsite } from "@/lib/download-website";
import { api } from "@/lib/api";
import JournalStatusBadge from "@/components/JournalStatusBadge";
import type { JournalStatus } from "@/lib/journals";
type EditorChoice = { id: number; name: string; email: string };
type Row = { preview_path: string; id: number; name: string; template_name: string; status: JournalStatus; editor_name: string; editor_email: string; page_count: number; created_at: string; updated_at: string };
const pageSize = 20;
export default function AdminEditorJournals() {
  const [editors, setEditors] = useState<EditorChoice[]>([]);
  const [editorError, setEditorError] = useState("");
  const [editor, setEditor] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [filters, setFilters] = useState({ editor: "", from: "", to: "" });
  const [offset, setOffset] = useState(0);
  const [rows, setRows] = useState<Row[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [downloading, setDownloading] = useState<number | null>(null);
  const [downloadMessage, setDownloadMessage] = useState("");
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    let live = true;
    api("admin/journal-editors").then(items => { if (live) { setEditors(items); setEditorError(""); } }).catch(e => { if (live) setEditorError(e.message); });
    return () => { live = false; };
  }, [refresh]);
  useEffect(() => {
    let live = true;
    setLoading(true); setError("");
    const query = new URLSearchParams({ offset: String(offset), limit: String(pageSize) });
    if (filters.editor) query.set("editor_id", filters.editor);
    if (filters.from) query.set("date_from", filters.from);
    if (filters.to) query.set("date_to", filters.to);
    api(`admin/editor-journals?${query}`).then(result => { if (live) { setRows(result.items); setTotal(result.total); } }).catch(e => { if (live) setError(e.message); }).finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
  }, [filters, offset, refresh]);
  function apply(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (from && to && from > to) { setError("Created from must not be later than created to."); return; }
    setOffset(0); setFilters({ editor, from, to });
  }
  async function download(row: Row) {
    setDownloading(row.id); setError(""); setDownloadMessage("");
    try { await downloadWebsite(row.id); setDownloadMessage(`Website ZIP downloaded for ${row.name}. Extract the folder and open index.html.`); }
    catch (e) { setError((e as Error).message); }
    finally { setDownloading(null); }
  }
  function clear() { setEditor(""); setFrom(""); setTo(""); setOffset(0); setFilters({ editor: "", from: "", to: "" }); }
  return <section className="admin-panel"><form className="admin-journal-filters" onSubmit={apply}><label>Editor<select value={editor} onChange={e => setEditor(e.target.value)}><option value="">All editors</option>{editors.map(item => <option key={item.id} value={item.id}>{item.name} — {item.email}</option>)}</select></label><label>Created from (UTC)<input type="date" value={from} max={to || undefined} onChange={e => setFrom(e.target.value)} /></label><label>Created to (UTC)<input type="date" value={to} min={from || undefined} onChange={e => setTo(e.target.value)} /></label><div className="admin-actions"><button disabled={loading}>Apply filters</button><button type="button" className="secondary" disabled={loading} onClick={clear}>Clear</button><button type="button" className="secondary" disabled={loading} onClick={() => setRefresh(value => value + 1)}>Refresh</button></div></form>{downloadMessage && <p className="message" role="status">{downloadMessage}</p>}{editorError && <p className="message error" role="alert">Editor filter unavailable: {editorError}</p>}{error && <p className="message error" role="alert">{error}</p>}{loading ? <p role="status">Loading editor journals…</p> : <><div className="admin-journal-results"><span>{total} {total === 1 ? "journal" : "journals"}</span><span className="journal-private-badge">Read-only access</span></div><div className="table-scroll"><table><thead><tr><th>Journal</th><th>Editor</th><th>Personal template</th><th>Status</th><th>Created</th><th>Pages</th><th>Actions</th></tr></thead><tbody>{rows.map(row => <tr key={row.id}><td><strong>{row.name}</strong></td><td>{row.editor_name}<small className="admin-journal-editor-email">{row.editor_email}</small></td><td>{row.template_name}</td><td><JournalStatusBadge status={row.status} /></td><td>{new Date(row.created_at).toLocaleDateString(undefined, { timeZone: "UTC" })}</td><td>{row.page_count}</td><td><div className="admin-actions"><Link className="button small" href={row.preview_path} target="_blank" rel="noopener noreferrer">Open journal ↗</Link><button className="small secondary" type="button" disabled={row.status !== "Published" || downloading !== null} title={row.status !== "Published" ? "Only Published journals can be downloaded" : "Download an offline HTML and CSS website"} onClick={() => void download(row)}>{downloading === row.id ? "Preparing ZIP…" : "Download Website"}</button></div></td></tr>)}</tbody></table></div>{!rows.length && !error && <p>No journals match these filters.</p>}<div className="admin-actions"><button disabled={offset === 0} onClick={() => setOffset(value => Math.max(0, value - pageSize))}>Previous</button><span>Page {Math.floor(offset / pageSize) + 1} of {Math.max(1, Math.ceil(total / pageSize))}</span><button disabled={offset + pageSize >= total} onClick={() => setOffset(value => value + pageSize)}>Next</button></div></>}</section>;
}
