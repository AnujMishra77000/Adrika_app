import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../models/parent_models.dart';

final parentApiProvider = Provider<ParentApi>((ref) {
  return ParentApi(ref.watch(apiClientProvider));
});

class ParentApi {
  ParentApi(this._client);

  final ApiClient _client;

  Future<ParentProfile> fetchProfile({required String accessToken}) async {
    final response =
        await _client.getMap('/parents/me/profile', accessToken: accessToken);
    return ParentProfile.fromJson(response);
  }

  Future<List<LinkedStudent>> fetchStudents({required String accessToken}) async {
    final response =
        await _client.getMap('/parents/me/students', accessToken: accessToken);
    final raw = response['items'] as List<dynamic>? ?? <dynamic>[];
    return raw
        .map((item) => LinkedStudent.fromJson(item as Map<String, dynamic>))
        .toList(growable: false);
  }

  Future<ParentDashboard> fetchDashboard({
    required String accessToken,
    required String studentId,
  }) async {
    final response = await _client.getMap(
      '/parents/me/dashboard',
      accessToken: accessToken,
      queryParameters: {'student_id': studentId},
    );
    return ParentDashboard.fromJson(response);
  }

  Future<List<ParentNotice>> fetchNotices({
    required String accessToken,
    required String studentId,
    int limit = 20,
    int offset = 0,
  }) async {
    final response = await _client.getMap(
      '/parents/me/students/$studentId/notices',
      accessToken: accessToken,
      queryParameters: {'limit': limit, 'offset': offset},
    );

    final raw = response['items'] as List<dynamic>? ?? <dynamic>[];
    return raw
        .map((item) => ParentNotice.fromJson(item as Map<String, dynamic>))
        .toList(growable: false);
  }

  Future<ParentNoticeDetail> fetchNoticeDetail({
    required String accessToken,
    required String studentId,
    required String noticeId,
  }) async {
    final response = await _client.getMap(
      '/parents/me/students/$studentId/notices/$noticeId',
      accessToken: accessToken,
    );
    return ParentNoticeDetail.fromJson(response);
  }

  Future<void> markNoticeRead({
    required String accessToken,
    required String studentId,
    required String noticeId,
  }) async {
    await _client.postMap(
      '/parents/me/students/$studentId/notices/$noticeId/read',
      accessToken: accessToken,
    );
  }

  Future<List<ParentHomework>> fetchHomework({
    required String accessToken,
    required String studentId,
    int limit = 20,
    int offset = 0,
  }) async {
    final response = await _client.getMap(
      '/parents/me/students/$studentId/homework',
      accessToken: accessToken,
      queryParameters: {'limit': limit, 'offset': offset},
    );

    final raw = response['items'] as List<dynamic>? ?? <dynamic>[];
    return raw
        .map((item) => ParentHomework.fromJson(item as Map<String, dynamic>))
        .toList(growable: false);
  }

  Future<ParentAttendanceFeed> fetchAttendanceFeed({
    required String accessToken,
    required String studentId,
    int limit = 30,
    int offset = 0,
  }) async {
    final response = await _client.getMap(
      '/parents/me/students/$studentId/attendance',
      accessToken: accessToken,
      queryParameters: {'limit': limit, 'offset': offset},
    );

    return ParentAttendanceFeed.fromJson(response);
  }

  Future<List<ParentAttendance>> fetchAttendance({
    required String accessToken,
    required String studentId,
    int limit = 30,
    int offset = 0,
  }) async {
    final feed = await fetchAttendanceFeed(
      accessToken: accessToken,
      studentId: studentId,
      limit: limit,
      offset: offset,
    );
    return feed.items;
  }

