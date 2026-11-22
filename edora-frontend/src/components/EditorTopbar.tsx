"use client";
import { usePathname } from "next/navigation";
export default function EditorTopbar() {
  const pathname = usePathname();
  const page = pathname === "/dashboard/articles" ? { title: "Manage Articles", description: "Create articles with multiple authors and a PDF document", actions: "article-topbar-actions" } : pathname === "/dashboard/volumes" ? { title: "Manage Volumes", description: "Group articles into volumes for your journal", actions: "volume-topbar-actions" } : null;
  return <div className="admin-topbar">{page ? <><div className="editor-topbar-title"><h1 className="editor-topbar-heading">{page.title}</h1><span className="editor-topbar-description">- {page.description}</span></div><div id={page.actions} className="admin-actions editor-topbar-actions" /></> : <><span>Workspace / Editor dashboard</span><span className="admin-access-badge">Editor account</span></>}</div>;
}
