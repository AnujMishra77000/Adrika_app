import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../models/student_models.dart";
import "../state/student_providers.dart";
import "widgets/student_announcement_card.dart";
import "widgets/student_attendance_holiday_row.dart";
import "widgets/student_doubt_cta_card.dart";
import "widgets/student_fade_slide_in.dart";
import "widgets/student_hero_banner.dart";
import "widgets/student_home_header.dart";
import "widgets/student_home_states.dart";
import "widgets/student_quick_action_grid.dart";
import "widgets/student_section_header.dart";
import "widgets/student_today_schedule_panel.dart";

class StudentDashboardScreen extends ConsumerWidget {
  const StudentDashboardScreen({super.key});

  Future<void> _refresh(WidgetRef ref) async {
    ref.invalidate(studentHomeSummaryProvider);
    ref.invalidate(studentNotificationsProvider);
    ref.invalidate(studentAnnouncementsProvider);
    await ref.read(studentHomeSummaryProvider.future);
  }

  String _firstName(String fullName) {
    final segments = fullName.trim().split(RegExp(r"\s+"));
    if (segments.isEmpty || segments.first.isEmpty) {
      return "Student";
    }
    return segments.first;
  }

  String _upcomingLectureLabel(DateTime? value) {
    if (value == null) {
      return "Timetable sync pending";
    }

    final now = DateTime.now();
    final diff = value.difference(now);

    if (diff.inMinutes <= 0) {
      return "Starting shortly";
    }
    if (diff.inHours < 1) {
      return "Starts in ${diff.inMinutes} min";
    }
    if (diff.inHours < 24) {
      return "Starts in ${diff.inHours} hr";
    }
    return "Starts in ${diff.inDays} day";
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final summaryAsync = ref.watch(studentHomeSummaryProvider);

    return SafeArea(
      top: true,
      bottom: false,
      child: Stack(
        children: [
          const _GhostBackdrop(),
          RefreshIndicator(
            onRefresh: () => _refresh(ref),
            child: summaryAsync.when(
              loading: () => const StudentHomeLoadingList(),
              error: (error, _) => StudentHomeErrorList(
                message: error.toString(),
                onRetry: () => ref.invalidate(studentHomeSummaryProvider),
              ),
              data: (summary) => _StudentHomeBody(
                summary: summary,
                greetingName: _firstName(summary.profile.fullName),
                upcomingLectureLabel:
                    _upcomingLectureLabel(summary.upcomingLecture.nextAt),
                onRouteTap: (route) => context.push(route),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _GhostBackdrop extends StatelessWidget {
  const _GhostBackdrop();

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            Color(0xFF130C2C),
            Color(0xFF1B1240),
            Color(0xFF111E46),
            Color(0xFF0C1738),
          ],
        ),
      ),
      child: Stack(
        children: [
          Positioned(
            left: -90,
            top: -120,
            child: _GhostOrb(
              size: 310,
              color: const Color(0xFF7F54F9).withValues(alpha: 0.30),
            ),
          ),
          Positioned(
            right: -80,
            top: 120,
            child: _GhostOrb(
              size: 270,
              color: const Color(0xFF3B7BFF).withValues(alpha: 0.22),
            ),
          ),
          Positioned(
            left: -40,
            bottom: -120,
            child: _GhostOrb(
              size: 260,
              color: const Color(0xFF925CFF).withValues(alpha: 0.18),
            ),
          ),
        ],
      ),
    );
  }
}

class _GhostOrb extends StatelessWidget {
  const _GhostOrb({required this.size, required this.color});

  final double size;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: RadialGradient(
          colors: [
            color,
            color.withValues(alpha: 0),
          ],
        ),
      ),
    );
  }
}

class _StudentHomeBody extends StatelessWidget {
  const _StudentHomeBody({
    required this.summary,
    required this.greetingName,
    required this.upcomingLectureLabel,
    required this.onRouteTap,
  });

  final StudentHomeSummary summary;
  final String greetingName;
  final String upcomingLectureLabel;
  final ValueChanged<String> onRouteTap;

