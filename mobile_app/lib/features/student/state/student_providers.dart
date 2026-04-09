import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../auth/state/auth_controller.dart';
import '../data/student_api.dart';
import '../models/student_models.dart';

String _requireAccessToken(Ref ref) {
  final token = ref.watch(authControllerProvider).accessToken;
  if (token == null || token.isEmpty) {
    throw StateError('Missing access token');
  }
  return token;
}

DateTime? _parseDate(String value) {
  if (value.isEmpty) {
    return null;
  }
  return DateTime.tryParse(value)?.toLocal();
}

final studentProfileProvider = FutureProvider<StudentProfile>((ref) async {
  final token = _requireAccessToken(ref);
  return ref.watch(studentApiProvider).fetchProfile(accessToken: token);
});

final studentDashboardProvider = FutureProvider<StudentDashboard>((ref) async {
  final token = _requireAccessToken(ref);
  return ref.watch(studentApiProvider).fetchDashboard(accessToken: token);
});

final studentNoticesProvider = FutureProvider<List<StudentNotice>>((ref) async {
  final token = _requireAccessToken(ref);
  return ref.watch(studentApiProvider).fetchNotices(accessToken: token);
});

final studentHomeworkProvider =
    FutureProvider<List<StudentHomework>>((ref) async {
  final token = _requireAccessToken(ref);
  return ref.watch(studentApiProvider).fetchHomework(accessToken: token);
});

final studentAttendanceSummaryProvider =
    FutureProvider<Map<String, dynamic>>((ref) async {
  final token = _requireAccessToken(ref);
  return ref
      .watch(studentApiProvider)
      .fetchAttendanceSummary(accessToken: token);
});

final studentNotificationsProvider =
    FutureProvider<List<StudentNotificationItem>>((ref) async {
  final token = _requireAccessToken(ref);
  return ref.watch(studentApiProvider).fetchNotifications(accessToken: token);
});

final studentAnnouncementsProvider =
    FutureProvider<List<StudentAnnouncementItem>>((ref) async {
  final notices = await ref.watch(studentNoticesProvider.future);
  return notices
      .map(StudentAnnouncementItem.fromNotice)
      .toList(growable: false);
});

