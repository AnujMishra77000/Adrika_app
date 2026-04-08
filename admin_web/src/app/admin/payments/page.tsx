"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import { apiRequest } from "@/lib/api";

type StudentItem = {
  student_id: string;
  full_name: string;
  admission_no: string;
};

type PaymentItem = {
  id: string;
  invoice_id: string;
  invoice_no: string;
  student_id: string;
  student_name: string;
  provider: string;
  external_ref: string | null;
  amount: number;
  status: string;
  paid_at: string | null;
  created_at: string;
};

function toLocalDatetimeInput(value: string | null) {
  if (!value) {
    return "";
  }
  const date = new Date(value);
  const tzOffsetMs = date.getTimezoneOffset() * 60 * 1000;
  const local = new Date(date.getTime() - tzOffsetMs);
  return local.toISOString().slice(0, 16);
}

export default function AdminPaymentsPage() {
  const [students, setStudents] = useState<StudentItem[]>([]);
  const [payments, setPayments] = useState<PaymentItem[]>([]);

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [filterStudentId, setFilterStudentId] = useState("");
  const [filterStatus, setFilterStatus] = useState("");

  const [selectedPaymentId, setSelectedPaymentId] = useState("");
  const [reconcileStatus, setReconcileStatus] = useState("success");
  const [reconcilePaidAt, setReconcilePaidAt] = useState("");
  const [reconcileExternalRef, setReconcileExternalRef] = useState("");
  const [reconcileNote, setReconcileNote] = useState("");

  const selectedPayment = useMemo(
    () => payments.find((item) => item.id === selectedPaymentId) ?? null,
    [payments, selectedPaymentId],
  );

  async function loadStudents() {
    const response = await apiRequest<{ items: StudentItem[] }>(
      "/api/v1/admin/students?limit=300&offset=0",
    );
    setStudents(response.items);
  }

  async function loadPayments() {
    const params = new URLSearchParams({ limit: "200", offset: "0" });
    if (filterStudentId) {
      params.set("student_id", filterStudentId);
    }
    if (filterStatus) {
      params.set("status", filterStatus);
    }

    const response = await apiRequest<{ items: PaymentItem[] }>(
      `/api/v1/admin/payments?${params.toString()}`,
    );
    setPayments(response.items);

    if (response.items.length === 0) {
      setSelectedPaymentId("");
      return;
    }

    const stillExists = response.items.some((item) => item.id === selectedPaymentId);
    const payment = stillExists
      ? response.items.find((item) => item.id === selectedPaymentId) ?? response.items[0]
      : response.items[0];

    selectPayment(payment);
  }

  function selectPayment(payment: PaymentItem) {
    setSelectedPaymentId(payment.id);
    setReconcileStatus(payment.status || "success");
    setReconcilePaidAt(toLocalDatetimeInput(payment.paid_at));
    setReconcileExternalRef(payment.external_ref ?? "");
    setReconcileNote("");
  }

  async function loadAll() {
    setLoading(true);
    setError(null);
    try {
      await Promise.all([loadStudents(), loadPayments()]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load payments");
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
    setLoading(true);
    setError(null);
    setSuccess(null);
    try {
      await loadPayments();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to filter payments");
    } finally {
      setLoading(false);
    }
  }

  async function reconcile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedPaymentId) {
      setError("Select a payment to reconcile");
      return;
    }

    setSubmitting(true);
    setError(null);
    setSuccess(null);

    try {
      const body: Record<string, unknown> = {
        status: reconcileStatus,
      };

      if (reconcilePaidAt) {
        body.paid_at = new Date(reconcilePaidAt).toISOString();
      }
      if (reconcileExternalRef.trim()) {
        body.external_ref = reconcileExternalRef.trim();
      }
      if (reconcileNote.trim()) {
        body.note = reconcileNote.trim();
      }

      await apiRequest(`/api/v1/admin/payments/${selectedPaymentId}/reconcile`, {
        method: "PATCH",
        body: JSON.stringify(body),
      });

      setSuccess("Payment reconciled successfully");
      await loadPayments();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reconcile payment");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section>
      <h1 style={{ marginTop: 0 }}>Payment Reconciliation</h1>
      <p className="muted">Review payment transactions and reconcile invoice/payment state.</p>
      {error ? <p style={{ color: "#dc2626" }}>{error}</p> : null}
      {success ? <p style={{ color: "#166534" }}>{success}</p> : null}

      <div className="grid" style={{ marginBottom: 16 }}>
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Filter Payments</h3>
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
                <option value="success">Success</option>
                <option value="failed">Failed</option>
                <option value="refunded">Refunded</option>
              </select>
            </label>

            <button className="btn" type="submit">
              Apply Filters
            </button>
          </form>
        </div>

        <div className="card">
          <h3 style={{ marginTop: 0 }}>Reconcile Selected Payment</h3>
          {selectedPayment ? (
            <p className="muted" style={{ marginTop: 0 }}>
              {selectedPayment.invoice_no} • {selectedPayment.student_name} • {selectedPayment.amount.toFixed(2)}
            </p>
          ) : (
            <p className="muted">Select a payment from the table.</p>
          )}

          <form onSubmit={reconcile}>
            <label className="field">
              <span>Status</span>
              <select value={reconcileStatus} onChange={(event) => setReconcileStatus(event.target.value)}>
                <option value="pending">Pending</option>
                <option value="success">Success</option>
                <option value="failed">Failed</option>
                <option value="refunded">Refunded</option>
              </select>
            </label>

            <label className="field">
              <span>Paid At (optional)</span>
              <input
                type="datetime-local"
                value={reconcilePaidAt}
                onChange={(event) => setReconcilePaidAt(event.target.value)}
              />
            </label>

            <label className="field">
              <span>External Reference (optional)</span>
              <input
                value={reconcileExternalRef}
                onChange={(event) => setReconcileExternalRef(event.target.value)}
              />
            </label>

            <label className="field">
              <span>Admin Note (optional)</span>
              <textarea
                rows={3}
                value={reconcileNote}
                onChange={(event) => setReconcileNote(event.target.value)}
              />
            </label>

            <button className="btn" type="submit" disabled={submitting || !selectedPaymentId}>
              {submitting ? "Reconciling..." : "Reconcile Payment"}
            </button>
          </form>
        </div>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Payment Transactions</h3>
        {loading ? (
          <p>Loading payments...</p>
        ) : payments.length === 0 ? (
          <p className="muted">No payments found.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Invoice</th>
                <th>Student</th>
                <th>Provider</th>
                <th>Amount</th>
                <th>Status</th>
                <th>Paid At</th>
                <th>External Ref</th>
              </tr>
            </thead>
            <tbody>
              {payments.map((payment) => (
                <tr
                  key={payment.id}
                  onClick={() => selectPayment(payment)}
                  style={{
                    cursor: "pointer",
                    background: payment.id === selectedPaymentId ? "#eef4ff" : "transparent",
                  }}
                >
                  <td>{payment.invoice_no}</td>
                  <td>{payment.student_name}</td>
                  <td>{payment.provider}</td>
                  <td>{payment.amount.toFixed(2)}</td>
                  <td>
                    <span className="badge">{payment.status}</span>
                  </td>
                  <td>{payment.paid_at ? payment.paid_at.replace("T", " ").slice(0, 16) : "-"}</td>
                  <td>{payment.external_ref ?? "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}
