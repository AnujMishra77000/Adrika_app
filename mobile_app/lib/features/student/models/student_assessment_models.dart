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

class StudentAssessmentItem {
  final String id;
  final String title;
  final String description;
  final String subjectId;
  final String? subjectName;
  final String? topic;
  final int? classLevel;
  final String? stream;
  final String assessmentType;
  final String status;
  final String availability;
  final DateTime? startsAt;
  final DateTime? endsAt;
  final int durationSec;
  final int durationMinutes;
  final int attemptLimit;
  final int questionCount;
  final double totalMarks;
  final double passingMarks;
  final bool hasSubmitted;
  final double? score;
  final bool? isPassed;
  final String? latestAttemptId;

  const StudentAssessmentItem({
    required this.id,
    required this.title,
    required this.description,
    required this.subjectId,
    required this.subjectName,
    required this.topic,
    required this.classLevel,
    required this.stream,
    required this.assessmentType,
    required this.status,
    required this.availability,
    required this.startsAt,
    required this.endsAt,
    required this.durationSec,
    required this.durationMinutes,
    required this.attemptLimit,
    required this.questionCount,
    required this.totalMarks,
    required this.passingMarks,
    required this.hasSubmitted,
    required this.score,
    required this.isPassed,
    required this.latestAttemptId,
  });

  bool get isLive => availability == 'live';
  bool get isScheduled => availability == 'scheduled';
  bool get isMissed => availability == 'missed';
  bool get isCompleted => availability == 'completed';

  factory StudentAssessmentItem.fromJson(Map<String, dynamic> json) {
    final latestAttempt = _toStringValue(json['latest_attempt_id']).trim();
    return StudentAssessmentItem(
      id: _toStringValue(json['id']),
      title: _toStringValue(json['title'], fallback: 'Assessment'),
      description: _toStringValue(json['description']),
      subjectId: _toStringValue(json['subject_id']),
      subjectName: _toStringValue(json['subject_name']).trim().isEmpty
          ? null
          : _toStringValue(json['subject_name']).trim(),
      topic: _toStringValue(json['topic']).trim().isEmpty
          ? null
          : _toStringValue(json['topic']).trim(),
      classLevel: json['class_level'] == null
          ? null
          : _toNum(json['class_level']).toInt(),
      stream: _toStringValue(json['stream']).trim().isEmpty
          ? null
          : _toStringValue(json['stream']).trim(),
      assessmentType: _toStringValue(json['assessment_type']),
      status: _toStringValue(json['status']),
      availability: _toStringValue(json['availability']),
      startsAt: _toDate(json['starts_at']),
      endsAt: _toDate(json['ends_at']),
      durationSec: _toNum(json['duration_sec']).toInt(),
      durationMinutes: _toNum(json['duration_minutes']).toInt(),
      attemptLimit: _toNum(json['attempt_limit']).toInt(),
      questionCount: _toNum(json['question_count']).toInt(),
      totalMarks: _toNum(json['total_marks']).toDouble(),
      passingMarks: _toNum(json['passing_marks']).toDouble(),
      hasSubmitted: _toBool(json['has_submitted']),
      score: json['score'] == null ? null : _toNum(json['score']).toDouble(),
      isPassed: json['is_passed'] == null ? null : _toBool(json['is_passed']),
      latestAttemptId: latestAttempt.isEmpty ? null : latestAttempt,
    );
  }
}

class StudentAssessmentQuestionOption {
  final String key;
  final String text;

  const StudentAssessmentQuestionOption({
    required this.key,
    required this.text,
  });

  factory StudentAssessmentQuestionOption.fromJson(Map<String, dynamic> json) {
    return StudentAssessmentQuestionOption(
      key: _toStringValue(json['key']),
      text: _toStringValue(json['text']),
    );
  }
}

class StudentAssessmentDetail {
  final String id;
  final String title;
  final String description;
  final String subjectId;
  final String? subjectName;
  final String? topic;
  final int? classLevel;
  final String? stream;
  final String assessmentType;
  final String status;
  final String availability;
  final DateTime? startsAt;
  final DateTime? endsAt;
  final int durationSec;
  final int durationMinutes;
  final int attemptLimit;
  final int questionCount;
  final double totalMarks;
  final double passingMarks;
  final String? latestAttemptId;

