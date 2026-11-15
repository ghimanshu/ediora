"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function Header() {
  const path = usePathname(); const router = useRouter();
  const [signedIn, setSignedIn] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => { let live = true; api("auth/me").then((user) => { if (live) { setSignedIn(true); setIsAdmin(user.role === "super_admin"); } }).catch(() => { if (live) setSignedIn(false); }); return () => { live = false; }; }, [path]);
  async function logout() {
    try { await api("auth/logout", {}); setSignedIn(false); setError(""); router.push("/login"); router.refresh(); }
    catch (e) { setError((e as Error).message); }
  }
  return <header><Link className="brand" href="/">edora<span>EDITOR COMMUNITY</span></Link>
    <nav aria-label="Main navigation">{[["/", "Home"], ["/about", "About us"], ["/editors", "For editors"], ["/contact", "Contact us"]].map(([href, text]) => <Link aria-current={path === href ? "page" : undefined} key={href} href={href}>{text}</Link>)}
    {signedIn ? <><Link href={isAdmin ? "/admin" : "/dashboard"}>{isAdmin ? "Admin" : "My account"}</Link><button className="small" onClick={logout}>Log out</button></> : <><Link href="/login">Log in</Link><Link className="button small" href="/register">Become an editor</Link></>}</nav>{error && <p role="alert">{error}</p>}</header>;
}
