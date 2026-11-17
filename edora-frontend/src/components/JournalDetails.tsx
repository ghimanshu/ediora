"use client";
import { useRef, useState, type KeyboardEvent } from "react";
import dynamic from "next/dynamic";
import JournalStatusBadge from "@/components/JournalStatusBadge";
import type { Journal } from "@/lib/journals";
const loading = () => <div className="admin-panel journal-section-loading" role="status">Loading section…</div>;
const JournalInfoPanel = dynamic(() => import("@/components/JournalInfoPanel"), { loading });
const JournalTemplatePanel = dynamic(() => import("@/components/JournalTemplatePanel"), { loading });
const JournalPagesPanel = dynamic(() => import("@/components/JournalPagesPanel"), { loading });
const JournalPreviewPanel = dynamic(() => import("@/components/JournalPreviewPanel"), { loading });
const sections = [
  { id: "info", title: "Journal Info", description: "Name, address & details", icon: "info" },
  { id: "template", title: "Journal Template", description: "Your personal design", icon: "template" },
  { id: "pages", title: "Journal Pages", description: "Content & page order", icon: "pages" },
  { id: "preview", title: "Preview", description: "View your website", icon: "preview" },
] as const;
type Section = typeof sections[number]["id"];
function SectionIcon({ icon }: { icon: string }) {
  return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{icon === "info" ? <><circle cx="12" cy="12" r="9" /><path d="M12 11v6M12 7h.01" /></> : icon === "template" ? <><rect x="3" y="3" width="18" height="18" rx="2" /><path d="M3 9h18M9 9v12" /></> : icon === "pages" ? <><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6M8 13h8M8 17h6" /></> : <><rect x="2" y="3" width="20" height="14" rx="2" /><path d="M8 21h8M12 17v4" /></>}</svg>;
}
export default function JournalDetails({ journal, onChanged }: { journal: Journal; onChanged: (journal: Journal) => void }) {
  const [active, setActive] = useState<Section>("info");
  const [visited, setVisited] = useState<Set<Section>>(() => new Set(["info"]));
  const [activePage, setActivePage] = useState(journal.pages[0]?.id ?? 0);
  const tabs = useRef<(HTMLButtonElement | null)[]>([]);
  function open(section: Section) { setVisited(current => new Set([...current, section])); setActive(section); }
  function keyDown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    let next = index;
    if (event.key === "ArrowRight") next = (index + 1) % sections.length;
    else if (event.key === "ArrowLeft") next = (index - 1 + sections.length) % sections.length;
    else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = sections.length - 1;
    else return;
    event.preventDefault(); tabs.current[next]?.focus(); open(sections[next].id);
  }
  return <div className="journal-manager"><div className="journal-manager-banner"><div><span className="eyebrow">Journal workspace</span><h2>{journal.name}</h2><JournalStatusBadge status={journal.status} /><p><span>{journal.pages.length} pages</span><span>Personal template</span><span>{journal.slug}</span></p></div><a className="button small" href={journal.preview_path} target="_blank" rel="noopener noreferrer">Preview journal ↗</a></div><div className="journal-section-tabs" role="tablist" aria-label="Journal management sections">{sections.map((section, index) => <button ref={element => { tabs.current[index] = element; }} key={section.id} type="button" role="tab" id={`journal-tab-${section.id}`} aria-selected={active === section.id} aria-controls={`journal-panel-${section.id}`} tabIndex={active === section.id ? 0 : -1} onClick={() => open(section.id)} onKeyDown={event => keyDown(event, index)}><span className="journal-section-icon"><SectionIcon icon={section.icon} /></span><span><strong>{section.title}</strong><small>{section.description}</small></span>{section.id === "pages" && <span className="journal-tab-count">{journal.pages.length}</span>}</button>)}</div>
    {sections.map(section => <div key={section.id} role="tabpanel" id={`journal-panel-${section.id}`} aria-labelledby={`journal-tab-${section.id}`} hidden={active !== section.id} tabIndex={0} className="journal-section-panel">{visited.has(section.id) && <>{section.id === "info" && <JournalInfoPanel journal={journal} onChanged={onChanged} />}{section.id === "template" && <JournalTemplatePanel journal={journal} onChanged={onChanged} />}{section.id === "pages" && <JournalPagesPanel journal={journal} onChanged={onChanged} onPreview={id => { setActivePage(id); open("preview"); }} />}{section.id === "preview" && <JournalPreviewPanel journal={journal} activePage={activePage} onPageChange={setActivePage} />}</>}</div>)}
  </div>;
}
