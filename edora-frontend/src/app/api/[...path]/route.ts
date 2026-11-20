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
    : path === "admin/journal-editors" || /^admin\/editor-journals(?:\/[1-9]\d*)?$/.test(path) ? ["GET"]
    : /^admin\/templates(?:\/[1-9]\d*)?$/.test(path)
      ? (path === "admin/templates" ? ["GET", "POST"] : ["PATCH", "DELETE"])
      : /^admin\/pages(?:\/[1-9]\d*)?$/.test(path)
        ? (path === "admin/pages" ? ["GET", "POST"] : ["GET", "PATCH", "DELETE"])
      : /^public\/journals\/[a-z0-9]{8}\/[a-z0-9]+(?:-[a-z0-9]+)*$/.test(path) ? ["GET"]
      : path === "editor/profile" ? ["PATCH"]
      : /^editor\/pages(?:\/[1-9]\d*)?$/.test(path) ? ["GET"]
      : path === "editor/journals" ? ["GET"]
      : path === "editor/journal" ? ["GET", "POST"]
      : path === "editor/journal/status" ? ["PATCH"]
      : path === "editor/journal/pages" ? ["POST"]
      : path === "editor/journal/pages/order" ? ["PATCH"]
      : path === "editor/journal/template" || /^editor\/journal\/pages\/[1-9]\d*$/.test(path) ? ["PATCH"]
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
    const body = request.method === "GET" ? undefined : await request.text();
    const maxBodyBytes = path === "editor/journal" && request.method === "POST" ? 6500000 : /^(?:admin\/pages(?:\/[1-9]\d*)?|editor\/journal\/pages(?:\/[1-9]\d*)?)$/.test(path) ? 650000 : 20000;
    if (body && Buffer.byteLength(body, "utf8") > maxBodyBytes) return NextResponse.json({ detail: "Request too large" }, { status: 413 });
    const upstream = await fetch(`${backend}/api/v1/${path}${request.nextUrl.search}`, {
      method: request.method, headers, body, cache: "no-store", signal: AbortSignal.timeout(20000),
    });
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
