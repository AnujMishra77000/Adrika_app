import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
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

  Future<Map<String, dynamic>> fetchAttendanceSummary(
      {required String accessToken}) {
    return _client.getMap(
      '/students/me/attendance/summary',
      accessToken: accessToken,
    );
  }
}
