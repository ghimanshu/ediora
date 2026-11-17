import { currentUser } from "@/lib/session";
import { redirect } from "next/navigation";
import EditorProfile from "@/components/EditorProfile";
export default async function Dashboard() {
  const user = await currentUser();
  if (!user) redirect("/login");
  return <EditorProfile initial={{ first_name: user.first_name, last_name: user.last_name, phone: user.phone, email: user.email, gender: user.gender }} />;
}
