import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../auth/state/auth_controller.dart';
import '../data/teacher_api.dart';
import '../models/teacher_models.dart';

String _requireAccessToken(Ref ref) {
  final token = ref.watch(authControllerProvider).accessToken;
  if (token == null || token.isEmpty) {
    throw StateError('Missing access token');
  }
  return token;
}

final teacherProfileProvider = FutureProvider<TeacherProfile>((ref) async {
  final token = _requireAccessToken(ref);
  return ref.watch(teacherApiProvider).fetchProfile(accessToken: token);
});

final teacherDashboardProvider = FutureProvider<TeacherDashboard>((ref) async {
  final token = _requireAccessToken(ref);
  return ref.watch(teacherApiProvider).fetchDashboard(accessToken: token);
});

final teacherAssignmentsProvider =
    FutureProvider<List<TeacherAssignment>>((ref) async {
  final token = _requireAccessToken(ref);
  return ref.watch(teacherApiProvider).fetchAssignments(accessToken: token);
});

final teacherNoticesProvider = FutureProvider<List<TeacherNotice>>((ref) async {
  final token = _requireAccessToken(ref);
  return ref.watch(teacherApiProvider).fetchNotices(accessToken: token);
});
