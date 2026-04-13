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

final teacherScheduledLecturesProvider =
    FutureProvider<List<TeacherScheduledLecture>>((ref) async {
  final token = _requireAccessToken(ref);
  return ref
      .watch(teacherApiProvider)
      .fetchScheduledLectures(accessToken: token, limit: 30);
});

final teacherCompletedLecturesProvider =
    FutureProvider<List<TeacherCompletedLecture>>((ref) async {
  final token = _requireAccessToken(ref);
  return ref
      .watch(teacherApiProvider)
      .fetchCompletedLectures(accessToken: token, limit: 12);
});

final teacherNoticesProvider = FutureProvider<List<TeacherNotice>>((ref) async {
  final token = _requireAccessToken(ref);
  return ref.watch(teacherApiProvider).fetchNotices(accessToken: token);
});

final teacherDoubtsProvider = FutureProvider<List<TeacherDoubtItem>>((ref) async {
  final token = _requireAccessToken(ref);
  return ref.watch(teacherApiProvider).fetchDoubts(accessToken: token);
});

final teacherDoubtDetailProvider =
    FutureProvider.family<TeacherDoubtDetail, String>((ref, doubtId) async {
  final token = _requireAccessToken(ref);
  return ref
      .watch(teacherApiProvider)
      .fetchDoubtDetail(accessToken: token, doubtId: doubtId);
});
