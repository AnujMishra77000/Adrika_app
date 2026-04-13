"use client";

import { useEffect, useState } from "react";

import { apiRequest } from "@/lib/api";

type OverviewStats = {
  students: number;
  parents: number;
  notices: number;
  homework: number;
  doubts: number;
  results: number;
  banners: number;
};

const initialStats: OverviewStats = {
  students: 0,
  parents: 0,
  notices: 0,
  homework: 0,
  doubts: 0,
  results: 0,
  banners: 0,
};

const cards: Array<{ key: keyof OverviewStats; label: string }> = [
  { key: "students", label: "Students" },
  { key: "parents", label: "Parents" },
  { key: "notices", label: "Notices" },
  { key: "homework", label: "Homework" },
  { key: "doubts", label: "Doubts" },
  { key: "results", label: "Results" },
  { key: "banners", label: "Banners" },
];

export default function AdminOverviewPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<OverviewStats>(initialStats);

  useEffect(() => {
    let mounted = true;

    async function load() {
      try {
        const [students, parents, notices, homework, doubts, results, banners] =
          await Promise.all([
            apiRequest<{ meta: { total: number } }>("/api/v1/admin/students?limit=1&offset=0"),
            apiRequest<{ meta: { total: number } }>("/api/v1/admin/parents?limit=1&offset=0"),
            apiRequest<{ meta: { total: number } }>("/api/v1/admin/notices?limit=1&offset=0"),
            apiRequest<{ meta: { total: number } }>("/api/v1/admin/homework?limit=1&offset=0"),
            apiRequest<{ meta: { total: number } }>("/api/v1/admin/doubts?limit=1&offset=0"),
            apiRequest<{ meta: { total: number } }>("/api/v1/admin/results?limit=1&offset=0"),
            apiRequest<{ meta: { total: number } }>("/api/v1/admin/banners?limit=1&offset=0"),
          ]);

        if (!mounted) {
          return;
        }

        setStats({
          students: students.meta.total,
          parents: parents.meta.total,
          notices: notices.meta.total,
          homework: homework.meta.total,
          doubts: doubts.meta.total,
          results: results.meta.total,
          banners: banners.meta.total,
        });
        setLoading(false);
      } catch (err) {
        if (!mounted) {
          return;
        }
        setError(err instanceof Error ? err.message : "Failed to load overview");
        setLoading(false);
      }
    }

    void load();
    return () => {
      mounted = false;
    };
  }, []);

  if (loading) {
    return <p>Loading overview...</p>;
  }

  if (error) {
    return <p style={{ color: "#dc2626" }}>{error}</p>;
  }

  return (
    <section>
      <h1 style={{ marginTop: 0 }}>Overview</h1>
      <p className="muted">Current operational counts from admin APIs.</p>
      <div className="grid" style={{ marginTop: 12 }}>
        {cards.map((card) => (
          <div className="card" key={card.key}>
            <strong>{card.label}</strong>
            <div>{stats[card.key]}</div>
          </div>
        ))}
      </div>
    </section>
  );
}
