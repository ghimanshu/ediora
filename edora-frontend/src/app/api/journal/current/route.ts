import { journalFeedProxy, feedOptions } from "@/lib/journal-feed-proxy";
export const runtime = "nodejs";
export const GET = journalFeedProxy("current");
export const OPTIONS = feedOptions;
