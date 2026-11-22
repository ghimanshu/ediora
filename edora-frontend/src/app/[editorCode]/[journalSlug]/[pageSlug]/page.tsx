import JournalNavigation from "@/components/JournalNavigation";
import JournalSubmissionForm from "@/components/JournalSubmissionForm";
import JournalInformationSidebar from "@/components/JournalInformationSidebar";
import JournalPublicationFeed from "@/components/JournalPublicationFeed";
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
  const title = journal.pages.find(page => page.slug === pageSlug.toLowerCase())?.title ?? (pageSlug.toLowerCase() === "archives" ? "Archives" : pageSlug.toLowerCase() === "current" ? "Current" : pageSlug.toLowerCase() === "submission" ? "Submission" : "Page");
  return { title: `${title} | ${journal.name}`, description: journal.name, robots: { index: false, follow: false } };
}
export default async function JournalWebsite({ params }: { params: Promise<Params> }) {
  const { editorCode, journalSlug, pageSlug } = await params;
  const journal = await getPublicJournal(editorCode, journalSlug);
  const slug = pageSlug.toLowerCase();
  const inactiveSlugs = journal.inactive_page_slugs ?? [];
  if (inactiveSlugs.includes(slug) || (slug === "submission" && inactiveSlugs.includes("submissions"))) notFound();
  const base = `/${editorCode}/${journalSlug}`;
  const isHome = slug === (journal.pages.find(item => item.slug === "home")?.slug ?? journal.pages[0]?.slug);
  const editorInChief = journal.journal_info?.editor_in_chief?.trim();
  const page = journal.pages.find(item => item.slug === slug);
  if (!page && slug !== "current" && slug !== "archives" && slug !== "submission") notFound();
  if (pageSlug !== slug) redirect(`${base}/${slug}`);
  const menu = journal.pages.map(item => ({ menu_group: item.menu_group, slug: item.slug, title: item.slug === "current" ? "Current" : item.slug === "archives" ? "Archives" : item.title }));
  for (const item of [{ slug: "current", title: "Current" }, { slug: "archives", title: "Archives" }]) if (!inactiveSlugs.includes(item.slug) && !menu.some(existing => existing.slug === item.slug)) menu.push({ ...item, menu_group: "" });
  if (slug === "submission" && !page) {
    const existingSubmission = journal.pages.find(item => item.slug === "submissions");
    if (existingSubmission) redirect(`${base}/submissions`);
  }
  if (!inactiveSlugs.some(item => ["submission", "submissions"].includes(item)) && !menu.some(item => ["submission", "submissions"].includes(item.slug))) menu.push({ slug: "submission", title: "Submission", menu_group: "" });
  const savedOrder = journal.menu_order ?? [];
  menu.sort((a, b) => (savedOrder.includes(a.slug) ? savedOrder.indexOf(a.slug) : savedOrder.length) - (savedOrder.includes(b.slug) ? savedOrder.indexOf(b.slug) : savedOrder.length));
  const layout = journal.template_layout;
  const showInfo = layout.show_journal_info !== false;
  const showSubmissions = (layout.show_submissions ?? layout.show_journal_info) !== false && !inactiveSlugs.some(item => ["submission", "submissions"].includes(item));
  const showDownloads = layout.show_downloads !== false;
  const hasRightPanel = showInfo || showSubmissions || showDownloads;
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
        {section.type === "menu" ? <JournalNavigation items={menu} base={base} active={slug} /> : section.type === "content" ? <div className={hasRightPanel ? "journal-content-with-info" : ""}><div className="journal-main-content">{page && <div className="journal-website-html" dangerouslySetInnerHTML={{ __html: (slug === "current" || slug === "archives") ? page.content_html.replace(/^\s*<h1\b[^>]*>[\s\S]*?<\/h1>/i, "") : page.content_html }} />}{slug === "contact-us" && <p className="journal-contact-email"><strong>Editorial office:</strong> <a href={`mailto:${journal.editor_email}`}>{journal.editor_email}</a></p>}{["submission", "submissions"].includes(slug) && <><h2>Submit your manuscript</h2><JournalSubmissionForm editorCode={editorCode} journalSlug={journalSlug} /></>}{(slug === "current" || slug === "archives") && <JournalPublicationFeed key={`${editorCode}/${journalSlug}/${slug}`} editorCode={editorCode} journalSlug={journalSlug} kind={slug} />}</div>{hasRightPanel && <JournalInformationSidebar showDownloads={showDownloads} submissionPath={`${base}/${journal.pages.some(item => item.slug === "submissions") ? "submissions" : "submission"}`} showInfo={showInfo} showSubmissions={showSubmissions} info={journal.journal_info} editorEmail={journal.editor_email} />}</div> : section.type === "header" ? <div className="journal-site-header"><div className="journal-site-brand"><h2>{section.title}</h2><p className="journal-website-section-text">{section.content}</p></div>{isHome && editorInChief && <div className="journal-header-chief"><strong>Editor-in-Chief:</strong><span>{editorInChief}</span></div>}</div> : <><h2>{section.title}</h2><p className="journal-website-section-text">{section.content}</p></>}
      </section>;
    })}
  </div>;
}
