"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
const items = [
  { href: "/dashboard", title: "Profile", detail: "Manage your profile", icon: <><circle cx="12" cy="8" r="4" /><path d="M4 22v-2a8 8 0 0 1 16 0v2" /></> },
  { href: "/dashboard/journal", title: "Journal", detail: "Build your journal website", icon: <><rect x="3" y="3" width="18" height="18" rx="2" /><path d="M3 9h18M9 9v12" /></> },
];
export default function EditorNavigation() {
  const path = usePathname();
  return <nav className="admin-navigation" aria-label="Editor navigation">{items.map(item => <Link key={item.href} href={item.href} aria-current={path === item.href || (item.href === "/dashboard/journal" && path.startsWith(`${item.href}/`)) ? "page" : undefined}><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" aria-hidden="true">{item.icon}</svg><span><strong>{item.title}</strong><small>{item.detail}</small></span></Link>)}</nav>;
}
