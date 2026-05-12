'use client';

import Link from 'next/link';
import { useParams, useSearchParams } from 'next/navigation';
import { FormEvent, useEffect, useMemo, useState } from 'react';

import { apiRequest } from '@/lib/api';
import { API_BASE_URL } from '@/lib/env';

import styles from '../../fees.module.css';

type StudentInfo = {
  student_id: string;
  user_id: string;
  full_name: string;
  class_name: string | null;
  class_level: number | null;
  stream: string;
  phone: string | null;
  parent_contact_number: string | null;
};

type CurrentAssignment = {
  assignment_id: string;
  fee_structure_id: string;
  fee_structure_name: string;
  fee_amount: number;
  installment_count: number;
  assigned_at: string;
  updated_at: string;
};

type FeeStructureOption = {
  id: string;
  name: string;
  class_level: number;
  stream: 'science' | 'commerce' | null;
  total_amount: number;
  installment_count: number;
};

type StudentBilling = {
  fee_amount: number | null;
  paid_amount: number;
  pending_amount: number;
  installments_paid_count: number;
  installment_target_count: number | null;
  last_paid_at: string | null;
  next_due_date?: string | null;
  missed_payment_count?: number;
  is_overdue?: boolean;
  is_fully_paid: boolean;
};

type StudentPaymentItem = {
  payment_id: string;
  invoice_id: string;
  invoice_no: string;
  installment_no: number | null;
  period_label: string;
  amount: number;
  payment_mode: string;
  reference_no: string | null;
  note: string | null;
  paid_at: string;
  created_at: string;
};

type StudentInstallmentItem = {
  invoice_id: string;
  invoice_no: string;
  installment_no: number | null;
  period_label: string;
  due_date: string | null;
  amount: number;
  balance_amount: number;
  status: string;
  paid_at: string | null;
  is_missed: boolean;
  days_overdue: number;
  reminder_enabled: boolean;
  last_reminder_sent_at: string | null;
};

type ReceiptInfo = {
  file_name: string;
  download_url: string;
  generated_at: string;
  invoice_no: string | null;
  payment_id: string;
};

type AssignmentResponse = {
  student: StudentInfo;
  current_assignment: CurrentAssignment | null;
  billing: StudentBilling;
  payments: StudentPaymentItem[];
  installments: StudentInstallmentItem[];
  available_structures: FeeStructureOption[];
};

type AssignResponse = {
  assignment_id: string;
  student_id: string;
  fee_structure_id: string;
  fee_structure_name: string;
  fee_amount: number;
  installment_count: number;
  assigned: boolean;
  paid_amount: number;
  pending_amount: number;
  is_fully_paid: boolean;
  updated_at: string;
};

type RecordPaymentResponse = {
  student_id: string;
  payment: StudentPaymentItem;
  billing: StudentBilling;
  receipt: ReceiptInfo | null;
};

type ReceiptFetchResponse = {
  student_id: string;
  student_name: string;
  is_fully_paid: boolean;
  generated: boolean;
  receipt: ReceiptInfo;
};

type ReceiptWhatsappResponse = {
  student_id: string;
  student_name: string;
  receipt: ReceiptInfo;
  delivery: {
    status: string;
    provider: string;
    to_phone: string;
    provider_message_id: string | null;
    provider_response: string;
  };
  message: string;
};

type SectionKey = 'students' | 'pending' | 'paid' | 'structure' | 'overdue';

function currency(value: number): string {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(value);
}

function prettyStream(stream: string): string {
  const value = stream.trim().toLowerCase();
  if (value === 'general' || value === 'general science') {
    return 'General Science';
  }
  if (value === 'science') {
    return 'Science';
  }
  if (value === 'commerce') {
    return 'Commerce';
  }
  return stream || '-';
}

function sectionOrDefault(value: string | null): SectionKey {
  if (value === 'students' || value === 'pending' || value === 'paid' || value === 'structure' || value === 'overdue') {
    return value;
  }
  return 'students';
}

