"use client";
import { FormEvent, useState } from "react";
import { api } from "@/lib/api";
import { getSectionColors, type TemplateInput, type TemplateSection } from "@/lib/templates";
import type { Journal } from "@/lib/journals";
import TemplatePreview from "@/components/TemplatePreview";
export default function JournalTemplateEditor({ journal, onSaved, onCancel }: { journal: Journal; onSaved: (journal: Journal) => void; onCancel: () => void }) {
  const [draft, setDraft] = useState<TemplateInput>(() => structuredClone({ name: journal.template_name, description: journal.template_description, layout: journal.template_layout }));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  function change(index: number, updates: Partial<TemplateSection>) { setDraft(current => ({ ...current, layout: { ...current.layout, sections: current.layout.sections.map((section, i) => i === index ? { ...section, ...updates } : section) } })); }
  function move(index: number, direction: number) {
    const sections = [...draft.layout.sections];
    [sections[index], sections[index + direction]] = [sections[index + direction], sections[index]];
    setDraft({ ...draft, layout: { ...draft.layout, sections } });
  }
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError("");
    try { onSaved(await api(`editor/journal/template?journal_id=${journal.id}`, draft, "PATCH")); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  return <section className="admin-panel template-editor"><h2>Edit my template copy</h2><p className="template-help">These changes apply only to your journal.</p>{error && <p className="message error" role="alert">{error}</p>}<form onSubmit={save}><fieldset disabled={busy} className="template-fieldset"><div className="template-editor-grid"><div className="template-editor-fields">{draft.layout.sections.map((section, index) => <div className="template-section-editor" key={section.type}><div className="template-section-heading"><strong>{section.type}</strong><div className="admin-actions"><button className="small secondary" type="button" aria-label={`Move ${section.type} up`} disabled={index === 0} onClick={() => move(index, -1)}>↑</button><button className="small secondary" type="button" aria-label={`Move ${section.type} down`} disabled={index === 3} onClick={() => move(index, 1)}>↓</button></div></div>{(section.type === "header" || section.type === "footer") && <><label>Title<input required maxLength={100} value={section.title} onChange={e => change(index, { title: e.target.value })} /></label><label>Default content<textarea maxLength={2000} value={section.content} onChange={e => change(index, { content: e.target.value })} /></label></>}<div className="template-color-controls">{(["background_color", "text_color"] as const).map(field => <label key={field}>{field === "background_color" ? "Background color" : "Text color"}<span className="template-color-input"><input type="color" aria-label={`${section.type} ${field} picker`} value={getSectionColors(section)[field]} onChange={e => change(index, { [field]: e.target.value })} /><input required pattern="#[0-9a-fA-F]{6}" maxLength={7} aria-label={`${section.type} ${field} hex`} value={section[field] ?? getSectionColors(section)[field]} onChange={e => change(index, { [field]: e.target.value })} /></span></label>)}</div></div>)}</div><div className="template-live-preview"><TemplatePreview layout={draft.layout} /><p className="template-help">The website preview uses your copied pages in the content area. Its menu lists your pages.</p></div></div><div className="admin-actions template-save-actions"><button disabled={busy}>{busy ? "Saving…" : "Save my template"}</button><button className="secondary" type="button" onClick={() => { if (window.confirm("Discard unsaved template changes?")) onCancel(); }}>Cancel</button></div></fieldset></form></section>;
}
