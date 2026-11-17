"use client";
import { FormEvent, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { getSectionColors, sectionColors, newTemplate, TemplateInput, WebsiteTemplate } from "@/lib/templates";
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
  function changeSection(index: number, field: "title" | "content" | "background_color" | "text_color", value: string) {
    setDraft(current => current && ({ ...current, layout: { ...current.layout, sections: current.layout.sections.map((section, i) => i === index ? { ...section, [field]: value } : section) } }));
  }
  function move(index: number, direction: number) {
    if (!draft) return;
    const sections = [...draft.layout.sections];
    [sections[index], sections[index + direction]] = [sections[index + direction], sections[index]];
    setDraft({ ...draft, layout: { ...draft.layout, sections } });
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
    {draft && <section className="admin-panel template-editor" aria-labelledby="template-editor-title"><h2 id="template-editor-title">{editingId ? "Edit template" : "Create template"}</h2><form onSubmit={save}><fieldset disabled={busy} className="template-fieldset"><div className="template-editor-grid"><div className="template-editor-fields">
      <label>Template name<input value={draft.name} onChange={e => setDraft({ ...draft, name: e.target.value })} maxLength={100} required autoFocus /></label>
      <label>Description<textarea value={draft.description} onChange={e => setDraft({ ...draft, description: e.target.value })} maxLength={500} rows={2} /></label>
      <label>Menu placement<select value={draft.layout.menu_position} onChange={e => setDraft({ ...draft, layout: { ...draft.layout, menu_position: e.target.value as TemplateInput["layout"]["menu_position"] } })}><option value="top">Horizontal / in section order</option><option value="left">Left sidebar beside content</option><option value="right">Right sidebar beside content</option></select></label>
      <p className="template-help">Reorder sections with the arrows. A sidebar menu stays beside the content. Text is rendered safely as plain text; menu items use one line each.</p>
      {draft.layout.sections.map((section, index) => <div className="template-section-editor" key={section.type}><div className="template-section-heading"><strong>{section.type}</strong><div className="admin-actions"><button type="button" className="small secondary" aria-label={`Move ${section.type} up`} disabled={index === 0} onClick={() => move(index, -1)}>↑</button><button type="button" className="small secondary" aria-label={`Move ${section.type} down`} disabled={index === draft.layout.sections.length - 1} onClick={() => move(index, 1)}>↓</button></div></div>{section.type !== "menu" && <label>Title<input value={section.title} maxLength={100} required onChange={e => changeSection(index, "title", e.target.value)} /></label>}<label>{section.type === "menu" ? "Menu items (one per line)" : "Default content"}<textarea value={section.content} maxLength={2000} rows={3} onChange={e => changeSection(index, "content", e.target.value)} /></label><div className="template-color-controls">{(["background_color", "text_color"] as const).map(field => <label key={field}>{field === "background_color" ? "Background color" : "Text color"}<span className="template-color-input"><input type="color" aria-label={`${section.type} ${field === "background_color" ? "background" : "text"} color picker`} value={getSectionColors(section)[field]} onChange={e => changeSection(index, field, e.target.value)} /><input type="text" aria-label={`${section.type} ${field === "background_color" ? "background" : "text"} hex color`} value={section[field] ?? getSectionColors(section)[field]} pattern="#[0-9a-fA-F]{6}" maxLength={7} required title="Enter a six-digit hex color, such as #244c40" spellCheck={false} onChange={e => changeSection(index, field, e.target.value)} /></span></label>)}</div><button type="button" className="small secondary template-reset-colors" onClick={() => setDraft(current => current && ({ ...current, layout: { ...current.layout, sections: current.layout.sections.map((item, i) => i === index ? { ...item, ...sectionColors[item.type] } : item) } }))}>Reset section colors</button></div>)}
    </div><div className="template-live-preview"><span className="eyebrow">Live layout preview</span><TemplatePreview layout={draft.layout} /><p className="template-help">Changes to a saved template also appear for users who selected it.</p></div></div><div className="admin-actions template-save-actions"><button disabled={busy}>{busy ? "Saving…" : "Save template"}</button><button type="button" className="secondary" onClick={cancel}>Cancel</button></div></fieldset></form></section>}
    {loading ? <p role="status">Loading templates…</p> : <div className="template-library">{templates.map(template => <article className="admin-panel template-card" key={template.id}><TemplatePreview layout={template.layout} /><div className="template-card-heading"><h2>{template.name}</h2><div className="admin-actions"><button className="small" disabled={busy} onClick={() => open(template)}>Edit template</button><button type="button" className="small danger" disabled={busy} aria-label={`Delete template ${template.name}`} onClick={() => void remove(template)}>Delete</button></div></div><p>{template.description}</p><small>Updated {new Date(template.updated_at).toLocaleDateString()}</small></article>)}{!templates.length && !error && <p>No templates yet. Create your first website template.</p>}</div>}
  </>;
}
