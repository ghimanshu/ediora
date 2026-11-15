"use client";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
type User = { id: number; first_name: string; last_name: string; email: string; phone: string; gender: string; role: string; is_active: boolean; is_verified: boolean };
const pageSize = 10;
export default function UserManagement() {
  const [users, setUsers] = useState<User[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [editing, setEditing] = useState<User | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const data = await api(`admin/users?offset=${offset}&limit=${pageSize}&search=${encodeURIComponent(query)}`);
      if (!data.items.length && offset > 0) { setOffset(Math.max(0, offset - pageSize)); return; }
      setUsers(data.items); setTotal(data.total);
    } catch (e) { setError((e as Error).message); }
    finally { setLoading(false); }
  }, [offset, query]);
  useEffect(() => { void load(); }, [load]);
  function profile(user: User) {
    return { first_name: user.first_name, last_name: user.last_name, email: user.email, phone: user.phone, gender: user.gender, is_active: user.is_active };
  }
  async function mutate(user: User, action: "save" | "toggle" | "delete", form?: HTMLFormElement) {
    if (action === "delete" && !window.confirm(`Permanently delete ${user.email}? This cannot be undone.`)) return;
    setBusy(true); setError(""); setMessage("");
    try {
      if (action === "delete") await api(`admin/users/${user.id}`, undefined, "DELETE");
      else {
        const data = form ? Object.fromEntries(new FormData(form)) : {};
        await api(`admin/users/${user.id}`, { ...profile(user), ...data, is_active: action === "toggle" ? !user.is_active : user.is_active }, "PATCH");
      }
      setEditing(null); setMessage(action === "delete" ? "User deleted." : "User updated. Email changes require verification again.");
      await load();
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  function save(event: FormEvent<HTMLFormElement>) { event.preventDefault(); if (editing) void mutate(editing, "save", event.currentTarget); }
  return <div className="admin-panel">
    <form className="admin-toolbar" onSubmit={e => { e.preventDefault(); setOffset(0); setQuery(search.trim()); }}>
      <label>Search users<input type="search" value={search} onChange={e => setSearch(e.target.value)} maxLength={254} placeholder="Name or email" /></label>
      <button disabled={busy || loading}>Search</button><button type="button" className="secondary" disabled={busy || loading} onClick={() => void load()}>Refresh</button>
    </form>
    {error && <p className="message error" role="alert">{error}</p>}{message && <p className="message" role="status">{message}</p>}
    {loading ? <p role="status">Loading users…</p> : <><p>{total} registered {total === 1 ? "user" : "users"}</p><div className="table-scroll"><table><thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Status</th><th>Verified</th><th>Actions</th></tr></thead><tbody>
      {users.map(user => <tr key={user.id}><td>{user.first_name} {user.last_name}</td><td>{user.email}</td><td>{user.role === "super_admin" ? "Super admin" : "Editor"}</td><td><span className={`admin-status ${user.is_active ? "active" : "inactive"}`}>{user.is_active ? "Active" : "Inactive"}</span></td><td>{user.is_verified ? "Yes" : "No"}</td><td>{user.role === "super_admin" ? "Protected account" : <div className="admin-actions"><button className="small" disabled={busy} onClick={() => setEditing(user)}>Edit</button><button className="small" disabled={busy} onClick={() => void mutate(user, "toggle")}>{user.is_active ? "Make inactive" : "Activate"}</button><button className="small danger" disabled={busy} onClick={() => void mutate(user, "delete")}>Delete</button></div>}</td></tr>)}
    </tbody></table></div>{!users.length && <p>No users found.</p>}<div className="admin-actions"><button disabled={busy || offset === 0} onClick={() => setOffset(Math.max(0, offset - pageSize))}>Previous</button><span>Page {Math.floor(offset / pageSize) + 1}</span><button disabled={busy || offset + pageSize >= total} onClick={() => setOffset(offset + pageSize)}>Next</button></div></>}
    {editing && <section className="card" aria-labelledby="edit-title"><h2 id="edit-title">Edit {editing.email}</h2><form key={editing.id} onSubmit={save}><div className="fields">
      <label>First name<input name="first_name" defaultValue={editing.first_name} minLength={1} maxLength={80} required /></label><label>Last name<input name="last_name" defaultValue={editing.last_name} minLength={1} maxLength={80} required /></label>
      <label>Email<input name="email" type="email" defaultValue={editing.email} maxLength={254} required /></label><label>Phone<input name="phone" type="tel" defaultValue={editing.phone} minLength={7} maxLength={25} required /></label>
      <label>Gender<select name="gender" defaultValue={editing.gender}>{["Male", "Female", "Other", "Prefer not to say"].map(g => <option key={g}>{g}</option>)}</select></label>
    </div><p>Changing the email signs the user out and requires them to verify the new address using Resend verification email.</p><button disabled={busy}>Save changes</button><button type="button" className="secondary" disabled={busy} onClick={() => setEditing(null)}>Cancel</button></form></section>}
  </div>;
}
