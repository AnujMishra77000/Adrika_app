'use client';

import { useEffect, useState } from 'react';

import { apiRequest } from '@/lib/api';

export default function AdminOverviewPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState({
    students: 0,
    notices: 0,
    homework: 0,
    doubts: 0,
    results: 0,
    banners: 0,
  });

  useEffect(() => {
    let mounted = true;

    async function load() {
      try {
        const [students, notices, homework, doubts, results, banners] = await Promise.all([
          apiRequest<{ meta: { total: number } }>('/api/v1/admin/students?limit=1&offset=0'),
          apiRequest<{ meta: { total: number } }>('/api/v1/admin/notices?limit=1&offset=0'),
          apiRequest<{ meta: { total: number } }>('/api/v1/admin/homework?limit=1&offset=0'),
          apiRequest<{ meta: { total: number } }>('/api/v1/admin/doubts?limit=1&offset=0'),
          apiRequest<{ meta: { total: number } }>('/api/v1/admin/results?limit=1&offset=0'),
          apiRequest<{ meta: { total: number } }>('/api/v1/admin/banners?limit=1&offset=0'),
        ]);

        if (mounted) {
          setStats({
            students: students.meta.total,
            notices: notices.meta.total,
            homework: homework.meta.total,
            doubts: doubts.meta.total,
            results: results.meta.total,
            banners: banners.meta.total,
          });
          setLoading(false);
        }
      } catch (err) {
        if (mounted) {
          setError(err instanceof Error ? err.message : 'Failed to load overview');
          setLoading(false);
        }
      }
    }

    void load();
    return () => {
      mounted = false;
    };
  }, []);

  if (loading) return <p>Loading overview...</p>;
  if (error) return <p style={{ color: '#dc2626' }}>{error}</p>;

  return (
    <section>
      <h1 style={{ marginTop: 0 }}>Overview</h1>
      <p className="muted">Current operational counts from admin APIs.</p>
      <div className="grid" style={{ marginTop: 12 }}>
        <div className="card"><strong>Students</strong><div>{stats.students}</div></div>
        <div className="card"><strong>Notices</strong><div>{stats.notices}</div></div>
        <div className="card"><strong>Homework</strong><div>{stats.homework}</div></div>
        <div className="card"><strong>Doubts</strong><div>{stats.doubts}</div></div>
        <div className="card"><strong>Results</strong><div>{stats.results}</div></div>
        <div className="card"><strong>Banners</strong><div>{stats.banners}</div></div>
      </div>
    </section>
  );
}
