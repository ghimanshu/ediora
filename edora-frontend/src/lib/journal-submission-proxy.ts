import { NextRequest, NextResponse } from "next/server";
const headers = { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "GET, POST, OPTIONS", "Access-Control-Allow-Headers": "Content-Type, Accept", "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" };
export function submissionOptions() { return new NextResponse(null, { status: 204, headers }); }
export function submissionProxy(captcha = false) {
  return async (request: NextRequest) => {
    const code = request.nextUrl.searchParams.get("editor_code") ?? "";
    const slug = request.nextUrl.searchParams.get("journal_slug") ?? "";
    if (!/^[a-z0-9]{8}$/.test(code) || slug.length > 150 || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug)) return NextResponse.json({ detail: "Valid editor_code and journal_slug are required" }, { status: 422, headers });
    try {
      let body: string | undefined;
      if (!captcha) {
        if (!request.headers.get("content-type")?.startsWith("application/json")) return NextResponse.json({ detail: "Use application/json" }, { status: 415, headers });
        const reader = request.body?.getReader();
        if (!reader) return NextResponse.json({ detail: "Submission is required" }, { status: 422, headers });
        const chunks: Uint8Array[] = []; let size = 0;
        while (true) {
          const { value, done } = await reader.read(); if (done) break;
          size += value.byteLength;
          if (size > 15000000) { await reader.cancel(); return NextResponse.json({ detail: "PDF must not exceed 10 MB" }, { status: 413, headers }); }
          chunks.push(value);
        }
        body = Buffer.concat(chunks).toString("utf8");
        try { JSON.parse(body); } catch { return NextResponse.json({ detail: "Invalid JSON" }, { status: 422, headers }); }
      }
      const backend = process.env.BACKEND_URL ?? "http://localhost:8000";
      const upstreamHeaders: Record<string, string> = { "Content-Type": "application/json", Accept: "application/json" };
      if (!captcha) {
        const gatewayKey = process.env.INTERNAL_API_KEY;
        if (!gatewayKey) return NextResponse.json({ detail: "Internal API gateway is not configured" }, { status: 503, headers });
        upstreamHeaders["X-Internal-API-Key"] = gatewayKey;
      }
      const response = await fetch(`${backend}/api/v1/public/journals/${code}/${slug}/submission${captcha ? "/captcha" : ""}`, { method: captcha ? "GET" : "POST", headers: upstreamHeaders, body, cache: "no-store", signal: AbortSignal.timeout(30000) });
      return NextResponse.json(await response.json(), { status: response.status, headers });
    } catch { return NextResponse.json({ detail: "Submission service is unavailable. Please try again." }, { status: 502, headers }); }
  };
}
