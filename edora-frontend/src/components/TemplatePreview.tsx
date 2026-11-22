import type { JournalInfo } from "@/lib/journals";
import JournalInformationSidebar from "@/components/JournalInformationSidebar";
import { getSectionColors, type TemplateLayout } from "@/lib/templates";
export default function TemplatePreview({ layout, compactInfo = false, journalInfo, editorEmail }: { layout: TemplateLayout; compactInfo?: boolean; journalInfo?: Partial<JournalInfo>; editorEmail?: string }) {
  const sidebar = layout.menu_position !== "top";
  const mainSections = layout.sections.filter(section => section.type !== "menu");
  const contentRow = mainSections.findIndex(section => section.type === "content") + 1;
  return <div className={`template-preview menu-${layout.menu_position}${compactInfo ? " admin-compact-info" : ""}`} aria-label="Website layout preview">
    {layout.sections.map((section, index) => {
      const colors = getSectionColors(section);
      const row = !sidebar ? index + 1 : section.type === "menu" ? contentRow : mainSections.findIndex(item => item.type === section.type) + 1;
      const column = !sidebar || (section.type !== "menu" && section.type !== "content") ? "1 / -1" : section.type === "menu" ? (layout.menu_position === "left" ? "1" : "2") : (layout.menu_position === "left" ? "2" : "1");
      return <div key={section.type} className={`template-block template-${section.type}`} style={{ gridRow: row, gridColumn: column, backgroundColor: colors.background_color, color: colors.text_color }}>
        {section.type === "content" && (layout.show_journal_info !== false || (layout.show_submissions ?? layout.show_journal_info) !== false || layout.show_downloads !== false) ? <div className="journal-content-with-info template-info-preview"><div><span className="template-block-label">content</span><strong>{section.title}</strong><p>{section.content}</p></div><JournalInformationSidebar showDownloads={layout.show_downloads !== false} showInfo={layout.show_journal_info !== false} showSubmissions={(layout.show_submissions ?? layout.show_journal_info) !== false} editorEmail={editorEmail ?? "editor@example.com"} info={journalInfo ?? (compactInfo ? { editor_in_chief: "Narjess ALOUI", frequency: "Four iss./ year", final_decision: "75 days", acceptance_rate: "15%", plagiarism: "<10%", language: "English", review_process: "Single-blind", open_access: "Yes", copyright: "CC-BY 4.0", eissn: "2323-5233" } : { editor_in_chief: "Editor-in-Chief", frequency: "Four issues / year", language: "English", open_access: "Yes", copyright: "CC-BY 4.0" })} /></div> : <><span className="template-block-label">{section.type}</span>{section.type !== "menu" && <strong>{section.title}</strong>}
        {section.type === "menu" ? <div className="template-menu-items">{section.content.split("\n").filter(Boolean).map((item, i) => <span key={i}>{item}</span>)}</div> : <p>{section.content}</p>}</>}
      </div>;
    })}
  </div>;
}
