import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = { title: "Therapeutic AI Coach", description: "Coaching conversationnel non médical" };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="fr"><body>{children}</body></html>;
}
