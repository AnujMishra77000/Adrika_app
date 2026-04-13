import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../../core/network/app_exception.dart";
import "../../auth/state/auth_controller.dart";
import "../data/student_api.dart";
import "../models/student_assessment_models.dart";
import "../models/student_models.dart";

Future<T> _withStudentSessionGuard<T>(
  Ref ref,
  Future<T> Function(String accessToken) run,
) async {
  final token = ref.read(authControllerProvider).accessToken;
  if (token == null || token.isEmpty) {
    throw StateError("Missing access token");
  }

  try {
    return await run(token);
  } on AppException catch (error) {
    if (error.statusCode == 401) {
      await ref.read(authControllerProvider.notifier).clearSessionLocal();
    }
    rethrow;
  }
}

DateTime? _parseDate(String value) {
  if (value.isEmpty) {
    return null;
  }
  return DateTime.tryParse(value)?.toLocal();
}

String _formatHourMinute(DateTime value) {
  final hour = value.hour.toString().padLeft(2, "0");
  final minute = value.minute.toString().padLeft(2, "0");
  return "$hour:$minute";
}

bool _isSameDay(DateTime a, DateTime b) {
  return a.year == b.year && a.month == b.month && a.day == b.day;
}

bool _isPracticeAssessmentType(String type) {
  return type == "daily_practice" || type == "subject_practice";
}

bool _isPendingAssessment(StudentAssessmentItem item) {
  return item.availability == "scheduled" || item.availability == "live";
}

final studentProfileProvider = FutureProvider<StudentProfile>((ref) async {
  return _withStudentSessionGuard(
    ref,
    (token) => ref.watch(studentApiProvider).fetchProfile(accessToken: token),
  );
});

final studentDashboardProvider = FutureProvider<StudentDashboard>((ref) async {
  return _withStudentSessionGuard(
    ref,
    (token) => ref.watch(studentApiProvider).fetchDashboard(accessToken: token),
  );
});

final studentNoticesProvider = FutureProvider<List<StudentNotice>>((ref) async {
  return _withStudentSessionGuard(
    ref,
    (token) => ref.watch(studentApiProvider).fetchNotices(accessToken: token),
  );
});

final studentHomeworkProvider =
    FutureProvider<List<StudentHomework>>((ref) async {
  return _withStudentSessionGuard(
    ref,
    (token) => ref.watch(studentApiProvider).fetchHomework(accessToken: token),
  );
});

Future<void> markStudentHomeworkReadAll(WidgetRef ref) async {
  final token = ref.read(authControllerProvider).accessToken;
  if (token == null || token.isEmpty) {
    throw StateError("Missing access token");
  }

  try {
    await ref.read(studentApiProvider).markHomeworkReadAll(accessToken: token);
  } on AppException catch (error) {
    if (error.statusCode == 401) {
      await ref.read(authControllerProvider.notifier).clearSessionLocal();
    }
    rethrow;
  }

  ref.invalidate(studentHomeworkProvider);
  ref.invalidate(studentDashboardProvider);
  ref.invalidate(studentHomeSummaryProvider);
  ref.invalidate(studentNotificationsProvider);
}

Future<void> submitStudentHomework(
  WidgetRef ref, {
  required String homeworkId,
  required String filePath,
  required String fileName,
  String? notes,
}) async {
  final token = ref.read(authControllerProvider).accessToken;
  if (token == null || token.isEmpty) {
    throw StateError('Missing access token');
  }

  try {
    await ref.read(studentApiProvider).submitHomework(
          accessToken: token,
          homeworkId: homeworkId,
          filePath: filePath,
          fileName: fileName,
          notes: notes,
        );
  } on AppException catch (error) {
    if (error.statusCode == 401) {
      await ref.read(authControllerProvider.notifier).clearSessionLocal();
    }
    rethrow;
  }

  ref.invalidate(studentHomeworkProvider);
  ref.invalidate(studentDashboardProvider);
  ref.invalidate(studentHomeSummaryProvider);
}

