import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../auth/state/auth_controller.dart';
import '../data/student_api.dart';
import '../models/student_models.dart';

String _requireAccessToken(Ref ref) {
  final token = ref.watch(authControllerProvider).accessToken;
  if (token == null || token.isEmpty) {
    throw StateError('Missing access token');
  }
  return token;
}

final studentProfileProvider = FutureProvider<StudentProfile>((ref) async {
  final token = _requireAccessToken(ref);
  return ref.watch(studentApiProvider).fetchProfile(accessToken: token);
});

final studentDashboardProvider = FutureProvider<StudentDashboard>((ref) async {
  final token = _requireAccessToken(ref);
  return ref.watch(studentApiProvider).fetchDashboard(accessToken: token);
});

final studentNoticesProvider = FutureProvider<List<StudentNotice>>((ref) async {
  final token = _requireAccessToken(ref);
  return ref.watch(studentApiProvider).fetchNotices(accessToken: token);
});

final studentHomeworkProvider =
    FutureProvider<List<StudentHomework>>((ref) async {
  final token = _requireAccessToken(ref);
  return ref.watch(studentApiProvider).fetchHomework(accessToken: token);
});

final studentAttendanceSummaryProvider =
    FutureProvider<Map<String, dynamic>>((ref) async {
  final token = _requireAccessToken(ref);
  return ref
      .watch(studentApiProvider)
      .fetchAttendanceSummary(accessToken: token);
});
