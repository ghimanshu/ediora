import TemplateSelector from "@/components/TemplateSelector";
import { currentUser } from "@/lib/session";
import { redirect } from "next/navigation";
export const dynamic = "force-dynamic";
export default async function Dashboard() {
  const editor = await currentUser();
  if (!editor) redirect("/login");
  if (editor.role === "super_admin") redirect("/admin");
  return <><section className="form-panel"><span className="eyebrow">Editor account · Email verified</span><h1>Hello, {editor.first_name}.</h1><p>Your Edora editor profile is ready.</p><dl>{[["Name", `${editor.first_name} ${editor.last_name}`], ["Email", editor.email], ["Phone", editor.phone], ["Gender", editor.gender], ["Role", "Editor"]].map(([k,v]) => <div className="wide" key={k}><dt>{k}</dt><dd>{v}</dd></div>)}</dl></section><TemplateSelector /></>;
}
