import type { Metadata } from "next";
import type { ReactNode } from "react";
import "@/styles/globals.css";
import { AuthProvider } from "@/hooks/useAuth";

export const metadata: Metadata = {
  title: "InterviewMate – Practice the full hiring process",
  description: "Prepare for placements and internships with realistic interview rounds and feedback based on your own results.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
