"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { apiRequest } from "@/lib/api";

import styles from "./dashboard.module.css";

type DashboardStats = {
  todaySchedule: number;
  weeklySchedule: number;
  studentCount: number;
  teachingStaff: number;
  revenueCollected: number;
};

type EnquiryStats = {
  initial: number;
  followUp: number;
  confirmed: number;
};

type SyllabusSubjectProgress = {
  subject_id: string | null;
  subject_name: string;
  estimated_hours: number;
  completed_hours: number;
  completion_percentage: number;
};

type SyllabusScopeProgress = {
  class_level: number;
  stream: string | null;
  label: string;
  overall_completion_percentage: number;
  total_estimated_hours: number;
  total_completed_hours: number;
  subjects: SyllabusSubjectProgress[];
};

type SyllabusCompletionResponse = {
  groups: SyllabusScopeProgress[];
  y_axis_ticks: number[];
  generated_at: string;
};

type RevenueMonthPoint = {
  month: string;
  label: string;
  collected_amount: number;
  pending_amount: number;
  assigned_amount: number;
  cumulative_collected_amount: number;
};

type RevenueAnalyticsResponse = {
  months: RevenueMonthPoint[];
  selected_month: string;
  selected: RevenueMonthPoint | null;
  totals: {
    assigned_amount: number;
    collected_amount: number;
    pending_amount: number;
  };
};

const initialStats: DashboardStats = {
  todaySchedule: 0,
  weeklySchedule: 0,
  studentCount: 0,
  teachingStaff: 0,
  revenueCollected: 0,
};

const initialEnquiryStats: EnquiryStats = {
  initial: 0,
  followUp: 0,
  confirmed: 0,
};

function scopeKey(scope: Pick<SyllabusScopeProgress, "class_level" | "stream">): string {
  return `${scope.class_level}-${scope.stream ?? "common"}`;
}

function toDateKey(value: Date): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function getWeekRange(today: Date): { from: string; to: string } {
  const weekday = today.getDay();
  const mondayDelta = (weekday + 6) % 7;
  const fromDate = new Date(today);
  fromDate.setDate(today.getDate() - mondayDelta);
  const toDate = new Date(fromDate);
  toDate.setDate(fromDate.getDate() + 6);
  return { from: toDateKey(fromDate), to: toDateKey(toDate) };
}

function getCountFromListResponse(response: { items?: unknown[]; meta?: { total?: number } }): number {
  if (typeof response.meta?.total === "number") {
    return response.meta.total;
  }
  return Array.isArray(response.items) ? response.items.length : 0;
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(value);
}

function wrapSubjectLabel(label: string, maxChars = 11): string[] {
  const words = label.trim().split(/\s+/);
  if (words.length <= 1 && label.length <= maxChars) {
    return [label];
  }

  const lines: string[] = [];
  let current = "";
  for (const word of words) {
    if ((`${current} ${word}`).trim().length <= maxChars) {
      current = `${current} ${word}`.trim();
      continue;
    }
    if (current) {
      lines.push(current);
    }
    current = word;
    if (lines.length === 1) {
      break;
    }
  }
  if (current) {
    lines.push(current);
  }
  return lines.slice(0, 2);
}

type DashboardCard = {
  title: string;
  value: string;
  hint: string;
  tone: "green" | "blue" | "yellow" | "orange" | "purple";
  href?: string;
};

type LectureTrackerItem = {
  id: string;
  class_level: number;
  stream: string | null;
  subject_name: string;
  teacher_name: string;
  topic: string;
  status: string;
  scheduled_at: string;
  completed_at: string | null;
  is_delayed?: boolean;
};

type TrackerSummary = {
  lectures_scheduled: number;
  lectures_completed: number;
  teachers_delayed_start: number;
  attendance_marked_students: number;
  attendance_attended: number;
  attendance_missed: number;
  attendance_present: number;
  attendance_absent: number;
  attendance_late: number;
  attendance_leave: number;
  tests_scheduled: number;
  tests_done: number;
  tests_pending: number;
  new_admissions: number;
  fee_payments_count: number;
  fee_payments_students: number;
  fee_paid_amount: number;
  overdue_students: number;
  overdue_invoices: number;
};

type TrackerClassActivity = {
  class_level: number;
  stream: string | null;
  scheduled: number;
  completed: number;
  pending: number;
  canceled: number;
};

type TrackerAttendanceClassWise = {
  class_level: number;
  stream: string | null;
  total_marked: number;
  present: number;
  absent: number;
  late: number;
  leave: number;
  attended: number;
  missed: number;
  missed_students: Array<{
    student_id: string;
    full_name: string;
    admission_no: string | null;
    roll_no: string | null;
    status: string;
  }>;
};

type TrackerTestClassWise = {
  class_level: number;
  stream: string | null;
  scheduled: number;
  done: number;
  pending: number;
};

type TrackerRecentDay = {
  date: string;
  label: string;
  lectures_scheduled: number;
  lectures_completed: number;
  tests_scheduled: number;
  new_admissions: number;
  fee_payments: number;
};

type TrackerAdmissionItem = {
  student_id: string;
  full_name: string;
  phone: string | null;
  class_level: number | null;
  stream: string | null;
  created_at: string | null;
};

