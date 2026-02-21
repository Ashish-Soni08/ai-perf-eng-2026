import "./globals.css";

export const metadata = {
  title: "GitHub Repo Summarizer",
  description: "Analyze any public GitHub repository with AI.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}
