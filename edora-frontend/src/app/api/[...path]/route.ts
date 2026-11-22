import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
const backend = process.env.BACKEND_URL ?? "http://localhost:8000";
const origin = process.env.APP_ORIGIN ?? "http://localhost:3000";
const cookieName = "edora_session";
const allowed: Record<string, string> = {
  "auth/register": "POST", "auth/login": "POST", "auth/logout": "POST",
  "auth/verify-email": "POST", "auth/resend-verification": "POST",
  "auth/me": "GET", "contact": "POST", "templates": "GET",
};
async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const path = (await context.params).path.join("/");
  const methods = /^admin\/users(?:\/[1-9]\d*)?$/.test(path)
    ? (path === "admin/users" ? ["GET"] : ["PATCH", "DELETE"])
    : /^admin\/editor-journals\/[1-9]\d*\/export$/.test(path) ? ["GET"]
    : /^editor\/articles\/[1-9]\d*\/pdf$/.test(path) ? ["GET"]
    : /^editor\/(?:articles|volumes)(?:\/[1-9]\d*)?$/.test(path) ? (/^editor\/(articles|volumes)$/.test(path) ? ["GET", "POST"] : ["PATCH", "DELETE"])
    : path === "admin/journal-editors" || /^admin\/editor-journals(?:\/[1-9]\d*)?$/.test(path) ? ["GET"]
    : /^admin\/templates(?:\/[1-9]\d*)?$/.test(path)
      ? (path === "admin/templates" ? ["GET", "POST"] : ["PATCH", "DELETE"])
      : /^admin\/pages(?:\/[1-9]\d*)?$/.test(path)
        ? (path === "admin/pages" ? ["GET", "POST"] : ["GET", "PATCH", "DELETE"])
      : /^public\/journals\/[a-z0-9]{8}\/[a-z0-9]+(?:-[a-z0-9]+)*$/.test(path) ? ["GET"]
      : path === "editor/profile" ? ["PATCH"]
      : /^editor\/pages(?:\/[1-9]\d*)?$/.test(path) ? ["GET"]
      : path === "editor/journals" ? ["GET"]
      : path === "editor/journal" ? ["GET", "POST", "DELETE"]
      : (path === "editor/journal/status" || path === "editor/journal/info") ? ["PATCH"]
      : path === "editor/journal/pages" ? ["POST"]
      : /^editor\/journal\/pages\/library\/[1-9]\d*$/.test(path) ? ["POST"]
      : path === "editor/journal/pages/order" ? ["PATCH"]
      : /^editor\/journal\/pages\/[1-9]\d*\/status$/.test(path) ? ["PATCH"]
      : /^editor\/journal\/pages\/[1-9]\d*$/.test(path) ? ["PATCH", "DELETE"]
      : path === "editor/journal/template" ? ["PATCH"]
      : path === "website/template" ? ["GET", "POST"]
      : allowed[path] ? [allowed[path]] : [];
  if (!methods.length) return NextResponse.json({ detail: "Not found" }, { status: 404 });
  if (!methods.includes(request.method)) return NextResponse.json({ detail: "Method not allowed" }, { status: 405 });
  if (request.method !== "GET" && request.headers.get("origin") !== origin)
    return NextResponse.json({ detail: "Invalid request origin" }, { status: 403 });
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const session = request.cookies.get(cookieName)?.value;
  if (session) headers.Authorization = `Bearer ${session}`;
  try {
    if (request.method !== "GET") {
      const gatewayKey = process.env.INTERNAL_API_KEY;
      if (!gatewayKey) return NextResponse.json({ detail: "Internal API gateway is not configured" }, { status: 503 });
      headers["X-Internal-API-Key"] = gatewayKey;
      const privateWrite = path.startsWith("editor/") || path.startsWith("admin/") || path === "website/template" || path === "auth/logout";
      if (privateWrite) {
        if (!session) return NextResponse.json({ detail: "Sign in required" }, { status: 401 });
        const identity = await fetch(`${backend}/api/v1/auth/me`, { headers: { Authorization: `Bearer ${session}` }, cache: "no-store", signal: AbortSignal.timeout(20000) });
        if (!identity.ok) return NextResponse.json({ detail: "Session expired or invalid" }, { status: identity.status === 403 ? 403 : 401 });
        const account = await identity.json();
        if (!/^[a-z0-9]{8}$/.test(account.public_code ?? "")) return NextResponse.json({ detail: "Invalid account editor code" }, { status: 502 });
        const requestedCodes = [request.nextUrl.searchParams.get("editor_code"), request.headers.get("x-editor-code")];
        if (requestedCodes.some(code => code !== null && code !== account.public_code)) return NextResponse.json({ detail: "Editor code does not match the authenticated account" }, { status: 403 });
        headers["X-Editor-Code"] = account.public_code;
      }
    }
    const body = request.method === "GET" ? undefined : await request.text();
    const maxBodyBytes = /^editor\/articles(?:\/[1-9]\d*)?$/.test(path) ? 15000000 : path === "editor/journal" && request.method === "POST" ? 6500000 : /^(?:admin\/pages(?:\/[1-9]\d*)?|editor\/journal\/pages(?:\/[1-9]\d*)?)$/.test(path) ? 650000 : 20000;
    if (body && Buffer.byteLength(body, "utf8") > maxBodyBytes) return NextResponse.json({ detail: "Request too large" }, { status: 413 });
    const upstream = await fetch(`${backend}/api/v1/${path}${request.nextUrl.search}`, {
      method: request.method, headers, body, cache: "no-store", signal: AbortSignal.timeout(20000),
    });
    if (/^editor\/articles\/[1-9]\d*\/pdf$/.test(path) && upstream.ok) {
      if (!upstream.headers.get("content-type")?.startsWith("application/pdf")) return NextResponse.json({ detail: "Invalid PDF response" }, { status: 502 });
      return new NextResponse(upstream.body, { status: upstream.status, headers: {
        "Content-Type": "application/pdf", "Content-Disposition": upstream.headers.get("content-disposition") ?? 'attachment; filename="article.pdf"',
        "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
      } });
    }
    if (/^admin\/editor-journals\/[1-9]\d*\/export$/.test(path) && upstream.ok) {
      if (!upstream.headers.get("content-type")?.startsWith("application/zip")) {
        return NextResponse.json({ detail: "Invalid website export response" }, { status: 502 });
      }
      return new NextResponse(upstream.body, { status: upstream.status, headers: {
        "Content-Type": "application/zip",
        "Content-Disposition": upstream.headers.get("content-disposition") ?? 'attachment; filename="journal-website.zip"',
        "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
      } });
    }
    const data = upstream.status === 204 ? null : await upstream.json();
    let response: NextResponse;
    if (path === "auth/login" && upstream.ok) {
      response = NextResponse.json({ message: "Signed in" });
      response.cookies.set(cookieName, data.access_token, {
        httpOnly: true, secure: process.env.COOKIE_SECURE === "true", sameSite: "lax",
        path: "/", maxAge: data.expires_in,
      });
    } else {
      // JSON null is a meaningful result (for example, no journal yet).
      // Only a 204 response must omit its body.
      response = upstream.status === 204
        ? new NextResponse(null, { status: 204 })
        : NextResponse.json(data, { status: upstream.status });
    }
    if (path === "auth/logout" && upstream.ok) response.cookies.delete(cookieName);
    response.headers.set("Cache-Control", "no-store");
    return response;
  } catch {
    return NextResponse.json({ detail: "Backend unavailable. Please try again shortly." }, { status: 502 });
  }
}
export const GET = proxy;
export const POST = proxy;

export const PATCH = proxy;
export const DELETE = proxy;
