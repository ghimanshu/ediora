import { journalFeedProxy, feedOptions } from "@/lib/journal-feed-proxy";
export const runtime = "nodejs";
export const GET = journalFeedProxy("info");
export const OPTIONS = feedOptions;
