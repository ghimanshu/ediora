import { getSectionColors, type TemplateLayout } from "@/lib/templates";
export default function TemplatePreview({ layout }: { layout: TemplateLayout }) {
  const sidebar = layout.menu_position !== "top";
  const mainSections = layout.sections.filter(section => section.type !== "menu");
  const contentRow = mainSections.findIndex(section => section.type === "content") + 1;
  return <div className={`template-preview menu-${layout.menu_position}`} aria-label="Website layout preview">
    {layout.sections.map((section, index) => {
      const colors = getSectionColors(section);
      const row = !sidebar ? index + 1 : section.type === "menu" ? contentRow : mainSections.findIndex(item => item.type === section.type) + 1;
      const column = !sidebar || (section.type !== "menu" && section.type !== "content") ? "1 / -1" : section.type === "menu" ? (layout.menu_position === "left" ? "1" : "2") : (layout.menu_position === "left" ? "2" : "1");
      return <div key={section.type} className={`template-block template-${section.type}`} style={{ gridRow: row, gridColumn: column, backgroundColor: colors.background_color, color: colors.text_color }}>
        <span className="template-block-label">{section.type}</span><strong>{section.title}</strong>
        {section.type === "menu" ? <div className="template-menu-items">{section.content.split("\n").filter(Boolean).map((item, i) => <span key={i}>{item}</span>)}</div> : <p>{section.content}</p>}
      </div>;
    })}
  </div>;
}
