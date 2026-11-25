"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Journal } from "@/lib/journals";
type Version = { id: number; version: number; page_count: number; requested_at: string; status: string; preview_path: string };
export default function JournalDeployments({ journalId, journal, admin = false }: { journalId: number; journal?: Journal; admin?: boolean }) {
  const [versions, setVersions] = useState<Version[]>([]);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const endpoint = admin ? `admin/editor-journals/${journalId}/deployments` : `editor/journal/deployments?journal_id=${journalId}`;
  useEffect(() => {
    let live = true;
    setLoading(true); setError("");
    api(endpoint).then(data => { if (live) setVersions(data); }).catch(e => { if (live) setError(e.message); }).finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
  }, [endpoint]);
  async function request() {
    if (!journal) return;
    setBusy(true); setError(""); setMessage("");
    try {
      const latest: Journal = await api(`editor/journal?journal_id=${journalId}`);
      if (latest.status !== "Published") throw new Error("Publish this journal before requesting deployment.");
      const active = latest.pages.filter(page => page.is_active);
      const disabled = new Set(latest.pages.filter(page => !page.is_active).map(page => page.slug));
      const slugs = new Set(active.map(page => page.slug));
      for (const slug of ["current", "archives", "submission"]) {
        if (disabled.has(slug) || (slug === "submission" && (slugs.has("submissions") || disabled.has("submissions")))) continue;
        slugs.add(slug);
      }
      if (!window.confirm(`Are you sure you want to request deployment of this version of your journal with ${slugs.size} pages live? A saved version will be sent to the admin for review.`)) return;
      const version: Version = await api(endpoint, { expected_updated_at: latest.updated_at, expected_page_count: slugs.size });
      setVersions(current => [version, ...current]);
      setMessage(`V${version.version} saved. Your deployment request has been sent to the admin.`);
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  return <section className="admin-panel journal-deployments"><div className="template-card-heading"><div><h2>{admin ? "Deployment requests & versions" : "Deployment"}</h2><p className="template-help">Saved versions remain unchanged when the journal is edited. Deployment is completed by the admin.</p></div>{!admin && <button type="button" disabled={busy || loading || journal?.status !== "Published"} onClick={() => void request()}>{busy ? "Preparing..." : "Request to deploy"}</button>}</div>{!admin && journal?.status !== "Published" && <p className="template-help">Publish your journal to request deployment.</p>}{error && <p role="alert" className="message error">{error}</p>}{message && <p role="status" className="message">{message}</p>}{loading ? <p role="status">Loading versions...</p> : versions.length ? <div className="table-scroll"><table><thead><tr><th>Version</th><th>Requested</th><th>Live pages</th><th>Status</th>{admin && <th>Preview</th>}</tr></thead><tbody>{versions.map(version => <tr key={version.id}><td>V{version.version}</td><td>{new Date(version.requested_at).toLocaleString()}</td><td>{version.page_count}</td><td>Requested</td>{admin && <td><a className="button small secondary" href={version.preview_path} target="_blank" rel="noopener noreferrer">Preview V{version.version}</a></td>}</tr>)}</tbody></table></div> : <p className="template-help">No deployment requests yet.</p>}</section>;
}
