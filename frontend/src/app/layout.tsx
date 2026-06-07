import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Reelise Hub — Second Brain Knowledge & Automation Dashboard",
  description: "Capture valuable resources, PDFs, and guides from Instagram Reels into your structured second brain and Notion databases automatically.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark scroll-smooth">
      <body className="antialiased selection:bg-violet-500/30 selection:text-violet-200">
        {children}
      </body>
    </html>
  );
}
