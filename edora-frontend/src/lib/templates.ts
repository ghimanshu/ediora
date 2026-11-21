export type SectionType = "header" | "menu" | "content" | "footer";
export type TemplateSection = { type: SectionType; title: string; content: string; background_color?: string; text_color?: string };
export type TemplateLayout = { show_journal_info?: boolean; show_submissions?: boolean | null; menu_position: "top" | "left" | "right"; sections: TemplateSection[] };
export type WebsiteTemplate = { id: number; name: string; description: string; layout: TemplateLayout; created_at: string; updated_at: string };
export type TemplateInput = Pick<WebsiteTemplate, "name" | "description" | "layout">;
export function newTemplate(): TemplateInput {
  return { name: "", description: "", layout: { menu_position: "top", sections: [
    { type: "header", title: "Your website", content: "A place for your ideas." },
    { type: "menu", title: "Explore", content: "Home\nAbout\nArticles\nContact" },
    { type: "content", title: "Welcome to your website", content: "Share your stories and showcase your work." },
    { type: "footer", title: "Stay connected", content: "Your website. All rights reserved." },
  ] } };
}

export const sectionColors: Record<SectionType, { background_color: string; text_color: string }> = {
  header: { background_color: "#244c40", text_color: "#ffffff" },
  menu: { background_color: "#e9e4d9", text_color: "#6b604a" },
  content: { background_color: "#ffffff", text_color: "#243b36" },
  footer: { background_color: "#dfe9e3", text_color: "#496453" },
};
export function getSectionColors(section: TemplateSection) {
  const defaults = sectionColors[section.type];
  return {
    background_color: /^#[0-9a-f]{6}$/i.test(section.background_color ?? "") ? section.background_color! : defaults.background_color,
    text_color: /^#[0-9a-f]{6}$/i.test(section.text_color ?? "") ? section.text_color! : defaults.text_color,
  };
}