type TrackerFeePaymentItem = {
  transaction_id: string;
  student_id: string;
  full_name: string;
  amount: number;
  payment_mode: string | null;
  paid_at: string | null;
};

type TrackerOverdueItem = {
  invoice_id: string;
  invoice_no: string;
  student_id: string;
  full_name: string;
  due_date: string | null;
  balance_amount: number;
};

type DailyActivityTrackerResponse = {
  date: string;
  timezone: string;
  summary: TrackerSummary;
  recent_days: TrackerRecentDay[];
  lectures: LectureTrackerItem[];
  attendance: {
    summary: {
      total_marked: number;
      present: number;
      absent: number;
      late: number;
      leave: number;
      attended: number;
      missed: number;
    };
    class_wise: TrackerAttendanceClassWise[];
  };
  tests: {
    items: Array<Record<string, unknown>>;
    class_wise: TrackerTestClassWise[];
  };
  admissions: TrackerAdmissionItem[];
  fee: {
    payments: TrackerFeePaymentItem[];
    overdue: TrackerOverdueItem[];
  };
  class_wise: {
    lectures: TrackerClassActivity[];
  };
};

const initialTrackerSummary: TrackerSummary = {
  lectures_scheduled: 0,
  lectures_completed: 0,
  teachers_delayed_start: 0,
  attendance_marked_students: 0,
  attendance_attended: 0,
  attendance_missed: 0,
  attendance_present: 0,
  attendance_absent: 0,
  attendance_late: 0,
  attendance_leave: 0,
  tests_scheduled: 0,
  tests_done: 0,
  tests_pending: 0,
  new_admissions: 0,
  fee_payments_count: 0,
  fee_payments_students: 0,
  fee_paid_amount: 0,
  overdue_students: 0,
  overdue_invoices: 0,
};

function toDisplayDateTime(value: string | null | undefined): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function toDisplayTime(value: string | null | undefined): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
}

function toClassScopeLabel(classLevel: number, stream: string | null): string {
  if (classLevel <= 10 || !stream) {
    return `${classLevel}th`;
  }
  return `${classLevel}th ${stream[0].toUpperCase()}${stream.slice(1)}`;
}

