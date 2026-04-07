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

class ParentProfile {
  final String parentId;
  final String userId;
  final String fullName;
  final String? email;
  final String? phone;
  final int linkedStudentsCount;

  const ParentProfile({
    required this.parentId,
    required this.userId,
    required this.fullName,
    required this.email,
    required this.phone,
    required this.linkedStudentsCount,
  });

  factory ParentProfile.fromJson(Map<String, dynamic> json) {
    return ParentProfile(
      parentId: json['parent_id']?.toString() ?? '',
      userId: json['user_id']?.toString() ?? '',
      fullName: json['full_name']?.toString() ?? '',
      email: json['email']?.toString(),
      phone: json['phone']?.toString(),
      linkedStudentsCount: _toNum(json['linked_students_count']).toInt(),
    );
  }
}

class LinkedStudent {
  final String studentId;
  final String fullName;
  final String admissionNo;
  final String rollNo;
  final String relationType;
  final bool isPrimary;

  const LinkedStudent({
    required this.studentId,
    required this.fullName,
    required this.admissionNo,
    required this.rollNo,
    required this.relationType,
    required this.isPrimary,
  });

  factory LinkedStudent.fromJson(Map<String, dynamic> json) {
    return LinkedStudent(
      studentId: json['student_id']?.toString() ?? '',
      fullName: json['full_name']?.toString() ?? '',
      admissionNo: json['admission_no']?.toString() ?? '',
      rollNo: json['roll_no']?.toString() ?? '',
      relationType: json['relation_type']?.toString() ?? 'guardian',
      isPrimary: _toBool(json['is_primary']),
    );
  }
}

class ParentDashboard {
  final String studentId;
  final int unreadNotifications;
  final int pendingHomeworkCount;
  final double attendancePercentage;
  final int upcomingTestsCount;
  final int pendingFeeInvoices;

  const ParentDashboard({
    required this.studentId,
    required this.unreadNotifications,
    required this.pendingHomeworkCount,
    required this.attendancePercentage,
    required this.upcomingTestsCount,
    required this.pendingFeeInvoices,
  });

  factory ParentDashboard.fromJson(Map<String, dynamic> json) {
    return ParentDashboard(
      studentId: json['student_id']?.toString() ?? '',
      unreadNotifications: _toNum(json['unread_notifications']).toInt(),
      pendingHomeworkCount: _toNum(json['pending_homework_count']).toInt(),
      attendancePercentage: _toNum(json['attendance_percentage']).toDouble(),
      upcomingTestsCount: _toNum(json['upcoming_tests_count']).toInt(),
      pendingFeeInvoices: _toNum(json['pending_fee_invoices']).toInt(),
    );
  }
}

class ParentNotice {
  final String id;
  final String title;
  final String bodyPreview;
  final String? publishAt;
  final bool isRead;

  const ParentNotice({
    required this.id,
    required this.title,
    required this.bodyPreview,
    required this.publishAt,
    required this.isRead,
  });

  factory ParentNotice.fromJson(Map<String, dynamic> json) {
    return ParentNotice(
      id: json['id']?.toString() ?? '',
      title: json['title']?.toString() ?? '',
      bodyPreview: json['body_preview']?.toString() ?? '',
      publishAt: json['publish_at']?.toString(),
      isRead: _toBool(json['is_read']),
    );
  }
}

class ParentHomework {
  final String id;
  final String title;
  final String description;
  final String dueDate;
  final String status;

  const ParentHomework({
    required this.id,
    required this.title,
    required this.description,
    required this.dueDate,
    required this.status,
  });

  factory ParentHomework.fromJson(Map<String, dynamic> json) {
    return ParentHomework(
      id: json['id']?.toString() ?? '',
      title: json['title']?.toString() ?? '',
      description: json['description']?.toString() ?? '',
      dueDate: json['due_date']?.toString() ?? '',
      status: json['status']?.toString() ?? '',
    );
  }
}

class ParentAttendance {
  final String id;
  final String attendanceDate;
  final String status;
  final String source;

  const ParentAttendance({
    required this.id,
    required this.attendanceDate,
    required this.status,
    required this.source,
  });

  factory ParentAttendance.fromJson(Map<String, dynamic> json) {
    return ParentAttendance(
      id: json['id']?.toString() ?? '',
      attendanceDate: json['attendance_date']?.toString() ?? '',
      status: json['status']?.toString() ?? '',
      source: json['source']?.toString() ?? '',
    );
  }
}

class ParentResult {
  final String id;
  final String assessmentId;
  final double score;
  final double totalMarks;
  final int? rank;
  final String? publishedAt;

  const ParentResult({
    required this.id,
    required this.assessmentId,
    required this.score,
    required this.totalMarks,
    required this.rank,
    required this.publishedAt,
  });

