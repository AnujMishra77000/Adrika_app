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

class TeacherProfile {
  final String teacherId;
  final String userId;
  final String fullName;
  final String employeeCode;
  final String designation;

  const TeacherProfile({
    required this.teacherId,
    required this.userId,
    required this.fullName,
    required this.employeeCode,
    required this.designation,
  });

  factory TeacherProfile.fromJson(Map<String, dynamic> json) {
    return TeacherProfile(
      teacherId: json['teacher_id']?.toString() ?? '',
      userId: json['user_id']?.toString() ?? '',
      fullName: json['full_name']?.toString() ?? '',
      employeeCode: json['employee_code']?.toString() ?? '',
      designation: json['designation']?.toString() ?? '',
    );
  }
}

class TeacherDashboard {
  final int assignedBatchesCount;
  final int assignedSubjectsCount;
  final int unreadNotifications;
  final int openDoubtsCount;
  final int pendingHomeworkCount;
  final int upcomingTestsCount;

  const TeacherDashboard({
    required this.assignedBatchesCount,
    required this.assignedSubjectsCount,
    required this.unreadNotifications,
    required this.openDoubtsCount,
    required this.pendingHomeworkCount,
    required this.upcomingTestsCount,
  });

  factory TeacherDashboard.fromJson(Map<String, dynamic> json) {
    return TeacherDashboard(
      assignedBatchesCount: _toNum(json['assigned_batches_count']).toInt(),
      assignedSubjectsCount: _toNum(json['assigned_subjects_count']).toInt(),
      unreadNotifications: _toNum(json['unread_notifications']).toInt(),
      openDoubtsCount: _toNum(json['open_doubts_count']).toInt(),
      pendingHomeworkCount: _toNum(json['pending_homework_count']).toInt(),
      upcomingTestsCount: _toNum(json['upcoming_tests_count']).toInt(),
    );
  }
}

class TeacherAssignment {
  final String assignmentId;
  final String batchName;
  final String standardName;
  final String subjectName;

  const TeacherAssignment({
    required this.assignmentId,
    required this.batchName,
    required this.standardName,
    required this.subjectName,
  });

  factory TeacherAssignment.fromJson(Map<String, dynamic> json) {
    return TeacherAssignment(
      assignmentId: json['assignment_id']?.toString() ?? '',
      batchName: json['batch_name']?.toString() ?? '',
      standardName: json['standard_name']?.toString() ?? '',
      subjectName: json['subject_name']?.toString() ?? '',
    );
  }
}

class TeacherNotice {
  final String id;
  final String title;
  final String bodyPreview;
  final String? publishAt;
  final bool isRead;

  const TeacherNotice({
    required this.id,
    required this.title,
    required this.bodyPreview,
    required this.publishAt,
    required this.isRead,
  });

  factory TeacherNotice.fromJson(Map<String, dynamic> json) {
    return TeacherNotice(
      id: json['id']?.toString() ?? '',
      title: json['title']?.toString() ?? '',
      bodyPreview: json['body_preview']?.toString() ?? '',
      publishAt: json['publish_at']?.toString(),
      isRead: _toBool(json['is_read']),
    );
  }
}
