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

type InboxReadFilter = "all" | "unread" | "read";

export default function AdminNotificationsPage() {
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [notificationType, setNotificationType] = useState("system");
  const [targetsJson, setTargetsJson] = useState('[{"target_type":"all","target_id":"all"}]');
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [items, setItems] = useState<AdminInboxNotification[]>([]);
  const [inboxLoading, setInboxLoading] = useState(true);
  const [inboxError, setInboxError] = useState<string | null>(null);
  const [inboxBusy, setInboxBusy] = useState<string | null>(null);
  const [unreadCount, setUnreadCount] = useState(0);
  const [readFilter, setReadFilter] = useState<InboxReadFilter>("unread");

  const inboxEndpoint = useMemo(() => {
    const isReadQuery =
      readFilter === "all" ? "" : readFilter === "unread" ? "&is_read=false" : "&is_read=true";
    return "/api/v1/admin/me/notifications?limit=50&offset=0" + isReadQuery;
  }, [readFilter]);

  async function loadInbox() {
    setInboxLoading(true);
    setInboxError(null);
    try {
      const response = await apiRequest<{ items: AdminInboxNotification[]; unread_count: number }>(
        inboxEndpoint,
      );
      setItems(response.items);
      setUnreadCount(response.unread_count ?? 0);
    } catch (err) {
      setInboxError(err instanceof Error ? err.message : "Failed to load admin inbox");
    } finally {
      setInboxLoading(false);
    }
  }

  useEffect(() => {
    void loadInbox();
    const timer = window.setInterval(() => {
      void loadInbox();
    }, 15000);
    return () => window.clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inboxEndpoint]);

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
      const response = await apiRequest<{ unread_count: number }>(
        "/api/v1/admin/me/notifications/read-all",
        {
          method: "POST",
        },
      );
      setUnreadCount(response.unread_count ?? 0);
      await loadInbox();
    } catch (err) {
      setInboxError(err instanceof Error ? err.message : "Failed to mark all as read");
    } finally {
      setInboxBusy(null);
    }
  }

  async function sendNotification(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setResult(null);
    try {
      const targets = JSON.parse(targetsJson);
      const response = await apiRequest<{ recipient_count: number }>("/api/v1/admin/notifications", {
        method: "POST",
        body: JSON.stringify({
          title,
          body,
          notification_type: notificationType,
          targets,
        }),
      });
      setResult("Notification queued for " + response.recipient_count + " users");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send notification");
    }
  }

  return (
    <section>
      <h1 style={{ marginTop: 0 }}>Notifications</h1>

      <div className="card" style={{ marginBottom: 16 }}>
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
            <select
              value={readFilter}
              onChange={(event) => setReadFilter(event.target.value as InboxReadFilter)}
            >
              <option value="unread">Unread</option>
              <option value="all">All</option>
              <option value="read">Read</option>
            </select>
            <button
              className="btn"
              type="button"
              onClick={() => void markAllRead()}
              disabled={inboxBusy === "all" || unreadCount === 0}
            >
              Mark All Read
            </button>
          </div>
        </div>

        <p className="muted" style={{ marginTop: 8, marginBottom: 0, fontSize: 13 }}>
          Incoming approvals (student/teacher registration) appear here automatically.
        </p>

        {inboxError ? <p style={{ color: "#dc2626" }}>{inboxError}</p> : null}

        {inboxLoading ? (
          <p>Loading inbox...</p>
        ) : items.length === 0 ? (
          <p className="muted">No notifications in this filter.</p>
        ) : (
          <div style={{ display: "grid", gap: 10, marginTop: 12 }}>
            {items.map((item) => {
              const requestId =
                item.metadata && typeof item.metadata["request_id"] === "string"
                  ? (item.metadata["request_id"] as string)
                  : null;

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
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      gap: 8,
                      flexWrap: "wrap",
                    }}
                  >
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
                      <button
                        className="btn"
                        type="button"
                        onClick={() => void markRead(item.id)}
                        disabled={inboxBusy === item.id}
                      >
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

      <div className="card" style={{ maxWidth: 760 }}>
        <h3 style={{ marginTop: 0 }}>Broadcast Notification</h3>
        <form onSubmit={sendNotification}>
          <label className="field">
            <span>Title</span>
            <input value={title} onChange={(e) => setTitle(e.target.value)} required />
          </label>
          <label className="field">
            <span>Body</span>
            <textarea rows={4} value={body} onChange={(e) => setBody(e.target.value)} required />
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
          <label className="field">
            <span>Targets (JSON)</span>
            <textarea rows={3} value={targetsJson} onChange={(e) => setTargetsJson(e.target.value)} />
          </label>
          {result ? <p style={{ color: "#166534" }}>{result}</p> : null}
          {error ? <p style={{ color: "#dc2626" }}>{error}</p> : null}
          <button className="btn" type="submit">
            Send
          </button>
        </form>
      </div>
    </section>
  );
}
