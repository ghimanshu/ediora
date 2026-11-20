export async function downloadWebsite(journalId: number) {
  const response = await fetch(`/api/admin/editor-journals/${journalId}/export`, { headers: { Accept: "application/zip" }, cache: "no-store" });
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new Error(typeof data?.detail === "string" ? data.detail : `Website export failed (HTTP ${response.status})`);
  }
  if (!response.headers.get("content-type")?.startsWith("application/zip")) throw new Error("The server did not return a website ZIP.");
  const blob = await response.blob();
  const match = response.headers.get("content-disposition")?.match(/filename="([a-z0-9-]+\.zip)"/i);
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = match?.[1] ?? `journal-${journalId}-website.zip`;
  document.body.appendChild(anchor);
  try { anchor.click(); }
  finally { anchor.remove(); window.setTimeout(() => URL.revokeObjectURL(url), 1000); }
}
