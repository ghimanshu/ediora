import { notFound } from "next/navigation";
import JournalWorkspace from "@/components/JournalWorkspace";
export default async function JournalPage({ params }: { params: Promise<{ journalId: string }> }) {
  const { journalId } = await params;
  if (!/^[1-9]\d*$/.test(journalId) || !Number.isSafeInteger(Number(journalId))) notFound();
  return <JournalWorkspace journalId={Number(journalId)} />;
}
