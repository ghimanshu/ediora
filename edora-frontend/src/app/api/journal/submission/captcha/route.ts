import { submissionProxy, submissionOptions } from "@/lib/journal-submission-proxy";
export const runtime = "nodejs";
export const GET = submissionProxy(true);
export const OPTIONS = submissionOptions;
