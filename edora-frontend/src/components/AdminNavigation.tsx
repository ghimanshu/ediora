"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
const groups = [
  { title: "Management", items: [
    { href: "/admin", title: "Users", detail: "Manage users", icon: "users" },
    { href: "/admin/templates", title: "Templates", detail: "Manage website templates", icon: "templates" },
    { href: "/admin/pages", title: "Pages", detail: "Manage web pages", icon: "pages" },
  ] },
  { title: "Editor", items: [
    { href: "/admin/editor-journals", title: "Journal", detail: "View editor journals", icon: "pages" },
  ] },
];
function Icon({ name }: { name: string }) {
  return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{name === "users" ? <><circle cx="9" cy="8" r="3" /><path d="M3 21v-2a6 6 0 0 1 12 0v2M16 5a3 3 0 0 1 0 6m3 10v-2a6 6 0 0 0-3-5" /></> : name === "templates" ? <><rect x="3" y="3" width="18" height="18" rx="2" /><path d="M3 9h18M9 9v12" /></> : <><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6M8 13h8M8 17h6" /></>}</svg>;
}
export default function AdminNavigation() {
  const pathname = usePathname();
  return <div className="admin-nav-groups">{groups.map(group => <section className="admin-nav-group" key={group.title}><p className="admin-nav-label" id={`admin-group-${group.title.toLowerCase()}`}>{group.title}</p><nav className="admin-navigation" aria-labelledby={`admin-group-${group.title.toLowerCase()}`}>{group.items.map(item => <Link key={item.href} href={item.href} aria-current={(pathname === item.href || (item.href !== "/admin" && pathname.startsWith(`${item.href}/`))) ? "page" : undefined}><Icon name={item.icon} /><span><strong>{item.title}</strong><small>{item.detail}</small></span></Link>)}</nav></section>)}</div>;
}
