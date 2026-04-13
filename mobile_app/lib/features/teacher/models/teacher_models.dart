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

int? _toIntOrNull(dynamic value) {
  if (value == null) {
    return null;
  }
  return int.tryParse(value.toString());
}

DateTime? _toDateTime(dynamic value) {
  if (value is DateTime) {
    return value;
  }
  if (value == null) {
    return null;
  }
  return DateTime.tryParse(value.toString())?.toLocal();
}

class TeacherProfile {
  final String teacherId;
  final String userId;
  final String fullName;
  final String employeeCode;
  final String designation;
  final String qualification;
  final String specialization;
  final String gender;
  final int? age;
  final String schoolCollege;
  final String address;

  const TeacherProfile({
    required this.teacherId,
    required this.userId,
    required this.fullName,
    required this.employeeCode,
    required this.designation,
    required this.qualification,
    required this.specialization,
    required this.gender,
    required this.age,
    required this.schoolCollege,
    required this.address,
  });

  factory TeacherProfile.fromJson(Map<String, dynamic> json) {
    return TeacherProfile(
      teacherId: json['teacher_id']?.toString() ?? '',
      userId: json['user_id']?.toString() ?? '',
      fullName: json['full_name']?.toString() ?? '',
      employeeCode: json['employee_code']?.toString() ?? '',
      designation: json['designation']?.toString() ?? '',
      qualification: json['qualification']?.toString() ?? '',
      specialization: json['specialization']?.toString() ?? '',
      gender: json['gender']?.toString() ?? '',
      age: _toIntOrNull(json['age']),
      schoolCollege: json['school_college']?.toString() ?? '',
      address: json['address']?.toString() ?? '',
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
  final String batchId;
  final String batchName;
  final String standardId;
  final String standardName;
  final String subjectId;
  final String subjectName;

  const TeacherAssignment({
    required this.assignmentId,
    required this.batchId,
    required this.batchName,
    required this.standardId,
    required this.standardName,
    required this.subjectId,
    required this.subjectName,
  });

  factory TeacherAssignment.fromJson(Map<String, dynamic> json) {
    return TeacherAssignment(
      assignmentId: json['assignment_id']?.toString() ?? '',
      batchId: json['batch_id']?.toString() ?? '',
      batchName: json['batch_name']?.toString() ?? '',
      standardId: json['standard_id']?.toString() ?? '',
      standardName: json['standard_name']?.toString() ?? '',
      subjectId: json['subject_id']?.toString() ?? '',
      subjectName: json['subject_name']?.toString() ?? '',
    );
  }
}

class TeacherScheduledLecture {
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

  const TeacherScheduledLecture({
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

  factory TeacherScheduledLecture.fromJson(Map<String, dynamic> json) {
    return TeacherScheduledLecture(
      id: json['id']?.toString() ?? '',
      classLevel: _toIntOrNull(json['class_level']) ?? 10,
      stream: json['stream']?.toString() ?? 'common',
      subjectId: json['subject_id']?.toString() ?? '',
      subjectName: json['subject_name']?.toString() ?? '',
      teacherId: json['teacher_id']?.toString() ?? '',
      teacherName: json['teacher_name']?.toString() ?? '',
      topic: json['topic']?.toString() ?? '',
      lectureNotes: json['lecture_notes']?.toString() ?? '',
      scheduledAt: _toDateTime(json['scheduled_at']),
      status: json['status']?.toString() ?? 'scheduled',
      completedAt: _toDateTime(json['completed_at']),
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

class TeacherCompletedLecture {
  final String lectureId;
  final String subjectId;
  final String subjectName;
  final String batchId;
  final int? classLevel;
  final String stream;
  final String topic;
  final String summary;
  final DateTime? completedAt;

  const TeacherCompletedLecture({
    required this.lectureId,
    required this.subjectId,
    required this.subjectName,
    required this.batchId,
    required this.classLevel,
    required this.stream,
    required this.topic,
    required this.summary,
    required this.completedAt,
  });

  factory TeacherCompletedLecture.fromJson(Map<String, dynamic> json) {
    return TeacherCompletedLecture(
      lectureId: json['lecture_id']?.toString() ?? '',
      subjectId: json['subject_id']?.toString() ?? '',
      subjectName: json['subject_name']?.toString() ?? '',
      batchId: json['batch_id']?.toString() ?? '',
      classLevel: _toIntOrNull(json['class_level']),
      stream: json['stream']?.toString() ?? '',
      topic: json['topic']?.toString() ?? '',
      summary: json['summary']?.toString() ?? '',
      completedAt: _toDateTime(json['completed_at']),
    );
  }
}

class TeacherDoubtItem {
  final String id;
  final String studentId;
  final String studentName;
  final String lectureId;
  final String lectureTopic;
  final String topic;
  final String status;
  final String priority;
  final DateTime? createdAt;

  const TeacherDoubtItem({
    required this.id,
    required this.studentId,
    required this.studentName,
    required this.lectureId,
    required this.lectureTopic,
    required this.topic,
    required this.status,
    required this.priority,
    required this.createdAt,
  });

  factory TeacherDoubtItem.fromJson(Map<String, dynamic> json) {
    return TeacherDoubtItem(
      id: json['id']?.toString() ?? '',
      studentId: json['student_id']?.toString() ?? '',
      studentName: json['student_name']?.toString() ?? 'Student',
      lectureId: json['lecture_id']?.toString() ?? '',
      lectureTopic: json['lecture_topic']?.toString() ?? '',
      topic: json['topic']?.toString() ?? '',
      status: json['status']?.toString() ?? 'open',
      priority: json['priority']?.toString() ?? 'normal',
      createdAt: _toDateTime(json['created_at']),
    );
  }
}

class TeacherDoubtMessage {
  final String id;
  final String senderUserId;
  final String senderName;
  final String message;
  final DateTime? createdAt;

  const TeacherDoubtMessage({
    required this.id,
    required this.senderUserId,
    required this.senderName,
    required this.message,
    required this.createdAt,
  });

  factory TeacherDoubtMessage.fromJson(Map<String, dynamic> json) {
    return TeacherDoubtMessage(
      id: json['id']?.toString() ?? '',
      senderUserId: json['sender_user_id']?.toString() ?? '',
      senderName: json['sender_name']?.toString() ?? 'Unknown',
      message: json['message']?.toString() ?? '',
      createdAt: _toDateTime(json['created_at']),
    );
  }
}

class TeacherDoubtDetail {
  final TeacherDoubtItem doubt;
  final String description;
  final List<TeacherDoubtMessage> messages;

  const TeacherDoubtDetail({
    required this.doubt,
    required this.description,
    required this.messages,
  });

  factory TeacherDoubtDetail.fromJson(Map<String, dynamic> json) {
    final doubtRaw =
        json['doubt'] as Map<String, dynamic>? ?? const <String, dynamic>{};
    final messageRaw = json['messages'] as List<dynamic>? ?? const <dynamic>[];
    return TeacherDoubtDetail(
      doubt: TeacherDoubtItem.fromJson(doubtRaw),
      description: doubtRaw['description']?.toString() ?? '',
      messages: messageRaw
          .map(
            (item) => TeacherDoubtMessage.fromJson(item as Map<String, dynamic>),
          )
          .toList(growable: false),
    );
  }
}
