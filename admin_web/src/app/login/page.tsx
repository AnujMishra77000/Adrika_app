'use client';

import { useRouter } from 'next/navigation';
import { FormEvent, useState } from 'react';

import { setAccessToken } from '@/lib/auth';
import { apiRequest } from '@/lib/api';

export default function LoginPage() {
  const router = useRouter();
  const [identifier, setIdentifier] = useState('admin@adr.local');
  const [password, setPassword] = useState('Admin@123');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const response = await apiRequest<{ tokens: { access_token: string } }>('/api/v1/auth/login', {
        method: 'POST',
        auth: false,
        body: JSON.stringify({
          identifier,
          password,
          device: {
            device_id: 'admin-web',
            platform: 'web',
            app_version: '0.1.0',
          },
        }),
      });
      setAccessToken(response.tokens.access_token);
      router.replace('/admin');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="page" style={{ maxWidth: 460, margin: '48px auto' }}>
      <div className="card">
        <h2 style={{ marginTop: 0 }}>Admin Login</h2>
        <p className="muted">Sign in with your admin account.</p>
        <form onSubmit={onSubmit}>
          <label className="field">
            <span>Email / Phone</span>
            <input value={identifier} onChange={(e) => setIdentifier(e.target.value)} required />
          </label>

          <label className="field">
            <span>Password</span>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </label>

          {error ? <p style={{ color: '#dc2626' }}>{error}</p> : null}

          <button className="btn" type="submit" disabled={loading}>
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
      </div>
    </main>
  );
}
