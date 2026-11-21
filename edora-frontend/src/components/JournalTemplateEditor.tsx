"use client";
import { FormEvent, useState } from "react";
import { api } from "@/lib/api";
import { type TemplateInput } from "@/lib/templates";
import type { Journal } from "@/lib/journals";
import TemplateEditor from "@/components/TemplateEditor";
export default function JournalTemplateEditor({ journal, onSaved, onCancel }: { journal: Journal; onSaved: (journal: Journal) => void; onCancel: () => void }) {
  const [draft, setDraft] = useState<TemplateInput>(() => structuredClone({ name: journal.template_name, description: journal.template_description, layout: journal.template_layout }));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError("");
    try { onSaved(await api(`editor/journal/template?journal_id=${journal.id}`, draft, "PATCH")); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  return <>{error && <p className="message error" role="alert">{error}</p>}<TemplateEditor draft={draft} busy={busy} editing editorMode previewInfo={journal.journal_info} onChange={setDraft} onSave={save} onCancel={() => { if (window.confirm("Discard unsaved template changes?")) onCancel(); }} /></>;
}
