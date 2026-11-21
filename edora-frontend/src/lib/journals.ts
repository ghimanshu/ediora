export type JournalInfo = { editor_in_chief: string; frequency: string; final_decision: string; acceptance_rate: string; plagiarism: string; language: string; review_process: string; open_access: string; copyright: string; eissn: string };
import { getSectionColors, type TemplateLayout } from "@/lib/templates";
export type JournalPage = { id: number; title: string; slug: string; content_html: string; created_at: string; updated_at: string };
export type PageChoice = Pick<JournalPage, "id" | "title" | "slug">;
export type JournalStatus = "Draft" | "Published" | "NotPublished";
export type Journal = { menu_order: string[]; journal_info: JournalInfo; status: JournalStatus; editor_code: string; slug: string; preview_path: string; id: number; name: string; template_name: string; template_description: string; template_layout: TemplateLayout; pages: JournalPage[]; created_at: string; updated_at: string };
function escapeHtml(text: string) { return text.replace(/[&<>"']/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]!)); }
export function journalPreviewDocument(journal: Journal, page: JournalPage) {
  const layout = journal.template_layout;
  const sidebar = layout.menu_position !== "top";
  const main = layout.sections.filter(section => section.type !== "menu");
  const contentRow = main.findIndex(section => section.type === "content") + 1;
  const blocks = layout.sections.map((section, index) => {
    const colors = getSectionColors(section);
    const row = !sidebar ? index + 1 : section.type === "menu" ? contentRow : main.findIndex(item => item.type === section.type) + 1;
    const column = !sidebar || !["menu", "content"].includes(section.type) ? "1 / -1" : section.type === "menu" ? (layout.menu_position === "left" ? "1" : "2") : (layout.menu_position === "left" ? "2" : "1");
    const body = section.type === "content" ? page.content_html : section.type === "menu" ? journal.pages.map(item => `<p>${escapeHtml(item.title)}</p>`).join("") : `<h2>${escapeHtml(section.title)}</h2><p>${escapeHtml(section.content).replace(/\n/g, "<br>")}</p>`;
    return `<div style="grid-row:${row};grid-column:${column};background:${colors.background_color};color:${colors.text_color};padding:20px;min-width:0">${body}</div>`;
  }).join("");
  return `<!doctype html><html><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src 'none';style-src 'unsafe-inline'"><style>body{margin:0;font:14px/1.7 system-ui;overflow-wrap:anywhere}.site{display:grid;grid-template-columns:${!sidebar ? "1fr" : layout.menu_position === "left" ? "180px minmax(0,1fr)" : "minmax(0,1fr) 180px"};gap:6px;background:#f3f5f4;padding:6px}h1{font-size:26px}h2{font-size:20px}pre{white-space:pre-wrap}a{color:inherit}@media(max-width:500px){.site{grid-template-columns:${sidebar ? "minmax(0,1fr) minmax(0,2fr)" : "1fr"}}}</style></head><body><div class="site">${blocks}</div></body></html>`;
}

export type PublicJournal = { menu_order: string[]; editor_email: string; journal_info: JournalInfo; name: string; slug: string; editor_code: string; template_layout: TemplateLayout; pages: Pick<JournalPage, "title" | "slug" | "content_html">[] };
