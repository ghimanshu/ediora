import type { CSSProperties } from "react";
import type { Metadata } from "next";
import { notFound, redirect } from "next/navigation";
import { getPublicJournal } from "@/lib/public-journal";
import { getSectionColors } from "@/lib/templates";
export const dynamic = "force-dynamic";
type Params = { editorCode: string; journalSlug: string; pageSlug: string };
export async function generateMetadata({ params }: { params: Promise<Params> }): Promise<Metadata> {
  const { editorCode, journalSlug, pageSlug } = await params;
  const journal = await getPublicJournal(editorCode, journalSlug);
  const title = journal.pages.find(page => page.slug === pageSlug.toLowerCase())?.title ?? (pageSlug.toLowerCase() === "archives" ? "Archives" : pageSlug.toLowerCase() === "current" ? "Current" : "Page");
  return { title: `${title} | ${journal.name}`, description: journal.name, robots: { index: false, follow: false } };
}
export default async function JournalWebsite({ params }: { params: Promise<Params> }) {
  const { editorCode, journalSlug, pageSlug } = await params;
  const journal = await getPublicJournal(editorCode, journalSlug);
  const slug = pageSlug.toLowerCase();
  const base = `/${editorCode}/${journalSlug}`;
  const page = journal.pages.find(item => item.slug === slug);
  if (!page && slug !== "current" && slug !== "archives") notFound();
  if (pageSlug !== slug) redirect(`${base}/${slug}`);
  const menu = journal.pages.map(item => ({ slug: item.slug, title: item.slug === "current" ? "Current" : item.slug === "archives" ? "Archives" : item.title }));
  for (const item of [{ slug: "current", title: "Current" }, { slug: "archives", title: "Archives" }]) if (!menu.some(existing => existing.slug === item.slug)) menu.push(item);
  const layout = journal.template_layout;
  const sidebar = layout.menu_position !== "top";
  const main = layout.sections.filter(section => section.type !== "menu");
  const contentRow = main.findIndex(section => section.type === "content") + 1;
  const columns = !sidebar ? "minmax(0, 1fr)" : layout.menu_position === "left" ? "220px minmax(0, 1fr)" : "minmax(0, 1fr) 220px";
  return <div className={`journal-website menu-${layout.menu_position}`} style={{ "--journal-columns": columns } as CSSProperties}>
    {layout.sections.map((section, index) => {
      const colors = getSectionColors(section);
      const row = !sidebar ? index + 1 : section.type === "menu" ? contentRow : main.findIndex(item => item.type === section.type) + 1;
      const column = !sidebar || !["menu", "content"].includes(section.type) ? "1 / -1" : section.type === "menu" ? (layout.menu_position === "left" ? "1" : "2") : (layout.menu_position === "left" ? "2" : "1");
      return <section key={section.type} className={`journal-website-section journal-website-${section.type}`} style={{ gridRow: row, gridColumn: column, backgroundColor: colors.background_color, color: colors.text_color }}>
        {section.type === "menu" ? <><h2>{section.title}</h2><nav className="journal-website-navigation" aria-label="Journal pages">{menu.map(item => <a href={`${base}/${item.slug}`} key={item.slug} aria-current={item.slug === slug ? "page" : undefined}>{item.title}</a>)}</nav></> : section.type === "content" ? <><h1>{page?.title ?? (slug === "current" ? "Current issue" : "Archives")}</h1>{page ? <div className="journal-website-html" dangerouslySetInnerHTML={{ __html: page.content_html }} /> : <div className="journal-website-empty"><h2>{slug === "current" ? "No current issue yet" : "No archived issues yet"}</h2><p>{slug === "current" ? "A current issue has not been added to this journal." : "Previous issues will appear here when they are available."}</p></div>}</> : <><h2>{section.title}</h2><p className="journal-website-section-text">{section.content}</p></>}
      </section>;
    })}
  </div>;
}
