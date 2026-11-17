import Link from "next/link";
import JournalLibrary from "@/components/JournalLibrary";
export default function JournalsPage() {
  return <section><div className="admin-page-heading"><div><span className="eyebrow">Your websites</span><h1>My journals</h1><p>Select a journal to manage its information, template, pages, and preview.</p></div><Link className="button" href="/dashboard/journal/new">+ Create journal</Link></div><JournalLibrary /></section>;
}