Future<String> startStudentAssessmentAttempt(
  WidgetRef ref, {
  required String assessmentId,
}) async {
  final token = ref.read(authControllerProvider).accessToken;
  if (token == null || token.isEmpty) {
    throw StateError("Missing access token");
  }

  try {
    final payload = await ref.read(studentApiProvider).startTestAttempt(
          accessToken: token,
          assessmentId: assessmentId,
        );
    final attemptId = payload["attempt_id"]?.toString() ?? "";
    if (attemptId.isEmpty) {
      throw StateError("Attempt id missing in response");
    }
    ref.invalidate(studentAssessmentAttemptDetailProvider(attemptId));
    return attemptId;
  } on AppException catch (error) {
    if (error.statusCode == 401) {
      await ref.read(authControllerProvider.notifier).clearSessionLocal();
    }
    rethrow;
  }
}

Future<void> saveStudentAssessmentAnswer(
  WidgetRef ref, {
  required String attemptId,
  required String questionId,
  required String selectedKey,
}) async {
  final token = ref.read(authControllerProvider).accessToken;
  if (token == null || token.isEmpty) {
    throw StateError("Missing access token");
  }

  try {
    await ref.read(studentApiProvider).saveTestAnswer(
          accessToken: token,
          attemptId: attemptId,
          questionId: questionId,
          selectedKey: selectedKey,
        );
  } on AppException catch (error) {
    if (error.statusCode == 401) {
      await ref.read(authControllerProvider.notifier).clearSessionLocal();
    }
    rethrow;
  }
}

Future<StudentAssessmentSubmitResult> submitStudentAssessmentAttempt(
  WidgetRef ref, {
  required String attemptId,
}) async {
  final token = ref.read(authControllerProvider).accessToken;
  if (token == null || token.isEmpty) {
    throw StateError("Missing access token");
  }

  try {
    final result = await ref.read(studentApiProvider).submitAttempt(
          accessToken: token,
          attemptId: attemptId,
        );
    ref.invalidate(studentAssessmentAttemptDetailProvider(attemptId));
    ref.invalidate(studentAssessmentsProvider);
    ref.invalidate(studentPracticeTestsProvider);
    ref.invalidate(studentOnlineTestsProvider);
    ref.invalidate(studentDashboardProvider);
    ref.invalidate(studentHomeSummaryProvider);
    ref.invalidate(studentNotificationsProvider);
    return result;
  } on AppException catch (error) {
    if (error.statusCode == 401) {
      await ref.read(authControllerProvider.notifier).clearSessionLocal();
    }
    rethrow;
  }
}

final studentAttendanceSummaryProvider =
    FutureProvider<Map<String, dynamic>>((ref) async {
  return _withStudentSessionGuard(
    ref,
    (token) => ref
        .watch(studentApiProvider)
        .fetchAttendanceSummary(accessToken: token),
  );
});

final studentNotificationsProvider =
    FutureProvider<List<StudentNotificationItem>>((ref) async {
  return _withStudentSessionGuard(
    ref,
    (token) =>
        ref.watch(studentApiProvider).fetchNotifications(accessToken: token),
  );
});

final studentAssessmentsProvider =
    FutureProvider<List<StudentAssessmentItem>>((ref) async {
  return _withStudentSessionGuard(
    ref,
    (token) => ref
        .watch(studentApiProvider)
        .fetchTests(accessToken: token, limit: 100),
  );
});

final studentPracticeTestsProvider =
    FutureProvider<List<StudentAssessmentItem>>((ref) async {
  final tests = await ref.watch(studentAssessmentsProvider.future);
  return tests
      .where((item) => _isPracticeAssessmentType(item.assessmentType))
      .toList(growable: false);
});

final studentOnlineTestsProvider =
    FutureProvider<List<StudentAssessmentItem>>((ref) async {
  final tests = await ref.watch(studentAssessmentsProvider.future);
  return tests
      .where((item) => item.assessmentType == "scheduled")
      .toList(growable: false);
});

