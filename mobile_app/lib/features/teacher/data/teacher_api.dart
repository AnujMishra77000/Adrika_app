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

  Future<List<TeacherAssignment>> fetchAssignments(
      {required String accessToken}) async {
    final response = await _client.getMap('/teachers/me/assignments',
        accessToken: accessToken);

    final raw = response['items'] as List<dynamic>? ?? <dynamic>[];
    return raw
        .map((item) => TeacherAssignment.fromJson(item as Map<String, dynamic>))
        .toList(growable: false);
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
}
