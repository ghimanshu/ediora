import { submissionProxy, submissionOptions } from "@/lib/journal-submission-proxy";
export const runtime = "nodejs";
export const POST = submissionProxy();
export const OPTIONS = submissionOptions;
