"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import { api } from "@/lib/api";
import type { Journal } from "@/lib/journals";
const JournalDetails = dynamic(() => import("@/components/JournalDetails"), { loading: () => <p role="status">Loading journal tools…</p> });
export default function JournalWorkspace({ journalId }: { journalId: number }) {
  const [journal, setJournal] = useState<Journal | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let live = true;
    setLoading(true); setError(""); setJournal(null);
    api(`editor/journal?journal_id=${journalId}`).then(data => { if (live) setJournal(data); }).catch(e => { if (live) setError(e.message); }).finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
  }, [journalId]);
  return <><Link className="journal-back-link" href="/dashboard/journal">← All journals</Link>{loading ? <div className="admin-panel" role="status">Loading journal…</div> : error ? <p className="message error" role="alert">{error}</p> : journal ? <JournalDetails key={journal.id} journal={journal} onChanged={setJournal} /> : <p>Journal not found.</p>}</>;
}
