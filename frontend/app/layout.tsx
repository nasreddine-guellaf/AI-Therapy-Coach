import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Therapy Coach | Guided reflection",
  description:
    "A non-medical conversational coaching experience for thoughtful reflection.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