export default function AdminDashboardPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<DashboardStats>(initialStats);
  const [enquiryStats, setEnquiryStats] = useState<EnquiryStats>(initialEnquiryStats);
  const [syllabus, setSyllabus] = useState<SyllabusCompletionResponse>({
    groups: [],
    y_axis_ticks: [20, 40, 60, 80, 100],
    generated_at: "",
  });
  const [selectedScopeKey, setSelectedScopeKey] = useState("10-common");
  const [revenueAnalytics, setRevenueAnalytics] = useState<RevenueAnalyticsResponse>({
    months: [],
    selected_month: "",
    selected: null,
    totals: {
      assigned_amount: 0,
      collected_amount: 0,
      pending_amount: 0,
    },
  });
  const [selectedRevenueMonth, setSelectedRevenueMonth] = useState("");
  const [trackerDate, setTrackerDate] = useState(() => toDateKey(new Date()));
  const [trackerSearch, setTrackerSearch] = useState("");
  const [trackerItems, setTrackerItems] = useState<LectureTrackerItem[]>([]);
  const [trackerSummary, setTrackerSummary] = useState<TrackerSummary>(initialTrackerSummary);
  const [trackerRecentDays, setTrackerRecentDays] = useState<TrackerRecentDay[]>([]);
  const [trackerLectureClassWise, setTrackerLectureClassWise] = useState<TrackerClassActivity[]>([]);
  const [trackerAttendanceClassWise, setTrackerAttendanceClassWise] = useState<TrackerAttendanceClassWise[]>([]);
  const [trackerTestClassWise, setTrackerTestClassWise] = useState<TrackerTestClassWise[]>([]);
  const [trackerAdmissions, setTrackerAdmissions] = useState<TrackerAdmissionItem[]>([]);
  const [trackerFeePayments, setTrackerFeePayments] = useState<TrackerFeePaymentItem[]>([]);
  const [trackerFeeOverdue, setTrackerFeeOverdue] = useState<TrackerOverdueItem[]>([]);
  const [trackerLoading, setTrackerLoading] = useState(false);
  const [trackerError, setTrackerError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    async function load() {
      try {
        const now = new Date();
        const todayKey = toDateKey(now);
        const weekRange = getWeekRange(now);

        const [
          students,
          teachers,
          feeSummary,
          todaySchedules,
          weeklySchedules,
          initialEnquiries,
          followUpEnquiries,
          confirmedEnquiries,
          syllabusResponse,
          revenueResponse,
        ] = await Promise.all([
          apiRequest<{ meta: { total: number } }>("/api/v1/admin/students?limit=1&offset=0"),
          apiRequest<{ meta: { total: number } }>("/api/v1/admin/teachers?limit=1&offset=0"),
          apiRequest<{ total_paid_amount: number }>("/api/v1/admin/fees/summary"),
          apiRequest<{ items?: unknown[]; meta?: { total?: number } }>(
            `/api/v1/admin/lecture-schedules?scheduled_from=${todayKey}&scheduled_to=${todayKey}&limit=100&offset=0`,
          ),
          apiRequest<{ items?: unknown[]; meta?: { total?: number } }>(
            `/api/v1/admin/lecture-schedules?scheduled_from=${weekRange.from}&scheduled_to=${weekRange.to}&limit=100&offset=0`,
          ),
          apiRequest<{ items?: unknown[]; meta?: { total?: number } }>(
            "/api/v1/admin/enquiries?status=interested&limit=1&offset=0",
          ),
          apiRequest<{ items?: unknown[]; meta?: { total?: number } }>(
            "/api/v1/admin/enquiries?status=follow_up&limit=1&offset=0",
          ),
          apiRequest<{ items?: unknown[]; meta?: { total?: number } }>(
            "/api/v1/admin/enquiries?status=confirmed&limit=1&offset=0",
          ),
          apiRequest<SyllabusCompletionResponse>("/api/v1/admin/syllabus/completion"),
          apiRequest<RevenueAnalyticsResponse>("/api/v1/admin/fees/monthly-analytics?months=12"),
        ]);

        if (!mounted) {
          return;
        }

        setStats({
          todaySchedule: getCountFromListResponse(todaySchedules),
          weeklySchedule: getCountFromListResponse(weeklySchedules),
          studentCount: students.meta.total ?? 0,
          teachingStaff: teachers.meta.total ?? 0,
          revenueCollected: feeSummary.total_paid_amount ?? 0,
        });
        setEnquiryStats({
          initial: getCountFromListResponse(initialEnquiries),
          followUp: getCountFromListResponse(followUpEnquiries),
          confirmed: getCountFromListResponse(confirmedEnquiries),
        });
        setSyllabus(syllabusResponse);
        setSelectedScopeKey((previousKey) => {
          if (syllabusResponse.groups.some((item) => scopeKey(item) == previousKey)) {
            return previousKey;
          }
          return syllabusResponse.groups[0] ? scopeKey(syllabusResponse.groups[0]) : "10-common";
        });
        setRevenueAnalytics(revenueResponse);
        setSelectedRevenueMonth((previous) => {
          if (previous && revenueResponse.months.some((item) => item.month === previous)) {
            return previous;
          }
          return (
            revenueResponse.selected_month ||
            (revenueResponse.months.length > 0 ? revenueResponse.months[revenueResponse.months.length - 1].month : "")
          );
        });
        setLoading(false);
        setError(null);
      } catch (err) {
        if (!mounted) {
          return;
        }
        setError(err instanceof Error ? err.message : "Failed to load dashboard");
        setLoading(false);
      }
    }

    void load();
    const interval = window.setInterval(() => {
      void load();
    }, 30000);
    return () => {
      mounted = false;
      window.clearInterval(interval);
    };
  }, []);

  const cards = useMemo<DashboardCard[]>(
    () => [
      {
        title: "Today's Schedule",
        value: String(stats.todaySchedule),
        hint: "Planned lectures for today",
        tone: "green",
        href: "/admin/lecture-schedules",
      },
      {
        title: "Weekly Schedule",
        value: String(stats.weeklySchedule),
        hint: "This week planned lectures",
        tone: "blue",
        href: "/admin/lecture-schedules",
      },
      {
        title: "Count of Student",
        value: String(stats.studentCount),
        hint: "Registered student strength",
        tone: "yellow",
        href: "/admin/students/count",
      },
      {
        title: "Teaching Staff",
        value: String(stats.teachingStaff),
        hint: "Active teacher count",
        tone: "orange",
        href: "/admin/teachers",
      },
      {
        title: "Revenue",
        value: formatCurrency(stats.revenueCollected),
        hint: "Collected fee amount",
        tone: "purple",
        href: "/admin/fees",
      },
    ],
    [stats],
  );

  const toneClassMap: Record<DashboardCard["tone"], string> = {
    green: styles.cardGreen,
    blue: styles.cardBlue,
    yellow: styles.cardYellow,
    orange: styles.cardOrange,
    purple: styles.cardPurple,
  };

  const selectedScope = useMemo(
    () => syllabus.groups.find((group) => scopeKey(group) === selectedScopeKey) ?? null,
    [selectedScopeKey, syllabus.groups],
  );

  const yAxisTicksDesc = useMemo(
    () => {
      const ticks = new Set<number>([...syllabus.y_axis_ticks, 0]);
      return [...ticks].sort((left, right) => right - left);
    },
    [syllabus.y_axis_ticks],
  );

  const chartModel = useMemo(() => {
    if (!selectedScope) {
      return null;
    }

    const subjects = selectedScope.subjects ?? [];
    const margin = { top: 16, right: 16, bottom: 86, left: 58 };
    const plotHeight = 220;
    const slotWidth = 92;
    const barWidth = 34;
    const plotWidth = Math.max(560, subjects.length * slotWidth);
    const width = margin.left + plotWidth + margin.right;
    const height = margin.top + plotHeight + margin.bottom;
    const yZero = margin.top + plotHeight;
    const yTicks = [...new Set<number>([0, ...syllabus.y_axis_ticks])].sort((a, b) => a - b);

    const bars = subjects.map((subject, index) => {
      const pct = Math.max(0, Math.min(100, Number(subject.completion_percentage || 0)));
      const barHeight = (pct / 100) * plotHeight;
      const x = margin.left + index * slotWidth + (slotWidth - barWidth) / 2;
      const y = yZero - barHeight;
      return {
        key: `${subject.subject_id ?? subject.subject_name}-${index}`,
        x,
        y,
        width: barWidth,
        height: barHeight,
        pct,
        labelLines: wrapSubjectLabel(subject.subject_name),
        labelX: margin.left + index * slotWidth + slotWidth / 2,
      };
    });

    return {
      width,
      height,
      margin,
      plotHeight,
      plotWidth,
      yZero,
      yTicks,
      bars,
    };
  }, [selectedScope, syllabus.y_axis_ticks]);

  const selectedRevenueItem = useMemo(() => {
    if (revenueAnalytics.months.length === 0) {
      return null;
    }
    return (
      revenueAnalytics.months.find((item) => item.month === selectedRevenueMonth) ??
      revenueAnalytics.selected ??
      revenueAnalytics.months[revenueAnalytics.months.length - 1]
    );
  }, [revenueAnalytics.months, revenueAnalytics.selected, selectedRevenueMonth]);

  const revenueChartModel = useMemo(() => {
    const months = revenueAnalytics.months ?? [];
    if (months.length === 0) {
      return null;
    }

    const margin = { top: 16, right: 16, bottom: 56, left: 76 };
    const plotHeight = 220;
    const slotWidth = 74;
    const barWidth = 20;
    const plotWidth = Math.max(540, months.length * slotWidth);
    const width = margin.left + plotWidth + margin.right;
    const height = margin.top + plotHeight + margin.bottom;
    const yZero = margin.top + plotHeight;
    const maxValueRaw = Math.max(
      1,
      ...months.map((item) => Math.max(item.collected_amount || 0, item.pending_amount || 0)),
    );
    const maxValue = Math.ceil(maxValueRaw / 1000) * 1000;
    const yTicks = [0, 0.25, 0.5, 0.75, 1].map((ratio) => Math.round(maxValue * ratio));

    const bars = months.map((item, index) => {
      const xCenter = margin.left + index * slotWidth + slotWidth / 2;
      const collectedHeight = (Math.max(item.collected_amount || 0, 0) / maxValue) * plotHeight;
      const pendingHeight = (Math.max(item.pending_amount || 0, 0) / maxValue) * plotHeight;
      return {
        key: item.month,
        month: item.month,
        label: item.label,
        xCenter,
        collected: {
          x: xCenter - barWidth - 2,
          y: yZero - collectedHeight,
          width: barWidth,
          height: collectedHeight,
          value: item.collected_amount || 0,
        },
        pending: {
          x: xCenter + 2,
          y: yZero - pendingHeight,
          width: barWidth,
          height: pendingHeight,
          value: item.pending_amount || 0,
        },
      };
    });

    return {
      width,
      height,
      margin,
      plotHeight,
      plotWidth,
      yZero,
      yTicks,
      bars,
      maxValue,
    };
  }, [revenueAnalytics.months]);

  const trackerDayLabel = useMemo(() => {
    const date = new Date(`${trackerDate}T00:00:00`);
    if (Number.isNaN(date.getTime())) {
      return trackerDate;
    }
    return date.toLocaleDateString("en-IN", {
      weekday: "long",
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  }, [trackerDate]);

  useEffect(() => {
    let mounted = true;

    async function loadTracker() {
      setTrackerLoading(true);
      try {
        const params = new URLSearchParams();
        params.set("day", trackerDate);
        if (trackerSearch.trim()) {
          params.set("search", trackerSearch.trim());
        }

        const response = await apiRequest<DailyActivityTrackerResponse>(
          `/api/v1/admin/activity-tracker/daily?${params.toString()}`,
        );

        if (!mounted) {
          return;
        }

        setTrackerItems(response.lectures ?? []);
        setTrackerSummary(response.summary ?? initialTrackerSummary);
        setTrackerRecentDays(response.recent_days ?? []);
        setTrackerLectureClassWise(response.class_wise?.lectures ?? []);
        setTrackerAttendanceClassWise(response.attendance?.class_wise ?? []);
        setTrackerTestClassWise(response.tests?.class_wise ?? []);
        setTrackerAdmissions(response.admissions ?? []);
        setTrackerFeePayments(response.fee?.payments ?? []);
        setTrackerFeeOverdue(response.fee?.overdue ?? []);
        setTrackerError(null);
      } catch (err) {
        if (!mounted) {
          return;
        }
        setTrackerError(err instanceof Error ? err.message : "Failed to load tracker activities");
      } finally {
        if (mounted) {
          setTrackerLoading(false);
        }
      }
    }

    void loadTracker();
    const interval = window.setInterval(() => {
      void loadTracker();
    }, 30000);

    return () => {
      mounted = false;
      window.clearInterval(interval);
    };
  }, [trackerDate, trackerSearch]);

  if (loading) {
    return <p>Loading dashboard...</p>;
  }

  if (error) {
    return <p style={{ color: "#dc2626" }}>{error}</p>;
  }

  return (
    <section className={styles.root}>
      <header className={styles.header}>
        <div className={styles.brandWrap}>
          <div className={styles.logoMark} aria-hidden="true">
            <Image
              src="/branding/adrika-logo.jpg"
              alt="Adrika Coaching Classes"
              width={40}
              height={40}
              priority
            />
          </div>
          <div>
            <h1 className={styles.title}>Adrika Coaching Classes</h1>
            <p className={styles.subtitle}>Admin Dashboard</p>
          </div>
        </div>
      </header>

      <div className={styles.cardGrid}>
        {cards.map((card) => (
          <article className={`${styles.card} ${toneClassMap[card.tone]}`} key={card.title}>
            <div className={styles.cardLabel}>{card.title}</div>
            <div className={styles.cardValue}>{card.value}</div>
            <div className={styles.cardHint}>{card.hint}</div>
            {card.href ? (
              <Link className={styles.cardAction} href={card.href}>
                Open
              </Link>
            ) : (
              <div className={styles.cardActionGhost}>Active</div>
            )}
          </article>
        ))}
      </div>

      <section className={styles.trackerSection}>
        <div className={styles.trackerHeader}>
          <div>
            <h2 className={styles.trackerTitle}>Daily Activity Tracker</h2>
            <p className={styles.trackerSubTitle}>24-hour class operations summary: lectures, attendance, tests, admissions and fees.</p>
          </div>
          <Link className={styles.cardAction} href="/admin/lecture-schedules">
            Open Lecture Tracker
          </Link>
        </div>

        <div className={styles.trackerControls}>
          <label className={styles.trackerField}>
            <span>Date</span>
            <input type="date" value={trackerDate} onChange={(event) => setTrackerDate(event.target.value)} />
          </label>
          <label className={styles.trackerField}>
            <span>Search</span>
            <input
              type="text"
              value={trackerSearch}
              onChange={(event) => setTrackerSearch(event.target.value)}
              placeholder="Teacher / subject / topic"
            />
          </label>
        </div>

        <div className={styles.trackerMetaRow}>
          <div className={styles.trackerDayChip}>{trackerDayLabel}</div>
          <div className={styles.trackerCountRow}>
            <div className={styles.trackerCountCard}>
              <span className={styles.trackerCountLabel}>Lectures Done</span>
              <strong className={styles.trackerCountValue}>{trackerSummary.lectures_completed}</strong>
            </div>
            <div className={styles.trackerCountCard}>
              <span className={styles.trackerCountLabel}>Attendance Marked</span>
              <strong className={styles.trackerCountValue}>{trackerSummary.attendance_marked_students}</strong>
            </div>
            <div className={styles.trackerCountCard}>
              <span className={styles.trackerCountLabel}>Tests Pending</span>
              <strong className={styles.trackerCountValue}>{trackerSummary.tests_pending}</strong>
            </div>
          </div>
        </div>

        <div className={styles.trackerRecentDays}>
          {trackerRecentDays.map((dayItem) => (
            <button
              key={dayItem.date}
              type="button"
              onClick={() => setTrackerDate(dayItem.date)}
              className={dayItem.date === trackerDate ? `${styles.trackerRecentChip} ${styles.trackerRecentChipActive}` : styles.trackerRecentChip}
            >
              <strong>{dayItem.label}</strong>
              <span>Lec {dayItem.lectures_completed}/{dayItem.lectures_scheduled}</span>
              <span>Tests {dayItem.tests_scheduled}</span>
            </button>
          ))}
        </div>

        <div className={styles.trackerSummaryGrid}>
          <article className={styles.trackerSummaryCard}><span>Teachers Delayed</span><strong>{trackerSummary.teachers_delayed_start}</strong></article>
          <article className={styles.trackerSummaryCard}><span>Attendance Missed</span><strong>{trackerSummary.attendance_missed}</strong></article>
          <article className={styles.trackerSummaryCard}><span>Tests Scheduled</span><strong>{trackerSummary.tests_scheduled}</strong></article>
          <article className={styles.trackerSummaryCard}><span>New Admissions</span><strong>{trackerSummary.new_admissions}</strong></article>
          <article className={styles.trackerSummaryCard}><span>Fee Paid Today</span><strong>{formatCurrency(trackerSummary.fee_paid_amount)}</strong></article>
          <article className={styles.trackerSummaryCard}><span>Overdue Students</span><strong>{trackerSummary.overdue_students}</strong></article>
        </div>

        {trackerError ? <p style={{ color: "#dc2626", margin: 0 }}>{trackerError}</p> : null}

        <div className={styles.trackerSplitGrid}>
          <section className={styles.trackerPanel}>
            <h3 className={styles.trackerPanelTitle}>Class-wise Attendance</h3>
            {trackerAttendanceClassWise.length === 0 ? <p className={styles.trackerEmpty}>No attendance activity for selected day.</p> : null}
            <div className={styles.trackerMiniGrid}>
              {trackerAttendanceClassWise.map((row) => (
                <article key={`${row.class_level}-${row.stream ?? "common"}`} className={styles.trackerMiniCard}>
                  <h4>{toClassScopeLabel(row.class_level, row.stream)}</h4>
                  <div className={styles.trackerMiniStats}>
                    <span>Attended: {row.attended}</span>
                    <span>Missed: {row.missed}</span>
                    <span>Present: {row.present}</span>
                    <span>Absent: {row.absent}</span>
                  </div>
                  {row.missed_students.length > 0 ? (
                    <p className={styles.trackerMiniHint}>Missed: {row.missed_students.slice(0, 3).map((s) => s.full_name).join(", ")}{row.missed_students.length > 3 ? "..." : ""}</p>
                  ) : null}
                </article>
              ))}
            </div>
          </section>

          <section className={styles.trackerPanel}>
            <h3 className={styles.trackerPanelTitle}>Class-wise Tests</h3>
            {trackerTestClassWise.length === 0 ? <p className={styles.trackerEmpty}>No test activity for selected day.</p> : null}
            <div className={styles.trackerMiniGrid}>
              {trackerTestClassWise.map((row) => (
                <article key={`${row.class_level}-${row.stream ?? "common"}`} className={styles.trackerMiniCard}>
                  <h4>{toClassScopeLabel(row.class_level, row.stream)}</h4>
                  <div className={styles.trackerMiniStats}>
                    <span>Scheduled: {row.scheduled}</span>
                    <span>Done: {row.done}</span>
                    <span>Pending: {row.pending}</span>
                  </div>
                </article>
              ))}
            </div>
          </section>
        </div>

        <section className={styles.trackerPanel}>
          <h3 className={styles.trackerPanelTitle}>Lecture Activities</h3>
          <div className={styles.trackerClassGrid}>
            {trackerLectureClassWise.map((row) => (
              <article key={`${row.class_level}-${row.stream ?? "common"}`} className={styles.trackerClassCard}>
                <strong>{toClassScopeLabel(row.class_level, row.stream)}</strong>
                <span>S: {row.scheduled}</span>
                <span>C: {row.completed}</span>
                <span>P: {row.pending}</span>
                <span>X: {row.canceled}</span>
              </article>
            ))}
          </div>
          <div className={styles.trackerList}>
            {trackerLoading ? <p className={styles.trackerEmpty}>Loading day activities...</p> : null}
            {!trackerLoading && trackerItems.length === 0 ? (
              <p className={styles.trackerEmpty}>No lecture activity found for selected day.</p>
            ) : null}

            {!trackerLoading
              ? trackerItems.map((item) => {
                  const done = item.status === "done";
                  return (
                    <article key={item.id} className={styles.trackerCard}>
                      <div className={styles.trackerCardTop}>
                        <h3 className={styles.trackerCardTitle}>{item.subject_name}</h3>
                        <span className={done ? styles.trackerBadgeDone : styles.trackerBadgeScheduled}>
                          {done ? "Completed" : item.is_delayed ? "Delayed" : "Scheduled"}
                        </span>
                      </div>
                      <p className={styles.trackerCardTopic}>{item.topic}</p>
                      <div className={styles.trackerCardGrid}>
                        <div>
                          <span className={styles.trackerItemLabel}>Class</span>
                          <div className={styles.trackerItemValue}>{toClassScopeLabel(item.class_level, item.stream)}</div>
                        </div>
                        <div>
                          <span className={styles.trackerItemLabel}>Teacher</span>
                          <div className={styles.trackerItemValue}>{item.teacher_name}</div>
                        </div>
                        <div>
                          <span className={styles.trackerItemLabel}>Scheduled Time</span>
                          <div className={styles.trackerItemValue}>{toDisplayTime(item.scheduled_at)}</div>
                        </div>
                        <div>
                          <span className={styles.trackerItemLabel}>Completion Time</span>
                          <div className={styles.trackerItemValue}>{done ? toDisplayDateTime(item.completed_at) : "-"}</div>
                        </div>
                      </div>
                    </article>
                  );
                })
              : null}
          </div>
        </section>

        <div className={styles.trackerSplitGrid}>
          <section className={styles.trackerPanel}>
            <h3 className={styles.trackerPanelTitle}>New Admissions</h3>
            {trackerAdmissions.length === 0 ? <p className={styles.trackerEmpty}>No new admissions on this day.</p> : null}
            <div className={styles.trackerSimpleList}>
              {trackerAdmissions.map((item) => (
                <div key={item.student_id} className={styles.trackerSimpleRow}>
                  <strong>{item.full_name}</strong>
                  <span>{item.class_level ? toClassScopeLabel(item.class_level, item.stream) : "-"}</span>
                  <span>{item.phone ?? "-"}</span>
                </div>
              ))}
            </div>
          </section>

          <section className={styles.trackerPanel}>
            <h3 className={styles.trackerPanelTitle}>Fee Payments</h3>
            {trackerFeePayments.length === 0 ? <p className={styles.trackerEmpty}>No fee payments on this day.</p> : null}
            <div className={styles.trackerSimpleList}>
              {trackerFeePayments.map((item) => (
                <div key={item.transaction_id} className={styles.trackerSimpleRow}>
                  <strong>{item.full_name}</strong>
                  <span>{formatCurrency(item.amount)}</span>
                  <span>{toDisplayTime(item.paid_at)}</span>
                </div>
              ))}
            </div>
          </section>
        </div>

        <section className={styles.trackerPanel}>
          <h3 className={styles.trackerPanelTitle}>Overdue Fee Students</h3>
          {trackerFeeOverdue.length === 0 ? <p className={styles.trackerEmpty}>No overdue fee records.</p> : null}
          <div className={styles.trackerSimpleList}>
            {trackerFeeOverdue.map((item) => (
              <div key={item.invoice_id} className={styles.trackerSimpleRow}>
                <strong>{item.full_name}</strong>
                <span>{item.invoice_no}</span>
                <span>{formatCurrency(item.balance_amount)}</span>
                <span>{item.due_date ? toDisplayDateTime(item.due_date) : "-"}</span>
              </div>
            ))}
          </div>
        </section>
      </section>

      <section className={styles.enquirySection}>
        <h2 className={styles.enquiryHeading}>Enqury</h2>
        <div className={styles.enquiryStatsGrid}>
          <article className={styles.enquiryStatCard}>
            <div className={styles.enquiryStatLabel}>
              <span className={`${styles.enquiryDot} ${styles.enquiryDotInitial}`} aria-hidden="true" />
              Initial Enquiry
            </div>
            <div className={styles.enquiryStatValue}>{enquiryStats.initial}</div>
          </article>
          <article className={styles.enquiryStatCard}>
            <div className={styles.enquiryStatLabel}>
              <span className={`${styles.enquiryDot} ${styles.enquiryDotFollowUp}`} aria-hidden="true" />
              Follow Up
            </div>
            <div className={styles.enquiryStatValue}>{enquiryStats.followUp}</div>
          </article>
          <article className={styles.enquiryStatCard}>
            <div className={styles.enquiryStatLabel}>
              <span className={`${styles.enquiryDot} ${styles.enquiryDotConfirmed}`} aria-hidden="true" />
              Confirmed
            </div>
            <div className={styles.enquiryStatValue}>{enquiryStats.confirmed}</div>
          </article>
        </div>
      </section>

      <section className={styles.syllabusSection}>
        <div className={styles.syllabusHeader}>
          <h2 className={styles.syllabusHeading}>Syllabus Completion Graph</h2>
          <p className={styles.syllabusSubheading}>Class-wise subject completion from planned vs completed lecture hours.</p>
        </div>

        {selectedScope ? (
          <>
            <div className={styles.scopeTabs}>
              {syllabus.groups.map((group) => {
                const key = scopeKey(group);
                return (
                  <button
                    key={key}
                    type="button"
                    className={key === selectedScopeKey ? `${styles.scopeTab} ${styles.scopeTabActive}` : styles.scopeTab}
                    onClick={() => setSelectedScopeKey(key)}
                  >
                    {group.label}
                  </button>
                );
              })}
            </div>

            <div className={styles.syllabusSummary}>
              <div className={styles.piePanel}>
                <div
                  className={styles.pieChart}
                  style={{
                    background: `conic-gradient(#4f46e5 0% ${selectedScope.overall_completion_percentage}%, #e9ddff ${selectedScope.overall_completion_percentage}% 100%)`,
                  }}
                >
                  <span>{Math.round(selectedScope.overall_completion_percentage)}%</span>
                </div>
                <p className={styles.pieCaption}>Overall {selectedScope.label}</p>
              </div>
              <div className={styles.syllabusMeta}>
                <div>Total Estimated Hours: {selectedScope.total_estimated_hours}</div>
                <div>Total Completed Hours: {selectedScope.total_completed_hours}</div>
              </div>
            </div>

            <div className={styles.chartShell}>
              <div className={styles.chartArea}>
                {chartModel ? (
                  <div className={styles.chartScroll}>
                    <svg
                      className={styles.chartSvg}
                      width={chartModel.width}
                      height={chartModel.height}
                      viewBox={`0 0 ${chartModel.width} ${chartModel.height}`}
                      role="img"
                      aria-label="Syllabus completion bar graph"
                    >
                      {chartModel.yTicks.map((tick) => {
                        const y = chartModel.yZero - (tick / 100) * chartModel.plotHeight;
                        const baseline = tick === 0;
                        return (
                          <g key={`tick-${tick}`}>
                            <line
                              x1={chartModel.margin.left}
                              y1={y}
                              x2={chartModel.margin.left + chartModel.plotWidth}
                              y2={y}
                              className={baseline ? styles.gridLineBaseline : styles.gridLine}
                            />
                            <text
                              x={chartModel.margin.left - 10}
                              y={y + 4}
                              textAnchor="end"
                              className={styles.yAxisTickText}
                            >
                              {tick}%
                            </text>
                          </g>
                        );
                      })}

                      <line
                        x1={chartModel.margin.left}
                        y1={chartModel.margin.top}
                        x2={chartModel.margin.left}
                        y2={chartModel.yZero}
                        className={styles.axisLine}
                      />
                      <line
                        x1={chartModel.margin.left}
                        y1={chartModel.yZero}
                        x2={chartModel.margin.left + chartModel.plotWidth}
                        y2={chartModel.yZero}
                        className={styles.axisLine}
                      />

                      {chartModel.bars.map((bar) => (
                        <g key={bar.key}>
                          <rect
                            x={bar.x}
                            y={bar.y}
                            width={bar.width}
                            height={bar.height}
                            rx={6}
                            className={styles.barRect}
                          />
                          <text x={bar.x + bar.width / 2} y={bar.y - 6} textAnchor="middle" className={styles.barValueText}>
                            {Math.round(bar.pct)}%
                          </text>
                          <text
                            x={bar.labelX}
                            y={chartModel.yZero + 16}
                            textAnchor="middle"
                            className={styles.xAxisLabelText}
                          >
                            {bar.labelLines.map((line, index) => (
                              <tspan key={`${bar.key}-line-${index}`} x={bar.labelX} dy={index === 0 ? 0 : 12}>
                                {line}
                              </tspan>
                            ))}
                          </text>
                        </g>
                      ))}
                    </svg>
                  </div>
                ) : null}
              </div>
            </div>
          </>
        ) : (
          <p className={styles.emptySyllabus}>No syllabus data available yet.</p>
        )}
      </section>

      <section className={styles.revenueSection}>
        <div className={styles.revenueHeader}>
          <h2 className={styles.revenueHeading}>Monthly Revenue Graph</h2>
          <div className={styles.revenueMonthPicker}>
            <label htmlFor="revenue-month">Month</label>
            <select
              id="revenue-month"
              value={selectedRevenueMonth}
              onChange={(event) => setSelectedRevenueMonth(event.target.value)}
            >
              {revenueAnalytics.months.map((item) => (
                <option key={item.month} value={item.month}>
                  {item.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {selectedRevenueItem ? (
          <div className={styles.revenueSummaryRow}>
            <div className={styles.revenueSummaryCard}>
              <div className={styles.revenueSummaryLabel}>Collected ({selectedRevenueItem.label})</div>
              <div className={styles.revenueSummaryValue}>{formatCurrency(selectedRevenueItem.collected_amount)}</div>
            </div>
            <div className={styles.revenueSummaryCard}>
              <div className={styles.revenueSummaryLabel}>Pending ({selectedRevenueItem.label})</div>
              <div className={styles.revenueSummaryValue}>{formatCurrency(selectedRevenueItem.pending_amount)}</div>
            </div>
            <div className={styles.revenueSummaryCard}>
              <div className={styles.revenueSummaryLabel}>Total Assigned ({selectedRevenueItem.label})</div>
              <div className={styles.revenueSummaryValue}>{formatCurrency(selectedRevenueItem.assigned_amount)}</div>
            </div>
          </div>
        ) : null}

        <div className={styles.revenueLegend}>
          <span className={styles.legendItem}>
            <i className={`${styles.legendSwatch} ${styles.legendSwatchCollected}`} />
            Collected Fee
          </span>
          <span className={styles.legendItem}>
            <i className={`${styles.legendSwatch} ${styles.legendSwatchPending}`} />
            Pending Fee
          </span>
        </div>

        <div className={styles.revenueChartShell}>
          <div className={styles.revenueChartArea}>
            {revenueChartModel ? (
              <div className={styles.revenueChartScroll}>
                <svg
                  className={styles.revenueChartSvg}
                  width={revenueChartModel.width}
                  height={revenueChartModel.height}
                  viewBox={`0 0 ${revenueChartModel.width} ${revenueChartModel.height}`}
                  role="img"
                  aria-label="Monthly revenue and pending fee graph"
                >
                  {revenueChartModel.yTicks.map((tick) => {
                    const ratio = revenueChartModel.maxValue > 0 ? tick / revenueChartModel.maxValue : 0;
                    const y = revenueChartModel.yZero - ratio * revenueChartModel.plotHeight;
                    const baseline = tick === 0;
                    return (
                      <g key={`rev-tick-${tick}`}>
                        <line
                          x1={revenueChartModel.margin.left}
                          y1={y}
                          x2={revenueChartModel.margin.left + revenueChartModel.plotWidth}
                          y2={y}
                          className={baseline ? styles.gridLineBaseline : styles.gridLine}
                        />
                        <text
                          x={revenueChartModel.margin.left - 10}
                          y={y + 4}
                          textAnchor="end"
                          className={styles.yAxisTickText}
                        >
                          {Math.round(tick / 1000)}k
                        </text>
                      </g>
                    );
                  })}

                  <line
                    x1={revenueChartModel.margin.left}
                    y1={revenueChartModel.margin.top}
                    x2={revenueChartModel.margin.left}
                    y2={revenueChartModel.yZero}
                    className={styles.axisLine}
                  />
                  <line
                    x1={revenueChartModel.margin.left}
                    y1={revenueChartModel.yZero}
                    x2={revenueChartModel.margin.left + revenueChartModel.plotWidth}
                    y2={revenueChartModel.yZero}
                    className={styles.axisLine}
                  />

                  {revenueChartModel.bars.map((bar) => {
                    const isSelected = selectedRevenueItem?.month === bar.month;
                    return (
                      <g key={`rev-bar-${bar.key}`}>
                        {isSelected ? (
                          <rect
                            x={bar.xCenter - 30}
                            y={revenueChartModel.margin.top}
                            width={60}
                            height={revenueChartModel.plotHeight}
                            rx={8}
                            className={styles.revenueSelectedBand}
                          />
                        ) : null}
                        <rect
                          x={bar.collected.x}
                          y={bar.collected.y}
                          width={bar.collected.width}
                          height={bar.collected.height}
                          rx={5}
                          className={styles.revenueCollectedBar}
                        />
                        <rect
                          x={bar.pending.x}
                          y={bar.pending.y}
                          width={bar.pending.width}
                          height={bar.pending.height}
                          rx={5}
                          className={styles.revenuePendingBar}
                        />
                        <text
                          x={bar.xCenter}
                          y={revenueChartModel.yZero + 16}
                          textAnchor="middle"
                          className={styles.xAxisLabelText}
                        >
                          {bar.label.split(" ")[0]}
                        </text>
                      </g>
                    );
                  })}
                </svg>
              </div>
            ) : (
              <p className={styles.emptySyllabus}>No fee analytics available yet.</p>
            )}
          </div>
        </div>
      </section>
    </section>
  );
}
