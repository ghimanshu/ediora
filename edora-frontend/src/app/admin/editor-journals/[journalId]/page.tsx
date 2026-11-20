import { notFound } from "next/navigation";
import AdminJournalViewer from "@/components/AdminJournalViewer";
export default async function ViewJournal({ params }: { params: Promise<{ journalId: string }> }) {
  const { journalId } = await params;
  if (!/^[1-9]\d*$/.test(journalId) || !Number.isSafeInteger(Number(journalId))) notFound();
  return <AdminJournalViewer journalId={Number(journalId)} />;
}
