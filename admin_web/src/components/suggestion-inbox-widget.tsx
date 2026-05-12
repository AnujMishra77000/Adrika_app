"use client";

import { useEffect, useMemo, useState } from "react";

import { apiRequest } from "@/lib/api";

type SuggestionThread = {
  id: string;
  student_name: string;
  student_phone: string | null;
  admission_no: string | null;
  class_name: string | null;
  stream: string | null;
  status: string;
  last_message_at: string | null;
  unread_for_admin: boolean;
};

type SuggestionMessage = {
  id: string;
  sender_user_id: string;
  sender_name: string;
  message: string;
  created_at: string | null;
};

type SuggestionThreadsResponse = {
  items: SuggestionThread[];
};

type SuggestionMessagesResponse = {
  thread: SuggestionThread;
  items: SuggestionMessage[];
};

function formatDateTime(value: string | null): string {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "-";
  }
  return date.toLocaleString("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export default function SuggestionInboxWidget() {
  const [open, setOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loadingThreads, setLoadingThreads] = useState(false);
  const [threads, setThreads] = useState<SuggestionThread[]>([]);
  const [selectedThreadId, setSelectedThreadId] = useState<string | null>(null);
  const [messages, setMessages] = useState<SuggestionMessage[]>([]);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [sending, setSending] = useState(false);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);

  const selectedThread = useMemo(
    () => threads.find((thread) => thread.id === selectedThreadId) ?? null,
    [threads, selectedThreadId],
  );

  async function loadUnreadCount() {
    try {
      const payload = await apiRequest<{ unread_count: number }>("/api/v1/admin/suggestions/unread-count");
      setUnreadCount(payload.unread_count ?? 0);
    } catch {
      // Keep silent to avoid interrupting admin workflow.
    }
  }

  async function loadThreads(preferredThreadId?: string | null) {
    setLoadingThreads(true);
    setError(null);
    try {
      const payload = await apiRequest<SuggestionThreadsResponse>(
        "/api/v1/admin/suggestions/threads?limit=200&offset=0",
      );
      const nextThreads = payload.items ?? [];
      setThreads(nextThreads);

      if (nextThreads.length === 0) {
        setSelectedThreadId(null);
        setMessages([]);
      } else {
        const targetId =
          preferredThreadId && nextThreads.some((thread) => thread.id === preferredThreadId)
            ? preferredThreadId
            : selectedThreadId && nextThreads.some((thread) => thread.id === selectedThreadId)
              ? selectedThreadId
              : nextThreads[0].id;
        setSelectedThreadId(targetId);
        await loadMessages(targetId);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load suggestions");
    } finally {
      setLoadingThreads(false);
    }
  }

  async function loadMessages(threadId: string) {
    setLoadingMessages(true);
    setError(null);
    try {
      const payload = await apiRequest<SuggestionMessagesResponse>(
        `/api/v1/admin/suggestions/threads/${threadId}/messages?limit=500&offset=0`,
      );
      setMessages(payload.items ?? []);
      await loadUnreadCount();
      const refreshed = await apiRequest<SuggestionThreadsResponse>(
        "/api/v1/admin/suggestions/threads?limit=200&offset=0",
      );
      setThreads(refreshed.items ?? []);
      if (!selectedThreadId && refreshed.items?.length) {
        setSelectedThreadId(refreshed.items[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load chat");
    } finally {
      setLoadingMessages(false);
    }
  }

  async function sendMessage() {
    if (!selectedThreadId || sending) {
      return;
    }
    const message = draft.trim();
    if (!message) {
      return;
    }

    setSending(true);
    setError(null);
    try {
      await apiRequest(`/api/v1/admin/suggestions/threads/${selectedThreadId}/messages`, {
        method: "POST",
        body: JSON.stringify({ message }),
      });
      setDraft("");
      await loadMessages(selectedThreadId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send message");
    } finally {
      setSending(false);
    }
  }

  useEffect(() => {
    void loadUnreadCount();
    const timer = window.setInterval(() => {
      void loadUnreadCount();
      if (open && selectedThreadId) {
        void loadMessages(selectedThreadId);
      }
    }, 10000);

    return () => {
      window.clearInterval(timer);
    };
  }, [open, selectedThreadId]);

  useEffect(() => {
    if (open) {
      void loadThreads(selectedThreadId);
    }
  }, [open]);

  return (
    <>
      <button
        type="button"
        className="suggestion-fab"
        onClick={() => setOpen((value) => !value)}
        aria-label="Open Suggestion Inbox"
      >
        <span className="suggestion-fab-icon" aria-hidden="true">
          💬
        </span>
        {unreadCount > 0 ? (
          <span className="suggestion-fab-badge">{unreadCount > 99 ? "99+" : unreadCount}</span>
        ) : null}
      </button>

      {open ? (
        <section className="suggestion-panel" aria-label="Suggestion Inbox">
          <header className="suggestion-panel-header">
            <h3>Suggestion Inbox</h3>
            <button type="button" className="suggestion-close" onClick={() => setOpen(false)}>
              ✕
            </button>
          </header>

          <div className="suggestion-thread-list">
            {loadingThreads ? (
              <p className="muted">Loading students...</p>
            ) : threads.length === 0 ? (
              <p className="muted">No suggestions yet.</p>
            ) : (
              threads.map((thread) => {
                const active = thread.id === selectedThreadId;
                return (
                  <button
                    key={thread.id}
                    type="button"
                    className={active ? "suggestion-thread-item active" : "suggestion-thread-item"}
                    onClick={() => {
                      setSelectedThreadId(thread.id);
                      void loadMessages(thread.id);
                    }}
                  >
                    <div className="suggestion-thread-row">
                      <strong>{thread.student_name}</strong>
                      {thread.unread_for_admin ? <span className="badge">New</span> : null}
                    </div>
                    <div className="muted" style={{ fontSize: 12 }}>
                      {thread.class_name || "Class"}
                      {thread.stream ? ` • ${thread.stream}` : ""}
                    </div>
                    <div className="muted" style={{ fontSize: 11 }}>
                      {formatDateTime(thread.last_message_at)}
                    </div>
                  </button>
                );
              })
            )}
          </div>

          <div className="suggestion-chat-body">
            {selectedThread ? (
              <div className="suggestion-chat-meta">
                <strong>{selectedThread.student_name}</strong>
                <span className="muted" style={{ fontSize: 12 }}>
                  {selectedThread.admission_no || "-"} • {selectedThread.student_phone || "-"}
                </span>
              </div>
            ) : null}

            <div className="suggestion-messages-scroll">
              {loadingMessages ? (
                <p className="muted">Loading chat...</p>
              ) : messages.length === 0 ? (
                <p className="muted">No messages yet.</p>
              ) : (
                messages.map((item) => {
                  const isAdminMessage = item.sender_name.toLowerCase().includes("admin");
                  return (
                    <div key={item.id} className={isAdminMessage ? "suggestion-bubble admin" : "suggestion-bubble student"}>
                      <div className="suggestion-bubble-head">
                        <strong>{item.sender_name}</strong>
                        <span>{formatDateTime(item.created_at)}</span>
                      </div>
                      <div>{item.message}</div>
                    </div>
                  );
                })
              )}
            </div>

            <div className="suggestion-compose-row">
              <textarea
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                placeholder="Reply to student suggestion..."
                rows={2}
              />
              <button type="button" className="btn" onClick={() => void sendMessage()} disabled={sending || !selectedThreadId}>
                {sending ? "Sending..." : "Send"}
              </button>
            </div>
            {error ? <p style={{ color: "#dc2626", margin: 0 }}>{error}</p> : null}
          </div>
        </section>
      ) : null}
    </>
  );
}
