"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
const items = [
  { href: "/dashboard/journal", title: "Journal", detail: "Build your journal website", icon: <><rect x="3" y="3" width="18" height="18" rx="2" /><path d="M3 9h18M9 9v12" /></> },
  { href: "/dashboard/articles", title: "Articles", detail: "Headings, authors & PDFs", icon: <><path d="M14 2H6v20h14V8zM14 2v6h6M8 13h8M8 17h6" /></> },
  { href: "/dashboard/volumes", title: "Volumes", detail: "Organize journal articles", icon: <><rect x="3" y="3" width="18" height="18" rx="2" /><path d="M3 9h18M9 9v12" /></> },
];
export default function EditorNavigation() {
  const path = usePathname();
  return <nav className="admin-navigation" aria-label="Editor navigation">{items.map(item => <Link key={item.href} href={item.href} aria-current={path === item.href || (item.href === "/dashboard/journal" && path.startsWith(`${item.href}/`)) ? "page" : undefined}><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" aria-hidden="true">{item.icon}</svg><span><strong>{item.title}</strong><small>{item.detail}</small></span></Link>)}</nav>;
}