  const StudentAssessmentDetail({
    required this.id,
    required this.title,
    required this.description,
    required this.subjectId,
    required this.subjectName,
    required this.topic,
    required this.classLevel,
    required this.stream,
    required this.assessmentType,
    required this.status,
    required this.availability,
    required this.startsAt,
    required this.endsAt,
    required this.durationSec,
    required this.durationMinutes,
    required this.attemptLimit,
    required this.questionCount,
    required this.totalMarks,
    required this.passingMarks,
    required this.latestAttemptId,
  });

  bool get isLive => availability == 'live';
  bool get isScheduled => availability == 'scheduled';
  bool get isMissed => availability == 'missed';
  bool get isCompleted => availability == 'completed';

  factory StudentAssessmentDetail.fromJson(Map<String, dynamic> json) {
    final latestAttempt = _toStringValue(json['latest_attempt_id']).trim();
    return StudentAssessmentDetail(
      id: _toStringValue(json['id']),
      title: _toStringValue(json['title'], fallback: 'Assessment'),
      description: _toStringValue(json['description']),
      subjectId: _toStringValue(json['subject_id']),
      subjectName: _toStringValue(json['subject_name']).trim().isEmpty
          ? null
          : _toStringValue(json['subject_name']).trim(),
      topic: _toStringValue(json['topic']).trim().isEmpty
          ? null
          : _toStringValue(json['topic']).trim(),
      classLevel: json['class_level'] == null
          ? null
          : _toNum(json['class_level']).toInt(),
      stream: _toStringValue(json['stream']).trim().isEmpty
          ? null
          : _toStringValue(json['stream']).trim(),
      assessmentType: _toStringValue(json['assessment_type']),
      status: _toStringValue(json['status']),
      availability: _toStringValue(json['availability']),
      startsAt: _toDate(json['starts_at']),
      endsAt: _toDate(json['ends_at']),
      durationSec: _toNum(json['duration_sec']).toInt(),
      durationMinutes: _toNum(json['duration_minutes']).toInt(),
      attemptLimit: _toNum(json['attempt_limit']).toInt(),
      questionCount: _toNum(json['question_count']).toInt(),
      totalMarks: _toNum(json['total_marks']).toDouble(),
      passingMarks: _toNum(json['passing_marks']).toDouble(),
      latestAttemptId: latestAttempt.isEmpty ? null : latestAttempt,
    );
  }
}

class StudentAttemptQuestion {
  final int seqNo;
  final String questionId;
  final String prompt;
  final List<StudentAssessmentQuestionOption> options;
  final double maxMarks;
  final String? selectedKey;
  final String? correctKey;
  final bool? isCorrect;
  final double? marksAwarded;

  const StudentAttemptQuestion({
    required this.seqNo,
    required this.questionId,
    required this.prompt,
    required this.options,
    required this.maxMarks,
    required this.selectedKey,
    required this.correctKey,
    required this.isCorrect,
    required this.marksAwarded,
  });

  factory StudentAttemptQuestion.fromJson(Map<String, dynamic> json) {
    final rawOptions = json['options'] as List<dynamic>? ?? <dynamic>[];
    final selected = _toStringValue(json['selected_key']).trim();
    final correct = _toStringValue(json['correct_key']).trim();
    return StudentAttemptQuestion(
      seqNo: _toNum(json['seq_no']).toInt(),
      questionId: _toStringValue(json['question_id']),
      prompt: _toStringValue(json['prompt']),
      options: rawOptions
          .map(
            (item) => StudentAssessmentQuestionOption.fromJson(
              item as Map<String, dynamic>,
            ),
          )
          .toList(growable: false),
      maxMarks: _toNum(json['max_marks']).toDouble(),
      selectedKey: selected.isEmpty ? null : selected,
      correctKey: correct.isEmpty ? null : correct,
      isCorrect:
          json['is_correct'] == null ? null : _toBool(json['is_correct']),
      marksAwarded: json['marks_awarded'] == null
          ? null
          : _toNum(json['marks_awarded']).toDouble(),
    );
  }
}

class StudentAssessmentAttemptDetail {
  final String attemptId;
  final String assessmentId;
  final String status;
  final DateTime? startedAt;
  final DateTime? expiresAt;
  final DateTime? submittedAt;
  final int remainingSeconds;
  final double? score;
  final double totalMarks;
  final double passingMarks;
  final bool? isPassed;
  final bool autoSubmitted;
  final List<StudentAttemptQuestion> questions;

