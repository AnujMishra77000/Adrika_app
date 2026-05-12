"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { apiRequest } from "@/lib/api";

type AdminInboxNotification = {
  id: string;
  notification_type: string;
  title: string;
  body: string;
  metadata: Record<string, unknown> | null;
  is_read: boolean;
  created_at: string;
};

type UploadedAttachment = {
  file_name: string;
  stored_name: string;
  file_url: string;
  content_type: string;
  file_size: number;
};

type NotificationHistoryItem = {
  id: string;
  created_at: string;
  actor_name: string | null;
  title: string;
  notification_type: string | null;
  recipient_count: number;
  targets: Array<{ target_type: string; target_id: string }>;
  broadcast_id: string | null;
};

type InboxReadFilter = "all" | "unread" | "read";
type AudienceMode = "all_students" | "jrkg_to_5" | "class_section";

function bytesToHuman(value: number): string {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function targetLabel(target: { target_type: string; target_id: string }): string {
  if (target.target_type === "all" || target.target_type === "all_students") return "All Students";
  if (target.target_type === "grade" && target.target_id === "jrkg-5") return "Jr.KG to 5th (Common)";
  if (target.target_type === "grade") return `Class ${target.target_id}`;
  if (target.target_type === "batch") return `Batch ${target.target_id}`;
  return `${target.target_type}: ${target.target_id}`;
}

export default function AdminNotificationsPage() {
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [notificationType, setNotificationType] = useState("system");
  const [audienceMode, setAudienceMode] = useState<AudienceMode>("all_students");
  const [classLevel, setClassLevel] = useState("10");
  const [stream, setStream] = useState<"" | "science" | "commerce">("");
  const [attachments, setAttachments] = useState<UploadedAttachment[]>([]);

  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [uploading, setUploading] = useState(false);

  const [items, setItems] = useState<AdminInboxNotification[]>([]);
  const [inboxLoading, setInboxLoading] = useState(true);
  const [inboxError, setInboxError] = useState<string | null>(null);
  const [inboxBusy, setInboxBusy] = useState<string | null>(null);
  const [unreadCount, setUnreadCount] = useState(0);
  const [readFilter, setReadFilter] = useState<InboxReadFilter>("unread");

  const [historyItems, setHistoryItems] = useState<NotificationHistoryItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [historyTitleInput, setHistoryTitleInput] = useState("");
  const [historyDateInput, setHistoryDateInput] = useState("");
  const [historyTitleFilter, setHistoryTitleFilter] = useState("");
  const [historyDateFilter, setHistoryDateFilter] = useState("");

  const inboxEndpoint = useMemo(() => {
    const isReadQuery =
      readFilter === "all" ? "" : readFilter === "unread" ? "&is_read=false" : "&is_read=true";
    return "/api/v1/admin/me/notifications?limit=50&offset=0" + isReadQuery;
  }, [readFilter]);

  const targets = useMemo(() => {
    if (audienceMode === "all_students") {
      return [{ target_type: "all", target_id: "all" }];
    }
    if (audienceMode === "jrkg_to_5") {
      return [{ target_type: "grade", target_id: "jrkg-5" }];
    }

    const grade = Number(classLevel);
    if (grade >= 11) {
      if (!stream) {
        return [{ target_type: "grade", target_id: String(grade) }];
      }
      return [{ target_type: "grade", target_id: `${grade}:${stream}` }];
    }
    return [{ target_type: "grade", target_id: classLevel }];
  }, [audienceMode, classLevel, stream]);

  async function loadInbox() {
    setInboxLoading(true);
    setInboxError(null);
    try {
      const response = await apiRequest<{ items: AdminInboxNotification[]; unread_count: number }>(inboxEndpoint);
      setItems(response.items);
      setUnreadCount(response.unread_count ?? 0);
    } catch (err) {
      setInboxError(err instanceof Error ? err.message : "Failed to load admin inbox");
    } finally {
      setInboxLoading(false);
    }
  }

  async function loadHistory() {
    setHistoryLoading(true);
    setHistoryError(null);
    try {
      const params = new URLSearchParams();
      params.set("limit", "50");
      params.set("offset", "0");
      if (historyTitleFilter.trim()) params.set("title", historyTitleFilter.trim());
      if (historyDateFilter) params.set("on_date", historyDateFilter);
      const response = await apiRequest<{ items: NotificationHistoryItem[] }>(
        `/api/v1/admin/notifications/history?${params.toString()}`,
      );
      setHistoryItems(response.items ?? []);
    } catch (err) {
      setHistoryError(err instanceof Error ? err.message : "Failed to load notification history");
    } finally {
      setHistoryLoading(false);
    }
  }

  useEffect(() => {
    void loadInbox();
    void loadHistory();
    const timer = window.setInterval(() => {
      void loadInbox();
      void loadHistory();
    }, 15000);
    return () => window.clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inboxEndpoint, historyTitleFilter, historyDateFilter]);

  async function markRead(notificationId: string) {
    setInboxBusy(notificationId);
    setInboxError(null);
    try {
      const response = await apiRequest<{ unread_count: number }>(
        "/api/v1/admin/me/notifications/" + notificationId + "/read",
        {
          method: "POST",
        },
      );
      setUnreadCount(response.unread_count ?? unreadCount);
      await loadInbox();
    } catch (err) {
      setInboxError(err instanceof Error ? err.message : "Failed to mark notification as read");
    } finally {
      setInboxBusy(null);
    }
  }

  async function markAllRead() {
    setInboxBusy("all");
    setInboxError(null);
    try {
      const response = await apiRequest<{ unread_count: number }>("/api/v1/admin/me/notifications/read-all", {
        method: "POST",
      });
      setUnreadCount(response.unread_count ?? 0);
      await loadInbox();
    } catch (err) {
      setInboxError(err instanceof Error ? err.message : "Failed to mark all as read");
    } finally {
      setInboxBusy(null);
    }
  }

  async function uploadFiles(fileList: FileList | null) {
    if (!fileList || fileList.length === 0) {
      return;
    }

    setUploading(true);
    setError(null);
    try {
      const next: UploadedAttachment[] = [];
      for (const file of Array.from(fileList)) {
        const formData = new FormData();
        formData.append("file", file);
        const uploaded = await apiRequest<UploadedAttachment>("/api/v1/admin/notifications/attachments", {
          method: "POST",
          body: formData,
        });
        next.push(uploaded);
      }
      setAttachments((prev) => [...prev, ...next]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to upload attachment");
    } finally {
      setUploading(false);
    }
  }

  function removeAttachment(storedName: string) {
    setAttachments((prev) => prev.filter((item) => item.stored_name !== storedName));
  }

  async function sendNotification(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setResult(null);

    const grade = Number(classLevel);
    if (audienceMode === "class_section" && grade >= 11 && !stream) {
      setError("Select section/stream for class 11 or 12.");
      return;
    }

    setSending(true);
    try {
      const response = await apiRequest<{ recipient_count: number; broadcast_id: string }>("/api/v1/admin/notifications", {
        method: "POST",
        body: JSON.stringify({
          title,
          body,
          notification_type: notificationType,
          targets,
          attachments: attachments.map((item) => ({
            file_name: item.file_name,
            file_url: item.file_url,
            content_type: item.content_type,
            file_size: item.file_size,
          })),
        }),
      });

      setResult(`Notification sent to ${response.recipient_count} students. Broadcast ID: ${response.broadcast_id}`);
      setTitle("");
      setBody("");
      setAttachments([]);
      await loadHistory();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send notification");
    } finally {
      setSending(false);
    }
  }

  return (
    <section>
      <h1 style={{ marginTop: 0 }}>Notifications Hub</h1>

      <div className="card" style={{ marginBottom: 16, borderRadius: 14 }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            gap: 12,
            alignItems: "center",
            flexWrap: "wrap",
          }}
        >
          <h3 style={{ margin: 0 }}>Admin Inbox</h3>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <span className="badge">Unread: {unreadCount}</span>
            <select value={readFilter} onChange={(event) => setReadFilter(event.target.value as InboxReadFilter)}>
              <option value="unread">Unread</option>
              <option value="all">All</option>
              <option value="read">Read</option>
            </select>
            <button className="btn" type="button" onClick={() => void markAllRead()} disabled={inboxBusy === "all" || unreadCount === 0}>
              Mark All Read
            </button>
          </div>
        </div>

        {inboxError ? <p style={{ color: "#dc2626" }}>{inboxError}</p> : null}

        {inboxLoading ? (
          <p>Loading inbox...</p>
        ) : items.length === 0 ? (
          <p className="muted">No notifications in this filter.</p>
        ) : (
          <div style={{ display: "grid", gap: 10, marginTop: 12 }}>
            {items.map((item) => {
              const requestId =
                item.metadata && typeof item.metadata["request_id"] === "string" ? (item.metadata["request_id"] as string) : null;

              return (
                <article
                  key={item.id}
                  style={{
                    border: "1px solid var(--line)",
                    borderRadius: 10,
                    padding: 12,
                    display: "grid",
                    gap: 6,
                    background: item.is_read ? "#fff" : "#f8fbff",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 8, flexWrap: "wrap" }}>
                    <strong>{item.title}</strong>
                    <span className="muted" style={{ fontSize: 12 }}>
                      {new Date(item.created_at).toLocaleString()}
                    </span>
                  </div>
                  <div>{item.body}</div>
                  <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                    <span className="badge">{item.notification_type}</span>
                    <span className="badge">{item.is_read ? "read" : "unread"}</span>
                    {requestId ? (
                      <Link href="/admin/registrations" style={{ color: "#0b5fff", fontSize: 13 }}>
                        Open request approvals
                      </Link>
                    ) : null}
                    {!item.is_read ? (
                      <button className="btn" type="button" onClick={() => void markRead(item.id)} disabled={inboxBusy === item.id}>
                        Mark Read
                      </button>
                    ) : null}
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </div>

      <div className="card" style={{ marginBottom: 16, borderRadius: 14 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
          <h3 style={{ margin: 0 }}>Master Broadcast Composer</h3>
          <span className="badge">Live Hub</span>
        </div>
        <p className="muted" style={{ marginTop: 8 }}>
          Send class-wise and section-wise notifications with attachments (images, PDF, docs) using a single workflow.
        </p>

        <form onSubmit={sendNotification}>
          <div style={{ display: "grid", gap: 12, gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))" }}>
            <label className="field">
              <span>Audience</span>
              <select value={audienceMode} onChange={(e) => setAudienceMode(e.target.value as AudienceMode)}>
                <option value="all_students">All Students</option>
                <option value="jrkg_to_5">Jr.KG to 5th (Common)</option>
                <option value="class_section">Class & Section</option>
              </select>
            </label>

            <label className="field">
              <span>Class</span>
              <select
                value={classLevel}
                disabled={audienceMode !== "class_section"}
                onChange={(e) => {
                  setClassLevel(e.target.value);
                  if (Number(e.target.value) <= 10) {
                    setStream("");
                  }
                }}
              >
                <option value="6">6th</option>
                <option value="7">7th</option>
                <option value="8">8th</option>
                <option value="9">9th</option>
                <option value="10">10th</option>
                <option value="11">11th</option>
                <option value="12">12th</option>
              </select>
            </label>

            <label className="field">
              <span>Section / Stream</span>
              <select
                value={stream}
                disabled={audienceMode !== "class_section" || Number(classLevel) <= 10}
                onChange={(e) => setStream(e.target.value as "" | "science" | "commerce")}
              >
                <option value="">Select</option>
                <option value="science">Science</option>
                <option value="commerce">Commerce</option>
              </select>
            </label>

            <label className="field">
              <span>Type</span>
              <select value={notificationType} onChange={(e) => setNotificationType(e.target.value)}>
                <option value="system">System</option>
                <option value="notice">Notice</option>
                <option value="homework">Homework</option>
                <option value="test">Test</option>
                <option value="result">Result</option>
                <option value="doubt">Doubt</option>
              </select>
            </label>
          </div>

          <label className="field">
            <span>Title</span>
            <input value={title} onChange={(e) => setTitle(e.target.value)} required />
          </label>

          <label className="field">
            <span>Message</span>
            <textarea rows={5} value={body} onChange={(e) => setBody(e.target.value)} required />
          </label>

          <label className="field">
            <span>Attachments (image / pdf / doc / docx / txt)</span>
            <input type="file" multiple onChange={(e) => void uploadFiles(e.target.files)} />
          </label>

          {uploading ? <p className="muted">Uploading attachments...</p> : null}

          {attachments.length > 0 ? (
            <div style={{ display: "grid", gap: 8, marginBottom: 10 }}>
              {attachments.map((item) => (
                <div
                  key={item.stored_name}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    gap: 10,
                    background: "#f8fbff",
                    border: "1px solid var(--line)",
                    borderRadius: 10,
                    padding: "8px 10px",
                  }}
                >
                  <div>
                    <strong>{item.file_name}</strong>
                    <div className="muted" style={{ fontSize: 12 }}>
                      {item.content_type} • {bytesToHuman(item.file_size)}
                    </div>
                  </div>
                  <button className="btn" type="button" onClick={() => removeAttachment(item.stored_name)}>
                    Remove
                  </button>
                </div>
              ))}
            </div>
          ) : null}

          <div style={{ marginBottom: 10 }}>
            <span className="badge">Audience</span>
            <p className="muted" style={{ marginTop: 8 }}>
              {targets.map(targetLabel).join(", ")}
            </p>
          </div>

          {result ? <p style={{ color: "#166534" }}>{result}</p> : null}
          {error ? <p style={{ color: "#dc2626" }}>{error}</p> : null}

          <button className="btn" type="submit" disabled={sending || uploading}>
            {sending ? "Sending..." : "Send Notification"}
          </button>
        </form>
      </div>

      <div className="card" style={{ marginBottom: 16, borderRadius: 14 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
          <h3 style={{ margin: 0 }}>Notification History</h3>
          <button className="btn" type="button" onClick={() => void loadHistory()}>
            Refresh
          </button>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 10, marginTop: 10 }}>
          <label className="field" style={{ marginBottom: 0 }}>
            <span>Search by Title</span>
            <input
              value={historyTitleInput}
              onChange={(e) => setHistoryTitleInput(e.target.value)}
              placeholder="e.g. Exam Update"
            />
          </label>
          <label className="field" style={{ marginBottom: 0 }}>
            <span>Search by Date</span>
            <input type="date" value={historyDateInput} onChange={(e) => setHistoryDateInput(e.target.value)} />
          </label>
          <div style={{ display: "flex", gap: 8, alignItems: "end" }}>
            <button
              className="btn"
              type="button"
              onClick={() => {
                setHistoryTitleFilter(historyTitleInput.trim());
                setHistoryDateFilter(historyDateInput);
              }}
            >
              Search
            </button>
            <button
              className="btn"
              type="button"
              onClick={() => {
                setHistoryTitleInput("");
                setHistoryDateInput("");
                setHistoryTitleFilter("");
                setHistoryDateFilter("");
              }}
            >
              Clear
            </button>
          </div>
        </div>

        {historyError ? <p style={{ color: "#dc2626" }}>{historyError}</p> : null}
        {historyLoading ? (
          <p>Loading history...</p>
        ) : historyItems.length === 0 ? (
          <p className="muted">No broadcast history found yet.</p>
        ) : (
          <div style={{ display: "grid", gap: 10, marginTop: 10 }}>
            {historyItems.map((item) => (
              <article
                key={item.id}
                style={{ border: "1px solid var(--line)", borderRadius: 10, padding: 12, background: "#fff" }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
                  <strong>{item.notification_type?.toUpperCase() ?? "SYSTEM"}</strong>
                  <span className="muted" style={{ fontSize: 12 }}>
                    {new Date(item.created_at).toLocaleString()}
                  </span>
                </div>
                <div style={{ marginTop: 6 }}>
                  <strong>Title:</strong> {item.title || "-"}
                </div>
                <div style={{ marginTop: 6, display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
                  <span className="badge">Recipients: {item.recipient_count}</span>
                  <span className="badge">By: {item.actor_name ?? "Admin"}</span>
                  <span className="badge">Broadcast: {item.broadcast_id ?? "-"}</span>
                </div>
                <div className="muted" style={{ marginTop: 6, fontSize: 13 }}>
                  Targets: {item.targets.map(targetLabel).join(", ") || "-"}
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
