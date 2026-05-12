'use client';

import Link from 'next/link';
import { FormEvent, useEffect, useMemo, useState } from 'react';

import { apiRequest } from '@/lib/api';

type Standard = {
  id: string;
  name: string;
  branch: { id: string; code: string; name: string };
};

type Batch = {
  id: string;
  name: string;
  academic_year: number;
  standard?: { id: string; name: string } | null;
  standard_name?: string | null;
};

type Student = {
  student_id: string;
  batch: { id: string; name: string; academic_year: number; standard_name: string | null } | null;
};

function batchStandardName(batch: Batch): string {
  return batch.standard_name ?? batch.standard?.name ?? '-';
}

export default function AdminCreateBatchPage() {
  const [standards, setStandards] = useState<Standard[]>([]);
  const [batches, setBatches] = useState<Batch[]>([]);
  const [students, setStudents] = useState<Student[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [newBatchStandardId, setNewBatchStandardId] = useState('');
  const [newBatchName, setNewBatchName] = useState('');
  const [newBatchYear, setNewBatchYear] = useState(String(new Date().getFullYear()));
  const [newStandardName, setNewStandardName] = useState('');
  const [standardSaving, setStandardSaving] = useState(false);

  const [search, setSearch] = useState('');
  const [yearFilter, setYearFilter] = useState('all');
  const [standardFilter, setStandardFilter] = useState('all');

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [standardRes, batchRes, studentRes] = await Promise.all([
        apiRequest<{ items: Standard[] }>('/api/v1/admin/standards?limit=200&offset=0'),
        apiRequest<{ items: Batch[] }>('/api/v1/admin/batches?limit=200&offset=0'),
        apiRequest<{ items: Student[] }>('/api/v1/admin/students?limit=100&offset=0'),
      ]);

      setStandards(standardRes.items);
      setBatches(batchRes.items);
      setStudents(studentRes.items);

      if (!newBatchStandardId && standardRes.items.length > 0) {
        setNewBatchStandardId(standardRes.items[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load batch workspace');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const studentsByBatch = useMemo(() => {
    const map: Record<string, number> = {};
    for (const student of students) {
      const batchId = student.batch?.id;
      if (!batchId) continue;
      map[batchId] = (map[batchId] ?? 0) + 1;
    }
    return map;
  }, [students]);

  const totalAssignedStudents = useMemo(
    () => Object.values(studentsByBatch).reduce((sum, count) => sum + count, 0),
    [studentsByBatch],
  );

  const visibleBatches = useMemo(() => {
    const query = search.trim().toLowerCase();
    return batches.filter((batch) => {
      if (yearFilter !== 'all' && String(batch.academic_year) !== yearFilter) {
        return false;
      }
      if (standardFilter !== 'all' && (batch.standard?.id ?? '') !== standardFilter) {
        return false;
      }
      if (!query) return true;
      const stdName = batchStandardName(batch).toLowerCase();
      return batch.name.toLowerCase().includes(query) || stdName.includes(query);
    });
  }, [batches, search, yearFilter, standardFilter]);

  const uniqueYears = useMemo(
    () => Array.from(new Set(batches.map((batch) => String(batch.academic_year)))).sort((a, b) => Number(b) - Number(a)),
    [batches],
  );

  async function createStandard(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = newStandardName.trim();
    if (!value) {
      setError('Standard name is required. Example: 11th Commerce');
      return;
    }

    setStandardSaving(true);
    setError(null);
    setSuccess(null);
    try {
      await apiRequest('/api/v1/admin/standards', {
        method: 'POST',
        body: JSON.stringify({ name: value }),
      });
      setSuccess(`Standard created: ${value}`);
      setNewStandardName('');
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create standard');
    } finally {
      setStandardSaving(false);
    }
  }

  async function createBatch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSuccess(null);
    try {
      await apiRequest('/api/v1/admin/batches', {
        method: 'POST',
        body: JSON.stringify({
          standard_id: newBatchStandardId,
          name: newBatchName.trim(),
          academic_year: Number(newBatchYear),
        }),
      });

      setNewBatchName('');
      setSuccess('Batch created successfully.');
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create batch');
    }
  }

  return (
    <section className="student-admin-theme">
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
        <div>
          <h1 style={{ marginTop: 0, marginBottom: 6 }}>Create Batch Workspace</h1>
          <p className="muted" style={{ marginTop: 0 }}>
            Dedicated page to create batches and monitor class-wise enrollment allocation.
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <Link className="btn" href="/admin/students">
            Back To Student Operations
          </Link>
          <Link className="btn" href="/admin/students#student-directory">
            Open Student Allocation
          </Link>
        </div>
      </div>

      {error ? <p style={{ color: '#dc2626' }}>{error}</p> : null}
      {success ? <p style={{ color: '#166534' }}>{success}</p> : null}

      <div className="grid" style={{ marginBottom: 14 }}>
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Total Batches</h3>
          <div style={{ fontSize: 28, fontWeight: 700 }}>{batches.length}</div>
        </div>
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Current Year Batches</h3>
          <div style={{ fontSize: 28, fontWeight: 700 }}>
            {batches.filter((batch) => batch.academic_year === new Date().getFullYear()).length}
          </div>
        </div>
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Students Allocated</h3>
          <div style={{ fontSize: 28, fontWeight: 700 }}>{totalAssignedStudents}</div>
        </div>
      </div>

      <div className="grid" style={{ gridTemplateColumns: 'minmax(360px, 520px) 1fr' }}>
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Create Standard</h3>
          <p className="muted" style={{ marginTop: 0 }}>
            First create missing standards like 11th Commerce / 12th Science, then create batches.
          </p>

          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 10 }}>
            {['Class 10', '11th Science', '11th Commerce', '12th Science', '12th Commerce'].map((name) => (
              <button
                key={name}
                className="btn"
                type="button"
                onClick={() => setNewStandardName(name)}
              >
                {name}
              </button>
            ))}
          </div>

          <form onSubmit={createStandard} style={{ marginBottom: 14 }}>
            <label className="field">
              <span>Standard Name</span>
              <input
                value={newStandardName}
                onChange={(e) => setNewStandardName(e.target.value)}
                placeholder="Example: 11th Commerce"
                required
              />
            </label>
            <button className="btn" type="submit" disabled={standardSaving}>
              {standardSaving ? 'Saving...' : 'Create Standard'}
            </button>
          </form>

          <h3 style={{ marginTop: 0 }}>Create New Batch</h3>
          <form onSubmit={createBatch}>
            <label className="field">
              <span>Standard</span>
              <select value={newBatchStandardId} onChange={(e) => setNewBatchStandardId(e.target.value)} required>
                <option value="">Select</option>
                {standards.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name} ({item.branch.code})
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>Batch Name</span>
              <input
                value={newBatchName}
                onChange={(e) => setNewBatchName(e.target.value)}
                placeholder="Example: Morning Batch A"
                required
              />
            </label>
            <label className="field">
              <span>Academic Year</span>
              <input
                value={newBatchYear}
                onChange={(e) => setNewBatchYear(e.target.value)}
                inputMode="numeric"
                pattern="[0-9]{4}"
                required
              />
            </label>
            <button className="btn" type="submit" disabled={loading}>
              {loading ? 'Saving...' : 'Create Batch'}
            </button>
          </form>
        </div>

        <div className="card">
          <h3 style={{ marginTop: 0 }}>Batch Directory</h3>
          <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))' }}>
            <label className="field">
              <span>Search</span>
              <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="batch / standard" />
            </label>
            <label className="field">
              <span>Academic Year</span>
              <select value={yearFilter} onChange={(e) => setYearFilter(e.target.value)}>
                <option value="all">All</option>
                {uniqueYears.map((year) => (
                  <option key={year} value={year}>
                    {year}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>Standard</span>
              <select value={standardFilter} onChange={(e) => setStandardFilter(e.target.value)}>
                <option value="all">All</option>
                {standards.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {loading ? (
            <p>Loading...</p>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Batch Name</th>
                  <th>Standard</th>
                  <th>Year</th>
                  <th>Students</th>
                </tr>
              </thead>
              <tbody>
                {visibleBatches.map((batch) => (
                  <tr key={batch.id}>
                    <td>{batch.name}</td>
                    <td>{batchStandardName(batch)}</td>
                    <td>{batch.academic_year}</td>
                    <td>{studentsByBatch[batch.id] ?? 0}</td>
                  </tr>
                ))}
                {visibleBatches.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="muted">
                      No batches found for selected filters.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </section>
  );
}
