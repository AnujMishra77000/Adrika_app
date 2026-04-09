import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../models/student_models.dart';
import '../state/student_providers.dart';
import 'widgets/student_announcement_card.dart';
import 'widgets/student_attendance_holiday_row.dart';
import 'widgets/student_doubt_cta_card.dart';
import 'widgets/student_fade_slide_in.dart';
import 'widgets/student_hero_banner.dart';
import 'widgets/student_home_header.dart';
import 'widgets/student_home_palette.dart';
import 'widgets/student_home_states.dart';
import 'widgets/student_quick_action_grid.dart';
import 'widgets/student_section_header.dart';

class StudentDashboardScreen extends ConsumerWidget {
  const StudentDashboardScreen({super.key});

  Future<void> _refresh(WidgetRef ref) async {
    ref.invalidate(studentHomeSummaryProvider);
    ref.invalidate(studentNotificationsProvider);
    ref.invalidate(studentAnnouncementsProvider);
    await ref.read(studentHomeSummaryProvider.future);
  }

  String _firstName(String fullName) {
    final segments = fullName.trim().split(RegExp(r'\s+'));
    if (segments.isEmpty) {
      return 'Student';
    }
    return segments.first;
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final summaryAsync = ref.watch(studentHomeSummaryProvider);

    return SafeArea(
      top: true,
      bottom: false,
      child: DecoratedBox(
        decoration: const BoxDecoration(
          color: StudentHomePalette.pageBackground,
        ),
        child: RefreshIndicator(
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
              onRouteTap: (route) => context.push(route),
            ),
          ),
        ),
      ),
    );
  }
}

class _StudentHomeBody extends StatelessWidget {
  const _StudentHomeBody({
    required this.summary,
    required this.greetingName,
    required this.onRouteTap,
  });

  final StudentHomeSummary summary;
  final String greetingName;
  final ValueChanged<String> onRouteTap;

  @override
  Widget build(BuildContext context) {
    final heroCards = <StudentHeroCardData>[
      StudentHeroCardData(
        title: 'Today\'s Lectures',
        value: summary.todayLectures.primaryValue,
        subtitle: 'Academic plan',
        route: '/student/lectures/today',
        icon: Icons.menu_book_outlined,
        accent: StudentHomePalette.accentGreen,
      ),
      StudentHeroCardData(
        title: 'Upcoming Lecture',
        value: summary.upcomingLecture.primaryValue,
        subtitle: 'Next schedule',
        route: '/student/lectures/upcoming',
        icon: Icons.schedule_outlined,
        accent: StudentHomePalette.accentBlue,
      ),
      StudentHeroCardData(
        title: 'Practice Test',
        value: summary.practiceTest.availableCount.toString(),
        subtitle: 'Open now',
        route: '/student/practice-tests',
        icon: Icons.quiz_outlined,
        accent: StudentHomePalette.accentPink,
      ),
      StudentHeroCardData(
        title: 'Progress',
        value: '${summary.progress.attendancePercent.toStringAsFixed(1)}%',
        subtitle: 'Current track',
        route: '/student/progress',
        icon: Icons.auto_graph_outlined,
        accent: StudentHomePalette.accentPurple,
      ),
    ];

    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 20),
      children: [
        StudentFadeSlideIn(
          delayMs: 40,
          child: StudentHomeHeader(
            greeting: 'Hello, $greetingName',
            subtitle: 'Keep your momentum high for today.',
            unreadCount: summary.unreadNotificationCount,
            onNotificationTap: () => onRouteTap('/student/notifications'),
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
        StudentFadeSlideIn(
          delayMs: 140,
          child: StudentSectionHeader(
            title: 'Announcements',
            actionLabel: 'All Notifications',
            onActionTap: () => onRouteTap('/student/notifications'),
          ),
        ),
        const SizedBox(height: 8),
        StudentFadeSlideIn(
          delayMs: 170,
          child: _AnnouncementList(
            items: summary.announcements,
            onTap: (id) => onRouteTap('/student/announcements/$id'),
          ),
        ),
        const SizedBox(height: 16),
        StudentFadeSlideIn(
          delayMs: 210,
          child: const StudentSectionHeader(
            title: 'Quick Access',
          ),
        ),
        const SizedBox(height: 8),
        StudentFadeSlideIn(
          delayMs: 240,
          child: StudentQuickActionGrid(
            items: summary.quickActions,
            onTap: onRouteTap,
          ),
        ),
        const SizedBox(height: 16),
        StudentFadeSlideIn(
          delayMs: 280,
          child: StudentDoubtCtaCard(
            data: summary.doubtCta,
            onTap: () => onRouteTap(summary.doubtCta.route),
          ),
        ),
        const SizedBox(height: 16),
        StudentFadeSlideIn(
          delayMs: 320,
          child: const StudentSectionHeader(
            title: 'Attendance & Holiday',
          ),
        ),
        const SizedBox(height: 8),
        StudentFadeSlideIn(
          delayMs: 350,
          child: StudentAttendanceHolidayRow(
            attendance: summary.attendance,
            holiday: summary.holiday,
            onAttendanceTap: () => onRouteTap('/student/attendance'),
            onHolidayTap: () => onRouteTap('/student/holidays'),
          ),
        ),
      ],
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
      return const StudentHomeEmptyState(
        title: 'No announcements yet',
        subtitle: 'Important institute updates will appear here.',
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
