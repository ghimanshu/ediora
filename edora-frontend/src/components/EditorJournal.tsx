"use client";
import dynamic from "next/dynamic";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import type { WebsiteTemplate } from "@/lib/templates";
import type { Journal, PageChoice } from "@/lib/journals";
import TemplatePreview from "@/components/TemplatePreview";
import type { NewJournalPage } from "@/components/JournalNewPageForm";
const JournalNewPageForm = dynamic(() => import("@/components/JournalNewPageForm"), { ssr: false, loading: () => <p role="status">Loading page editor…</p> });
export default function EditorJournal() {
  const router = useRouter();
  const pageSelectionInitialized = useRef(false);
  const [templates, setTemplates] = useState<WebsiteTemplate[]>([]);
  const [pages, setPages] = useState<PageChoice[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<number | null>(null);
  const [selectedPages, setSelectedPages] = useState<number[]>([]);
  const [newPages, setNewPages] = useState<NewJournalPage[]>([]);
  const [pageForm, setPageForm] = useState<NewJournalPage | null>(null);
  const [name, setName] = useState("");
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function load() {
    setLoading(true); setError("");
    try {
      const [templateList, pageList] = await Promise.all([api("templates"), api("editor/pages")]);
      setTemplates(templateList); setPages(pageList);
      setSelectedTemplate(current => templateList.some((item: WebsiteTemplate) => item.id === current) ? current : null);
      if (!pageSelectionInitialized.current) {
        setSelectedPages(pageList.map((page: PageChoice) => page.id).slice(0, 100));
        pageSelectionInitialized.current = true;
      } else {
        setSelectedPages(current => current.filter(id => pageList.some((item: PageChoice) => item.id === id)));
      }

    } catch (e) { setError((e as Error).message); }
    finally { setLoading(false); }
  }
  useEffect(() => { void load(); }, []);
  async function create() {
    setBusy(true); setError("");
    try { const created: Journal = await api("editor/journal", { name: name.trim(), template_id: selectedTemplate, page_ids: selectedPages, new_pages: newPages.map(({ title, slug, content_html }) => ({ title, slug, content_html })) }); router.push(`/dashboard/journal/${created.id}`); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  if (loading) return <p role="status">Loading your journal workspace…</p>;
  const totalPages = selectedPages.length + newPages.length;
  const totalNewHtml = newPages.reduce((sum, page) => sum + page.content_html.length, 0);
  const template = templates.find(item => item.id === selectedTemplate);
  return <>
    <Link href="/dashboard/journal" className="journal-back-link">← All journals</Link>
    {error && <p className="message error" role="alert">{error}</p>}
    <div className="journal-steps" aria-label="Journal creation steps">{["Choose a template", "Select pages", "Create journal"].map((title, index) => <span key={title} aria-current={step === index + 1 ? "step" : undefined}><b>{index + 1}</b>{title}</span>)}</div>
    <div className="template-library-toolbar"><p>Start with the admin library. Creating your journal makes separate copies for your account.</p><button className="small secondary" disabled={busy || !!pageForm} onClick={() => void load()}>Refresh library</button></div>
    {step === 1 && <section><h2>Choose your website template</h2><div className="template-library">{templates.map(item => <article className={`admin-panel template-card ${selectedTemplate === item.id ? "template-selected" : ""}`} key={item.id}><TemplatePreview layout={item.layout} /><div className="template-card-heading"><h2>{item.name}</h2><button disabled={busy} aria-pressed={selectedTemplate === item.id} onClick={() => setSelectedTemplate(item.id)}>{selectedTemplate === item.id ? "Selected" : "Select template"}</button></div><p>{item.description}</p></article>)}</div>{!templates.length && <p>No templates are available. Ask an administrator to add a template.</p>}<div className="admin-actions template-save-actions"><button disabled={!template || busy} onClick={() => setStep(2)}>Next: select pages</button></div></section>}
    {step === 2 && <section className="admin-panel"><div className="template-card-heading"><h2>Select or create pages</h2><button disabled={busy || !!pageForm || totalPages >= 100} onClick={() => { setError(""); setPageForm({ key: crypto.randomUUID(), title: "", slug: "", content_html: "<p></p>" }); }}>+ Create page</button></div><p className="template-help">Admin pages are selected by default. Deselect any you do not need, or create your own pages. Admin copies appear in selection order, followed by your new pages.</p><h3>Admin page library</h3><div className="journal-page-choices">{pages.map(page => <label key={page.id} className="journal-page-choice"><input type="checkbox" checked={selectedPages.includes(page.id)} disabled={busy || !!pageForm || (!selectedPages.includes(page.id) && totalPages >= 100)} onChange={e => setSelectedPages(current => e.target.checked ? [...current, page.id] : current.filter(id => id !== page.id))} /><span><strong>{page.title}</strong><small>{page.menu_group ? `${page.menu_group} / ` : ""}{page.slug}</small></span>{selectedPages.includes(page.id) && <span className="admin-access-badge">{selectedPages.indexOf(page.id) + 1}</span>}</label>)}</div>{!pages.length && <p>No admin pages are available. You can create your own pages below.</p>}
      <h3>Your new private pages</h3>{!newPages.length && !pageForm && <p>No custom pages added yet. Use Create page to write your own content.</p>}{newPages.length > 0 && <div className="table-scroll"><table><thead><tr><th>Page</th><th>URL slug</th><th>Actions</th></tr></thead><tbody>{newPages.map(page => <tr key={page.key}><td>{page.title}</td><td>{page.slug}</td><td><div className="admin-actions"><button className="small" disabled={busy || !!pageForm} onClick={() => setPageForm({ ...page })}>Edit draft</button><button className="small danger" disabled={busy || !!pageForm} onClick={() => { if (window.confirm(`Remove "${page.title}" from this journal draft?`)) setNewPages(current => current.filter(item => item.key !== page.key)); }}>Remove</button></div></td></tr>)}</tbody></table></div>}
      {pageForm && <JournalNewPageForm key={pageForm.key} initial={pageForm} existingSlugs={[...pages.filter(page => selectedPages.includes(page.id)).map(page => page.slug), ...newPages.filter(page => page.key !== pageForm.key).map(page => page.slug)]} onCancel={() => setPageForm(null)} onSave={page => { const combined = newPages.filter(item => item.key !== page.key).reduce((sum, item) => sum + item.content_html.length, 0) + page.content_html.length; if (combined > 1000000) { setError("Combined new page HTML must not exceed 1,000,000 characters."); return; } setNewPages(current => current.some(item => item.key === page.key) ? current.map(item => item.key === page.key ? page : item) : [...current, page]); setPageForm(null); setError(""); }} />}
      <p>{selectedPages.length} admin pages + {newPages.length} new pages = {totalPages} / 100 pages</p><p className="template-help">New pages stay in this draft until you create your journal. Refreshing the browser discards unsaved drafts.</p><div className="admin-actions template-save-actions"><button className="secondary" disabled={busy || !!pageForm} onClick={() => setStep(1)}>Back</button><button disabled={busy || !!pageForm || !totalPages || totalNewHtml > 1000000} onClick={() => { const slugs = [...pages.filter(page => selectedPages.includes(page.id)).map(page => page.slug), ...newPages.map(page => page.slug)]; if (new Set(slugs).size !== slugs.length) { setError("Each selected or new page must have a different URL slug. Edit the matching custom page slug or deselect the admin page."); return; } setError(""); setStep(3); }}>Next: create journal</button></div></section>}
    {step === 3 && <section className="admin-panel"><h2>Make this journal yours</h2><form onSubmit={e => { e.preventDefault(); void create(); }}><fieldset disabled={busy} className="template-fieldset"><label>Journal name<input required maxLength={150} value={name} onChange={e => setName(e.target.value)} placeholder="My research journal" /></label><div className="journal-review"><p><strong>Template:</strong> {template?.name ?? "Please choose a template"}</p><strong>Pages to copy or create:</strong><ol>{selectedPages.map(id => <li key={id}>{pages.find(item => item.id === id)?.title}</li>)}{newPages.map(page => <li key={page.key}>{page.title} <span className="admin-access-badge">New private page</span></li>)}</ol></div><p className="message">Your template, colors, sections, selected admin pages, and new pages will be saved privately for your account. You can edit them afterward without changing the shared library.</p><div className="admin-actions template-save-actions"><button className="secondary" type="button" onClick={() => setStep(2)}>Back</button><button disabled={busy || !template || !totalPages || !name.trim()}>{busy ? "Creating copies…" : "Create my journal"}</button></div></fieldset></form></section>}
  </>;
}