function todayIsoDate(): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function formatDateTime(value: string | null): string {
  if (!value) {
    return '-';
  }
  return new Date(value).toLocaleString();
}

function formatDate(value: string | null): string {
  if (!value) {
    return '-';
  }
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) {
    return value;
  }
  return dt.toLocaleDateString('en-IN');
}

export default function AdminFeeStudentAssignmentPage() {
  const params = useParams<{ studentId: string }>();
  const searchParams = useSearchParams();

  const studentId = typeof params.studentId === 'string' ? params.studentId : '';
  const section = sectionOrDefault(searchParams.get('section'));

  const [student, setStudent] = useState<StudentInfo | null>(null);
  const [currentAssignment, setCurrentAssignment] = useState<CurrentAssignment | null>(null);
  const [structures, setStructures] = useState<FeeStructureOption[]>([]);
  const [billing, setBilling] = useState<StudentBilling | null>(null);
  const [payments, setPayments] = useState<StudentPaymentItem[]>([]);
  const [installments, setInstallments] = useState<StudentInstallmentItem[]>([]);
  const [selectedStructureId, setSelectedStructureId] = useState('');
  const [receipt, setReceipt] = useState<ReceiptInfo | null>(null);

  const [loading, setLoading] = useState(true);
  const [assigning, setAssigning] = useState(false);
  const [recordingPayment, setRecordingPayment] = useState(false);
  const [loadingReceipt, setLoadingReceipt] = useState(false);
  const [sendingWhatsapp, setSendingWhatsapp] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const [paymentAmount, setPaymentAmount] = useState('');
  const [paidOn, setPaidOn] = useState(todayIsoDate());
  const [paymentMode, setPaymentMode] = useState('cash');
  const [referenceNo, setReferenceNo] = useState('');
  const [periodLabel, setPeriodLabel] = useState('');
  const [paymentNote, setPaymentNote] = useState('');
  const [selectedInstallmentNo, setSelectedInstallmentNo] = useState<string>('auto');

  const returnHref = useMemo(() => `/admin/fees?section=${section}`, [section]);

  const sortedInstallments = useMemo(
    () => [...installments].sort((a, b) => (a.installment_no ?? 999) - (b.installment_no ?? 999)),
    [installments],
  );

  const firstInstallmentPaidAmount = useMemo(() => {
    const first = sortedInstallments.find((item) => item.installment_no === 1) ?? sortedInstallments[0];
    if (!first) {
      return 0;
    }
    return Math.max(Number(first.amount || 0) - Number(first.balance_amount || 0), 0);
  }, [sortedInstallments]);

  const nextInstallmentDateFromSchedule = useMemo(() => {
    const pending = sortedInstallments.find((item) => Number(item.balance_amount || 0) > 0.0001);
    return pending?.due_date ?? null;
  }, [sortedInstallments]);

  const missedInstallmentDates = useMemo(
    () => sortedInstallments.filter((item) => item.is_missed).map((item) => formatDate(item.due_date)),
    [sortedInstallments],
  );

  const pendingInstallmentOptions = useMemo(
    () => sortedInstallments.filter((item) => item.installment_no !== null && Number(item.balance_amount || 0) > 0.0001),
    [sortedInstallments],
  );

  async function loadReceipt(options?: { regenerate?: boolean }) {
    if (!studentId) {
      return;
    }

    setLoadingReceipt(true);
    try {
      const query = options?.regenerate ? '?regenerate=true' : '';
      const response = await apiRequest<ReceiptFetchResponse>(`/api/v1/admin/fees/students/${studentId}/receipt/latest${query}`);
      setReceipt(response.receipt);
    } catch {
      setReceipt(null);
    } finally {
      setLoadingReceipt(false);
    }
  }

  async function load() {
    if (!studentId) {
      setError('Invalid student id');
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await apiRequest<AssignmentResponse>(`/api/v1/admin/fees/students/${studentId}/assignment`);
      setStudent(response.student);
      setCurrentAssignment(response.current_assignment);
      setStructures(response.available_structures);
      setBilling(response.billing);
      setPayments(response.payments);
      setInstallments(response.installments ?? []);
      setSelectedInstallmentNo('auto');

      if (response.current_assignment?.fee_structure_id) {
        setSelectedStructureId(response.current_assignment.fee_structure_id);
      } else if (response.available_structures.length > 0) {
        setSelectedStructureId(response.available_structures[0].id);
      } else {
        setSelectedStructureId('');
      }

      if (response.billing.pending_amount > 0) {
        setPaymentAmount(String(response.billing.pending_amount));
      } else {
        setPaymentAmount('');
      }

      if (response.current_assignment) {
        await loadReceipt();
      } else {
        setReceipt(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load student assignment');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [studentId]);

  async function submitAssign(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!selectedStructureId) {
      setError('Select a fee structure first.');
      return;
    }

    setAssigning(true);
    setError(null);
    setSuccessMessage(null);

    try {
      await apiRequest<AssignResponse>(`/api/v1/admin/fees/students/${studentId}/assignment`, {
        method: 'PUT',
        body: JSON.stringify({ fee_structure_id: selectedStructureId }),
      });

      await load();
      setSuccessMessage('Fee structure assigned successfully.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to assign fee structure');
    } finally {
      setAssigning(false);
    }
  }

  async function submitPayment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!billing || !currentAssignment) {
      setError('Assign fee structure before recording payment.');
      return;
    }

    const amount = Number(paymentAmount);
    if (!Number.isFinite(amount) || amount <= 0) {
      setError('Enter a valid payment amount.');
      return;
    }

    setRecordingPayment(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const response = await apiRequest<RecordPaymentResponse>(`/api/v1/admin/fees/students/${studentId}/payments`, {
        method: 'POST',
        body: JSON.stringify({
          amount,
          paid_on: paidOn,
          payment_mode: paymentMode,
          reference_no: referenceNo.trim() || null,
          note: paymentNote.trim() || null,
          period_label: periodLabel.trim() || null,
          installment_no: selectedInstallmentNo === 'auto' ? null : Number(selectedInstallmentNo),
        }),
      });

      setBilling(response.billing);
      setPayments((prev) => [response.payment, ...prev]);
      setPaymentNote('');
      setReferenceNo('');
      setPeriodLabel('');
      setSelectedInstallmentNo('auto');
      setPaymentAmount(response.billing.pending_amount > 0 ? String(response.billing.pending_amount) : '');
      setSuccessMessage('Payment updated and pending amount recalculated.');

      if (response.receipt) {
        setReceipt(response.receipt);
      } else if (response.billing.is_fully_paid) {
        await loadReceipt();
      }

      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to record payment');
    } finally {
      setRecordingPayment(false);
    }
  }

  async function onDownloadReceipt() {
    if (!receipt) {
      return;
    }
    const href = `${API_BASE_URL}${receipt.download_url}`;
    window.open(href, '_blank', 'noopener,noreferrer');
  }

  async function onRegenerateReceipt() {
    setError(null);
    setSuccessMessage(null);
    try {
      await loadReceipt({ regenerate: true });
      setSuccessMessage('Receipt regenerated successfully.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to regenerate receipt');
    }
  }

  async function onSendWhatsapp() {
    setSendingWhatsapp(true);
    setError(null);
    setSuccessMessage(null);
    try {
      const response = await apiRequest<ReceiptWhatsappResponse>(`/api/v1/admin/fees/students/${studentId}/receipt/latest/whatsapp`, {
        method: 'POST',
        body: JSON.stringify({}),
      });
      setSuccessMessage(`Receipt sent on WhatsApp (${response.delivery.status}) to ${response.delivery.to_phone}.`);
      setReceipt(response.receipt);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send WhatsApp receipt');
    } finally {
      setSendingWhatsapp(false);
    }
  }

  return (
    <section className={styles.root}>
      <div className={styles.headerRow}>
        <h1 className={styles.title}>Update Student Fee</h1>
        <Link className={styles.btnSecondary} href={returnHref}>
          Back to Student List
        </Link>
      </div>

      {error ? <p className={styles.error}>{error}</p> : null}
      {successMessage ? <p className={styles.subtitle}>{successMessage}</p> : null}

      {loading ? (
        <div className={styles.card}>Loading student details...</div>
      ) : !student ? (
        <div className={styles.card}>Student not found.</div>
      ) : (
        <>
          <div className={styles.summaryGrid}>
            <div className={styles.summaryCard}>
              <div className={styles.summaryLabel}>Student</div>
              <div style={{ marginTop: 8, display: 'grid', gap: 6, fontSize: 14 }}>
                <div><strong>Name:</strong> {student.full_name}</div>
                <div><strong>Class:</strong> {student.class_name ?? '-'}</div>
                <div><strong>Stream:</strong> {prettyStream(student.stream)}</div>
                <div><strong>Contact:</strong> {student.phone ?? '-'}</div>
                <div><strong>Parents Number:</strong> {student.parent_contact_number ?? '-'}</div>
              </div>
            </div>

            <div className={styles.summaryCard}>
              <div className={styles.summaryLabel}>Fee Status</div>
              <div style={{ marginTop: 8, display: 'grid', gap: 6, fontSize: 14 }}>
                <div><strong>Assigned Structure:</strong> {currentAssignment?.fee_structure_name ?? '-'}</div>
                <div><strong>Total Fee:</strong> {billing?.fee_amount !== null && billing?.fee_amount !== undefined ? currency(billing.fee_amount) : '-'}</div>
                <div><strong>Paid:</strong> {currency(billing?.paid_amount ?? 0)}</div>
                <div><strong>Pending:</strong> {currency(billing?.pending_amount ?? 0)}</div>
                <div><strong>First Installment Paid:</strong> {currency(firstInstallmentPaidAmount)}</div>
                <div><strong>Next Installment Date:</strong> {formatDate(nextInstallmentDateFromSchedule ?? (billing?.next_due_date as string | null) ?? null)}</div>
                <div><strong>Missed Installment Dates:</strong> {missedInstallmentDates.length > 0 ? missedInstallmentDates.join(', ') : '-'}</div>
                <div>
                  <strong>Installments:</strong>{' '}
                  {billing?.installment_target_count
                    ? `${billing.installments_paid_count}/${billing.installment_target_count}`
                    : `${billing?.installments_paid_count ?? 0}/-`}
                </div>
                <div><strong>Last Paid:</strong> {formatDateTime(billing?.last_paid_at ?? null)}</div>
                <div><strong>Next Due:</strong> {formatDate((billing?.next_due_date as string | null) ?? null)}</div>
                <div><strong>Missed Installments:</strong> {billing?.missed_payment_count ?? 0}</div>
                <div>
                  <strong>Overdue:</strong>{' '}
                  {billing?.is_overdue ? <span className={styles.cross}>Yes</span> : <span className={styles.tick}>No</span>}
                </div>
                <div>
                  <strong>Full Paid:</strong>{' '}
                  {billing?.is_fully_paid ? <span className={styles.tick}>✓</span> : <span className={styles.cross}>✕</span>}
                </div>
              </div>

              {currentAssignment ? (
                <div style={{ marginTop: 12 }}>
                  <div className={styles.buttonRow}>
                    <button className={styles.btnPrimary} type="button" onClick={onDownloadReceipt} disabled={!receipt || loadingReceipt}>
                      {loadingReceipt ? 'Loading...' : payments.length > 0 ? 'Print Updated Receipt PDF' : 'Print & Save Receipt PDF'}
                    </button>
                    <button className={styles.btnNeutral} type="button" onClick={onRegenerateReceipt} disabled={loadingReceipt}>
                      Regenerate Receipt
                    </button>
                    <button className={styles.btnSecondary} type="button" onClick={onSendWhatsapp} disabled={sendingWhatsapp || loadingReceipt || !receipt}>
                      {sendingWhatsapp ? 'Sending...' : 'Send Receipt to Parent WhatsApp'}
                    </button>
                  </div>
                  <p className={styles.cardSubtle} style={{ marginTop: 8 }}>
                    {receipt
                      ? `Latest receipt: ${receipt.file_name} (${formatDateTime(receipt.generated_at)})`
                      : 'Generate receipt once fee is finalized.'}
                  </p>
                </div>
              ) : null}
            </div>
          </div>

          <div className={styles.summaryGrid}>
            <div className={styles.card}>
              <h3 className={styles.cardTitle}>Assign Fee Structure</h3>
              {structures.length === 0 ? (
                <p className={styles.cardSubtle}>
                  No matching active fee structure found for this student class/stream. Create one in{' '}
                  <Link href="/admin/fees?section=structure" style={{ color: '#8fb6ff', fontWeight: 600 }}>
                    Fee Structure
                  </Link>{' '}
                  section.
                </p>
              ) : (
                <form onSubmit={submitAssign}>
                  <label className={styles.field} style={{ maxWidth: 560 }}>
                    <span className={styles.fieldLabel}>Fee Structure</span>
                    <select
                      className={styles.select}
                      value={selectedStructureId}
                      onChange={(event) => setSelectedStructureId(event.target.value)}
                      required
                    >
                      {structures.map((item) => (
                        <option key={item.id} value={item.id}>
                          {`${item.name} • ${currency(item.total_amount)} • ${item.installment_count} installment(s)`}
                        </option>
                      ))}
                    </select>
                  </label>

                  <button className={styles.btnPrimary} type="submit" disabled={assigning}>
                    {assigning ? 'Saving...' : 'Save Structure'}
                  </button>
                </form>
              )}
            </div>

            <div className={styles.card}>
              <h3 className={styles.cardTitle}>Add Paid Installment</h3>
              {!currentAssignment ? (
                <p className={styles.cardSubtle}>Assign structure first to record payment.</p>
              ) : billing?.is_fully_paid ? (
                <p style={{ marginBottom: 0, color: '#9deeb9', fontWeight: 600 }}>Fee is fully paid.</p>
              ) : (
                <form onSubmit={submitPayment}>
                  <div className={styles.formGrid}>
                    <label className={styles.field}>
                      <span className={styles.fieldLabel}>Paid Amount</span>
                      <input
                        className={styles.input}
                        type="number"
                        min="1"
                        step="0.01"
                        value={paymentAmount}
                        onChange={(event) => setPaymentAmount(event.target.value)}
                        required
                      />
                    </label>
                    <label className={styles.field}>
                      <span className={styles.fieldLabel}>Paid On</span>
                      <input className={styles.input} type="date" value={paidOn} onChange={(event) => setPaidOn(event.target.value)} required />
                    </label>
                    <label className={styles.field}>
                      <span className={styles.fieldLabel}>Payment Mode</span>
                      <select className={styles.select} value={paymentMode} onChange={(event) => setPaymentMode(event.target.value)}>
                        <option value="cash">Cash</option>
                        <option value="upi">UPI</option>
                        <option value="bank_transfer">Bank Transfer</option>
                        <option value="card">Card</option>
                        <option value="cheque">Cheque</option>
                        <option value="other">Other</option>
                      </select>
                    </label>
                  </div>

                  <label className={styles.field}>
                    <span className={styles.fieldLabel}>Installment Selection</span>
                    <select className={styles.select} value={selectedInstallmentNo} onChange={(event) => setSelectedInstallmentNo(event.target.value)}>
                      <option value="auto">Auto Allocate (Next Due)</option>
                      {pendingInstallmentOptions.map((item) => (
                        <option key={item.invoice_id} value={String(item.installment_no)}>
                          {`Installment ${item.installment_no ?? '-'} • Due ${formatDate(item.due_date)} • Balance ${currency(item.balance_amount)}`}
                        </option>
                      ))}
                    </select>
                  </label>

                  <label className={styles.field}>
                    <span className={styles.fieldLabel}>Reference Number (optional)</span>
                    <input className={styles.input} value={referenceNo} onChange={(event) => setReferenceNo(event.target.value)} />
                  </label>

                  <label className={styles.field}>
                    <span className={styles.fieldLabel}>Installment Label (optional)</span>
                    <input className={styles.input} value={periodLabel} onChange={(event) => setPeriodLabel(event.target.value)} placeholder="Installment April" />
                  </label>

                  <label className={styles.field}>
                    <span className={styles.fieldLabel}>Note (optional)</span>
                    <textarea className={styles.textarea} rows={2} value={paymentNote} onChange={(event) => setPaymentNote(event.target.value)} />
                  </label>

                  <button className={styles.btnPrimary} type="submit" disabled={recordingPayment}>
                    {recordingPayment ? 'Updating...' : 'Update Paid Fee'}
                  </button>
                </form>
              )}
            </div>
          </div>

          <div className={styles.card}>
            <h3 className={styles.cardTitle}>Installment Schedule & Missed Dates</h3>
            {installments.length === 0 ? (
              <p className={styles.cardSubtle}>No installment schedule available yet.</p>
            ) : (
              <div className={styles.tableWrap}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th>Installment</th>
                      <th>Invoice</th>
                      <th>Due Date</th>
                      <th>Status</th>
                      <th>Amount</th>
                      <th>Balance</th>
                      <th>Missed</th>
                      <th>Last Reminder</th>
                    </tr>
                  </thead>
                  <tbody>
                    {installments.map((item) => (
                      <tr key={item.invoice_id}>
                        <td>{item.installment_no ?? '-'}</td>
                        <td>
                          <div style={{ fontWeight: 700 }}>{item.invoice_no}</div>
                          <div className={styles.muted} style={{ fontSize: 12 }}>{item.period_label}</div>
                        </td>
                        <td>{formatDate(item.due_date)}</td>
                        <td style={{ textTransform: 'capitalize' }}>{item.status}</td>
                        <td>{currency(item.amount)}</td>
                        <td>{currency(item.balance_amount)}</td>
                        <td>
                          {item.is_missed ? (
                            <span className={styles.cross} title="Missed installment">{item.days_overdue}d</span>
                          ) : (
                            <span className={styles.tick} title="On time">✓</span>
                          )}
                        </td>
                        <td>{formatDateTime(item.last_reminder_sent_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className={styles.card}>
            <h3 className={styles.cardTitle}>Installment History</h3>
            {payments.length === 0 ? (
              <p className={styles.cardSubtle}>No installments recorded yet.</p>
            ) : (
              <div className={styles.tableWrap}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th>Installment</th>
                      <th>Invoice</th>
                      <th>Amount</th>
                      <th>Mode</th>
                      <th>Reference</th>
                      <th>Paid At</th>
                      <th>Paid</th>
                    </tr>
                  </thead>
                  <tbody>
                    {payments.map((item) => (
                      <tr key={item.payment_id}>
                        <td>{item.installment_no ?? '-'}</td>
                        <td>
                          <div style={{ fontWeight: 700 }}>{item.invoice_no}</div>
                          <div className={styles.muted} style={{ fontSize: 12 }}>{item.period_label}</div>
                        </td>
                        <td>{currency(item.amount)}</td>
                        <td style={{ textTransform: 'capitalize' }}>{item.payment_mode.replace('_', ' ')}</td>
                        <td>{item.reference_no ?? '-'}</td>
                        <td>{formatDateTime(item.paid_at)}</td>
                        <td><span className={styles.tick}>✓</span></td>
                      </tr>
                    ))}
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
