import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../models/student_assessment_models.dart';
import '../models/student_models.dart';

final studentApiProvider = Provider<StudentApi>((ref) {
  return StudentApi(ref.watch(apiClientProvider));
});

class StudentApi {
  StudentApi(this._client);

  final ApiClient _client;

  Future<StudentProfile> fetchProfile({required String accessToken}) async {
    final response =
        await _client.getMap('/students/me/profile', accessToken: accessToken);
    return StudentProfile.fromJson(response);
  }

  Future<StudentDashboard> fetchDashboard({required String accessToken}) async {
    final response = await _client.getMap(
      '/students/me/dashboard',
      accessToken: accessToken,
    );
    return StudentDashboard.fromJson(response);
  }

  Future<List<StudentNotice>> fetchNotices({
    required String accessToken,
    int limit = 20,
  }) async {
    final response = await _client.getMap(
      '/students/me/notices',
      accessToken: accessToken,
      queryParameters: {'limit': limit, 'offset': 0},
    );

    final raw = response['items'] as List<dynamic>? ?? <dynamic>[];
    return raw
        .map((item) => StudentNotice.fromJson(item as Map<String, dynamic>))
        .toList(growable: false);
  }

  Future<StudentNoticeDetail> fetchNoticeDetail({
    required String accessToken,
    required String noticeId,
  }) async {
    final response = await _client.getMap(
      '/students/me/notices/$noticeId',
      accessToken: accessToken,
    );

    try {
      await _client.postMap(
        '/students/me/notices/$noticeId/read',
        accessToken: accessToken,
      );
    } catch (_) {
      // Best-effort read sync should never block detail rendering.
    }

    return StudentNoticeDetail.fromJson(response);
  }

  Future<List<StudentHomework>> fetchHomework({
    required String accessToken,
    int limit = 20,
  }) async {
    final response = await _client.getMap(
      '/students/me/homework',
      accessToken: accessToken,
      queryParameters: {'limit': limit, 'offset': 0},
    );

    final raw = response['items'] as List<dynamic>? ?? <dynamic>[];
    return raw
        .map((item) => StudentHomework.fromJson(item as Map<String, dynamic>))
        .toList(growable: false);
  }

  Future<StudentHomework> fetchHomeworkDetail({
    required String accessToken,
    required String homeworkId,
  }) async {
    final response = await _client.getMap(
      '/students/me/homework/$homeworkId',
      accessToken: accessToken,
    );
    return StudentHomework.fromJson(response);
  }

  Future<void> markHomeworkReadAll({required String accessToken}) async {
    await _client.postMap(
      '/students/me/homework/read-all',
      accessToken: accessToken,
    );
  }

  Future<Map<String, dynamic>> submitHomework({
    required String accessToken,
    required String homeworkId,
    required String filePath,
    required String fileName,
    String? notes,
  }) async {
    final formData = FormData.fromMap({
      'file': await MultipartFile.fromFile(filePath, filename: fileName),
      if ((notes ?? '').trim().isNotEmpty) 'notes': notes!.trim(),
    });

    return _client.postFormMap(
      '/students/me/homework/$homeworkId/submit',
      accessToken: accessToken,
      formData: formData,
    );
  }

  Future<Map<String, dynamic>> fetchAttendanceSummary({
    required String accessToken,
  }) {
    return _client.getMap(
      '/students/me/attendance/summary',
      accessToken: accessToken,
    );
  }

  Future<List<StudentNotificationItem>> fetchNotifications({
    required String accessToken,
    int limit = 20,
  }) async {
    try {
      final response = await _client.getMap(
        '/students/me/notifications',
        accessToken: accessToken,
        queryParameters: {'limit': limit, 'offset': 0},
      );

      final raw = response['items'] as List<dynamic>? ?? <dynamic>[];
      return raw
          .map(
            (item) =>
                StudentNotificationItem.fromJson(item as Map<String, dynamic>),
          )
          .toList(growable: false);
    } catch (_) {
      // Fallback keeps UI functional when notifications endpoint is introduced later.
      final notices =
          await fetchNotices(accessToken: accessToken, limit: limit);
      return notices
          .map(StudentNotificationItem.fromNotice)
          .toList(growable: false);
    }
  }


  Future<List<StudentScheduledLecture>> fetchScheduledLectures({
    required String accessToken,
    String status = "scheduled",
    int limit = 50,
    int offset = 0,
  }) async {
    final response = await _client.getMap(
      "/students/me/lectures/scheduled",
      accessToken: accessToken,
      queryParameters: {
        "status": status,
        "limit": limit,
        "offset": offset,
      },
    );

    final raw = response["items"] as List<dynamic>? ?? <dynamic>[];
    return raw
        .map(
          (item) =>
              StudentScheduledLecture.fromJson(item as Map<String, dynamic>),
        )
        .toList(growable: false);
  }

  Future<List<StudentCompletedLecture>> fetchCompletedLectures({
    required String accessToken,
    int limit = 50,
    int offset = 0,
  }) async {
    final response = await _client.getMap(
      '/students/me/doubts/lectures/done',
      accessToken: accessToken,
      queryParameters: {'limit': limit, 'offset': offset},
    );

    final raw = response['items'] as List<dynamic>? ?? <dynamic>[];
    return raw
        .map(
          (item) => StudentCompletedLecture.fromJson(item as Map<String, dynamic>),
        )
        .toList(growable: false);
  }

