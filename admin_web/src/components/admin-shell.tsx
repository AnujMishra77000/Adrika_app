'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';

import { clearAccessToken } from '@/lib/auth';
import { apiRequest } from '@/lib/api';

type AuthState = 'loading' | 'ready';

const NAV_ITEMS = [
  { href: '/admin', label: 'Overview' },
  { href: '/admin/students', label: 'Students' },
  { href: '/admin/notices', label: 'Notices' },
  { href: '/admin/homework', label: 'Homework' },
  { href: '/admin/attendance', label: 'Attendance' },
  { href: '/admin/assessments', label: 'Assessments' },
  { href: '/admin/results', label: 'Results' },
  { href: '/admin/doubts', label: 'Doubts' },
  { href: '/admin/content', label: 'Content' },
  { href: '/admin/notifications', label: 'Notifications' },
  { href: '/admin/audit-logs', label: 'Audit Logs' },
];

export default function AdminShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [state, setState] = useState<AuthState>('loading');
  const [adminName, setAdminName] = useState<string>('Admin');

  useEffect(() => {
    let mounted = true;

    async function verify() {
      try {
        const me = await apiRequest<{ full_name: string; roles: string[] }>('/api/v1/auth/me');
        if (!me.roles.includes('admin')) {
          clearAccessToken();
          router.replace('/login');
          return;
        }
        if (mounted) {
          setAdminName(me.full_name);
          setState('ready');
        }
      } catch {
        clearAccessToken();
        router.replace('/login');
      }
    }

    void verify();
    return () => {
      mounted = false;
    };
  }, [router]);

  const nav = useMemo(() => NAV_ITEMS, []);

  if (state === 'loading') {
    return <div className="page">Validating admin session...</div>;
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '240px 1fr', minHeight: '100vh' }}>
      <aside style={{ borderRight: '1px solid var(--line)', background: '#fff', padding: 16 }}>
        <div style={{ marginBottom: 16 }}>
          <h3 style={{ margin: 0 }}>ADR Admin</h3>
          <div className="muted" style={{ fontSize: 13 }}>{adminName}</div>
        </div>

        <nav style={{ display: 'grid', gap: 6 }}>
          {nav.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                style={{
                  padding: '8px 10px',
                  borderRadius: 8,
                  background: active ? '#e7efff' : 'transparent',
                  color: active ? '#0b5fff' : 'inherit',
                }}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        <button
          className="btn"
          style={{ marginTop: 16, width: '100%', background: '#334155' }}
          onClick={() => {
            clearAccessToken();
            router.replace('/login');
          }}
        >
          Logout
        </button>
      </aside>

      <main className="page">{children}</main>
    </div>
  );
}
