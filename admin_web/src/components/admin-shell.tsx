"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import { apiRequest } from "@/lib/api";
import { clearAuthTokens } from "@/lib/auth";
import SuggestionInboxWidget from "@/components/suggestion-inbox-widget";

type AuthState = "loading" | "ready";

type NavItem = {
  href: string;
  label: string;
  icon: string;
  iconKey?: "dashboard" | "students" | "teachers" | "parents" | "notices" | "notifications";
  key?: "notifications";
};

const NAV_ITEMS: NavItem[] = [
  { href: "/admin/dashboard", label: "Dashboard", icon: "", iconKey: "dashboard" },
  { href: "/admin/enquiries", label: "Enquiry", icon: "⌕" },
  { href: "/admin/students", label: "Students", icon: "", iconKey: "students" },
  { href: "/admin/teachers", label: "Teachers", icon: "", iconKey: "teachers" },
  { href: "/admin/registrations", label: "Registrations", icon: "✎" },
  { href: "/admin/parents", label: "Parents", icon: "", iconKey: "parents" },
  { href: "/admin/fees", label: "Fees", icon: "₹" },
  { href: "/admin/lecture-schedules", label: "Lecture Schedule", icon: "◷" },
  { href: "/admin/notices", label: "Notices", icon: "", iconKey: "notices" },
  { href: "/admin/homework", label: "Homework", icon: "▤" },
  { href: "/admin/homework/completions", label: "HW Completion", icon: "✓" },
  { href: "/admin/attendance", label: "Attendance", icon: "◴" },
  { href: "/admin/assessments", label: "Assessments", icon: "▣" },
  { href: "/admin/results", label: "Results", icon: "★" },
  { href: "/admin/doubts", label: "Doubts", icon: "◔" },
  { href: "/admin/content", label: "Content", icon: "◧" },
  { href: "/admin/notifications", label: "Notifications", icon: "", iconKey: "notifications", key: "notifications" },
  { href: "/admin/audit-logs", label: "Audit Logs", icon: "⧉" },
  { href: "/admin/banner", label: "Banner", icon: "🖼" },
];

function NavGlyph({ iconKey, fallback }: { iconKey?: NavItem["iconKey"]; fallback: string }) {
  const svgProps = {
    width: 16,
    height: 16,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.9,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
  };

  switch (iconKey) {
    case "dashboard":
      return (
        <svg {...svgProps}>
          <rect x="3" y="3" width="8" height="8" rx="2" />
          <rect x="13" y="3" width="8" height="8" rx="2" />
          <rect x="3" y="13" width="8" height="8" rx="2" />
          <rect x="13" y="13" width="8" height="8" rx="2" />
        </svg>
      );
    case "students":
      return (
        <svg {...svgProps}>
          <circle cx="12" cy="8" r="3.2" />
          <path d="M6.5 19.2c1.8-2.6 3.7-3.9 5.5-3.9s3.7 1.3 5.5 3.9" />
        </svg>
      );
    case "teachers":
      return (
        <svg {...svgProps}>
          <circle cx="10" cy="8.5" r="2.7" />
          <path d="M5.8 18.7c1.3-2.1 2.8-3.2 4.2-3.2 1.5 0 2.9 1.1 4.2 3.2" />
          <path d="M14 5.2l4-1.8 4 1.8-4 1.8z" />
          <path d="M18 7v2.7" />
        </svg>
      );
    case "parents":
      return (
        <svg {...svgProps}>
          <circle cx="8.2" cy="8.4" r="2.4" />
          <circle cx="15.8" cy="8.4" r="2.4" />
          <path d="M3.7 18.7c1.1-1.8 2.4-2.7 3.9-2.7 1.4 0 2.7.9 3.8 2.7" />
          <path d="M12.6 18.7c1.1-1.8 2.4-2.7 3.8-2.7 1.5 0 2.8.9 3.9 2.7" />
        </svg>
      );
    case "notices":
      return (
        <svg {...svgProps}>
          <path d="M4 18.5h3.7l11-5.5V5.4l-11 5.5H4z" />
          <path d="M7.5 11v7.5" />
          <path d="M18.7 8.2c1.6 1.2 1.6 3.8 0 5" />
        </svg>
      );
    case "notifications":
      return (
        <svg {...svgProps}>
          <path d="M18 9.5c0-3.4-2.6-5.8-6-5.8s-6 2.4-6 5.8v4.2L4 16h16l-2-2.3z" />
          <path d="M10 18.2c.5 1.2 1.2 1.8 2 1.8s1.5-.6 2-1.8" />
        </svg>
      );
    default:
      return <>{fallback}</>;
  }
}

