import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'ADR Admin Dashboard',
  description: 'Coaching institute administration dashboard',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
