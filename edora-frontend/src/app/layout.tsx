import type { Metadata } from "next";
import PortalChrome from "@/components/PortalChrome";
import "./globals.css";
export const metadata: Metadata = { title: "Edora | Editor community", description: "Join the Edora editor community." };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body><PortalChrome>{children}</PortalChrome></body></html>;
}
