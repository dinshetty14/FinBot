import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FinBot — FinSolve Technologies Q&A Assistant",
  description:
    "Advanced RAG-powered internal Q&A assistant with role-based access control for FinSolve Technologies",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
