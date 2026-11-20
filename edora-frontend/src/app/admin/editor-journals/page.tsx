import AdminEditorJournals from "@/components/AdminEditorJournals";
export default function EditorTemplatesPage() {
  return <section><div className="admin-page-heading"><div><span className="eyebrow">Editor websites</span><h1>Editor Journal</h1><p>Browse editor journals by editor or creation date.</p></div><span className="journal-private-badge">View only</span></div><AdminEditorJournals /></section>;
}
