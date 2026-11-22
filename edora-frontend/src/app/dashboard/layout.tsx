import { redirect } from "next/navigation";
import { currentUser } from "@/lib/session";
import EditorTopbar from "@/components/EditorTopbar";
import EditorNavigation from "@/components/EditorNavigation";
export const dynamic = "force-dynamic";
export default async function EditorLayout({ children }: { children: React.ReactNode }) {
  const editor = await currentUser();
  if (!editor) redirect("/login");
  if (editor.role !== "editor") redirect("/admin");
  return <div className="admin-shell editor-shell"><aside className="admin-sidebar"><div className="admin-workspace"><span className="admin-workspace-mark">e</span><div><strong>Edora workspace</strong><span>Editor portal</span></div></div><p className="admin-nav-label">Your workspace</p><EditorNavigation /><div className="admin-sidebar-account"><span className="admin-avatar">ED</span><div><strong>{editor.first_name} {editor.last_name}</strong><span>{editor.email}</span></div></div></aside><div className="admin-content"><EditorTopbar /><div className="admin-content-body">{children}</div></div></div>;
}
