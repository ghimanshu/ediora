export async function api(path: string, body?: unknown, method?: "GET" | "POST" | "PATCH" | "DELETE") {
  const response = await fetch(`/api/${path}`, {
    method: method ?? (body === undefined ? "GET" : "POST"),
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store",
  });
  const data = response.status === 204 ? {} : await response.json();
  if (!response.ok) {
    const detail = data.detail;
    throw new Error(Array.isArray(detail)
      ? detail.map((e: { loc: string[]; msg: string }) => `${e.loc.at(-1)}: ${e.msg}`).join(". ")
      : detail ?? "Request failed");
  }
  return data;
}
