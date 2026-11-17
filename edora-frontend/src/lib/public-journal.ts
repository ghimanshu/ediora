import { cache } from "react";
import { notFound } from "next/navigation";
import type { PublicJournal } from "@/lib/journals";
export const getPublicJournal = cache(async (editorCode: string, journalSlug: string): Promise<PublicJournal> => {
  if (!/^[a-z0-9]{8}$/.test(editorCode) || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(journalSlug)) notFound();
  const origin = process.env.APP_ORIGIN ?? "http://localhost:3000";
  const response = await fetch(`${origin}/api/public/journals/${editorCode}/${journalSlug}`, { cache: "no-store", signal: AbortSignal.timeout(20000) });
  if (response.status === 404 || response.status === 422) notFound();
  if (!response.ok) throw new Error("Journal preview is temporarily unavailable. Please try again.");
  return response.json();
});
