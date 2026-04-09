import 'package:flutter/material.dart';

num _toNum(dynamic value) {
  if (value is num) {
    return value;
  }
  return num.tryParse(value?.toString() ?? '') ?? 0;
}

bool _toBool(dynamic value, {bool fallback = false}) {
  if (value is bool) {
    return value;
  }
  if (value is String) {
    return value.toLowerCase() == 'true';
  }
  return fallback;
}

DateTime? _toDate(dynamic value) {
  if (value is DateTime) {
    return value;
  }
  if (value == null) {
    return null;
  }
  return DateTime.tryParse(value.toString())?.toLocal();
}

String _toStringValue(dynamic value, {String fallback = ''}) {
  if (value == null) {
    return fallback;
  }
  return value.toString();
}

class StudentProfile {
  final String studentId;
  final String userId;
  final String fullName;
  final String admissionNo;
  final String rollNo;

  const StudentProfile({
    required this.studentId,
    required this.userId,
    required this.fullName,
    required this.admissionNo,
    required this.rollNo,
  });

  factory StudentProfile.fromJson(Map<String, dynamic> json) {
    return StudentProfile(
      studentId: json['student_id']?.toString() ?? '',
      userId: json['user_id']?.toString() ?? '',
      fullName: json['full_name']?.toString() ?? '',
      admissionNo: json['admission_no']?.toString() ?? '',
      rollNo: json['roll_no']?.toString() ?? '',
    );
  }
}

class StudentDashboard {
  final int unreadNotifications;
  final int pendingHomeworkCount;
  final double attendancePercentage;
  final int upcomingTestsCount;

  const StudentDashboard({
    required this.unreadNotifications,
    required this.pendingHomeworkCount,
    required this.attendancePercentage,
    required this.upcomingTestsCount,
  });

  factory StudentDashboard.fromJson(Map<String, dynamic> json) {
    return StudentDashboard(
      unreadNotifications: _toNum(json['unread_notifications']).toInt(),
      pendingHomeworkCount: _toNum(json['pending_homework_count']).toInt(),
      attendancePercentage: _toNum(json['attendance_percentage']).toDouble(),
      upcomingTestsCount: _toNum(json['upcoming_tests_count']).toInt(),
    );
  }
}

class StudentNotice {
  final String id;
  final String title;
  final String bodyPreview;
  final String? publishAt;
  final bool isRead;

  const StudentNotice({
    required this.id,
    required this.title,
    required this.bodyPreview,
    required this.publishAt,
    required this.isRead,
  });

  factory StudentNotice.fromJson(Map<String, dynamic> json) {
    return StudentNotice(
      id: json['id']?.toString() ?? '',
      title: json['title']?.toString() ?? '',
      bodyPreview: json['body_preview']?.toString() ?? '',
      publishAt: json['publish_at']?.toString(),
      isRead: _toBool(json['is_read']),
    );
  }
}

class StudentHomework {
  final String id;
  final String title;
  final String description;
  final String dueDate;
  final String status;

  const StudentHomework({
    required this.id,
    required this.title,
    required this.description,
    required this.dueDate,
    required this.status,
  });

  factory StudentHomework.fromJson(Map<String, dynamic> json) {
    return StudentHomework(
      id: json['id']?.toString() ?? '',
      title: json['title']?.toString() ?? '',
      description: json['description']?.toString() ?? '',
      dueDate: json['due_date']?.toString() ?? '',
      status: json['status']?.toString() ?? '',
    );
  }
}

class StudentNotificationItem {
  final String id;
  final String title;
  final String previewText;
  final String body;
  final DateTime? timestamp;
  final bool isRead;
  final String source;

  const StudentNotificationItem({
    required this.id,
    required this.title,
    required this.previewText,
    required this.body,
    required this.timestamp,
    required this.isRead,
    required this.source,
  });

  factory StudentNotificationItem.fromJson(Map<String, dynamic> json) {
    final rawBody = _toStringValue(json['body']);
    final preview = _toStringValue(
      json['body_preview'],
      fallback: rawBody,
    ).trim();

    return StudentNotificationItem(
      id: _toStringValue(json['id']),
      title: _toStringValue(json['title'], fallback: 'Notification'),
      previewText: preview,
      body: rawBody.isEmpty ? preview : rawBody,
      timestamp: _toDate(json['created_at'] ?? json['publish_at']),
      isRead: _toBool(json['is_read']),
      source: _toStringValue(json['source'], fallback: 'system'),
    );
  }

  factory StudentNotificationItem.fromNotice(StudentNotice notice) {
    return StudentNotificationItem(
      id: notice.id,
      title: notice.title,
      previewText: notice.bodyPreview,
      body: notice.bodyPreview,
      timestamp: _toDate(notice.publishAt),
      isRead: notice.isRead,
      source: 'notice',
    );
  }
}

