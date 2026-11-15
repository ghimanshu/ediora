import TemplateManagement from "@/components/TemplateManagement";
export default function Page() {
  return <section><div className="admin-page-heading"><div><span className="eyebrow">Website management</span><h1>Manage website templates</h1><p>Create reusable website layouts with a header, menu, content, and footer.</p></div><span className="admin-section-label">Templates</span></div><TemplateManagement /></section>;
}