  @override
  Widget build(BuildContext context) {
    final heroCards = <StudentHeroCardData>[
      StudentHeroCardData(
        title: "Today Lectures",
        value: summary.todayLectures.primaryValue,
        subtitle: summary.todayLectures.secondaryText,
        route: "/student/lectures/today",
        icon: Icons.menu_book_outlined,
        accent: const Color(0xFF9CB0FF),
      ),
      StudentHeroCardData(
        title: "Upcoming Lecture",
        value: summary.upcomingLecture.primaryValue,
        subtitle: upcomingLectureLabel,
        route: "/student/lectures/upcoming",
        icon: Icons.schedule_outlined,
        accent: const Color(0xFF80CBFF),
      ),
      StudentHeroCardData(
        title: "Practice Test",
        value: summary.practiceTest.availableCount.toString(),
        subtitle: "${summary.practiceTest.attemptedToday} attempted today",
        route: "/student/practice-tests",
        icon: Icons.quiz_outlined,
        accent: const Color(0xFFD7A6FF),
      ),
      StudentHeroCardData(
        title: "Progress",
        value: "${summary.progress.attendancePercent.toStringAsFixed(1)}%",
        subtitle: summary.progress.trendLabel,
        route: "/student/progress",
        icon: Icons.auto_graph_outlined,
        accent: const Color(0xFFA4DBCB),
      ),
    ];

    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(16, 18, 16, 24),
      children: [
        const StudentFadeSlideIn(
          delayMs: 20,
          child: _StudentBrandStrip(),
        ),
        const SizedBox(height: 12),
        StudentFadeSlideIn(
          delayMs: 40,
          child: StudentHomeHeader(
            greeting: "Hello $greetingName",
            unreadCount: summary.unreadNotificationCount,
            onNotificationTap: () => onRouteTap("/student/notifications"),
            photoUrl: summary.profile.photoUrl,
            greetingColor: const Color(0xFFF5F2FF),
          ),
        ),
        const SizedBox(height: 14),
        StudentFadeSlideIn(
          delayMs: 90,
          child: StudentHeroBanner(
            cards: heroCards,
            onCardTap: onRouteTap,
          ),
        ),
        const SizedBox(height: 16),
        const StudentFadeSlideIn(
          delayMs: 120,
          child: StudentSectionHeader(
            title: "Today Schedule",
            titleColor: Color(0xFFECE8FF),
          ),
        ),
        const SizedBox(height: 8),
        StudentFadeSlideIn(
          delayMs: 150,
          child: StudentTodaySchedulePanel(
            items: summary.todaySchedule,
            onTap: onRouteTap,
          ),
        ),
        const SizedBox(height: 16),
        StudentFadeSlideIn(
          delayMs: 190,
          child: StudentSectionHeader(
            title: "Announcements",
            actionLabel: "All Notifications",
            onActionTap: () => onRouteTap("/student/notifications"),
            titleColor: const Color(0xFFECE8FF),
            actionColor: const Color(0xFF9AB8FF),
          ),
        ),
        const SizedBox(height: 8),
        StudentFadeSlideIn(
          delayMs: 220,
          child: _AnnouncementList(
            items: summary.announcements,
            onTap: (id) => onRouteTap("/student/announcements/$id"),
          ),
        ),
        const SizedBox(height: 16),
        const StudentFadeSlideIn(
          delayMs: 250,
          child: StudentSectionHeader(
            title: "Quick Access",
            titleColor: Color(0xFFECE8FF),
          ),
        ),
        const SizedBox(height: 8),
        StudentFadeSlideIn(
          delayMs: 280,
          child: StudentQuickActionGrid(
            items: summary.quickActions,
            onTap: onRouteTap,
          ),
        ),
        const SizedBox(height: 16),
        StudentFadeSlideIn(
          delayMs: 310,
          child: StudentDoubtCtaCard(
            data: summary.doubtCta,
            onTap: () => onRouteTap(summary.doubtCta.route),
          ),
        ),
        const SizedBox(height: 16),
        const StudentFadeSlideIn(
          delayMs: 340,
          child: StudentSectionHeader(
            title: "Attendance & Holiday",
            titleColor: Color(0xFFECE8FF),
          ),
        ),
        const SizedBox(height: 8),
        StudentFadeSlideIn(
          delayMs: 370,
          child: StudentAttendanceHolidayRow(
            attendance: summary.attendance,
            holiday: summary.holiday,
            onAttendanceTap: () => onRouteTap("/student/attendance"),
            onHolidayTap: () => onRouteTap("/student/holidays"),
          ),
        ),
      ],
    );
  }
}

class _StudentBrandStrip extends StatelessWidget {
  const _StudentBrandStrip();

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
      child: Row(
        children: [
          const Icon(
            Icons.auto_awesome_rounded,
            size: 20,
            color: Colors.white,
          ),
          const SizedBox(width: 8),
          Text(
            "Adrika Smart App",
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  color: Colors.white,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 0.2,
                ),
          ),
        ],
      ),
    );
  }
}

class _AnnouncementList extends StatelessWidget {
  const _AnnouncementList({
    required this.items,
    required this.onTap,
  });

  final List<StudentAnnouncementItem> items;
  final ValueChanged<String> onTap;

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) {
      return Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.white.withValues(alpha: 0.10)),
          color: Colors.white.withValues(alpha: 0.04),
        ),
        child: Text(
          "No announcements yet. Important institute updates will appear here.",
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: const Color(0xFFC2BDDD),
              ),
        ),
      );
    }

    final topItems = items.take(4).toList(growable: false);

    return Column(
      children: topItems
          .map(
            (item) => Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: StudentAnnouncementCard(
                item: item,
                onTap: () => onTap(item.id),
              ),
            ),
          )
          .toList(growable: false),
    );
  }
}