final studentAssessmentDetailProvider =
    FutureProvider.family<StudentAssessmentDetail, String>(
        (ref, assessmentId) async {
  return _withStudentSessionGuard(
    ref,
    (token) => ref.watch(studentApiProvider).fetchTestDetail(
          accessToken: token,
          assessmentId: assessmentId,
        ),
  );
});

final studentAssessmentAttemptDetailProvider =
    FutureProvider.family<StudentAssessmentAttemptDetail, String>(
        (ref, attemptId) async {
  return _withStudentSessionGuard(
    ref,
    (token) => ref.watch(studentApiProvider).fetchAttemptDetail(
          accessToken: token,
          attemptId: attemptId,
        ),
  );
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
  return _withStudentSessionGuard(ref, (token) async {
    final api = ref.watch(studentApiProvider);

    final profileFuture = api.fetchProfile(accessToken: token);
    final dashboardFuture = api.fetchDashboard(accessToken: token);
    final noticesFuture = api.fetchNotices(accessToken: token, limit: 8);
    final notificationsFuture =
        api.fetchNotifications(accessToken: token, limit: 12);
    final attendanceFuture = api.fetchAttendanceSummary(accessToken: token);
    final homeworkFuture = api.fetchHomework(accessToken: token, limit: 20);
    final assessmentsFuture = api.fetchTests(accessToken: token, limit: 100);
    final scheduledLecturesFuture =
        api.fetchScheduledLectures(accessToken: token, limit: 100);

    final profile = await profileFuture;
    final dashboard = await dashboardFuture;
    final notices = await noticesFuture;
    final notifications = await notificationsFuture;
    final attendanceRaw = await attendanceFuture;
    final homework = await homeworkFuture;
    List<StudentAssessmentItem> assessments;
    try {
      assessments = await assessmentsFuture;
    } catch (_) {
      assessments = const <StudentAssessmentItem>[];
    }

    List<StudentScheduledLecture> scheduledLectures;
    try {
      scheduledLectures = await scheduledLecturesFuture;
    } catch (_) {
      scheduledLectures = const <StudentScheduledLecture>[];
    }

    final announcements =
        notices.map(StudentAnnouncementItem.fromNotice).toList(growable: false);

    final attendance = StudentAttendanceSummary.fromApi(
      attendanceRaw,
      dashboardAttendancePercent: dashboard.attendancePercentage,
    );

    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);

    final scheduledLectureItems = scheduledLectures
        .where((item) => item.status == 'scheduled')
        .where((item) => item.scheduledAt != null)
        .toList(growable: false)
      ..sort((a, b) =>
          (a.scheduledAt ?? now).compareTo(b.scheduledAt ?? now));

    final todayScheduledLectures = scheduledLectureItems
        .where((item) => _isSameDay(item.scheduledAt!, today))
        .toList(growable: false);

    final upcomingScheduledLectures = scheduledLectureItems
        .where((item) => item.scheduledAt!.isAfter(now))
        .toList(growable: false);

    final dueTodayHomework = homework.where((item) {
      final dueDate = _parseDate(item.dueDate);
      if (dueDate == null) {
        return false;
      }
      return _isSameDay(dueDate, today);
    }).toList(growable: false);

    final lectureAnchor = todayScheduledLectures.isNotEmpty
        ? todayScheduledLectures.first
        : (upcomingScheduledLectures.isNotEmpty
            ? upcomingScheduledLectures.first
            : null);

    final todayLectures = StudentLectureSummary(
      title: "Today Lectures",
      primaryValue: todayScheduledLectures.length.toString(),
      secondaryText: todayScheduledLectures.isEmpty
          ? "No lecture schedule synced yet"
          : "${todayScheduledLectures.first.topic} at ${_formatHourMinute(todayScheduledLectures.first.scheduledAt!)}",
      nextAt: lectureAnchor?.scheduledAt,
    );

    final upcomingLecture = StudentLectureSummary(
      title: "Upcoming Lecture",
      primaryValue: lectureAnchor == null
          ? "Pending"
          : (lectureAnchor.subjectName.isEmpty
              ? "Scheduled"
              : lectureAnchor.subjectName),
      secondaryText: lectureAnchor == null
          ? "Timetable will appear once published"
          : lectureAnchor.topic,
      nextAt: lectureAnchor?.scheduledAt,
    );

    final pendingPracticeTests = assessments
        .where(
          (item) =>
              _isPracticeAssessmentType(item.assessmentType) &&
              _isPendingAssessment(item),
        )
        .toList(growable: false);

    final pendingOnlineTests = assessments
        .where(
          (item) =>
              item.assessmentType == "scheduled" && _isPendingAssessment(item),
        )
        .toList(growable: false);

    final completedPracticeCount = assessments
        .where(
          (item) =>
              _isPracticeAssessmentType(item.assessmentType) &&
              item.isCompleted,
        )
        .length;

    final practiceAvailableCount = pendingPracticeTests.isNotEmpty
        ? pendingPracticeTests.length
        : dashboard.upcomingTestsCount;

    final practiceTest = StudentPracticeTestSummary(
      availableCount: practiceAvailableCount,
      attemptedToday: completedPracticeCount,
      hint: practiceAvailableCount > 0
          ? "You have tests waiting for practice"
          : "No active practice tests right now",
    );

    final progress = StudentProgressSummary(
      attendancePercent: attendance.attendancePercent,
      scorePercent: attendance.attendancePercent,
      trendLabel: attendance.attendancePercent >= 75
          ? "Steady learning momentum"
          : "Focus on attendance to improve outcomes",
    );

    final holidayDate = DateTime(now.year, now.month, now.day + 6);
    final holiday = StudentHolidaySummary(
      nextHolidayName: "Institute Holiday",
      date: holidayDate,
      subtitle: "Festival calendar sync is enabled",
    );

    final quickActions = <StudentQuickActionItem>[
      const StudentQuickActionItem(
        id: "notices",
        title: "Notices",
        route: "/student/notices",
        iconKey: "notice",
        accentColor: Color(0xFFF9B86A),
      ),
      const StudentQuickActionItem(
        id: "notes",
        title: "Notes",
        route: "/student/notes",
        iconKey: "notes",
        accentColor: Color(0xFFFF9CCB),
      ),
      StudentQuickActionItem(
        id: "homework",
        title: "Homework",
        route: "/student/homework",
        iconKey: "homework",
        accentColor: Color(0xFF89E2C4),
        badgeCount: dashboard.pendingHomeworkCount,
      ),
      StudentQuickActionItem(
        id: "online_test",
        title: "Online Test",
        route: "/student/online-tests",
        iconKey: "online_test",
        accentColor: Color(0xFF7FC7FF),
        badgeCount: pendingOnlineTests.length,
      ),
      StudentQuickActionItem(
        id: "practice_test",
        title: "Practice Test",
        route: "/student/practice-tests",
        iconKey: "practice",
        accentColor: Color(0xFFB6A4FF),
        badgeCount: practiceAvailableCount,
      ),
    ];

    const doubtCta = StudentDoubtCtaData(
      title: "Need help with a topic?",
      subtitle: "Raise a structured doubt and track every response.",
      actionLabel: "Raise Doubt",
      route: "/student/raise-doubt",
    );

    final scheduleItems = <StudentTodayScheduleItem>[];

    if (todayScheduledLectures.isNotEmpty) {
      for (final lecture in todayScheduledLectures.take(3)) {
        scheduleItems.add(
          StudentTodayScheduleItem(
            id: "schedule-lecture-${lecture.id}",
            kind: "Lecture",
            title: lecture.topic,
            subtitle: lecture.subjectName.isEmpty
                ? (lecture.teacherName.isEmpty ? "Lecture" : lecture.teacherName)
                : "${lecture.subjectName} • ${lecture.teacherName}",
            scheduledAt:
                lecture.scheduledAt ?? DateTime(now.year, now.month, now.day, 9, 0),
            route: "/student/lectures/today",
          ),
        );
      }
    } else if (upcomingScheduledLectures.isNotEmpty) {
      final lecture = upcomingScheduledLectures.first;
      scheduleItems.add(
        StudentTodayScheduleItem(
          id: "schedule-lecture-${lecture.id}",
          kind: "Lecture",
          title: lecture.topic,
          subtitle: lecture.subjectName.isEmpty
              ? (lecture.teacherName.isEmpty ? "Lecture" : lecture.teacherName)
              : "${lecture.subjectName} • ${lecture.teacherName}",
          scheduledAt:
              lecture.scheduledAt ?? DateTime(now.year, now.month, now.day, 9, 0),
          route: "/student/lectures/upcoming",
        ),
      );
    }

    if (pendingOnlineTests.isNotEmpty || practiceTest.availableCount > 0) {
      final nearestTest = (pendingOnlineTests + pendingPracticeTests)
        ..sort((a, b) {
          final aTime = a.startsAt ?? now;
          final bTime = b.startsAt ?? now;
          return aTime.compareTo(bTime);
        });

      final test = nearestTest.first;
      scheduleItems.add(
        StudentTodayScheduleItem(
          id: "schedule-test",
          kind: "Test",
          title: test.title,
          subtitle: test.topic ??
              "${pendingOnlineTests.length + pendingPracticeTests.length} tests waiting",
          scheduledAt:
              test.startsAt ?? DateTime(now.year, now.month, now.day, 14, 30),
          route: test.assessmentType == "scheduled"
              ? "/student/online-tests"
              : "/student/practice-tests",
        ),
      );
    }

    for (var index = 0; index < dueTodayHomework.length; index++) {
      final task = dueTodayHomework[index];
      final parsed = _parseDate(task.dueDate);
      final fallback = DateTime(now.year, now.month, now.day, 18 + (index % 3));
      scheduleItems.add(
        StudentTodayScheduleItem(
          id: "schedule-homework-${task.id}",
          kind: "Homework",
          title: task.title,
          subtitle: task.status.isEmpty
              ? "Complete before day end"
              : "Status: ${task.status}",
          scheduledAt: parsed ?? fallback,
          route: "/student/homework",
        ),
      );
    }

    scheduleItems.sort((a, b) => a.scheduledAt.compareTo(b.scheduledAt));

    if (scheduleItems.isEmpty) {
      scheduleItems.add(
        StudentTodayScheduleItem(
          id: "schedule-empty",
          kind: "Info",
          title: "No pending tasks right now",
          subtitle: "Fresh schedule entries will appear here automatically",
          scheduledAt: now.add(const Duration(hours: 1)),
          route: "/student/lectures/today",
        ),
      );
    }

    return StudentHomeSummary(
      profile: profile,
      dashboard: dashboard,
      notifications: notifications,
      scheduledLectures: scheduledLectures,
      announcements: announcements,
      todayLectures: todayLectures,
      upcomingLecture: upcomingLecture,
      practiceTest: practiceTest,
      progress: progress,
      attendance: attendance,
      holiday: holiday,
      quickActions: quickActions,
      todaySchedule: scheduleItems.take(7).toList(growable: false),
      doubtCta: doubtCta,
    );
  });
});

final studentNoticeDetailProvider =
    FutureProvider.family<StudentNoticeDetail, String>((ref, id) async {
  return _withStudentSessionGuard(
    ref,
    (token) => ref.watch(studentApiProvider).fetchNoticeDetail(
          accessToken: token,
          noticeId: id,
        ),
  );
});

final studentHomeworkDetailProvider =
    FutureProvider.family<StudentHomework, String>((ref, id) async {
  return _withStudentSessionGuard(
    ref,
    (token) => ref.watch(studentApiProvider).fetchHomeworkDetail(
          accessToken: token,
          homeworkId: id,
        ),
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
  final detail = await ref.watch(studentNoticeDetailProvider(id).future);
  return StudentAnnouncementItem(
    id: detail.id,
    title: detail.title,
    previewText: detail.body,
    body: detail.body,
    timestamp: detail.publishAt,
    isRead: detail.isRead,
    source: 'notice',
  );
});
