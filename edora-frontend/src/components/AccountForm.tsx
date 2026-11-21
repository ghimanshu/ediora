"use client";
import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
export default function AccountForm({ mode }: { mode: "login" | "register" | "resend" | "contact" }) {
  const [message, setMessage] = useState(""); const [error, setError] = useState(false); const [busy, setBusy] = useState(false);
  const router = useRouter();
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault(); const form = e.currentTarget; const data = Object.fromEntries(new FormData(form));
    setBusy(true); setMessage(""); setError(false);
    try {
      if (mode === "register" && data.password !== data.confirmPassword) throw new Error("Passwords do not match");
      delete data.confirmPassword;
      const path = mode === "contact" ? "contact" : `auth/${mode === "resend" ? "resend-verification" : mode}`;
      const result = await api(path, data);
      if (mode === "login") { const user = await api("auth/me"); router.push(user.role === "super_admin" ? "/admin" : "/dashboard/journal"); router.refresh(); }
      else { setMessage(result.message); form.reset(); }
    } catch (e) { setMessage((e as Error).message); setError(true); }
    finally { setBusy(false); }
  }
  const title = { login: "Welcome back", register: "Create your editor account", resend: "Verify your email", contact: "Let’s talk." }[mode];
  return <section className={mode === "contact" ? "form-panel" : `form-panel auth-panel auth-${mode}`}>{mode === "login" ? <div className="login-card-header"><span className="login-card-mark" aria-hidden="true"><svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6"><path d="M12 5v15M3 4l9 2 9-2v15l-9 2-9-2V4Z" /></svg></span><div><strong>Edora publishing portal</strong><p>Your journals. Your publishing workspace.</p></div></div> : <span className="eyebrow">Edora community</span>}<h1>{title}</h1><p>{mode === "register" ? "Join Edora and start managing your journals." : mode === "contact" ? "Send a message to the Edora team." : mode === "resend" ? "Enter your email to receive a new verification link." : "Sign in to your publishing workspace."}</p>
    <form onSubmit={submit}><div className="fields">
      {mode === "register" && <><label>First name<input name="first_name" autoComplete="given-name" maxLength={80} required /></label><label>Last name<input name="last_name" autoComplete="family-name" maxLength={80} required /></label><label>Phone<input name="phone" type="tel" autoComplete="tel" minLength={7} maxLength={25} required /></label><label>Gender<select name="gender" required defaultValue=""><option value="" disabled>Select an option</option>{["Male", "Female", "Other", "Prefer not to say"].map(g => <option key={g}>{g}</option>)}</select></label></>}
      {mode === "contact" && <label className="wide">Name<input name="name" autoComplete="name" maxLength={100} required /></label>}
      <label className="wide">Email address<input name="email" type="email" autoComplete="email" maxLength={254} required /></label>
      {(mode === "login" || mode === "register") && <label className={mode === "register" ? "" : "wide"}>Password<input name="password" type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} minLength={mode === "register" ? 12 : 1} maxLength={128} required />{mode === "register" && <small>Use at least 12 characters.</small>}</label>}
      {mode === "register" && <label>Confirm password<input name="confirmPassword" type="password" autoComplete="new-password" minLength={12} maxLength={128} required /></label>}
      {mode === "contact" && <label className="wide">Message<textarea name="message" minLength={10} maxLength={5000} required /></label>}
    </div><button disabled={busy} type="submit">{busy ? "Please wait…" : { login: "Log in", register: "Create editor account", resend: "Send verification email", contact: "Send message" }[mode]}</button></form>
    {message && <p role={error ? "alert" : "status"} className={`message ${error ? "error" : ""}`}>{message}</p>}
    {mode === "login" && <><p>New to Edora? <Link className="textlink" href="/register">Register as an editor</Link></p><Link className="textlink" href="/resend-verification">Resend verification email</Link></>}
    {(mode === "register" || mode === "resend") && <p><Link className="textlink" href="/login">Back to log in</Link> · <Link className="textlink" href="/resend-verification">Resend email</Link></p>}
  </section>;
}
