"use client";
import { FormEvent, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { newTemplate, TemplateInput, WebsiteTemplate } from "@/lib/templates";
import TemplateEditor from "@/components/TemplateEditor";
import TemplatePreview from "@/components/TemplatePreview";
export default function TemplateManagement() {
  const [templates, setTemplates] = useState<WebsiteTemplate[]>([]);
  const [draft, setDraft] = useState<TemplateInput | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  async function load() {
    setLoading(true); setError("");
    try { setTemplates(await api("admin/templates")); }
    catch (e) { setError((e as Error).message); }
    finally { setLoading(false); }
  }
  useEffect(() => { void load(); }, []);
  function open(template?: WebsiteTemplate) {
    if (draft && !window.confirm("Discard your unsaved template changes?")) return;
    setEditingId(template?.id ?? null);
    setDraft(template ? structuredClone({ name: template.name, description: template.description, layout: template.layout }) : newTemplate());
    setError(""); setMessage("");
  }
  function cancel() {
    if (window.confirm("Discard your unsaved template changes?")) { setDraft(null); setEditingId(null); }
  }
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!draft) return;
    setBusy(true); setError(""); setMessage("");
    try {
      const saved: WebsiteTemplate = await api(editingId ? `admin/templates/${editingId}` : "admin/templates", draft, editingId ? "PATCH" : "POST");
      setTemplates(current => editingId ? current.map(item => item.id === saved.id ? saved : item) : [...current, saved]);
      setDraft(null); setEditingId(null); setMessage("Template saved. Users can now select it for their website.");
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  async function remove(template: WebsiteTemplate) {
    const draftWarning = editingId === template.id ? " Unsaved edits will also be discarded." : "";
    if (!window.confirm(`Permanently delete "${template.name}"? This cannot be undone.${draftWarning}`)) return;
    setBusy(true); setError(""); setMessage("");
    try {
      await api(`admin/templates/${template.id}`, undefined, "DELETE");
      setTemplates(current => current.filter(item => item.id !== template.id));
      if (editingId === template.id) { setDraft(null); setEditingId(null); }
      setMessage(`Template "${template.name}" deleted.`);
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  return <>
    <div className="template-library-toolbar"><span>{templates.length} saved templates</span><div className="admin-actions"><button className="secondary" disabled={busy || loading || !!draft} onClick={() => void load()}>Refresh</button><button disabled={busy || loading} onClick={() => open()}>+ Create template</button></div></div>
    {error && <p className="message error" role="alert">{error}</p>}{message && <p className="message" role="status">{message}</p>}
    {draft && <TemplateEditor key={editingId ?? "new"} draft={draft} busy={busy} editing={editingId !== null} onChange={setDraft} onSave={save} onCancel={cancel} />}
    {loading ? <p role="status">Loading templates…</p> : <div className="template-library">{templates.map(template => <article className="admin-panel template-card" key={template.id}><TemplatePreview layout={template.layout} compactInfo /><div className="template-card-heading"><h2>{template.name}</h2><div className="admin-actions"><button className="small" disabled={busy} onClick={() => open(template)}>Edit template</button><button type="button" className="small danger" disabled={busy} aria-label={`Delete template ${template.name}`} onClick={() => void remove(template)}>Delete</button></div></div><p>{template.description}</p><small>Updated {new Date(template.updated_at).toLocaleDateString()}</small></article>)}{!templates.length && !error && <p>No templates yet. Create your first website template.</p>}</div>}
  </>;
}