export default function AdminShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [state, setState] = useState<AuthState>("loading");
  const [adminName, setAdminName] = useState<string>("Admin");
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [actionsOpen, setActionsOpen] = useState(false);
  const actionsMenuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let mounted = true;

    async function verify() {
      try {
        const me = await apiRequest<{ full_name: string; roles: string[] }>("/api/v1/auth/me");
        if (!me.roles.includes("admin")) {
          clearAuthTokens();
          router.replace("/login");
          return;
        }
        if (mounted) {
          setAdminName(me.full_name);
          setState("ready");
        }
      } catch {
        clearAuthTokens();
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

  useEffect(() => {
    setActionsOpen(false);
  }, [pathname]);

  useEffect(() => {
    function onPointerDown(event: MouseEvent) {
      if (!actionsMenuRef.current) {
        return;
      }
      if (!actionsMenuRef.current.contains(event.target as Node)) {
        setActionsOpen(false);
      }
    }
    document.addEventListener("mousedown", onPointerDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
    };
  }, []);

  const nav = useMemo(() => NAV_ITEMS, []);
  const showSidebar = pathname === "/admin/dashboard";
  const showActionsDropdown = pathname !== "/admin/dashboard";

  if (state === "loading") {
    return <div className="page">Validating admin session...</div>;
  }

  return (
    <div className={showSidebar ? "admin-shell-root" : "admin-shell-root no-sidebar"}>
      {showSidebar ? (
        <aside className="admin-sidebar">
          <div className="admin-sidebar-brand">
            <h3>ADR Admin</h3>
            <div className="muted">
              {adminName}
            </div>
          </div>

          <nav className="admin-sidebar-nav">
            {nav.map((item) => {
              const active = pathname === item.href || pathname.startsWith(item.href + "/");
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={active ? "admin-nav-item active" : "admin-nav-item"}
                >
                  <span className="admin-nav-main">
                    <span className="admin-nav-icon" aria-hidden="true">
                      <NavGlyph iconKey={item.iconKey} fallback={item.icon} />
                    </span>
                    <span className="admin-nav-label">{item.label}</span>
                  </span>
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
            style={{ marginTop: 12, width: "100%" }}
            onClick={() => {
              clearAuthTokens();
              router.replace("/login");
            }}
          >
            Logout
          </button>
        </aside>
      ) : null}

      <main className="admin-main-surface">
        <div className="admin-main-toolbar">
          <div className="admin-actions-dropdown" ref={actionsMenuRef}>
            {showActionsDropdown ? (
              <>
                <button
                  className="admin-actions-trigger"
                  type="button"
                  aria-expanded={actionsOpen}
                  aria-haspopup="menu"
                  onClick={() => setActionsOpen((prev) => !prev)}
                >
                  Admin Actions
                  <span aria-hidden="true">{actionsOpen ? "▴" : "▾"}</span>
                </button>
                {actionsOpen ? (
                  <div className="admin-actions-menu" role="menu">
                    {nav.map((item) => {
                      const active = pathname === item.href || pathname.startsWith(item.href + "/");
                      return (
                        <Link
                          key={`menu-${item.href}`}
                          href={item.href}
                          className={active ? "admin-actions-link active" : "admin-actions-link"}
                          role="menuitem"
                        >
                          {item.label}
                        </Link>
                      );
                    })}
                  </div>
                ) : null}
              </>
            ) : null}
          </div>
        </div>
        <div className="admin-main-content">{children}</div>
      </main>
      <SuggestionInboxWidget />
    </div>
  );
}
