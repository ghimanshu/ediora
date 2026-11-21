"use client";
import { useState } from "react";
import dynamic from "next/dynamic";
import type { Journal } from "@/lib/journals";
const JournalTemplateEditor = dynamic(() => import("@/components/JournalTemplateEditor"), { ssr: false, loading: () => <p role="status">Loading template editor...</p> });
export default function JournalTemplatePanel({ journal, onChanged }: { journal: Journal; onChanged: (journal: Journal) => void }) {
  const [revision, setRevision] = useState(0);
  const [message, setMessage] = useState("");
  return <>{message && <p className="message" role="status">{message}</p>}<JournalTemplateEditor key={`${journal.id}-${revision}`} journal={journal} onCancel={() => { setRevision(value => value + 1); setMessage(""); }} onSaved={updated => { onChanged(updated); setRevision(value => value + 1); setMessage("Your personal template has been saved."); }} /></>;
}
