"use client";
import { useEffect } from "react";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
export default function RichTextEditor({ initialContent, onChange, disabled }: { initialContent: string; onChange: (html: string) => void; disabled: boolean }) {
  const editor = useEditor({
    extensions: [StarterKit.configure({ heading: { levels: [1, 2, 3] }, link: { openOnClick: false, protocols: ["http", "https", "mailto", "tel"] } })],
    content: initialContent,
    immediatelyRender: false,
    shouldRerenderOnTransaction: true,
    onUpdate: ({ editor }) => onChange(editor.getHTML()),
    editorProps: { attributes: { role: "textbox", "aria-label": "Page HTML content", "aria-multiline": "true", class: "page-rich-content" } },
  });
  useEffect(() => { editor?.setEditable(!disabled); }, [editor, disabled]);
  if (!editor) return <p role="status">Loading editor…</p>;
  function link() {
    if (!editor) return;
    const url = window.prompt("Link URL (https://, http://, mailto:, tel:, or a relative path)", editor.getAttributes("link").href ?? "https://");
    if (url === null) return;
    if (!url.trim()) { editor.chain().focus().extendMarkRange("link").unsetLink().run(); return; }
    if (!/^(https?:\/\/|mailto:|tel:|\/(?!\/)|#)/i.test(url.trim())) { window.alert("Enter a supported link URL."); return; }
    editor.chain().focus().extendMarkRange("link").setLink({ href: url.trim() }).run();
  }
  const tools = [
    { label: "Bold", active: editor.isActive("bold"), run: () => editor.chain().focus().toggleBold().run() },
    { label: "Italic", active: editor.isActive("italic"), run: () => editor.chain().focus().toggleItalic().run() },
    { label: "Underline", active: editor.isActive("underline"), run: () => editor.chain().focus().toggleUnderline().run() },
    { label: "Strike", active: editor.isActive("strike"), run: () => editor.chain().focus().toggleStrike().run() },
    { label: "Bullets", active: editor.isActive("bulletList"), run: () => editor.chain().focus().toggleBulletList().run() },
    { label: "Numbered list", active: editor.isActive("orderedList"), run: () => editor.chain().focus().toggleOrderedList().run() },
    { label: "Quote", active: editor.isActive("blockquote"), run: () => editor.chain().focus().toggleBlockquote().run() },
    { label: "Code block", active: editor.isActive("codeBlock"), run: () => editor.chain().focus().toggleCodeBlock().run() },
    { label: "Link", active: editor.isActive("link"), run: link },
  ];
  return <div className="page-editor"><div className="page-editor-toolbar" role="group" aria-label="Content formatting"><select aria-label="Paragraph style" disabled={disabled} value={editor.isActive("heading", { level: 1 }) ? "1" : editor.isActive("heading", { level: 2 }) ? "2" : editor.isActive("heading", { level: 3 }) ? "3" : "paragraph"} onChange={e => e.target.value === "paragraph" ? editor.chain().focus().setParagraph().run() : editor.chain().focus().toggleHeading({ level: Number(e.target.value) as 1 | 2 | 3 }).run()}><option value="paragraph">Paragraph</option><option value="1">Heading 1</option><option value="2">Heading 2</option><option value="3">Heading 3</option></select>{tools.map(tool => <button type="button" key={tool.label} disabled={disabled} aria-pressed={tool.active} onClick={tool.run}>{tool.label}</button>)}<button type="button" disabled={disabled || !editor.can().undo()} onClick={() => editor.chain().focus().undo().run()}>Undo</button><button type="button" disabled={disabled || !editor.can().redo()} onClick={() => editor.chain().focus().redo().run()}>Redo</button></div><EditorContent editor={editor} /><div className="page-editor-caption">Tiptap · Rich text is saved as HTML</div></div>;
}