final studentHomeSummaryProvider =
    FutureProvider<StudentHomeSummary>((ref) async {
  final token = _requireAccessToken(ref);
  final api = ref.watch(studentApiProvider);

  final profileFuture = api.fetchProfile(accessToken: token);
  final dashboardFuture = api.fetchDashboard(accessToken: token);
  final noticesFuture = api.fetchNotices(accessToken: token, limit: 8);
  final notificationsFuture =
      api.fetchNotifications(accessToken: token, limit: 12);
  final attendanceFuture = api.fetchAttendanceSummary(accessToken: token);
  final homeworkFuture = api.fetchHomework(accessToken: token, limit: 20);

  final profile = await profileFuture;
  final dashboard = await dashboardFuture;
  final notices = await noticesFuture;
  final notifications = await notificationsFuture;
  final attendanceRaw = await attendanceFuture;
  final homework = await homeworkFuture;

  final announcements =
      notices.map(StudentAnnouncementItem.fromNotice).toList(growable: false);

  final attendance = StudentAttendanceSummary.fromApi(
    attendanceRaw,
    dashboardAttendancePercent: dashboard.attendancePercentage,
  );

  final now = DateTime.now();
  final today = DateTime(now.year, now.month, now.day);

  final dueTodayCount = homework.where((item) {
    final dueDate = _parseDate(item.dueDate);
    if (dueDate == null) {
      return false;
    }
    return dueDate.year == today.year &&
        dueDate.month == today.month &&
        dueDate.day == today.day;
  }).length;

  final upcomingHomework = homework
      .map((item) => _parseDate(item.dueDate))
      .whereType<DateTime>()
      .where((date) => date.isAfter(today))
      .toList()
    ..sort((a, b) => a.compareTo(b));

  final todayLectures = StudentLectureSummary(
    title: 'Today\'s Lectures',
    primaryValue: dueTodayCount.toString(),
    secondaryText: dueTodayCount == 0
        ? 'No lecture schedule synced yet'
        : '$dueTodayCount sessions planned today',
    nextAt: dueTodayCount == 0 ? null : now.add(const Duration(hours: 2)),
  );

  final upcomingLecture = StudentLectureSummary(
    title: 'Upcoming Lecture',
    primaryValue: upcomingHomework.isNotEmpty ? 'Scheduled' : 'Pending',
    secondaryText: upcomingHomework.isNotEmpty
        ? 'Next academic item is lined up'
        : 'Timetable will appear once published',
    nextAt: upcomingHomework.isNotEmpty ? upcomingHomework.first : null,
  );

  final practiceTest = StudentPracticeTestSummary(
    availableCount: dashboard.upcomingTestsCount,
    attemptedToday: 0,
    hint: dashboard.upcomingTestsCount > 0
        ? 'You have tests waiting for practice'
        : 'No active practice tests right now',
  );

  final progress = StudentProgressSummary(
    attendancePercent: attendance.attendancePercent,
    scorePercent: attendance.attendancePercent,
    trendLabel: attendance.attendancePercent >= 75
        ? 'Steady learning momentum'
        : 'Focus on attendance to improve outcomes',
  );

  final holidayDate = DateTime(now.year, now.month, now.day + 6);
  final holiday = StudentHolidaySummary(
    nextHolidayName: 'Institute Holiday',
    date: holidayDate,
    subtitle: 'Festival calendar sync is enabled',
  );

  final quickActions = <StudentQuickActionItem>[
    const StudentQuickActionItem(
      id: 'notes',
      title: 'Notes',
      route: '/student/notes',
      iconKey: 'notes',
      accentColor: Color(0xFFFF9CCB),
    ),
    const StudentQuickActionItem(
      id: 'homework',
      title: 'Homework',
      route: '/student/homework',
      iconKey: 'homework',
      accentColor: Color(0xFF89E2C4),
    ),
    const StudentQuickActionItem(
      id: 'online_test',
      title: 'Online Test',
      route: '/student/online-tests',
      iconKey: 'online_test',
      accentColor: Color(0xFF7FC7FF),
    ),
    const StudentQuickActionItem(
      id: 'practice_test',
      title: 'Practice Test',
      route: '/student/practice-tests',
      iconKey: 'practice',
      accentColor: Color(0xFFB6A4FF),
    ),
    const StudentQuickActionItem(
      id: 'chat',
      title: 'Chat App',
      route: '/student/chat',
      iconKey: 'chat',
      accentColor: Color(0xFF98C9FF),
    ),
  ];

  const doubtCta = StudentDoubtCtaData(
    title: 'Need help with a topic?',
    subtitle: 'Raise a structured doubt and track every response.',
    actionLabel: 'Raise Doubt',
    route: '/student/raise-doubt',
  );

  return StudentHomeSummary(
    profile: profile,
    dashboard: dashboard,
    notifications: notifications,
    announcements: announcements,
    todayLectures: todayLectures,
    upcomingLecture: upcomingLecture,
    practiceTest: practiceTest,
    progress: progress,
    attendance: attendance,
    holiday: holiday,
    quickActions: quickActions,
    doubtCta: doubtCta,
  );
});

final studentNotificationDetailProvider =
    FutureProvider.family<StudentNotificationItem?, String>((ref, id) async {
  final items = await ref.watch(studentNotificationsProvider.future);
  for (final item in items) {
    if (item.id == id) {
      return item;
    }
  }
  return null;
});

final studentAnnouncementDetailProvider =
    FutureProvider.family<StudentAnnouncementItem?, String>((ref, id) async {
  final items = await ref.watch(studentAnnouncementsProvider.future);
  for (final item in items) {
    if (item.id == id) {
      return item;
    }
  }
  return null;
});
