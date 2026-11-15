import type { Metadata } from "next";
import Link from "next/link";
import Header from "@/components/Header";
import "./globals.css";
export const metadata: Metadata = { title: "Edora | Editor community", description: "Join the Edora editor community." };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body><Header /><main>{children}</main><footer><Link className="brand" href="/">edora</Link><p>Thoughtful publishing starts with thoughtful people.</p><small>© {new Date().getFullYear()} Edora · Editor portal</small></footer></body></html>;
}
