"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import { apiRequest } from "@/lib/api";

type StudentItem = {
  student_id: string;
  full_name: string;
  admission_no: string;
  roll_no: string;
};

type FeeInvoice = {
  id: string;
  student_id: string;
  student_name: string;
  invoice_no: string;
  period_label: string;
  due_date: string;
  amount: number;
  status: string;
  paid_at: string | null;
  created_at: string;
};

function suggestedInvoiceNo() {
  const now = new Date();
  const pad = (value: number) => `${value}`.padStart(2, "0");
  return `INV-${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}-${now.getTime()}`;
}

function defaultDueDate() {
  const now = new Date();
  now.setDate(now.getDate() + 7);
  return now.toISOString().slice(0, 10);
}

export default function AdminFeesPage() {
  const [students, setStudents] = useState<StudentItem[]>([]);
  const [invoices, setInvoices] = useState<FeeInvoice[]>([]);

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [filterStudentId, setFilterStudentId] = useState("");
  const [filterStatus, setFilterStatus] = useState("");

  const [studentId, setStudentId] = useState("");
  const [invoiceNo, setInvoiceNo] = useState(suggestedInvoiceNo());
  const [periodLabel, setPeriodLabel] = useState("Apr-2026");
  const [dueDate, setDueDate] = useState(defaultDueDate());
  const [amount, setAmount] = useState("1000");
  const [status, setStatus] = useState("pending");

  const studentNameMap = useMemo(
    () => new Map(students.map((item) => [item.student_id, item.full_name])),
    [students],
  );

  async function loadStudents() {
    const response = await apiRequest<{ items: StudentItem[] }>(
      "/api/v1/admin/students?limit=300&offset=0",
    );
    setStudents(response.items);
    if (!studentId && response.items.length > 0) {
      setStudentId(response.items[0].student_id);
    }
  }

  async function loadInvoices() {
    const params = new URLSearchParams({ limit: "200", offset: "0" });
    if (filterStudentId) {
      params.set("student_id", filterStudentId);
    }
    if (filterStatus) {
      params.set("status", filterStatus);
    }

    const response = await apiRequest<{ items: FeeInvoice[] }>(
      `/api/v1/admin/fee-invoices?${params.toString()}`,
    );
    setInvoices(response.items);
  }

  async function loadAll() {
    setLoading(true);
    setError(null);
    try {
      await Promise.all([loadStudents(), loadInvoices()]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load fee invoices");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await loadInvoices();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to filter invoices");
    } finally {
      setLoading(false);
    }
  }

  async function createInvoice(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await apiRequest("/api/v1/admin/fee-invoices", {
        method: "POST",
        body: JSON.stringify({
          student_id: studentId,
          invoice_no: invoiceNo,
          period_label: periodLabel,
          due_date: dueDate,
          amount: Number(amount),
          status,
        }),
      });

      setInvoiceNo(suggestedInvoiceNo());
      setPeriodLabel("");
      setAmount("1000");
      setStatus("pending");
      await loadInvoices();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create fee invoice");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section>
      <h1 style={{ marginTop: 0 }}>Fee Invoices</h1>
      <p className="muted">Create and monitor student fee invoices.</p>
      {error ? <p style={{ color: "#dc2626" }}>{error}</p> : null}

      <div className="grid" style={{ marginBottom: 16 }}>
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Filter Invoices</h3>
          <form onSubmit={applyFilters}>
            <label className="field">
              <span>Student</span>
              <select value={filterStudentId} onChange={(event) => setFilterStudentId(event.target.value)}>
                <option value="">All students</option>
                {students.map((student) => (
                  <option key={student.student_id} value={student.student_id}>
                    {student.full_name} ({student.admission_no})
                  </option>
                ))}
              </select>
            </label>

            <label className="field">
              <span>Status</span>
              <select value={filterStatus} onChange={(event) => setFilterStatus(event.target.value)}>
                <option value="">All statuses</option>
                <option value="pending">Pending</option>
                <option value="paid">Paid</option>
                <option value="overdue">Overdue</option>
                <option value="cancelled">Cancelled</option>
              </select>
            </label>

            <button className="btn" type="submit">
              Apply Filters
            </button>
          </form>
        </div>

        <div className="card">
          <h3 style={{ marginTop: 0 }}>Create Invoice</h3>
          <form onSubmit={createInvoice}>
            <label className="field">
              <span>Student</span>
              <select value={studentId} onChange={(event) => setStudentId(event.target.value)} required>
                <option value="">Select student</option>
                {students.map((student) => (
                  <option key={student.student_id} value={student.student_id}>
                    {student.full_name} ({student.admission_no})
                  </option>
                ))}
              </select>
            </label>

            <label className="field">
              <span>Invoice Number</span>
              <input value={invoiceNo} onChange={(event) => setInvoiceNo(event.target.value)} required />
            </label>

            <label className="field">
              <span>Period Label</span>
              <input value={periodLabel} onChange={(event) => setPeriodLabel(event.target.value)} required />
            </label>

            <label className="field">
              <span>Due Date</span>
              <input type="date" value={dueDate} onChange={(event) => setDueDate(event.target.value)} required />
            </label>

            <label className="field">
              <span>Amount</span>
              <input type="number" min="1" step="0.01" value={amount} onChange={(event) => setAmount(event.target.value)} required />
            </label>

            <label className="field">
              <span>Status</span>
              <select value={status} onChange={(event) => setStatus(event.target.value)}>
                <option value="pending">Pending</option>
                <option value="paid">Paid</option>
                <option value="overdue">Overdue</option>
                <option value="cancelled">Cancelled</option>
              </select>
            </label>

            <button className="btn" type="submit" disabled={submitting}>
              {submitting ? "Creating..." : "Create Invoice"}
            </button>
          </form>
        </div>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Invoice List</h3>
        {loading ? (
          <p>Loading invoices...</p>
        ) : invoices.length === 0 ? (
          <p className="muted">No invoices found.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Invoice</th>
                <th>Student</th>
                <th>Period</th>
                <th>Due Date</th>
                <th>Amount</th>
                <th>Status</th>
                <th>Paid At</th>
              </tr>
            </thead>
            <tbody>
              {invoices.map((invoice) => (
                <tr key={invoice.id}>
                  <td>{invoice.invoice_no}</td>
                  <td>{invoice.student_name || studentNameMap.get(invoice.student_id) || invoice.student_id}</td>
                  <td>{invoice.period_label}</td>
                  <td>{invoice.due_date}</td>
                  <td>{invoice.amount.toFixed(2)}</td>
                  <td>
                    <span className="badge">{invoice.status}</span>
                  </td>
                  <td>{invoice.paid_at ? invoice.paid_at.replace("T", " ").slice(0, 16) : "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}
