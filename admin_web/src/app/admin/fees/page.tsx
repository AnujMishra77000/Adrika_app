'use client';

import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { FormEvent, useEffect, useMemo, useState } from 'react';

import { apiRequest } from '@/lib/api';

import styles from './fees.module.css';

type FeeStructure = {
  id: string;
  name: string;
  class_level: number;
  stream: 'science' | 'commerce' | null;
  total_amount: number;
  installment_count: number;
  description: string | null;
  is_active: boolean;
};

type FeeStudent = {
  student_id: string;
  user_id: string;
  full_name: string;
  phone: string | null;
  parent_contact_number: string | null;
  class_name: string | null;
  class_level: number | null;
  stream: string;
  invoice_count: number;
  total_amount: number;
  paid_amount: number;
  pending_amount: number;
  next_due_date: string | null;
  payment_status: 'pending' | 'paid' | 'not_assigned' | string;
  account_status: string;
  fee_structure_assigned: boolean;
  fee_structure_id: string | null;
  fee_structure_name: string | null;
  fee_amount: number | null;
  installments_paid_count: number;
  installment_target_count: number | null;
  is_fully_paid: boolean;
  last_paid_at: string | null;
};

type FeeSummary = {
  total_students: number;
  paid_students: number;
  pending_students: number;
  students_without_fee: number;
  total_invoiced_amount: number;
  total_paid_amount: number;
  total_pending_amount: number;
};

type SectionKey = 'structure' | 'students' | 'pending' | 'paid';

const SECTION_LABELS: Record<SectionKey, string> = {
  structure: 'Fee Structure',
  students: 'Student List',
  pending: 'Pending',
  paid: 'Paid',
};

const DEFAULT_SUMMARY: FeeSummary = {
  total_students: 0,
  paid_students: 0,
  pending_students: 0,
  students_without_fee: 0,
  total_invoiced_amount: 0,
  total_paid_amount: 0,
  total_pending_amount: 0,
};

function currency(value: number): string {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(value);
}

function normalizedStream(classLevel: number, stream: string): 'science' | 'commerce' | null {
  if (classLevel === 10) {
    return null;
  }
  if (stream === 'science' || stream === 'commerce') {
    return stream;
  }
  return null;
}