  Future<List<ParentResult>> fetchResults({
    required String accessToken,
    required String studentId,
    int limit = 20,
    int offset = 0,
  }) async {
    final response = await _client.getMap(
      '/parents/me/students/$studentId/results',
      accessToken: accessToken,
      queryParameters: {'limit': limit, 'offset': offset},
    );

    final raw = response['items'] as List<dynamic>? ?? <dynamic>[];
    return raw
        .map((item) => ParentResult.fromJson(item as Map<String, dynamic>))
        .toList(growable: false);
  }

  Future<List<ParentProgress>> fetchProgress({
    required String accessToken,
    required String studentId,
    int limit = 12,
  }) async {
    final response = await _client.getMap(
      '/parents/me/students/$studentId/progress',
      accessToken: accessToken,
      queryParameters: {'limit': limit},
    );

    final raw = response['items'] as List<dynamic>? ?? <dynamic>[];
    return raw
        .map((item) => ParentProgress.fromJson(item as Map<String, dynamic>))
        .toList(growable: false);
  }

  Future<List<ParentFeeInvoice>> fetchFeeInvoices({
    required String accessToken,
    required String studentId,
    String? status,
    int limit = 50,
    int offset = 0,
  }) async {
    final query = <String, dynamic>{'limit': limit, 'offset': offset};
    if (status != null && status.isNotEmpty) {
      query['status'] = status;
    }

    final response = await _client.getMap(
      '/parents/me/students/$studentId/fees',
      accessToken: accessToken,
      queryParameters: query,
    );

    final raw = response['items'] as List<dynamic>? ?? <dynamic>[];
    return raw
        .map((item) => ParentFeeInvoice.fromJson(item as Map<String, dynamic>))
        .toList(growable: false);
  }

  Future<List<ParentPayment>> fetchPayments({
    required String accessToken,
    required String studentId,
    String? status,
    int limit = 50,
    int offset = 0,
  }) async {
    final query = <String, dynamic>{'limit': limit, 'offset': offset};
    if (status != null && status.isNotEmpty) {
      query['status'] = status;
    }

    final response = await _client.getMap(
      '/parents/me/students/$studentId/payments',
      accessToken: accessToken,
      queryParameters: query,
    );

    final raw = response['items'] as List<dynamic>? ?? <dynamic>[];
    return raw
        .map((item) => ParentPayment.fromJson(item as Map<String, dynamic>))
        .toList(growable: false);
  }

  Future<ParentPreference> fetchPreferences({required String accessToken}) async {
    final response =
        await _client.getMap('/parents/me/preferences', accessToken: accessToken);
    return ParentPreference.fromJson(response);
  }

  Future<ParentPreference> updatePreferences({
    required String accessToken,
    required ParentPreference preference,
  }) async {
    final response = await _client.putMap(
      '/parents/me/preferences',
      accessToken: accessToken,
      body: preference.toJson(),
    );
    return ParentPreference.fromJson(response);
  }

  Future<ParentNotificationList> fetchNotifications({
    required String accessToken,
    bool? isRead,
    int limit = 30,
    int offset = 0,
  }) async {
    final query = <String, dynamic>{'limit': limit, 'offset': offset};
    if (isRead != null) {
      query['is_read'] = isRead;
    }

    final response = await _client.getMap(
      '/parents/me/notifications',
      accessToken: accessToken,
      queryParameters: query,
    );

    final raw = response['items'] as List<dynamic>? ?? <dynamic>[];
    final notifications = raw
        .map((item) => ParentNotification.fromJson(item as Map<String, dynamic>))
        .toList(growable: false);

    return ParentNotificationList(
      items: notifications,
      unreadCount: (response['unread_count'] as num?)?.toInt() ?? 0,
    );
  }

  Future<void> markNotificationRead({
    required String accessToken,
    required String notificationId,
  }) async {
    await _client.postMap(
      '/parents/me/notifications/$notificationId/read',
      accessToken: accessToken,
    );
  }

  Future<void> markAllNotificationsRead({required String accessToken}) async {
    await _client.postMap(
      '/parents/me/notifications/read-all',
      accessToken: accessToken,
    );
  }
}
