"use client";
import { useEffect, useState } from "react";
type Article = { how_to_cite?: string; id: number; title: string; authors: string[]; abstract: string; article_url: string | null };
type Volume = { id: number; title: string; volume: string; number: string; published_at: string; articles: Article[] };
export default function JournalPublicationFeed({ editorCode, journalSlug, kind }: { editorCode: string; journalSlug: string; kind: "current" | "archives" }) {
  const [volumes, setVolumes] = useState<Volume[]>([]);
  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError("");
    const query = new URLSearchParams({ editor_code: editorCode, journal_slug: journalSlug, offset: String(offset), limit: "10" });
    async function load() {
      try {
        const response = await fetch(`/api/journal/${kind}?${query}`, { cache: "no-store", signal: controller.signal });
        const data = await response.json();
        if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Unable to load published volumes.");
        if (data.editor_code !== editorCode || data.journal_slug !== journalSlug) throw new Error("Unexpected journal data.");
        const items = kind === "current" ? (data.issue ? [data.issue] : []) : data.items;
        if (!Array.isArray(items)) throw new Error("Invalid volume data.");
        if (!controller.signal.aborted) { setVolumes(items); setTotal(data.total ?? items.length); }
      } catch (e) { if (!controller.signal.aborted) setError((e as Error).message); }
      finally { if (!controller.signal.aborted) setLoading(false); }
    }
    void load();
    return () => controller.abort();
  }, [editorCode, journalSlug, kind, offset, retry]);
  return <section className="journal-publication-feed" aria-label={kind === "current" ? "Current published volume" : "Archived published volumes"}>
    {(loading || error || !volumes.length) && <h1 className="journal-feed-title">{kind === "current" ? "Current" : "Archives"}</h1>}
    {loading ? <p role="status">Loading published volumes...</p> : error ? <div role="alert"><p>{error}</p><button onClick={() => setRetry(value => value + 1)}>Retry</button></div> : <>
      {!volumes.length && <p>{kind === "current" ? "No current volume has been published yet." : "No archived volumes have been published yet."}</p>}
      {volumes.map((volume, index) => <section className="journal-volume" key={volume.id}>
        <div className="journal-page-heading">{index === 0 ? <h1>{kind === "current" ? "Current" : "Archives"}</h1> : <h2>Volume</h2>}<div className="journal-volume-inline" aria-label="Volume information"><strong>{volume.title}</strong><span>{[volume.volume && `Vol. ${volume.volume}`, volume.number && `No. ${volume.number}`].filter(Boolean).join(" ")}</span><time dateTime={volume.published_at}>{new Date(volume.published_at).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric", timeZone: "UTC" })}</time></div></div><div className="journal-list-header"><h2>Articles <span>({volume.articles.length})</span></h2></div>
        {!volume.articles.length && <p>No published articles in this volume yet.</p>}
        {volume.articles.map(article => <article className="journal-article-row" key={article.id}><div><h4>{article.title}</h4><p className="journal-article-authors">{article.authors.join(", ")}</p>{article.how_to_cite && <details className="article-citation"><summary>How to Cite</summary><p>{article.how_to_cite}</p></details>}</div>{article.article_url && /^https?:\/\//i.test(article.article_url) && <a className="journal-pdf-link" href={article.article_url} target="_blank" rel="noopener noreferrer" aria-label={`View PDF: ${article.title} (opens in a new tab)`}>PDF <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M15 3h6v6M10 14 21 3M21 14v5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5" /></svg></a>}</article>)}
      </section>)}
      {kind === "archives" && total > 10 && <nav aria-label="Archive pagination"><button disabled={offset === 0} onClick={() => setOffset(value => Math.max(0, value - 10))}>Previous volumes</button><span> {offset + 1} to {Math.min(offset + 10, total)} of {total} </span><button disabled={offset + 10 >= total} onClick={() => setOffset(value => value + 10)}>Next volumes</button></nav>}
    </>}
  </section>;
}
