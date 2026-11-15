import UserManagement from "@/components/UserManagement";
export default function AdminPage() {
  return <section><div className="admin-page-heading"><div><span className="eyebrow">User directory</span><h1>Manage users</h1><p>Manage registered profiles and account access.</p></div><span className="admin-section-label">Users</span></div><UserManagement /></section>;
}
