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
