import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../models/teacher_models.dart';

final teacherApiProvider = Provider<TeacherApi>((ref) {
  return TeacherApi(ref.watch(apiClientProvider));
});

class TeacherApi {
  TeacherApi(this._client);

  final ApiClient _client;

  Future<TeacherProfile> fetchProfile({required String accessToken}) async {
    final response =
        await _client.getMap('/teachers/me/profile', accessToken: accessToken);
    return TeacherProfile.fromJson(response);
  }

  Future<TeacherDashboard> fetchDashboard({required String accessToken}) async {
    final response = await _client.getMap(
      '/teachers/me/dashboard',
      accessToken: accessToken,
    );
    return TeacherDashboard.fromJson(response);
  }

  Future<List<TeacherAssignment>> fetchAssignments({
    required String accessToken,
  }) async {
    final response = await _client.getMap(
      '/teachers/me/assignments',
      accessToken: accessToken,
    );

    final raw = response['items'] as List<dynamic>? ?? <dynamic>[];
    return raw
        .map((item) => TeacherAssignment.fromJson(item as Map<String, dynamic>))
        .toList(growable: false);
  }

  Future<List<TeacherScheduledLecture>> fetchScheduledLectures({
    required String accessToken,
    String status = "scheduled",
    int limit = 50,
  }) async {
    final response = await _client.getMap(
      "/teachers/me/lectures/scheduled",
      accessToken: accessToken,
      queryParameters: {
        "status": status,
        "limit": limit,
        "offset": 0,
      },
    );

    final raw = response["items"] as List<dynamic>? ?? <dynamic>[];
    return raw
        .map(
          (item) =>
              TeacherScheduledLecture.fromJson(item as Map<String, dynamic>),
        )
        .toList(growable: false);
  }

  Future<List<TeacherCompletedLecture>> fetchCompletedLectures({
    required String accessToken,
    int limit = 10,
  }) async {
    final response = await _client.getMap(
      '/teachers/me/lectures/done',
      accessToken: accessToken,
      queryParameters: {
        'limit': limit,
        'offset': 0,
      },
    );

    final raw = response['items'] as List<dynamic>? ?? <dynamic>[];
    return raw
        .map(
          (item) =>
              TeacherCompletedLecture.fromJson(item as Map<String, dynamic>),
        )
        .toList(growable: false);
  }

  Future<TeacherCompletedLecture> createCompletedLecture({
    required String accessToken,
    required String subjectId,
    required String topic,
    required int classLevel,
    String? batchId,
    String? stream,
    String? summary,
  }) async {
    final payload = <String, dynamic>{
      'subject_id': subjectId,
      'topic': topic,
      'class_level': classLevel,
    };

    if (batchId != null && batchId.trim().isNotEmpty) {
      payload['batch_id'] = batchId.trim();
    }
    if (stream != null && stream.trim().isNotEmpty) {
      payload['stream'] = stream.trim().toLowerCase();
    }
    if (summary != null && summary.trim().isNotEmpty) {
      payload['summary'] = summary.trim();
    }

    final response = await _client.postMap(
      '/teachers/me/lectures/done',
      accessToken: accessToken,
      body: payload,
    );
    return TeacherCompletedLecture.fromJson(response);
  }

  Future<List<TeacherNotice>> fetchNotices({
    required String accessToken,
    int limit = 20,
  }) async {
    final response = await _client.getMap(
      '/teachers/me/notices',
      accessToken: accessToken,
      queryParameters: {'limit': limit, 'offset': 0},
    );

    final raw = response['items'] as List<dynamic>? ?? <dynamic>[];
    return raw
        .map((item) => TeacherNotice.fromJson(item as Map<String, dynamic>))
        .toList(growable: false);
  }

  Future<List<TeacherDoubtItem>> fetchDoubts({
    required String accessToken,
    String? status,
    int limit = 100,
  }) async {
    final query = <String, dynamic>{'limit': limit, 'offset': 0};
    if (status != null && status.trim().isNotEmpty) {
      query['status'] = status.trim();
    }

    final response = await _client.getMap(
      '/teachers/me/doubts',
      accessToken: accessToken,
      queryParameters: query,
    );

    final raw = response['items'] as List<dynamic>? ?? <dynamic>[];
    return raw
        .map((item) => TeacherDoubtItem.fromJson(item as Map<String, dynamic>))
        .toList(growable: false);
  }

  Future<TeacherDoubtDetail> fetchDoubtDetail({
    required String accessToken,
    required String doubtId,
  }) async {
    final response = await _client.getMap(
      '/teachers/me/doubts/$doubtId',
      accessToken: accessToken,
    );

    return TeacherDoubtDetail.fromJson(response);
  }

  Future<List<TeacherDoubtMessage>> fetchDoubtMessages({
    required String accessToken,
    required String doubtId,
    DateTime? since,
  }) async {
    final query = <String, dynamic>{};
    if (since != null) {
      query['since'] = since.toUtc().toIso8601String();
    }

    final response = await _client.getMap(
      '/teachers/me/doubts/$doubtId/messages',
      accessToken: accessToken,
      queryParameters: query,
    );
    final raw = response['items'] as List<dynamic>? ?? <dynamic>[];
    return raw
        .map(
          (item) => TeacherDoubtMessage.fromJson(item as Map<String, dynamic>),
        )
        .toList(growable: false);
  }

  Future<TeacherDoubtMessage> sendDoubtMessage({
    required String accessToken,
    required String doubtId,
    required String message,
  }) async {
    final response = await _client.postMap(
      '/teachers/me/doubts/$doubtId/messages',
      accessToken: accessToken,
      body: {'message': message},
    );
    return TeacherDoubtMessage.fromJson(response);
  }

  Future<void> updateDoubtStatus({
    required String accessToken,
    required String doubtId,
    required String status,
  }) async {
    await _client.postMap(
      '/teachers/me/doubts/$doubtId/status',
      accessToken: accessToken,
      body: {'status': status},
    );
  }
}
