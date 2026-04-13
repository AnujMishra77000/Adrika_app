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
  final String? photoUrl;

  const StudentProfile({
    required this.studentId,
    required this.userId,
    required this.fullName,
    required this.admissionNo,
    required this.rollNo,
    this.photoUrl,
  });

  factory StudentProfile.fromJson(Map<String, dynamic> json) {
    final photo = _toStringValue(
      json["photo_url"] ?? json["profile_photo_url"] ?? json["avatar_url"],
    );

    return StudentProfile(
      studentId: json['student_id']?.toString() ?? '',
      userId: json['user_id']?.toString() ?? '',
      fullName: json['full_name']?.toString() ?? '',
      admissionNo: json['admission_no']?.toString() ?? '',
      rollNo: json['roll_no']?.toString() ?? '',
      photoUrl: photo.isEmpty ? null : photo,
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
  final int attachmentCount;

  const StudentNotice({
    required this.id,
    required this.title,
    required this.bodyPreview,
    required this.publishAt,
    required this.isRead,
    required this.attachmentCount,
  });

  factory StudentNotice.fromJson(Map<String, dynamic> json) {
    return StudentNotice(
      id: json['id']?.toString() ?? '',
      title: json['title']?.toString() ?? '',
      bodyPreview: json['body_preview']?.toString() ?? '',
      publishAt: json['publish_at']?.toString(),
      isRead: _toBool(json['is_read']),
      attachmentCount: _toNum(json['attachment_count']).toInt(),
    );
  }
}

class StudentNoticeAttachment {
  final String id;
  final String attachmentType;
  final String fileName;
  final String fileUrl;
  final String contentType;
  final int fileSizeBytes;
  final int? imageWidth;
  final int? imageHeight;

  const StudentNoticeAttachment({
    required this.id,
    required this.attachmentType,
    required this.fileName,
    required this.fileUrl,
    required this.contentType,
    required this.fileSizeBytes,
    required this.imageWidth,
    required this.imageHeight,
  });

  factory StudentNoticeAttachment.fromJson(Map<String, dynamic> json) {
    return StudentNoticeAttachment(
      id: _toStringValue(json['id']),
      attachmentType: _toStringValue(json['attachment_type']),
      fileName: _toStringValue(json['file_name']),
      fileUrl: _toStringValue(json['file_url']),
      contentType: _toStringValue(json['content_type']),
      fileSizeBytes: _toNum(json['file_size_bytes']).toInt(),
      imageWidth: json['image_width'] == null
          ? null
          : _toNum(json['image_width']).toInt(),
      imageHeight: json['image_height'] == null
          ? null
          : _toNum(json['image_height']).toInt(),
    );
  }
}

class StudentNoticeDetail {
  final String id;
  final String title;
  final String body;
  final DateTime? publishAt;
  final bool isRead;
  final List<StudentNoticeAttachment> attachments;

  const StudentNoticeDetail({
    required this.id,
    required this.title,
    required this.body,
    required this.publishAt,
    required this.isRead,
    required this.attachments,
  });

  factory StudentNoticeDetail.fromJson(Map<String, dynamic> json) {
    final rawAttachments = json['attachments'] as List<dynamic>? ?? <dynamic>[];

    return StudentNoticeDetail(
      id: _toStringValue(json['id']),
      title: _toStringValue(json['title'], fallback: 'Notice'),
      body: _toStringValue(json['body']),
      publishAt: _toDate(json['publish_at']),
      isRead: _toBool(json['is_read']),
      attachments: rawAttachments
          .map(
            (item) => StudentNoticeAttachment.fromJson(
              item as Map<String, dynamic>,
            ),
          )
          .toList(growable: false),
    );
  }
}

class StudentHomeworkAttachment {
  final String id;
  final String attachmentType;
  final String fileName;
  final String fileUrl;
  final String contentType;
  final int fileSizeBytes;
  final bool isGenerated;

  const StudentHomeworkAttachment({
    required this.id,
    required this.attachmentType,
    required this.fileName,
    required this.fileUrl,
    required this.contentType,
    required this.fileSizeBytes,
    required this.isGenerated,
  });

  factory StudentHomeworkAttachment.fromJson(Map<String, dynamic> json) {
    return StudentHomeworkAttachment(
      id: _toStringValue(json['id']),
      attachmentType: _toStringValue(json['attachment_type']),
      fileName: _toStringValue(json['file_name']),
      fileUrl: _toStringValue(json['file_url']),
      contentType: _toStringValue(json['content_type']),
      fileSizeBytes: _toNum(json['file_size_bytes']).toInt(),
      isGenerated: _toBool(json['is_generated']),
    );
  }
}

class StudentHomeworkSubmissionAttachment {
  final String id;
  final String fileName;
  final String fileUrl;
  final String contentType;
  final int fileSizeBytes;

  const StudentHomeworkSubmissionAttachment({
    required this.id,
    required this.fileName,
    required this.fileUrl,
    required this.contentType,
    required this.fileSizeBytes,
  });

  factory StudentHomeworkSubmissionAttachment.fromJson(
    Map<String, dynamic> json,
  ) {
    return StudentHomeworkSubmissionAttachment(
      id: _toStringValue(json['id']),
      fileName: _toStringValue(json['file_name']),
      fileUrl: _toStringValue(json['file_url']),
      contentType: _toStringValue(json['content_type']),
      fileSizeBytes: _toNum(json['file_size_bytes']).toInt(),
    );
  }
}

class StudentHomeworkSubmission {
  final String id;
  final String status;
  final DateTime? submittedAt;
  final String? notes;
  final List<StudentHomeworkSubmissionAttachment> attachments;

  const StudentHomeworkSubmission({
    required this.id,
    required this.status,
    required this.submittedAt,
    required this.notes,
    required this.attachments,
  });

  factory StudentHomeworkSubmission.fromJson(Map<String, dynamic> json) {
    final rawAttachments = json['attachments'] as List<dynamic>? ?? <dynamic>[];
    final notes = _toStringValue(json['notes']).trim();

    return StudentHomeworkSubmission(
      id: _toStringValue(json['id']),
      status: _toStringValue(json['status']),
      submittedAt: _toDate(json['submitted_at']),
      notes: notes.isEmpty ? null : notes,
      attachments: rawAttachments
          .map(
            (item) => StudentHomeworkSubmissionAttachment.fromJson(
              item as Map<String, dynamic>,
            ),
          )
          .toList(growable: false),
    );
  }
}

class StudentHomework {
  final String id;
  final String title;
  final String description;
  final String dueDate;
  final DateTime? dueAt;
  final DateTime? expiresAt;
  final String status;
  final bool isRead;
  final int attachmentCount;
  final List<StudentHomeworkAttachment> attachments;
  final bool isSubmitted;
  final StudentHomeworkSubmission? submission;

  const StudentHomework({
    required this.id,
    required this.title,
    required this.description,
    required this.dueDate,
    required this.dueAt,
    required this.expiresAt,
    required this.status,
    required this.isRead,
    required this.attachmentCount,
    required this.attachments,
    required this.isSubmitted,
    required this.submission,
  });

  factory StudentHomework.fromJson(Map<String, dynamic> json) {
    final rawAttachments = json['attachments'] as List<dynamic>? ?? <dynamic>[];
    final submissionRaw = json['submission'];
    final submission = submissionRaw is Map<String, dynamic>
        ? StudentHomeworkSubmission.fromJson(submissionRaw)
        : null;

    return StudentHomework(
      id: _toStringValue(json['id']),
      title: _toStringValue(json['title']),
      description: _toStringValue(json['description']),
      dueDate: _toStringValue(json['due_date']),
      dueAt: _toDate(json['due_at']),
      expiresAt: _toDate(json['expires_at']),
      status: _toStringValue(json['status']),
      isRead: _toBool(json['is_read']),
      attachmentCount: _toNum(json['attachment_count']).toInt(),
      attachments: rawAttachments
          .map(
            (item) => StudentHomeworkAttachment.fromJson(
              item as Map<String, dynamic>,
            ),
          )
          .toList(growable: false),
      isSubmitted: _toBool(json['is_submitted'], fallback: submission != null),
      submission: submission,
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
  final String? noticeId;

  const StudentNotificationItem({
    required this.id,
    required this.title,
    required this.previewText,
    required this.body,
    required this.timestamp,
    required this.isRead,
    required this.source,
    required this.noticeId,
  });

  factory StudentNotificationItem.fromJson(Map<String, dynamic> json) {
    final rawBody = _toStringValue(json['body']);
    final preview = _toStringValue(
      json['body_preview'],
      fallback: rawBody,
    ).trim();
    final metadata = json['metadata'] is Map<String, dynamic>
        ? json['metadata'] as Map<String, dynamic>
        : <String, dynamic>{};

    return StudentNotificationItem(
      id: _toStringValue(json['id']),
      title: _toStringValue(json['title'], fallback: 'Notification'),
      previewText: preview,
      body: rawBody.isEmpty ? preview : rawBody,
      timestamp: _toDate(json['created_at'] ?? json['publish_at']),
      isRead: _toBool(json['is_read']),
      source: _toStringValue(json['source'], fallback: 'system'),
      noticeId: _toStringValue(
        json['notice_id'] ?? metadata['notice_id'],
      ).trim().isEmpty
          ? null
          : _toStringValue(json['notice_id'] ?? metadata['notice_id']),
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
      noticeId: notice.id,
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

class StudentScheduledLecture {
  final String id;
  final int classLevel;
  final String stream;
  final String subjectId;
  final String subjectName;
  final String teacherId;
  final String teacherName;
  final String topic;
  final String lectureNotes;
  final DateTime? scheduledAt;
  final String status;
  final DateTime? completedAt;

  const StudentScheduledLecture({
    required this.id,
    required this.classLevel,
    required this.stream,
    required this.subjectId,
    required this.subjectName,
    required this.teacherId,
    required this.teacherName,
    required this.topic,
    required this.lectureNotes,
    required this.scheduledAt,
    required this.status,
    required this.completedAt,
  });

  factory StudentScheduledLecture.fromJson(Map<String, dynamic> json) {
    return StudentScheduledLecture(
      id: _toStringValue(json['id']),
      classLevel: _toNum(json['class_level']).toInt(),
      stream: _toStringValue(json['stream'], fallback: 'common'),
      subjectId: _toStringValue(json['subject_id']),
      subjectName: _toStringValue(json['subject_name']),
      teacherId: _toStringValue(json['teacher_id']),
      teacherName: _toStringValue(json['teacher_name']),
      topic: _toStringValue(json['topic']),
      lectureNotes: _toStringValue(json['lecture_notes']),
      scheduledAt: _toDate(json['scheduled_at']),
      status: _toStringValue(json['status'], fallback: 'scheduled'),
      completedAt: _toDate(json['completed_at']),
    );
  }
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
  final int badgeCount;

  const StudentQuickActionItem({
    required this.id,
    required this.title,
    required this.route,
    required this.iconKey,
    required this.accentColor,
    this.badgeCount = 0,
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

class StudentTodayScheduleItem {
  final String id;
  final String kind;
  final String title;
  final String subtitle;
  final DateTime scheduledAt;
  final String route;

  const StudentTodayScheduleItem({
    required this.id,
    required this.kind,
    required this.title,
    required this.subtitle,
    required this.scheduledAt,
    required this.route,
  });
}

class StudentHomeSummary {
  final StudentProfile profile;
  final StudentDashboard dashboard;
  final List<StudentNotificationItem> notifications;
  final List<StudentScheduledLecture> scheduledLectures;
  final List<StudentAnnouncementItem> announcements;
  final StudentLectureSummary todayLectures;
  final StudentLectureSummary upcomingLecture;
  final StudentPracticeTestSummary practiceTest;
  final StudentProgressSummary progress;
  final StudentAttendanceSummary attendance;
  final StudentHolidaySummary holiday;
  final List<StudentQuickActionItem> quickActions;
  final List<StudentTodayScheduleItem> todaySchedule;
  final StudentDoubtCtaData doubtCta;

  const StudentHomeSummary({
    required this.profile,
    required this.dashboard,
    required this.notifications,
    required this.scheduledLectures,
    required this.announcements,
    required this.todayLectures,
    required this.upcomingLecture,
    required this.practiceTest,
    required this.progress,
    required this.attendance,
    required this.holiday,
    required this.quickActions,
    required this.todaySchedule,
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

class StudentCompletedLecture {
  final String lectureId;
  final String topic;
  final String summary;
  final DateTime? completedAt;
  final String subjectId;
  final String subjectName;
  final String teacherId;
  final String teacherName;
  final int classLevel;
  final String stream;

  const StudentCompletedLecture({
    required this.lectureId,
    required this.topic,
    required this.summary,
    required this.completedAt,
    required this.subjectId,
    required this.subjectName,
    required this.teacherId,
    required this.teacherName,
    required this.classLevel,
    required this.stream,
  });

  factory StudentCompletedLecture.fromJson(Map<String, dynamic> json) {
    return StudentCompletedLecture(
      lectureId: _toStringValue(json['lecture_id']),
      topic: _toStringValue(json['topic']),
      summary: _toStringValue(json['summary']),
      completedAt: _toDate(json['completed_at']),
      subjectId: _toStringValue(json['subject_id']),
      subjectName: _toStringValue(json['subject_name']),
      teacherId: _toStringValue(json['teacher_id']),
      teacherName: _toStringValue(json['teacher_name']),
      classLevel: _toNum(json['class_level']).toInt(),
      stream: _toStringValue(json['stream']),
    );
  }
}

class StudentDoubtThreadSummary {
  final String id;
  final String lectureId;
  final String teacherId;
  final String subjectId;
  final String topic;
  final String status;
  final DateTime? createdAt;

  const StudentDoubtThreadSummary({
    required this.id,
    required this.lectureId,
    required this.teacherId,
    required this.subjectId,
    required this.topic,
    required this.status,
    required this.createdAt,
  });

  factory StudentDoubtThreadSummary.fromJson(Map<String, dynamic> json) {
    return StudentDoubtThreadSummary(
      id: _toStringValue(json['id']),
      lectureId: _toStringValue(json['lecture_id']),
      teacherId: _toStringValue(json['teacher_id']),
      subjectId: _toStringValue(json['subject_id']),
      topic: _toStringValue(json['topic']),
      status: _toStringValue(json['status'], fallback: 'open'),
      createdAt: _toDate(json['created_at']),
    );
  }
}

class StudentDoubtMessage {
  final String id;
  final String senderUserId;
  final String senderName;
  final String message;
  final DateTime? createdAt;

  const StudentDoubtMessage({
    required this.id,
    required this.senderUserId,
    required this.senderName,
    required this.message,
    required this.createdAt,
  });

  factory StudentDoubtMessage.fromJson(Map<String, dynamic> json) {
    return StudentDoubtMessage(
      id: _toStringValue(json['id']),
      senderUserId: _toStringValue(json['sender_user_id']),
      senderName: _toStringValue(json['sender_name'], fallback: 'Unknown'),
      message: _toStringValue(json['message']),
      createdAt: _toDate(json['created_at']),
    );
  }
}

class StudentDoubtThreadDetail {
  final StudentDoubtThreadSummary doubt;
  final String description;
  final List<StudentDoubtMessage> messages;

  const StudentDoubtThreadDetail({
    required this.doubt,
    required this.description,
    required this.messages,
  });

  factory StudentDoubtThreadDetail.fromJson(Map<String, dynamic> json) {
    final doubtRaw = json['doubt'] as Map<String, dynamic>? ?? const <String, dynamic>{};
    final messagesRaw = json['messages'] as List<dynamic>? ?? const <dynamic>[];

    return StudentDoubtThreadDetail(
      doubt: StudentDoubtThreadSummary.fromJson(doubtRaw),
      description: _toStringValue(doubtRaw['description']),
      messages: messagesRaw
          .map((item) => StudentDoubtMessage.fromJson(item as Map<String, dynamic>))
          .toList(growable: false),
    );
  }
}
