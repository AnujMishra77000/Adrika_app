import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../auth/state/auth_controller.dart';
import '../data/parent_api.dart';
import '../models/parent_models.dart';

String _requireAccessToken(Ref ref) {
  final token = ref.watch(authControllerProvider).accessToken;
  if (token == null || token.isEmpty) {
    throw StateError('Missing access token');
  }
  return token;
}

final linkedStudentsProvider = FutureProvider<List<LinkedStudent>>((ref) async {
  final token = _requireAccessToken(ref);
  return ref.watch(parentApiProvider).fetchStudents(accessToken: token);
});

final selectedStudentIdProvider = StateProvider<String?>((ref) => null);

final activeStudentIdProvider = Provider<String?>((ref) {
  final selected = ref.watch(selectedStudentIdProvider);
  final students = ref.watch(linkedStudentsProvider);

  return students.maybeWhen(
    data: (items) {
      if (items.isEmpty) {
        return null;
      }

      if (selected == null || selected.isEmpty) {
        return items.first.studentId;
      }

      return selected;
    },
    orElse: () => selected,
  );
});

final parentProfileProvider = FutureProvider<ParentProfile>((ref) async {
  final token = _requireAccessToken(ref);
  return ref.watch(parentApiProvider).fetchProfile(accessToken: token);
});

final parentDashboardProvider = FutureProvider<ParentDashboard>((ref) async {
  final token = _requireAccessToken(ref);
  final studentId = ref.watch(activeStudentIdProvider);
  if (studentId == null) {
    throw StateError('No linked student found');
  }

  return ref.watch(parentApiProvider).fetchDashboard(
        accessToken: token,
        studentId: studentId,
      );
});

final noticesPreviewProvider = FutureProvider<List<ParentNotice>>((ref) async {
  final token = _requireAccessToken(ref);
  final studentId = ref.watch(activeStudentIdProvider);
  if (studentId == null) {
    return const <ParentNotice>[];
  }

  return ref.watch(parentApiProvider).fetchNotices(
        accessToken: token,
        studentId: studentId,
      );
});

final homeworkPreviewProvider =
    FutureProvider<List<ParentHomework>>((ref) async {
  final token = _requireAccessToken(ref);
  final studentId = ref.watch(activeStudentIdProvider);
  if (studentId == null) {
    return const <ParentHomework>[];
  }

  return ref.watch(parentApiProvider).fetchHomework(
        accessToken: token,
        studentId: studentId,
      );
});

final attendancePreviewProvider =
    FutureProvider<List<ParentAttendance>>((ref) async {
  final token = _requireAccessToken(ref);
  final studentId = ref.watch(activeStudentIdProvider);
  if (studentId == null) {
    return const <ParentAttendance>[];
  }

  return ref.watch(parentApiProvider).fetchAttendance(
        accessToken: token,
        studentId: studentId,
      );
});

final resultsPreviewProvider = FutureProvider<List<ParentResult>>((ref) async {
  final token = _requireAccessToken(ref);
  final studentId = ref.watch(activeStudentIdProvider);
  if (studentId == null) {
    return const <ParentResult>[];
  }

  return ref.watch(parentApiProvider).fetchResults(
        accessToken: token,
        studentId: studentId,
      );
});

final progressPreviewProvider =
    FutureProvider<List<ParentProgress>>((ref) async {
  final token = _requireAccessToken(ref);
  final studentId = ref.watch(activeStudentIdProvider);
  if (studentId == null) {
    return const <ParentProgress>[];
  }

  return ref.watch(parentApiProvider).fetchProgress(
        accessToken: token,
        studentId: studentId,
      );
});

final feeInvoicesProvider = FutureProvider<List<ParentFeeInvoice>>((ref) async {
  final token = _requireAccessToken(ref);
  final studentId = ref.watch(activeStudentIdProvider);
  if (studentId == null) {
    return const <ParentFeeInvoice>[];
  }

  return ref.watch(parentApiProvider).fetchFeeInvoices(
        accessToken: token,
        studentId: studentId,
      );
});

final paymentsProvider = FutureProvider<List<ParentPayment>>((ref) async {
  final token = _requireAccessToken(ref);
  final studentId = ref.watch(activeStudentIdProvider);
  if (studentId == null) {
    return const <ParentPayment>[];
  }

  return ref.watch(parentApiProvider).fetchPayments(
        accessToken: token,
        studentId: studentId,
      );
});

final parentPreferencesProvider = FutureProvider<ParentPreference>((ref) async {
  final token = _requireAccessToken(ref);
  return ref.watch(parentApiProvider).fetchPreferences(accessToken: token);
});

final parentNotificationsProvider =
    FutureProvider<ParentNotificationList>((ref) async {
  final token = _requireAccessToken(ref);
  return ref.watch(parentApiProvider).fetchNotifications(accessToken: token);
});