export default function AdminFeesPage() {
  const searchParams = useSearchParams();

  const [section, setSection] = useState<SectionKey>('students');
  const [summary, setSummary] = useState<FeeSummary>(DEFAULT_SUMMARY);

  const [structures, setStructures] = useState<FeeStructure[]>([]);
  const [students, setStudents] = useState<FeeStudent[]>([]);

  const [loadingStructures, setLoadingStructures] = useState(true);
  const [loadingStudents, setLoadingStudents] = useState(false);
  const [savingStructure, setSavingStructure] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [search, setSearch] = useState('');
  const [classFilter, setClassFilter] = useState('');
  const [streamFilter, setStreamFilter] = useState('');

  const [editingStructureId, setEditingStructureId] = useState<string | null>(null);
  const [name, setName] = useState('');
  const [classLevel, setClassLevel] = useState('10');
  const [stream, setStream] = useState<'science' | 'commerce' | ''>('');
  const [totalAmount, setTotalAmount] = useState('');
  const [installmentCount, setInstallmentCount] = useState('1');
  const [description, setDescription] = useState('');
  const [isActive, setIsActive] = useState(true);

  const selectedClassLevel = Number(classLevel);
  const viewForSection = section === 'pending' ? 'pending' : section === 'paid' ? 'paid' : 'all';
  const showFullPaidColumn = section === 'students' || section === 'paid';

  const cards = useMemo(
    () => [
      { title: 'Fully Paid', value: String(summary.paid_students) },
      { title: 'Pending Fees', value: String(summary.pending_students) },
      { title: 'Without Setup', value: String(summary.students_without_fee) },
      { title: 'Pending Amount', value: currency(summary.total_pending_amount) },
    ],
    [summary],
  );

  async function loadSummary() {
    const response = await apiRequest<FeeSummary>('/api/v1/admin/fees/summary');
    setSummary(response);
  }

  async function loadStructures() {
    setLoadingStructures(true);
    const response = await apiRequest<{ items: FeeStructure[] }>('/api/v1/admin/fees/structures?limit=100&offset=0');
    setStructures(response.items);
    setLoadingStructures(false);
  }

  async function loadStudents(
    view: 'all' | 'pending' | 'paid',
    options?: { searchText?: string; classValue?: string; streamValue?: string },
  ) {
    setLoadingStudents(true);

    const params = new URLSearchParams({
      view,
      limit: '100',
      offset: '0',
    });

    const searchValue = options?.searchText ?? search;
    const classValue = options?.classValue ?? classFilter;
    const streamValue = options?.streamValue ?? streamFilter;

    const trimmedSearch = searchValue.trim();
    if (trimmedSearch) {
      params.set('search', trimmedSearch);
    }

    if (classValue) {
      params.set('class_level', classValue);
    }

    if (streamValue) {
      params.set('stream', streamValue);
    }

    const response = await apiRequest<{ items: FeeStudent[] }>(`/api/v1/admin/fees/students?${params.toString()}`);
    setStudents(response.items);
    setLoadingStudents(false);
  }

  async function bootstrap() {
    setError(null);
    try {
      await Promise.all([loadSummary(), loadStructures(), loadStudents('all')]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load fee module');
      setLoadingStructures(false);
      setLoadingStudents(false);
    }
  }

  useEffect(() => {
    void bootstrap();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const sectionQuery = searchParams.get('section');
    if (sectionQuery === 'structure' || sectionQuery === 'students' || sectionQuery === 'pending' || sectionQuery === 'paid') {
      setSection(sectionQuery);
    }
  }, [searchParams]);

  useEffect(() => {
    if (section === 'structure') {
      return;
    }

    setError(null);
    void loadStudents(viewForSection).catch((err) => {
      setError(err instanceof Error ? err.message : 'Failed to load student fee list');
      setLoadingStudents(false);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [section]);

  async function onApplyFilter() {
    setError(null);
    try {
      await loadStudents(viewForSection);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to apply filters');
      setLoadingStudents(false);
    }
  }

  async function onPresetFilter(classValue: string, streamValue: string) {
    setClassFilter(classValue);
    setStreamFilter(streamValue);
    setError(null);
    try {
      await loadStudents(viewForSection, { classValue, streamValue });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to filter student list');
      setLoadingStudents(false);
    }
  }

  function resetStructureForm() {
    setEditingStructureId(null);
    setName('');
    setClassLevel('10');
    setStream('');
    setTotalAmount('');
    setInstallmentCount('1');
    setDescription('');
    setIsActive(true);
  }

  async function submitStructure(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSavingStructure(true);
    setError(null);

    try {
      const payload = {
        name: name.trim(),
        class_level: selectedClassLevel,
        stream: normalizedStream(selectedClassLevel, stream),
        total_amount: Number(totalAmount),
        installment_count: Number(installmentCount),
        description: description.trim() || null,
        is_active: isActive,
      };

      if (editingStructureId) {
        await apiRequest(`/api/v1/admin/fees/structures/${editingStructureId}`, {
          method: 'PATCH',
          body: JSON.stringify(payload),
        });
      } else {
        await apiRequest('/api/v1/admin/fees/structures', {
          method: 'POST',
          body: JSON.stringify(payload),
        });
      }

      resetStructureForm();
      await Promise.all([loadSummary(), loadStructures()]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save fee structure');
    } finally {
      setSavingStructure(false);
    }
  }

  function editStructure(structureItem: FeeStructure) {
    setEditingStructureId(structureItem.id);
    setName(structureItem.name);
    setClassLevel(String(structureItem.class_level));
    setStream((structureItem.stream as 'science' | 'commerce' | null) ?? '');
    setTotalAmount(String(structureItem.total_amount));
    setInstallmentCount(String(structureItem.installment_count));
    setDescription(structureItem.description ?? '');
    setIsActive(structureItem.is_active);
    setSection('structure');
  }

  async function removeStructure(structureId: string) {
    const ok = window.confirm('Delete this fee structure?');
    if (!ok) {
      return;
    }

    setError(null);
    try {
      await apiRequest(`/api/v1/admin/fees/structures/${structureId}`, { method: 'DELETE' });
      await Promise.all([loadSummary(), loadStructures()]);
      if (editingStructureId === structureId) {
        resetStructureForm();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete fee structure');
    }
  }

  return (
    <section className={styles.root}>
      <div className={styles.headerRow}>
        <div>
          <h1 className={styles.title}>Fee Management</h1>
          <p className={styles.subtitle}>Structured fee operations for Student List, Pending and Paid flows.</p>
        </div>
      </div>

      {error ? <p className={styles.error}>{error}</p> : null}

      <div className={styles.summaryGrid}>
        {cards.map((card) => (
          <div className={styles.summaryCard} key={card.title}>
            <div className={styles.summaryLabel}>{card.title}</div>
            <div className={styles.summaryValue}>{card.value}</div>
          </div>
        ))}
      </div>

      <div className={styles.sectionTabs}>
        {(Object.keys(SECTION_LABELS) as SectionKey[]).map((key) => {
          const active = section === key;
          return (
            <button
              key={key}
              type="button"
              className={`${styles.tabButton} ${active ? styles.tabActive : ''}`.trim()}
              onClick={() => setSection(key)}
            >
              {SECTION_LABELS[key]}
            </button>
          );
        })}
      </div>

      {section === 'structure' ? (
        <>
          <div className={styles.card}>
            <h3 className={styles.cardTitle}>{editingStructureId ? 'Update Fee Structure' : 'Create Fee Structure'}</h3>
            <form onSubmit={submitStructure}>
              <label className={styles.field}>
                <span className={styles.fieldLabel}>Name</span>
                <input className={styles.input} value={name} onChange={(e) => setName(e.target.value)} required />
              </label>

              <div className={styles.formGrid}>
                <label className={styles.field}>
                  <span className={styles.fieldLabel}>Class</span>
                  <select className={styles.select} value={classLevel} onChange={(e) => setClassLevel(e.target.value)} required>
                    <option value="10">10th</option>
                    <option value="11">11th</option>
                    <option value="12">12th</option>
                  </select>
                </label>

                <label className={styles.field}>
                  <span className={styles.fieldLabel}>Stream {selectedClassLevel === 10 ? '(Not Required)' : ''}</span>
                  <select
                    className={styles.select}
                    value={stream}
                    onChange={(e) => setStream(e.target.value as 'science' | 'commerce' | '')}
                    disabled={selectedClassLevel === 10}
                    required={selectedClassLevel !== 10}
                  >
                    <option value="">Select</option>
                    <option value="science">Science</option>
                    <option value="commerce">Commerce</option>
                  </select>
                </label>
              </div>

              <div className={styles.formGrid}>
                <label className={styles.field}>
                  <span className={styles.fieldLabel}>Total Amount</span>
                  <input
                    className={styles.input}
                    type="number"
                    min="1"
                    step="1"
                    value={totalAmount}
                    onChange={(e) => setTotalAmount(e.target.value)}
                    required
                  />
                </label>
                <label className={styles.field}>
                  <span className={styles.fieldLabel}>Installments</span>
                  <input
                    className={styles.input}
                    type="number"
                    min="1"
                    max="24"
                    value={installmentCount}
                    onChange={(e) => setInstallmentCount(e.target.value)}
                    required
                  />
                </label>
              </div>

              <label className={styles.field}>
                <span className={styles.fieldLabel}>Description (optional)</span>
                <textarea className={styles.textarea} rows={3} value={description} onChange={(e) => setDescription(e.target.value)} />
              </label>

              <label style={{ display: 'inline-flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
                Active
              </label>

              <div className={styles.buttonRow}>
                <button className={styles.btnPrimary} type="submit" disabled={savingStructure}>
                  {savingStructure ? 'Saving...' : editingStructureId ? 'Update Structure' : 'Create Structure'}
                </button>
                {editingStructureId ? (
                  <button className={styles.btnSecondary} type="button" onClick={resetStructureForm}>
                    Cancel Edit
                  </button>
                ) : null}
              </div>
            </form>
          </div>

          <div className={styles.card}>
            <h3 className={styles.cardTitle}>Fee Structure List</h3>
            {loadingStructures ? (
              <p className={styles.muted}>Loading...</p>
            ) : (
              <div className={styles.tableWrap}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Class</th>
                      <th>Stream</th>
                      <th>Total</th>
                      <th>Installments</th>
                      <th>Status</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {structures.map((item) => (
                      <tr key={item.id}>
                        <td>{item.name}</td>
                        <td>{item.class_level}</td>
                        <td>{item.stream ?? '-'}</td>
                        <td>{currency(item.total_amount)}</td>
                        <td>{item.installment_count}</td>
                        <td>
                          <span className={styles.badge}>{item.is_active ? 'active' : 'inactive'}</span>
                        </td>
                        <td>
                          <div className={styles.buttonRow}>
                            <button className={styles.btnNeutral} type="button" onClick={() => editStructure(item)}>
                              Edit
                            </button>
                            <button className={styles.btnDanger} type="button" onClick={() => removeStructure(item.id)}>
                              Delete
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                    {structures.length === 0 ? (
                      <tr>
                        <td colSpan={7} className={styles.muted}>
                          No fee structures found.
                        </td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      ) : (
        <>
          <div className={styles.card}>
            <h3 className={styles.cardTitle}>{SECTION_LABELS[section]} Filters</h3>
            <div className={styles.presetRow}>
              <button className={styles.btnPreset} type="button" onClick={() => onPresetFilter('', '')}>All</button>
              <button className={styles.btnPreset} type="button" onClick={() => onPresetFilter('10', '')}>10th</button>
              <button className={styles.btnPreset} type="button" onClick={() => onPresetFilter('11', 'science')}>11th Science</button>
              <button className={styles.btnPreset} type="button" onClick={() => onPresetFilter('11', 'commerce')}>11th Commerce</button>
              <button className={styles.btnPreset} type="button" onClick={() => onPresetFilter('12', 'science')}>12th Science</button>
              <button className={styles.btnPreset} type="button" onClick={() => onPresetFilter('12', 'commerce')}>12th Commerce</button>
            </div>

            <div className={styles.filtersGrid}>
              <label className={styles.field}>
                <span className={styles.fieldLabel}>Search (name / mobile / parent mobile)</span>
                <input className={styles.input} value={search} onChange={(e) => setSearch(e.target.value)} />
              </label>
              <label className={styles.field}>
                <span className={styles.fieldLabel}>Class</span>
                <select className={styles.select} value={classFilter} onChange={(e) => setClassFilter(e.target.value)}>
                  <option value="">All</option>
                  <option value="10">10th</option>
                  <option value="11">11th</option>
                  <option value="12">12th</option>
                </select>
              </label>
              <label className={styles.field}>
                <span className={styles.fieldLabel}>Stream</span>
                <select className={styles.select} value={streamFilter} onChange={(e) => setStreamFilter(e.target.value)}>
                  <option value="">All</option>
                  <option value="science">Science</option>
                  <option value="commerce">Commerce</option>
                </select>
              </label>
            </div>
            <button className={styles.btnPrimary} type="button" onClick={onApplyFilter}>
              Apply Filters
            </button>
          </div>

          <div className={styles.card}>
            <h3 className={styles.cardTitle}>{SECTION_LABELS[section]}</h3>
            {loadingStudents ? (
              <p className={styles.muted}>Loading...</p>
            ) : (
              <div className={styles.tableWrap}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th>Student Name</th>
                      <th>Class</th>
                      <th>Stream</th>
                      <th>Contact</th>
                      <th>Parents Number</th>
                      <th>Fee</th>
                      <th>Paid</th>
                      <th>Pending</th>
                      <th>Installments</th>
                      <th>Update</th>
                      <th>Assigned</th>
                      {showFullPaidColumn ? <th>Full Paid</th> : null}
                    </tr>
                  </thead>
                  <tbody>
                    {students.map((row) => (
                      <tr key={row.student_id}>
                        <td>
                          <div style={{ fontWeight: 700 }}>{row.full_name}</div>
                          <div className={styles.muted} style={{ fontSize: 12 }}>
                            {row.fee_structure_name ?? 'No structure assigned'}
                          </div>
                        </td>
                        <td>{row.class_name ?? '-'}</td>
                        <td>{row.stream || '-'}</td>
                        <td>{row.phone ?? '-'}</td>
                        <td>{row.parent_contact_number ?? '-'}</td>
                        <td>{row.fee_amount !== null ? currency(row.fee_amount) : '-'}</td>
                        <td>{currency(row.paid_amount)}</td>
                        <td>{currency(row.pending_amount)}</td>
                        <td>
                          {row.installment_target_count
                            ? `${row.installments_paid_count}/${row.installment_target_count}`
                            : `${row.installments_paid_count}/-`}
                        </td>
                        <td>
                          <Link className={styles.btnLink} href={`/admin/fees/students/${row.student_id}?section=${section}`}>
                            Update
                          </Link>
                        </td>
                        <td>
                          {row.fee_structure_assigned ? (
                            <span className={styles.tick} title="Fee structure assigned">✓</span>
                          ) : (
                            <span className={styles.cross} title="Not assigned">✕</span>
                          )}
                        </td>
                        {showFullPaidColumn ? (
                          <td>
                            {row.is_fully_paid ? (
                              <span className={styles.tick} title="Fully paid">✓</span>
                            ) : (
                              <span className={styles.cross} title="Not fully paid">✕</span>
                            )}
                          </td>
                        ) : null}
                      </tr>
                    ))}
                    {students.length === 0 ? (
                      <tr>
                        <td colSpan={showFullPaidColumn ? 12 : 11} className={styles.muted}>
                          No students found for this section.
                        </td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </section>
  );
}
