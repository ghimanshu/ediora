import { journalFeedProxy, feedOptions } from "@/lib/journal-feed-proxy";
export const runtime = "nodejs";
export const GET = journalFeedProxy("archives");
export const OPTIONS = feedOptions;
