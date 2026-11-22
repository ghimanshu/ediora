"use client";
import { useRef, useState, type FormEvent } from "react";
import type { JournalInfo } from "@/lib/journals";
import TemplatePreview from "@/components/TemplatePreview";
import { getSectionColors, sectionColors, type TemplateInput, type SectionType } from "@/lib/templates";
const allTabs = ["settings", "header", "menu", "content", "footer"] as const;
type Tab = typeof allTabs[number];
export default function TemplateEditor({ draft, busy, editing, onChange, onSave, onCancel, editorMode = false, previewInfo, previewEmail }: { editorMode?: boolean; previewInfo?: Partial<JournalInfo>; previewEmail?: string; draft: TemplateInput; busy: boolean; editing: boolean; onChange: (draft: TemplateInput) => void; onSave: (event: FormEvent<HTMLFormElement>) => void; onCancel: () => void }) {
  const tabs = editorMode ? allTabs.filter(tab => tab !== "settings") : allTabs;
  const [active, setActive] = useState<Tab>(editorMode ? "header" : "settings");
  const [error, setError] = useState("");
  const buttons = useRef<(HTMLButtonElement | null)[]>([]);
  function layoutChange(values: Partial<TemplateInput["layout"]>) { onChange({ ...draft, layout: { ...draft.layout, ...values } }); }
  function sectionChange(type: SectionType, values: Partial<TemplateInput["layout"]["sections"][number]>) {
    layoutChange({ sections: draft.layout.sections.map(section => section.type === type ? { ...section, ...values } : section) });
  }
  function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError("");
    if (!draft.name.trim()) { setActive("settings"); setError("Enter a template name."); return; }
    for (const section of draft.layout.sections) {
      if (!section.title.trim() || [section.background_color, section.text_color].some(color => color !== undefined && !/^#[0-9a-f]{6}$/i.test(color))) {
        setActive(section.type); setError("Enter a title and valid six-digit hex colors for this section."); return;
      }
    }
    onSave(event);
  }
  const section = draft.layout.sections.find(item => item.type === active);
  return <section className="admin-panel admin-template-editor" aria-labelledby="template-editor-title"><div className="journal-panel-heading"><div><h2 id="template-editor-title">{editorMode ? "Edit my template copy" : editing ? "Edit template" : "Create template"}</h2><p>{editorMode ? "Changes apply only to this journal. Preview updates as you edit." : "Edit a section and see the result in the live preview."}</p></div></div>
    <form onSubmit={save}><fieldset disabled={busy} className="template-fieldset"><div className="admin-template-columns"><div className="admin-template-controls">
      <div className="admin-template-tabs" role="tablist" aria-label="Template sections">{tabs.map((tab, index) => <button type="button" role="tab" key={tab} id={`template-tab-${tab}`} aria-controls={`template-panel-${tab}`} aria-selected={active === tab} tabIndex={active === tab ? 0 : -1} ref={node => { buttons.current[index] = node; }} onClick={() => { setActive(tab); setError(""); }} onKeyDown={event => {
        let target = index;
        if (event.key === "ArrowRight") target = (index + 1) % tabs.length;
        else if (event.key === "ArrowLeft") target = (index + tabs.length - 1) % tabs.length;
        else if (event.key === "Home") target = 0;
        else if (event.key === "End") target = tabs.length - 1;
        else return;
        event.preventDefault(); setActive(tabs[target]); buttons.current[target]?.focus();
      }}>{tab[0].toUpperCase() + tab.slice(1)}</button>)}</div>
      <div className="admin-template-tab-panel" role="tabpanel" id={`template-panel-${active}`} aria-labelledby={`template-tab-${active}`} tabIndex={0}>
        {active === "settings" ? <><h3>Template settings</h3><label>Template name<input required maxLength={100} value={draft.name} onChange={event => onChange({ ...draft, name: event.target.value })} /></label><label>Description<textarea rows={3} maxLength={500} value={draft.description} onChange={event => onChange({ ...draft, description: event.target.value })} /></label></> : section && <><h3>{active[0].toUpperCase() + active.slice(1)}</h3>
          {active === "menu" ? (!editorMode && <label>Menu placement<select value={draft.layout.menu_position} onChange={event => layoutChange({ menu_position: event.target.value as TemplateInput["layout"]["menu_position"] })}><option value="top">Horizontal</option><option value="left">Left sidebar</option><option value="right">Right sidebar</option></select></label>) : (!editorMode || active === "header" || active === "footer") && <><label>Title<input required maxLength={100} value={section.title} onChange={event => sectionChange(section.type, { title: event.target.value })} /></label><label>Default content<textarea rows={4} maxLength={2000} value={section.content} onChange={event => sectionChange(section.type, { content: event.target.value })} /></label></>}
          <div className="template-color-controls">{(["background_color", "text_color"] as const).map(field => <label key={field}>{field === "background_color" ? "Background color" : "Text color"}<span className="template-color-input"><input type="color" aria-label={`${active} ${field} picker`} value={getSectionColors(section)[field]} onChange={event => sectionChange(section.type, { [field]: event.target.value })} /><input required pattern="#[0-9a-fA-F]{6}" maxLength={7} aria-label={`${active} ${field} hex`} value={section[field] ?? getSectionColors(section)[field]} onChange={event => sectionChange(section.type, { [field]: event.target.value })} /></span></label>)}</div>
          <button type="button" className="small secondary" onClick={() => sectionChange(section.type, sectionColors[section.type])}>Reset colors</button>
          {active === "content" && <div className="admin-template-optional"><h4>Optional right-hand panels</h4><label><input type="checkbox" checked={draft.layout.show_journal_info !== false} onChange={event => layoutChange({ show_journal_info: event.target.checked, show_submissions: draft.layout.show_submissions ?? draft.layout.show_journal_info !== false })} />Journal Info</label><p>Show the journal's saved editorial and publishing details.</p><label><input type="checkbox" checked={(draft.layout.show_submissions ?? draft.layout.show_journal_info) !== false} onChange={event => layoutChange({ show_submissions: event.target.checked })} />Submission to editor</label><p>Show the editor's email and a Submit manuscript button.</p><label><input type="checkbox" checked={draft.layout.show_downloads !== false} onChange={event => layoutChange({ show_downloads: event.target.checked })} />Downloads</label><p>Include the Copyright Form and Sample Manuscript PDF downloads.</p></div>}
        </>}
        {error && <p className="message error" role="alert">{error}</p>}
      </div>
    </div><div className="admin-template-preview"><div className="admin-template-preview-label"><span className="eyebrow">Live preview</span><span>{editorMode ? "Your journal design" : "Sample journal details"}</span></div><TemplatePreview layout={draft.layout} compactInfo journalInfo={previewInfo} editorEmail={previewEmail} /><p className="template-help">{editorMode ? "Your journal pages and navigation are used on the website." : "New journals copy this design. Existing editor copies remain independent."}</p></div></div>
    <div className="admin-actions template-save-actions"><button disabled={busy}>{busy ? "Saving..." : editorMode ? "Save my template" : "Save template"}</button><button type="button" className="secondary" onClick={onCancel}>Cancel</button></div></fieldset></form>
  </section>;
}
