import { articlePdfProxy, feedOptions } from "@/lib/journal-feed-proxy";
export const runtime = "nodejs";
export const GET = articlePdfProxy;
export const OPTIONS = feedOptions;
