import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = { title: 'ORCHESTRA — AI Engineering Command Center', description: 'Plan, coordinate, monitor and verify AI engineering agents.' };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
