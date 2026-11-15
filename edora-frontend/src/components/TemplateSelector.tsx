"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { WebsiteTemplate } from "@/lib/templates";
import TemplatePreview from "@/components/TemplatePreview";
export default function TemplateSelector() {
  const [templates, setTemplates] = useState<WebsiteTemplate[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  useEffect(() => {
    let live = true;
    Promise.all([api("templates"), api("website/template")]).then(([items, selected]) => {
      if (live) { setTemplates(items); setSelectedId(selected?.id ?? null); }
    }).catch(e => { if (live) setError(e.message); }).finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
  }, []);
  async function choose(id: number) {
    setBusy(true); setError(""); setMessage("");
    try { const selected = await api("website/template", { template_id: id }); setSelectedId(selected.id); setMessage("Website template selected and saved."); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  return <section className="website-template-selector"><h2>Your website template</h2><p>Choose a layout for your website. Your selection is saved to your account.</p>{error && <p className="message error" role="alert">{error}</p>}{message && <p className="message" role="status">{message}</p>}{loading ? <p role="status">Loading templates…</p> : <div className="template-library">{templates.map(template => <article className={`template-card card ${selectedId === template.id ? "template-selected" : ""}`} key={template.id}><TemplatePreview layout={template.layout} /><h3>{template.name}</h3><p>{template.description}</p><button disabled={busy || selectedId === template.id} onClick={() => void choose(template.id)}>{selectedId === template.id ? "Selected" : "Use this template"}</button></article>)}{!templates.length && !error && <p>No templates are available yet.</p>}</div>}</section>;
}
