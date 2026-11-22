import { NextRequest, NextResponse } from "next/server";
const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, OPTIONS",
  "Access-Control-Allow-Headers": "Accept, Content-Type",
  "Cache-Control": "no-store",
  "X-Content-Type-Options": "nosniff",
};
export function feedOptions() { return new NextResponse(null, { status: 204, headers: corsHeaders }); }
export function journalFeedProxy(kind: "current" | "archives" | "info") {
  return async (request: NextRequest) => {
    const query = request.nextUrl.searchParams;
    const code = query.get("editor_code") ?? "";
    const slug = query.get("journal_slug") ?? "";
    if (!/^[a-z0-9]{8}$/.test(code) || slug.length > 150 || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug)) {
      return NextResponse.json({ detail: "A valid editor_code and journal_slug are required" }, { status: 422, headers: corsHeaders });
    }
    const paging = new URLSearchParams();
    if (kind === "archives") {
      for (const key of ["offset", "limit"] as const) {
        const value = query.get(key);
        if (value !== null) {
          if (!/^\d+$/.test(value) || !Number.isSafeInteger(Number(value)) || (key === "limit" && (Number(value) < 1 || Number(value) > 100))) {
            return NextResponse.json({ detail: "Invalid archive pagination" }, { status: 422, headers: corsHeaders });
          }
          paging.set(key, value);
        }
      }
    }
    const backend = process.env.BACKEND_URL ?? "http://localhost:8000";
    try {
      const response = await fetch(`${backend}/api/v1/public/journals/${code}/${slug}/${kind}${paging.size ? `?${paging}` : ""}`, {
        headers: { Accept: "application/json" }, cache: "no-store", signal: AbortSignal.timeout(20000),
      });
      const data = await response.json();
      return NextResponse.json(data, { status: response.status, headers: corsHeaders });
    } catch {
      return NextResponse.json({ detail: "Journal feed is temporarily unavailable. Please try again." }, { status: 502, headers: corsHeaders });
    }
  };
}


export async function articlePdfProxy(request: NextRequest) {
  const query = request.nextUrl.searchParams;
  const code = query.get("editor_code") ?? "";
  const slug = query.get("journal_slug") ?? "";
  const id = query.get("article_id") ?? "";
  if (!/^[a-z0-9]{8}$/.test(code) || slug.length > 150 || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug) || !/^[1-9]\d*$/.test(id)) {
    return NextResponse.json({ detail: "Valid editor_code, journal_slug and article_id are required" }, { status: 422, headers: corsHeaders });
  }
  try {
    const backend = process.env.BACKEND_URL ?? "http://localhost:8000";
    const response = await fetch(`${backend}/api/v1/public/journals/${code}/${slug}/articles/${id}/pdf`, { cache: "no-store", signal: AbortSignal.timeout(20000) });
    if (!response.ok) return NextResponse.json(await response.json(), { status: response.status, headers: corsHeaders });
    if (!response.headers.get("content-type")?.startsWith("application/pdf")) throw new Error("Invalid PDF response");
    return new NextResponse(response.body, { headers: { ...corsHeaders, "Content-Type": "application/pdf", "Content-Disposition": response.headers.get("content-disposition") ?? 'attachment; filename="article.pdf"' } });
  } catch { return NextResponse.json({ detail: "PDF is temporarily unavailable" }, { status: 502, headers: corsHeaders }); }
}
