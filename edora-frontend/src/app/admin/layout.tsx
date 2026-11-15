import { redirect } from "next/navigation";
import { currentUser } from "@/lib/session";
import AdminNavigation from "@/components/AdminNavigation";
export const dynamic = "force-dynamic";
export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  const user = await currentUser();
  if (!user) redirect("/login");
  if (user.role !== "super_admin") redirect("/dashboard");
  return <div className="admin-shell"><aside className="admin-sidebar"><div className="admin-workspace"><span className="admin-workspace-mark">e</span><div><strong>Edora workspace</strong><span>Super administrator</span></div></div><p className="admin-nav-label">Management</p><AdminNavigation /><div className="admin-sidebar-account"><span className="admin-avatar">SA</span><div><strong>Super admin</strong><span>{user.email}</span></div></div></aside><div className="admin-content"><div className="admin-topbar"><span>Workspace / Administration</span><span className="admin-access-badge">Super admin access</span></div><div className="admin-content-body">{children}</div></div></div>;
}
