import type { JournalStatus } from "@/lib/journals";
export default function JournalStatusBadge({ status }: { status: JournalStatus }) {
  return <span className={`journal-status-badge journal-status-${status.toLowerCase()}`}><span aria-hidden="true" />{status}</span>;
}
