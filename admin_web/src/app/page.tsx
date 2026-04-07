import Link from 'next/link';

export default function HomePage() {
  return (
    <main className="page" style={{ maxWidth: 720, margin: '0 auto' }}>
      <h1>ADR Admin Dashboard</h1>
      <p className="muted">Phase 2 admin interface for managing student-side operations.</p>
      <div style={{ display: 'flex', gap: 10, marginTop: 16 }}>
        <Link href="/login" className="btn">Go To Login</Link>
      </div>
    </main>
  );
}
