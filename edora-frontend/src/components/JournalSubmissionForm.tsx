"use client";
import { useEffect, useRef } from "react";
type Config = { api_origin: string; editor_code: string; journal_slug: string };
declare global { interface Window { EdoraSubmission?: { mount: (root: HTMLElement, config: Config) => void } } }
export default function JournalSubmissionForm({ editorCode, journalSlug }: { editorCode: string; journalSlug: string }) {
  const root = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const element = root.current;
    function mount() { if (element?.isConnected) window.EdoraSubmission?.mount(element, { api_origin: location.origin, editor_code: editorCode, journal_slug: journalSlug }); }
    let script = document.querySelector<HTMLScriptElement>('script[src="/journal-submission.js"]');
    if (window.EdoraSubmission) mount();
    else {
      if (!script) { script = document.createElement("script"); script.src = "/journal-submission.js"; script.async = true; document.body.appendChild(script); }
      script.addEventListener("load", mount);
    }
    return () => { script?.removeEventListener("load", mount); if (element) { element.replaceChildren(); delete element.dataset.submissionReady; } };
  }, [editorCode, journalSlug]);
  return <div ref={root} data-journal-submission data-editor-code={editorCode} data-journal-slug={journalSlug}><noscript>Enable JavaScript to submit your manuscript.</noscript></div>;
}
