import { cookies } from "next/headers";
export async function currentUser() {
  const jar = await cookies();
  if (!jar.has("edora_session")) return null;
  const response = await fetch(`${process.env.APP_ORIGIN ?? "http://localhost:3000"}/api/auth/me`, {
    headers: { Cookie: jar.toString() }, cache: "no-store", signal: AbortSignal.timeout(20000),
  });
  if (response.status === 401 || response.status === 403) return null;
  if (!response.ok) throw new Error("Account service unavailable. Please try again shortly.");
  return response.json();
}
