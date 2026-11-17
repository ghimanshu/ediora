export async function api(path: string, body?: unknown, method?: "GET" | "POST" | "PATCH" | "DELETE") {
  const response = await fetch(`/api/${path}`, {
    method: method ?? (body === undefined ? "GET" : "POST"),
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store",
  });
  if (response.status === 204) return {};
  const text = await response.text();
  let data;
  try {
    data = text.trim() ? JSON.parse(text) : undefined;
  } catch {
    throw new Error(response.ok
      ? "The server returned an invalid response. Please try again."
      : `Request failed (HTTP ${response.status}). Please try again.`);
  }
  if (data === undefined) {
    throw new Error(response.ok
      ? "The server returned an empty response. Please try again."
      : `Request failed (HTTP ${response.status}). Please try again.`);
  }
  if (!response.ok) {
    const detail = data && typeof data === "object" ? data.detail : undefined;
    throw new Error(Array.isArray(detail)
      ? detail.map((e: { loc: string[]; msg: string }) => `${e.loc?.at(-1) ?? "Input"}: ${e.msg}`).join(". ")
      : typeof detail === "string" ? detail : `Request failed (HTTP ${response.status})`);
  }
  return data;
}
