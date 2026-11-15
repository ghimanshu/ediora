"use client";
import { useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
export default function VerifyEmail() {
  const [message, setMessage] = useState(""); const [busy, setBusy] = useState(false); const [done, setDone] = useState(false);
  async function verify() {
    const token = new URLSearchParams(window.location.search).get("token");
    if (!token) { setMessage("No verification token found. Request a new link below."); return; }
    setBusy(true);
    try { const result = await api("auth/verify-email", { token }); setMessage(result.message); setDone(true); window.history.replaceState({}, "", "/verify-email"); }
    catch (e) { setMessage((e as Error).message); }
    finally { setBusy(false); }
  }
  return <section className="form-panel"><span className="eyebrow">One final step</span><h1>Verify your email.</h1><p>Confirm your email address to activate your editor account.</p>{!done && <button disabled={busy} onClick={verify}>{busy ? "Verifying…" : "Verify my email"}</button>}{message && <p className="message" role="status">{message}</p>}<p><Link className="textlink" href="/login">Log in</Link> · <Link className="textlink" href="/resend-verification">Request a new link</Link></p></section>;
}
