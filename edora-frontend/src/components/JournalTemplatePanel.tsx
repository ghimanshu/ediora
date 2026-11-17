"use client";
import { useState } from "react";
import dynamic from "next/dynamic";
import type { Journal } from "@/lib/journals";
import TemplatePreview from "@/components/TemplatePreview";
const JournalTemplateEditor = dynamic(() => import("@/components/JournalTemplateEditor"), { ssr: false, loading: () => <p role="status">Loading template editor…</p> });
export default function JournalTemplatePanel({ journal, onChanged }: { journal: Journal; onChanged: (journal: Journal) => void }) {
  const [editing, setEditing] = useState(false);
  const [message, setMessage] = useState("");
  if (editing) return <JournalTemplateEditor journal={journal} onCancel={() => setEditing(false)} onSaved={updated => { onChanged(updated); setEditing(false); setMessage("Your personal template has been saved."); }} />;
  return <section className="admin-panel"><div className="journal-panel-heading"><div><h2>Journal template</h2><p>Customize the layout, colors, and sections of your personal copy.</p></div><button onClick={() => { setEditing(true); setMessage(""); }}>Edit my template</button></div>{message && <p className="message" role="status">{message}</p>}<div className="journal-template-overview"><div><span className="eyebrow">Personal template</span><h3>{journal.template_name}</h3><p>{journal.template_description || "A custom layout for your journal."}</p><div className="journal-template-facts"><span>{journal.template_layout.sections.length} sections</span><span>{journal.template_layout.menu_position === "top" ? "Horizontal menu" : `${journal.template_layout.menu_position} sidebar`}</span></div><p className="journal-isolation-note">Editing this template never changes the admin template or another editor’s website.</p></div><TemplatePreview layout={journal.template_layout} /></div></section>;
}
