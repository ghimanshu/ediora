export type ArticleStatus = "Submitted" | "Published" | "UnPublished";
export type ManagedArticle = { how_to_cite: string; status: ArticleStatus; submitter_name: string; submitter_email: string; notification_sent: boolean; journal_name: string; created_at: string; id: number; journal_id: number; title: string; authors: string[]; abstract: string; is_published: boolean; volume_id: number | null; volume_title: string | null; has_pdf: boolean; pdf_size: number };
export type ManagedVolume = { is_archived: boolean; journal_name: string; created_at: string; id: number; journal_id: number; title: string; volume: string; number: string; is_published: boolean; published_at: string | null; article_ids: number[] };
export async function pdfBase64(file: File) {
  if (file.size > 10 * 1024 * 1024) throw new Error("PDF must not exceed 10 MB");
  const bytes = new Uint8Array(await file.arrayBuffer());
  const parts: string[] = [];
  for (let index = 0; index < bytes.length; index += 32768) parts.push(String.fromCharCode(...bytes.subarray(index, index + 32768)));
  return btoa(parts.join(""));
}

export type JournalChoice = { id: number; name: string };
export type PublicationFilters = { journal: string; from: string; to: string };
export function publicationQuery(filters: PublicationFilters) {
  const query = new URLSearchParams();
  if (filters.journal) query.set("journal_id", filters.journal);
  if (filters.from) query.set("date_from", filters.from);
  if (filters.to) query.set("date_to", filters.to);
  return query.toString();
}
