"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { apiRequest } from "@/lib/api";
import { clearAccessToken } from "@/lib/auth";

type AuthState = "loading" | "ready";

type NavItem = {
  href: string;
  label: string;
  key?: "notifications";
};

const NAV_ITEMS: NavItem[] = [
  { href: "/admin", label: "Overview" },
  { href: "/admin/students", label: "Students" },
  { href: "/admin/registrations", label: "Registrations" },
  { href: "/admin/parents", label: "Parents" },
  { href: "/admin/fees", label: "Fee Invoices" },
  { href: "/admin/payments", label: "Payments" },
  { href: "/admin/notices", label: "Notices" },
  { href: "/admin/homework", label: "Homework" },
  { href: "/admin/attendance", label: "Attendance" },
  { href: "/admin/assessments", label: "Assessments" },
  { href: "/admin/results", label: "Results" },
  { href: "/admin/doubts", label: "Doubts" },
  { href: "/admin/content", label: "Content" },
  { href: "/admin/notifications", label: "Notifications", key: "notifications" },
  { href: "/admin/audit-logs", label: "Audit Logs" },
];

export default function AdminShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [state, setState] = useState<AuthState>("loading");
  const [adminName, setAdminName] = useState<string>("Admin");
  const [unreadCount, setUnreadCount] = useState<number>(0);

  useEffect(() => {
    let mounted = true;

    async function verify() {
      try {
        const me = await apiRequest<{ full_name: string; roles: string[] }>("/api/v1/auth/me");
        if (!me.roles.includes("admin")) {
          clearAccessToken();
          router.replace("/login");
          return;
        }
        if (mounted) {
          setAdminName(me.full_name);
          setState("ready");
        }
      } catch {
        clearAccessToken();
        router.replace("/login");
      }
    }

    void verify();
    return () => {
      mounted = false;
    };
  }, [router]);

  useEffect(() => {
    if (state !== "ready") {
      return;
    }

    let mounted = true;
    async function loadUnreadCount() {
      try {
        const response = await apiRequest<{ unread_count: number }>(
          "/api/v1/admin/me/notifications?is_read=false&limit=1&offset=0",
        );
        if (mounted) {
          setUnreadCount(response.unread_count ?? 0);
        }
      } catch {
        // Ignore notification counter errors so navigation remains available.
      }
    }

    void loadUnreadCount();
    const timer = window.setInterval(() => {
      void loadUnreadCount();
    }, 15000);

    return () => {
      mounted = false;
      window.clearInterval(timer);
    };
  }, [state]);

  const nav = useMemo(() => NAV_ITEMS, []);

  if (state === "loading") {
    return <div className="page">Validating admin session...</div>;
  }

  return (
    <div style={{ display: "grid", gridTemplateColumns: "240px 1fr", minHeight: "100vh" }}>
      <aside style={{ borderRight: "1px solid var(--line)", background: "#fff", padding: 16 }}>
        <div style={{ marginBottom: 16 }}>
          <h3 style={{ margin: 0 }}>ADR Admin</h3>
          <div className="muted" style={{ fontSize: 13 }}>
            {adminName}
          </div>
        </div>

        <nav style={{ display: "grid", gap: 6 }}>
          {nav.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                style={{
                  padding: "8px 10px",
                  borderRadius: 8,
                  background: active ? "#e7efff" : "transparent",
                  color: active ? "#0b5fff" : "inherit",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  gap: 8,
                }}
              >
                <span>{item.label}</span>
                {item.key === "notifications" && unreadCount > 0 ? (
                  <span
                    style={{
                      minWidth: 18,
                      height: 18,
                      borderRadius: 999,
                      background: "#ef4444",
                      color: "#fff",
                      fontSize: 11,
                      display: "inline-flex",
                      alignItems: "center",
                      justifyContent: "center",
                      padding: "0 6px",
                      lineHeight: 1,
                    }}
                  >
                    {unreadCount > 99 ? "99+" : unreadCount}
                  </span>
                ) : null}
              </Link>
            );
          })}
        </nav>

        <button
          className="btn"
          style={{ marginTop: 16, width: "100%", background: "#334155" }}
          onClick={() => {
            clearAccessToken();
            router.replace("/login");
          }}
        >
          Logout
        </button>
      </aside>

      <main className="page">{children}</main>
    </div>
  );
}