  const StudentAssessmentAttemptDetail({
    required this.attemptId,
    required this.assessmentId,
    required this.status,
    required this.startedAt,
    required this.expiresAt,
    required this.submittedAt,
    required this.remainingSeconds,
    required this.score,
    required this.totalMarks,
    required this.passingMarks,
    required this.isPassed,
    required this.autoSubmitted,
    required this.questions,
  });

  bool get isCompleted => status == 'submitted' || status == 'auto_submitted';
  bool get isStarted => status == 'started';

  factory StudentAssessmentAttemptDetail.fromJson(Map<String, dynamic> json) {
    final rawQuestions = json['questions'] as List<dynamic>? ?? <dynamic>[];
    return StudentAssessmentAttemptDetail(
      attemptId: _toStringValue(json['attempt_id']),
      assessmentId: _toStringValue(json['assessment_id']),
      status: _toStringValue(json['status']),
      startedAt: _toDate(json['started_at']),
      expiresAt: _toDate(json['expires_at']),
      submittedAt: _toDate(json['submitted_at']),
      remainingSeconds: _toNum(json['remaining_seconds']).toInt(),
      score: json['score'] == null ? null : _toNum(json['score']).toDouble(),
      totalMarks: _toNum(json['total_marks']).toDouble(),
      passingMarks: _toNum(json['passing_marks']).toDouble(),
      isPassed: json['is_passed'] == null ? null : _toBool(json['is_passed']),
      autoSubmitted: _toBool(json['auto_submitted']),
      questions: rawQuestions
          .map(
            (item) => StudentAttemptQuestion.fromJson(
              item as Map<String, dynamic>,
            ),
          )
          .toList(growable: false),
    );
  }
}

class StudentAssessmentQuestionEvaluation {
  final int seqNo;
  final String questionId;
  final String prompt;
  final String? selectedKey;
  final String? correctKey;
  final bool isCorrect;
  final double marksAwarded;
  final double maxMarks;

  const StudentAssessmentQuestionEvaluation({
    required this.seqNo,
    required this.questionId,
    required this.prompt,
    required this.selectedKey,
    required this.correctKey,
    required this.isCorrect,
    required this.marksAwarded,
    required this.maxMarks,
  });

  factory StudentAssessmentQuestionEvaluation.fromJson(
    Map<String, dynamic> json,
  ) {
    final selected = _toStringValue(json['selected_key']).trim();
    final correct = _toStringValue(json['correct_key']).trim();
    return StudentAssessmentQuestionEvaluation(
      seqNo: _toNum(json['seq_no']).toInt(),
      questionId: _toStringValue(json['question_id']),
      prompt: _toStringValue(json['prompt']),
      selectedKey: selected.isEmpty ? null : selected,
      correctKey: correct.isEmpty ? null : correct,
      isCorrect: _toBool(json['is_correct']),
      marksAwarded: _toNum(json['marks_awarded']).toDouble(),
      maxMarks: _toNum(json['max_marks']).toDouble(),
    );
  }
}

class StudentAssessmentSubmitResult {
  final String attemptId;
  final String status;
  final double score;
  final double totalMarks;
  final double passingMarks;
  final bool isPassed;
  final DateTime? submittedAt;
  final bool autoSubmitted;
  final List<StudentAssessmentQuestionEvaluation> questionEvaluation;

  const StudentAssessmentSubmitResult({
    required this.attemptId,
    required this.status,
    required this.score,
    required this.totalMarks,
    required this.passingMarks,
    required this.isPassed,
    required this.submittedAt,
    required this.autoSubmitted,
    required this.questionEvaluation,
  });

  factory StudentAssessmentSubmitResult.fromJson(Map<String, dynamic> json) {
    final rawEvaluation =
        json['question_evaluation'] as List<dynamic>? ?? <dynamic>[];
    return StudentAssessmentSubmitResult(
      attemptId: _toStringValue(json['attempt_id']),
      status: _toStringValue(json['status']),
      score: _toNum(json['score']).toDouble(),
      totalMarks: _toNum(json['total_marks']).toDouble(),
      passingMarks: _toNum(json['passing_marks']).toDouble(),
      isPassed: _toBool(json['is_passed']),
      submittedAt: _toDate(json['submitted_at']),
      autoSubmitted: _toBool(json['auto_submitted']),
      questionEvaluation: rawEvaluation
          .map(
            (item) => StudentAssessmentQuestionEvaluation.fromJson(
              item as Map<String, dynamic>,
            ),
          )
          .toList(growable: false),
    );
  }
}