class StudentAnnouncementItem {
  final String id;
  final String title;
  final String previewText;
  final String body;
  final DateTime? timestamp;
  final bool isRead;
  final String source;

  const StudentAnnouncementItem({
    required this.id,
    required this.title,
    required this.previewText,
    required this.body,
    required this.timestamp,
    required this.isRead,
    required this.source,
  });

  factory StudentAnnouncementItem.fromJson(Map<String, dynamic> json) {
    final rawBody = _toStringValue(json['body']);
    final preview = _toStringValue(
      json['body_preview'],
      fallback: rawBody,
    ).trim();

    return StudentAnnouncementItem(
      id: _toStringValue(json['id']),
      title: _toStringValue(json['title'], fallback: 'Announcement'),
      previewText: preview,
      body: rawBody.isEmpty ? preview : rawBody,
      timestamp: _toDate(json['publish_at'] ?? json['created_at']),
      isRead: _toBool(json['is_read']),
      source: _toStringValue(json['source'], fallback: 'notice'),
    );
  }

  factory StudentAnnouncementItem.fromNotice(StudentNotice notice) {
    return StudentAnnouncementItem(
      id: notice.id,
      title: notice.title,
      previewText: notice.bodyPreview,
      body: notice.bodyPreview,
      timestamp: _toDate(notice.publishAt),
      isRead: notice.isRead,
      source: 'notice',
    );
  }
}

class StudentLectureSummary {
  final String title;
  final String primaryValue;
  final String secondaryText;
  final DateTime? nextAt;

  const StudentLectureSummary({
    required this.title,
    required this.primaryValue,
    required this.secondaryText,
    required this.nextAt,
  });
}

class StudentPracticeTestSummary {
  final int availableCount;
  final int attemptedToday;
  final String hint;

  const StudentPracticeTestSummary({
    required this.availableCount,
    required this.attemptedToday,
    required this.hint,
  });
}

class StudentProgressSummary {
  final double attendancePercent;
  final double scorePercent;
  final String trendLabel;

  const StudentProgressSummary({
    required this.attendancePercent,
    required this.scorePercent,
    required this.trendLabel,
  });
}

class StudentAttendanceSummary {
  final int presentCount;
  final int absentCount;
  final int lateCount;
  final double attendancePercent;

  const StudentAttendanceSummary({
    required this.presentCount,
    required this.absentCount,
    required this.lateCount,
    required this.attendancePercent,
  });

  factory StudentAttendanceSummary.fromApi(
    Map<String, dynamic> json, {
    required double dashboardAttendancePercent,
  }) {
    final present = _toNum(json['present_count']).toInt();
    final absent = _toNum(json['absent_count']).toInt();
    final late = _toNum(json['late_count']).toInt();
    final total = present + absent + late;

    final computedPercent = total == 0 ? 0.0 : (present / total) * 100;

    return StudentAttendanceSummary(
      presentCount: present,
      absentCount: absent,
      lateCount: late,
      attendancePercent: dashboardAttendancePercent > 0
          ? dashboardAttendancePercent
          : computedPercent,
    );
  }
}

class StudentHolidaySummary {
  final String nextHolidayName;
  final DateTime? date;
  final String subtitle;

  const StudentHolidaySummary({
    required this.nextHolidayName,
    required this.date,
    required this.subtitle,
  });
}

class StudentQuickActionItem {
  final String id;
  final String title;
  final String route;
  final String iconKey;
  final Color accentColor;

  const StudentQuickActionItem({
    required this.id,
    required this.title,
    required this.route,
    required this.iconKey,
    required this.accentColor,
  });
}

class StudentDoubtCtaData {
  final String title;
  final String subtitle;
  final String actionLabel;
  final String route;

  const StudentDoubtCtaData({
    required this.title,
    required this.subtitle,
    required this.actionLabel,
    required this.route,
  });
}

class StudentHomeSummary {
  final StudentProfile profile;
  final StudentDashboard dashboard;
  final List<StudentNotificationItem> notifications;
  final List<StudentAnnouncementItem> announcements;
  final StudentLectureSummary todayLectures;
  final StudentLectureSummary upcomingLecture;
  final StudentPracticeTestSummary practiceTest;
  final StudentProgressSummary progress;
  final StudentAttendanceSummary attendance;
  final StudentHolidaySummary holiday;
  final List<StudentQuickActionItem> quickActions;
  final StudentDoubtCtaData doubtCta;

  const StudentHomeSummary({
    required this.profile,
    required this.dashboard,
    required this.notifications,
    required this.announcements,
    required this.todayLectures,
    required this.upcomingLecture,
    required this.practiceTest,
    required this.progress,
    required this.attendance,
    required this.holiday,
    required this.quickActions,
    required this.doubtCta,
  });

  int get unreadNotificationCount {
    final unreadFromList = notifications.where((item) => !item.isRead).length;
    if (unreadFromList > 0) {
      return unreadFromList;
    }
    return dashboard.unreadNotifications;
  }
}
