"use client";
import type { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import Header from "@/components/Header";
export default function PortalChrome({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  if (/^\/[a-z0-9]{8}\/[a-z0-9]+(?:-[a-z0-9]+)*\/[^/]+\/?$/.test(pathname)) return <>{children}</>;
  return <><Header /><main>{children}</main><footer><Link className="brand" href="/">edora</Link><p>Thoughtful publishing starts with thoughtful people.</p><small>© {new Date().getFullYear()} Edora · Editor portal</small></footer></>;
}