  Future<StudentCompletedLecture> fetchCompletedLectureDetail({
    required String accessToken,
    required String lectureId,
  }) async {
    final response = await _client.getMap(
      '/students/me/doubts/lectures/done/$lectureId',
      accessToken: accessToken,
    );
    return StudentCompletedLecture.fromJson(response);
  }

  Future<List<StudentDoubtThreadSummary>> fetchMyDoubts({
    required String accessToken,
    int limit = 100,
  }) async {
    final response = await _client.getMap(
      '/students/me/doubts',
      accessToken: accessToken,
      queryParameters: {'limit': limit, 'offset': 0},
    );

    final raw = response['items'] as List<dynamic>? ?? <dynamic>[];
    return raw
        .map(
          (item) => StudentDoubtThreadSummary.fromJson(item as Map<String, dynamic>),
        )
        .toList(growable: false);
  }

  Future<StudentDoubtThreadSummary> raiseDoubtFromLecture({
    required String accessToken,
    required String lectureId,
    required String topic,
    required String description,
  }) async {
    final response = await _client.postMap(
      '/students/me/doubts/lectures/done/$lectureId/raise',
      accessToken: accessToken,
      body: {
        'topic': topic,
        'description': description,
      },
    );

    return StudentDoubtThreadSummary.fromJson(response);
  }

  Future<StudentDoubtThreadDetail> fetchDoubtDetail({
    required String accessToken,
    required String doubtId,
  }) async {
    final response = await _client.getMap(
      '/students/me/doubts/$doubtId',
      accessToken: accessToken,
    );
    return StudentDoubtThreadDetail.fromJson(response);
  }

  Future<List<StudentDoubtMessage>> fetchDoubtMessages({
    required String accessToken,
    required String doubtId,
    DateTime? since,
  }) async {
    final query = <String, dynamic>{};
    if (since != null) {
      query['since'] = since.toUtc().toIso8601String();
    }

    final response = await _client.getMap(
      '/students/me/doubts/$doubtId/messages',
      accessToken: accessToken,
      queryParameters: query,
    );

    final raw = response['items'] as List<dynamic>? ?? <dynamic>[];
    return raw
        .map(
          (item) => StudentDoubtMessage.fromJson(item as Map<String, dynamic>),
        )
        .toList(growable: false);
  }

  Future<StudentDoubtMessage> sendDoubtMessage({
    required String accessToken,
    required String doubtId,
    required String message,
  }) async {
    final response = await _client.postMap(
      '/students/me/doubts/$doubtId/messages',
      accessToken: accessToken,
      body: {'message': message},
    );
    return StudentDoubtMessage.fromJson(response);
  }
  Future<List<StudentAssessmentItem>> fetchTests({
    required String accessToken,
    String? assessmentType,
    int limit = 50,
  }) async {
    final query = <String, dynamic>{'limit': limit, 'offset': 0};
    if (assessmentType != null && assessmentType.trim().isNotEmpty) {
      query['assessment_type'] = assessmentType.trim();
    }

    final response = await _client.getMap(
      '/students/me/tests',
      accessToken: accessToken,
      queryParameters: query,
    );

    final raw = response['items'] as List<dynamic>? ?? <dynamic>[];
    return raw
        .map(
          (item) =>
              StudentAssessmentItem.fromJson(item as Map<String, dynamic>),
        )
        .toList(growable: false);
  }

  Future<StudentAssessmentDetail> fetchTestDetail({
    required String accessToken,
    required String assessmentId,
  }) async {
    final response = await _client.getMap(
      '/students/me/tests/$assessmentId',
      accessToken: accessToken,
    );
    return StudentAssessmentDetail.fromJson(response);
  }

  Future<Map<String, dynamic>> startTestAttempt({
    required String accessToken,
    required String assessmentId,
  }) {
    return _client.postMap(
      '/students/me/tests/$assessmentId/attempts',
      accessToken: accessToken,
    );
  }

  Future<Map<String, dynamic>> saveTestAnswer({
    required String accessToken,
    required String attemptId,
    required String questionId,
    required String selectedKey,
  }) {
    return _client.putMap(
      '/students/me/tests/attempts/$attemptId/answers/$questionId',
      accessToken: accessToken,
      body: {'selected_key': selectedKey},
    );
  }

  Future<StudentAssessmentAttemptDetail> fetchAttemptDetail({
    required String accessToken,
    required String attemptId,
  }) async {
    final response = await _client.getMap(
      '/students/me/tests/attempts/$attemptId',
      accessToken: accessToken,
    );
    return StudentAssessmentAttemptDetail.fromJson(response);
  }

  Future<StudentAssessmentSubmitResult> submitAttempt({
    required String accessToken,
    required String attemptId,
  }) async {
    final response = await _client.postMap(
      '/students/me/tests/attempts/$attemptId/submit',
      accessToken: accessToken,
    );
    return StudentAssessmentSubmitResult.fromJson(response);
  }
}
