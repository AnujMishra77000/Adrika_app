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

      final exists = items.any((item) => item.studentId == selected);
      return exists ? selected : items.first.studentId;
    },
    orElse: () => selected,
  );
});

final activeLinkedStudentProvider = Provider<LinkedStudent?>((ref) {
  final activeStudentId = ref.watch(activeStudentIdProvider);
  final students = ref.watch(linkedStudentsProvider);

  return students.maybeWhen(
    data: (items) {
      if (activeStudentId == null) {
        return null;
      }
      for (final item in items) {
        if (item.studentId == activeStudentId) {
          return item;
        }
      }
      return null;
    },
    orElse: () => null,
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

final parentNoticesByStudentProvider =
    FutureProvider.family<List<ParentNotice>, String>((ref, studentId) async {
  final token = _requireAccessToken(ref);
  return ref.watch(parentApiProvider).fetchNotices(
        accessToken: token,
        studentId: studentId,
        limit: 50,
      );
});

final parentHomeworkByStudentProvider =
    FutureProvider.family<List<ParentHomework>, String>((ref, studentId) async {
  final token = _requireAccessToken(ref);
  return ref.watch(parentApiProvider).fetchHomework(
        accessToken: token,
        studentId: studentId,
        limit: 50,
      );
});

final parentAttendanceFeedByStudentProvider =
    FutureProvider.family<ParentAttendanceFeed, String>((ref, studentId) async {
  final token = _requireAccessToken(ref);
  return ref.watch(parentApiProvider).fetchAttendanceFeed(
        accessToken: token,
        studentId: studentId,
        limit: 90,
      );
});

final parentResultsByStudentProvider =
    FutureProvider.family<List<ParentResult>, String>((ref, studentId) async {
  final token = _requireAccessToken(ref);
  return ref.watch(parentApiProvider).fetchResults(
        accessToken: token,
        studentId: studentId,
        limit: 50,
      );
});

final parentProgressByStudentProvider =
    FutureProvider.family<List<ParentProgress>, String>((ref, studentId) async {
  final token = _requireAccessToken(ref);
  return ref.watch(parentApiProvider).fetchProgress(
        accessToken: token,
        studentId: studentId,
        limit: 12,
      );
});

final parentFeeInvoicesByStudentProvider =
    FutureProvider.family<List<ParentFeeInvoice>, String>((ref, studentId) async {
  final token = _requireAccessToken(ref);
  return ref.watch(parentApiProvider).fetchFeeInvoices(
        accessToken: token,
        studentId: studentId,
        limit: 100,
      );
});

final parentPaymentsByStudentProvider =
    FutureProvider.family<List<ParentPayment>, String>((ref, studentId) async {
  final token = _requireAccessToken(ref);
  return ref.watch(parentApiProvider).fetchPayments(
        accessToken: token,
        studentId: studentId,
        limit: 100,
      );
});

final noticesPreviewProvider = FutureProvider<List<ParentNotice>>((ref) async {
  final studentId = ref.watch(activeStudentIdProvider);
  if (studentId == null) {
    return const <ParentNotice>[];
  }

  final items = await ref.watch(parentNoticesByStudentProvider(studentId).future);
  return items.take(5).toList(growable: false);
});

final homeworkPreviewProvider = FutureProvider<List<ParentHomework>>((ref) async {
  final studentId = ref.watch(activeStudentIdProvider);
  if (studentId == null) {
    return const <ParentHomework>[];
  }

  final items = await ref.watch(parentHomeworkByStudentProvider(studentId).future);
  return items.take(5).toList(growable: false);
});

final attendancePreviewProvider =
    FutureProvider<List<ParentAttendance>>((ref) async {
  final studentId = ref.watch(activeStudentIdProvider);
  if (studentId == null) {
    return const <ParentAttendance>[];
  }

  final feed =
      await ref.watch(parentAttendanceFeedByStudentProvider(studentId).future);
  return feed.items.take(5).toList(growable: false);
});

final resultsPreviewProvider = FutureProvider<List<ParentResult>>((ref) async {
  final studentId = ref.watch(activeStudentIdProvider);
  if (studentId == null) {
    return const <ParentResult>[];
  }

  final items = await ref.watch(parentResultsByStudentProvider(studentId).future);
  return items.take(5).toList(growable: false);
});

final progressPreviewProvider = FutureProvider<List<ParentProgress>>((ref) async {
  final studentId = ref.watch(activeStudentIdProvider);
  if (studentId == null) {
    return const <ParentProgress>[];
  }

  final items = await ref.watch(parentProgressByStudentProvider(studentId).future);
  return items.take(5).toList(growable: false);
});

final feeInvoicesProvider = FutureProvider<List<ParentFeeInvoice>>((ref) async {
  final studentId = ref.watch(activeStudentIdProvider);
  if (studentId == null) {
    return const <ParentFeeInvoice>[];
  }

  return ref.watch(parentFeeInvoicesByStudentProvider(studentId).future);
});

final paymentsProvider = FutureProvider<List<ParentPayment>>((ref) async {
  final studentId = ref.watch(activeStudentIdProvider);
  if (studentId == null) {
    return const <ParentPayment>[];
  }

  return ref.watch(parentPaymentsByStudentProvider(studentId).future);
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
