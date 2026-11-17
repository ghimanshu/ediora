"use client";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
export type EditorProfileData = { first_name: string; last_name: string; email: string; phone: string; gender: string };
export default function EditorProfile({ initial }: { initial: EditorProfileData }) {
  const [draft, setDraft] = useState(initial);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const router = useRouter();
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError(""); setMessage("");
    try {
      const saved = await api("editor/profile", draft, "PATCH");
      if (!saved.is_verified) { router.push("/resend-verification"); router.refresh(); return; }
      setMessage("Your profile has been updated."); router.refresh();
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  return <section><div className="admin-page-heading"><div><span className="eyebrow">Your account</span><h1>My profile</h1><p>Keep your personal and contact details up to date.</p></div><span className="admin-section-label">Profile</span></div><div className="admin-panel editor-profile-panel">{error && <p className="message error" role="alert">{error}</p>}{message && <p className="message" role="status">{message}</p>}<form onSubmit={save}><fieldset className="template-fieldset" disabled={busy}><div className="fields">{([['first_name', 'First name'], ['last_name', 'Last name'], ['phone', 'Phone'], ['email', 'Email address']] as const).map(([key, title]) => <label key={key}>{title}<input name={key} value={draft[key]} type={key === "email" ? "email" : key === "phone" ? "tel" : "text"} required maxLength={key === "email" ? 254 : key === "phone" ? 25 : 80} minLength={key === "phone" ? 7 : 1} onChange={e => setDraft({ ...draft, [key]: e.target.value })} /></label>)}<label>Gender<select value={draft.gender} onChange={e => setDraft({ ...draft, gender: e.target.value })}>{["Male", "Female", "Other", "Prefer not to say"].map(value => <option key={value}>{value}</option>)}</select></label></div>{draft.email !== initial.email && <p className="message">Changing your email signs you out and sends a verification link to the new address. You will need to verify it before signing in again.</p>}<div className="template-save-actions"><button disabled={busy}>{busy ? "Saving…" : "Save profile"}</button></div></fieldset></form></div></section>;
}