  factory ParentResult.fromJson(Map<String, dynamic> json) {
    return ParentResult(
      id: json['id']?.toString() ?? '',
      assessmentId: json['assessment_id']?.toString() ?? '',
      score: _toNum(json['score']).toDouble(),
      totalMarks: _toNum(json['total_marks']).toDouble(),
      rank: json['rank'] == null ? null : _toNum(json['rank']).toInt(),
      publishedAt: json['published_at']?.toString(),
    );
  }
}

class ParentProgress {
  final String periodType;
  final String periodStart;
  final Map<String, dynamic> metrics;

  const ParentProgress({
    required this.periodType,
    required this.periodStart,
    required this.metrics,
  });

  factory ParentProgress.fromJson(Map<String, dynamic> json) {
    final metrics =
        json['metrics'] as Map<String, dynamic>? ?? <String, dynamic>{};

    return ParentProgress(
      periodType: json['period_type']?.toString() ?? '',
      periodStart: json['period_start']?.toString() ?? '',
      metrics: metrics,
    );
  }
}

class ParentFeeInvoice {
  final String id;
  final String invoiceNo;
  final String periodLabel;
  final String dueDate;
  final double amount;
  final String status;
  final String? paidAt;

  const ParentFeeInvoice({
    required this.id,
    required this.invoiceNo,
    required this.periodLabel,
    required this.dueDate,
    required this.amount,
    required this.status,
    required this.paidAt,
  });

  factory ParentFeeInvoice.fromJson(Map<String, dynamic> json) {
    return ParentFeeInvoice(
      id: json['id']?.toString() ?? '',
      invoiceNo: json['invoice_no']?.toString() ?? '',
      periodLabel: json['period_label']?.toString() ?? '',
      dueDate: json['due_date']?.toString() ?? '',
      amount: _toNum(json['amount']).toDouble(),
      status: json['status']?.toString() ?? '',
      paidAt: json['paid_at']?.toString(),
    );
  }
}

class ParentPayment {
  final String id;
  final String invoiceId;
  final String provider;
  final String? externalRef;
  final double amount;
  final String status;
  final String? paidAt;

  const ParentPayment({
    required this.id,
    required this.invoiceId,
    required this.provider,
    required this.externalRef,
    required this.amount,
    required this.status,
    required this.paidAt,
  });

  factory ParentPayment.fromJson(Map<String, dynamic> json) {
    return ParentPayment(
      id: json['id']?.toString() ?? '',
      invoiceId: json['invoice_id']?.toString() ?? '',
      provider: json['provider']?.toString() ?? '',
      externalRef: json['external_ref']?.toString(),
      amount: _toNum(json['amount']).toDouble(),
      status: json['status']?.toString() ?? '',
      paidAt: json['paid_at']?.toString(),
    );
  }
}

class ParentPreference {
  final bool inAppEnabled;
  final bool pushEnabled;
  final bool whatsappEnabled;
  final bool feeRemindersEnabled;
  final String preferredLanguage;

  const ParentPreference({
    required this.inAppEnabled,
    required this.pushEnabled,
    required this.whatsappEnabled,
    required this.feeRemindersEnabled,
    required this.preferredLanguage,
  });

  factory ParentPreference.fromJson(Map<String, dynamic> json) {
    return ParentPreference(
      inAppEnabled: _toBool(json['in_app_enabled'], fallback: true),
      pushEnabled: _toBool(json['push_enabled'], fallback: true),
      whatsappEnabled: _toBool(json['whatsapp_enabled']),
      feeRemindersEnabled:
          _toBool(json['fee_reminders_enabled'], fallback: true),
      preferredLanguage: json['preferred_language']?.toString() ?? 'en',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'in_app_enabled': inAppEnabled,
      'push_enabled': pushEnabled,
      'whatsapp_enabled': whatsappEnabled,
      'fee_reminders_enabled': feeRemindersEnabled,
      'preferred_language': preferredLanguage,
    };
  }
}

class ParentNotification {
  final String id;
  final String title;
  final String body;
  final String notificationType;
  final bool isRead;
  final String? createdAt;

  const ParentNotification({
    required this.id,
    required this.title,
    required this.body,
    required this.notificationType,
    required this.isRead,
    required this.createdAt,
  });

  factory ParentNotification.fromJson(Map<String, dynamic> json) {
    return ParentNotification(
      id: json['id']?.toString() ?? '',
      title: json['title']?.toString() ?? '',
      body: json['body']?.toString() ?? '',
      notificationType: json['notification_type']?.toString() ?? 'system',
      isRead: _toBool(json['is_read']),
      createdAt: json['created_at']?.toString(),
    );
  }
}

class ParentNotificationList {
  final List<ParentNotification> items;
  final int unreadCount;

  const ParentNotificationList(
      {required this.items, required this.unreadCount});
}
