import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/config/app_env.dart';
import '../../../core/utils/attachment_opener.dart';
import '../../auth/state/auth_controller.dart';
import '../data/student_api.dart';
import '../models/student_models.dart';
import '../state/student_providers.dart';
import 'student_homework_screen.dart';
import 'widgets/student_home_states.dart';
import 'widgets/student_page_background.dart';

String _formatDate(DateTime? value) {
  if (value == null) {
    return 'Not available';
  }
  return '${value.day}/${value.month}/${value.year}';
}

String _formatDateTime(DateTime? value) {
  if (value == null) {
    return 'Not available';
  }
  final hour = value.hour.toString().padLeft(2, '0');
  final minute = value.minute.toString().padLeft(2, '0');
  return '${value.day}/${value.month}/${value.year} $hour:$minute';
}

AppBar _featureAppBar(String title) {
  return AppBar(
    elevation: 0,
    scrolledUnderElevation: 0,
    backgroundColor: Colors.transparent,
    flexibleSpace: const DecoratedBox(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            Color(0xFF27154A),
            Color(0xFF162C5C),
          ],
        ),
      ),
    ),
    title: Text(
      title,
      style: const TextStyle(
        color: Colors.white,
        fontWeight: FontWeight.w700,
      ),
    ),
  );
}

class StudentNotificationsScreen extends ConsumerWidget {
  const StudentNotificationsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final notifications = ref.watch(studentNotificationsProvider);

    return Scaffold(
      backgroundColor: const Color(0xFF130C2C),
      appBar: _featureAppBar('Student Notifications'),
      body: notifications.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => _FeatureErrorState(
          message: error.toString(),
          onRetry: () => ref.invalidate(studentNotificationsProvider),
        ),
        data: (items) {
          if (items.isEmpty) {
            return ListView(
              padding: const EdgeInsets.all(16),
              children: const [
                StudentHomeEmptyState(
                  title: 'No notifications',
                  subtitle: 'You are all caught up.',
                ),
              ],
            );
          }

          return RefreshIndicator(
            onRefresh: () async {
              ref.invalidate(studentNotificationsProvider);
              await ref.read(studentNotificationsProvider.future);
            },
            child: ListView.separated(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.fromLTRB(16, 14, 16, 18),
              itemCount: items.length,
              separatorBuilder: (_, __) => const SizedBox(height: 10),
              itemBuilder: (context, index) {
                final item = items[index];
                return Material(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(14),
                  child: InkWell(
                    borderRadius: BorderRadius.circular(14),
                    onTap: () {
                      final noticeId = item.noticeId;
                      if (noticeId != null && noticeId.isNotEmpty) {
                        context.push('/student/announcements/$noticeId');
                        return;
                      }
                      context.push('/student/notifications/${item.id}');
                    },
                    child: Ink(
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(14),
                        border: Border.all(
                          color: item.isRead
                              ? const Color(0xFFDDE6F2)
                              : const Color(0xFF9AA6FF),
                        ),
                      ),
                      child: Padding(
                        padding: const EdgeInsets.all(14),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Icon(
                                  item.isRead
                                      ? Icons.mark_email_read_outlined
                                      : Icons.mark_email_unread_outlined,
                                  size: 18,
                                  color: item.isRead
                                      ? const Color(0xFF64748B)
                                      : const Color(0xFF5B5CE2),
                                ),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: Text(
                                    item.title,
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    style: Theme.of(context)
                                        .textTheme
                                        .titleSmall
                                        ?.copyWith(
                                          fontWeight: FontWeight.w700,
                                        ),
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 8),
                            Text(
                              item.previewText,
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                              style: Theme.of(context)
                                  .textTheme
                                  .bodyMedium
                                  ?.copyWith(
                                    color: const Color(0xFF334155),
                                  ),
                            ),
                            const SizedBox(height: 8),
                            Text(
                              _formatDateTime(item.timestamp),
                              style: Theme.of(context)
                                  .textTheme
                                  .labelMedium
                                  ?.copyWith(
                                    color: const Color(0xFF64748B),
                                  ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                );
              },
            ),
          );
        },
      ),
    );
  }
}

class StudentNotificationDetailScreen extends ConsumerWidget {
  const StudentNotificationDetailScreen({
    super.key,
    required this.notificationId,
  });

  final String notificationId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final item = ref.watch(studentNotificationDetailProvider(notificationId));

    return Scaffold(
      backgroundColor: const Color(0xFF130C2C),
      appBar: _featureAppBar('Notification Detail'),
      body: item.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => _FeatureErrorState(
          message: error.toString(),
          onRetry: () =>
              ref.invalidate(studentNotificationDetailProvider(notificationId)),
        ),
        data: (notification) {
          if (notification == null) {
            return const Center(child: Text('Notification not found'));
          }

          return _FeatureBodyContainer(
            title: notification.title,
            subtitle: _formatDateTime(notification.timestamp),
            icon: Icons.notifications_active_outlined,
            child: Text(
              notification.body,
              style: Theme.of(context).textTheme.bodyLarge,
            ),
          );
        },
      ),
    );
  }
}

class StudentAnnouncementDetailScreen extends ConsumerWidget {
  const StudentAnnouncementDetailScreen({
    super.key,
    required this.announcementId,
  });

  final String announcementId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detail = ref.watch(studentNoticeDetailProvider(announcementId));

    return Scaffold(
      backgroundColor: const Color(0xFF130C2C),
      appBar: _featureAppBar('Announcement Detail'),
      body: detail.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => _FeatureErrorState(
          message: error.toString(),
          onRetry: () => ref.invalidate(studentNoticeDetailProvider(announcementId)),
        ),
        data: (notice) {
          return _FeatureBodyContainer(
            title: notice.title,
            subtitle: _formatDateTime(notice.publishAt),
            icon: Icons.campaign_outlined,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  notice.body,
                  style: Theme.of(context).textTheme.bodyLarge,
                ),
                if (notice.attachments.isNotEmpty) ...[
                  const SizedBox(height: 16),
                  _NoticeAttachmentList(
                    attachments: notice.attachments,
                    accessToken: ref.watch(
                      authControllerProvider.select((state) => state.accessToken),
                    ),
                  ),
                ],
              ],
            ),
          );
        },
      ),
    );
  }
}

class _NoticeAttachmentList extends StatelessWidget {
  const _NoticeAttachmentList({
    required this.attachments,
    required this.accessToken,
  });

  final List<StudentNoticeAttachment> attachments;
  final String? accessToken;

  Future<void> _openAttachment(
    BuildContext context,
    StudentNoticeAttachment attachment,
    String resolvedUrl,
  ) async {
    final messenger = ScaffoldMessenger.of(context);
    messenger.showSnackBar(
      const SnackBar(
        content: Text('Opening attachment...'),
        duration: Duration(milliseconds: 900),
      ),
    );

    try {
      await AttachmentOpener.openFromUrl(
        url: resolvedUrl,
        fileName: attachment.fileName,
        contentType: attachment.contentType,
        accessToken: accessToken,
      );
    } catch (error) {
      if (!context.mounted) {
        return;
      }
      messenger.showSnackBar(
        SnackBar(
          content: Text('Unable to open attachment. $error'),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Attachments',
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.w700,
              ),
        ),
        const SizedBox(height: 8),
        ...attachments.map(
          (attachment) {
            final resolvedUrl =
                AppEnv.resolveServerUrl(attachment.fileUrl) ?? attachment.fileUrl;
            final icon = attachment.attachmentType == 'pdf'
                ? Icons.picture_as_pdf_rounded
                : Icons.image_outlined;

            return Container(
              margin: const EdgeInsets.only(bottom: 8),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.08),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.white.withValues(alpha: 0.14)),
              ),
              child: ListTile(
                onTap: () => _openAttachment(context, attachment, resolvedUrl),
                onLongPress: () async {
                  await Clipboard.setData(ClipboardData(text: resolvedUrl));
                  if (context.mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Attachment link copied')),
                    );
                  }
                },
                leading: Icon(icon, color: const Color(0xFFECE8FF)),
                title: Text(
                  attachment.fileName,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: const Color(0xFFF4F2FF),
                        fontWeight: FontWeight.w600,
                      ),
                ),
                subtitle: Text(
                  resolvedUrl,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(
                        color: const Color(0xFFB5BBD9),
                      ),
                ),
                trailing: IconButton(
                  icon: const Icon(
                    Icons.open_in_new_rounded,
                    color: Color(0xFFECE8FF),
                  ),
                  onPressed: () => _openAttachment(context, attachment, resolvedUrl),
                ),
              ),
            );
          },
        ),
      ],
    );
  }
}


class StudentTodayLecturesScreen extends ConsumerWidget {
  const StudentTodayLecturesScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final summary = ref.watch(studentHomeSummaryProvider);

    return Scaffold(
      backgroundColor: const Color(0xFF130C2C),
      appBar: _featureAppBar('Today\'s Lectures'),
      body: summary.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => _FeatureErrorState(
          message: error.toString(),
          onRetry: () => ref.invalidate(studentHomeSummaryProvider),
        ),
        data: (data) {
          final now = DateTime.now();
          final todayItems = data.scheduledLectures
              .where((item) => item.status == 'scheduled' && item.scheduledAt != null)
              .where((item) {
                final at = item.scheduledAt!;
                return at.year == now.year && at.month == now.month && at.day == now.day;
              })
              .toList(growable: false)
            ..sort((a, b) => (a.scheduledAt ?? now).compareTo(b.scheduledAt ?? now));

          return _FeatureBodyContainer(
            title: data.todayLectures.title,
            subtitle: data.todayLectures.secondaryText,
            icon: Icons.menu_book_outlined,
            child: todayItems.isEmpty
                ? const Text(
                    'No lectures scheduled for today yet.',
                    style: TextStyle(color: Color(0xFFD4D9F7)),
                  )
                : Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: todayItems
                        .take(8)
                        .map((item) => _StudentScheduledLectureTile(item: item))
                        .toList(growable: false),
                  ),
          );
        },
      ),
    );
  }
}

class StudentUpcomingLectureScreen extends ConsumerWidget {
  const StudentUpcomingLectureScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final summary = ref.watch(studentHomeSummaryProvider);

    return Scaffold(
      backgroundColor: const Color(0xFF130C2C),
      appBar: _featureAppBar('Upcoming Lecture'),
      body: summary.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => _FeatureErrorState(
          message: error.toString(),
          onRetry: () => ref.invalidate(studentHomeSummaryProvider),
        ),
        data: (data) {
          final now = DateTime.now();
          final upcomingItems = data.scheduledLectures
              .where((item) => item.status == 'scheduled' && item.scheduledAt != null)
              .where((item) => item.scheduledAt!.isAfter(now))
              .toList(growable: false)
            ..sort((a, b) => (a.scheduledAt ?? now).compareTo(b.scheduledAt ?? now));

          return _FeatureBodyContainer(
            title: data.upcomingLecture.title,
            subtitle: data.upcomingLecture.secondaryText,
            icon: Icons.schedule_outlined,
            child: upcomingItems.isEmpty
                ? const Text(
                    'No upcoming lectures at the moment.',
                    style: TextStyle(color: Color(0xFFD4D9F7)),
                  )
                : Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: upcomingItems
                        .take(10)
                        .map((item) => _StudentScheduledLectureTile(item: item))
                        .toList(growable: false),
                  ),
          );
        },
      ),
    );
  }
}

class _StudentScheduledLectureTile extends StatelessWidget {
  const _StudentScheduledLectureTile({required this.item});

  final StudentScheduledLecture item;

  @override
  Widget build(BuildContext context) {
    final scheduledText = _formatDateTime(item.scheduledAt);
    final subtitle = item.subjectName.isEmpty
        ? (item.teacherName.isEmpty ? 'Scheduled lecture' : item.teacherName)
        : '${item.subjectName} • ${item.teacherName}';

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0x171F2A65),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0x3D8FA7FF)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.schedule, color: Color(0xFFD6DDFF), size: 18),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  item.topic,
                  style: const TextStyle(
                    color: Color(0xFFEAEFFF),
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  subtitle,
                  style: const TextStyle(color: Color(0xFFB8C2E8), fontSize: 12),
                ),
                const SizedBox(height: 4),
                Text(
                  scheduledText,
                  style: const TextStyle(color: Color(0xFFA6B4E7), fontSize: 12),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class StudentPracticeTestScreen extends ConsumerWidget {
  const StudentPracticeTestScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final summary = ref.watch(studentHomeSummaryProvider);

    return Scaffold(
      backgroundColor: const Color(0xFF130C2C),
      appBar: _featureAppBar('Practice Test'),
      body: summary.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => _FeatureErrorState(
          message: error.toString(),
          onRetry: () => ref.invalidate(studentHomeSummaryProvider),
        ),
        data: (data) => _FeatureBodyContainer(
          title: 'Practice Test Hub',
          subtitle: data.practiceTest.hint,
          icon: Icons.quiz_outlined,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _MetricLine(
                label: 'Available tests',
                value: data.practiceTest.availableCount.toString(),
              ),
              _MetricLine(
                label: 'Attempted today',
                value: data.practiceTest.attemptedToday.toString(),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class StudentProgressScreen extends ConsumerWidget {
  const StudentProgressScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final summary = ref.watch(studentHomeSummaryProvider);

    return Scaffold(
      backgroundColor: const Color(0xFF130C2C),
      appBar: _featureAppBar('Progress'),
      body: summary.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => _FeatureErrorState(
          message: error.toString(),
          onRetry: () => ref.invalidate(studentHomeSummaryProvider),
        ),
        data: (data) => _FeatureBodyContainer(
          title: 'Progress Snapshot',
          subtitle: data.progress.trendLabel,
          icon: Icons.auto_graph_outlined,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _MetricLine(
                label: 'Attendance',
                value: '${data.progress.attendancePercent.toStringAsFixed(1)}%',
              ),
              _MetricLine(
                label: 'Consistency score',
                value: '${data.progress.scorePercent.toStringAsFixed(1)}%',
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class StudentNotesScreen extends StatelessWidget {
  const StudentNotesScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const _SimpleFeaturePage(
      title: 'Notes',
      subtitle: 'Class notes and study material will appear here.',
      icon: Icons.note_alt_outlined,
    );
  }
}

class StudentOnlineTestScreen extends StatelessWidget {
  const StudentOnlineTestScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const _SimpleFeaturePage(
      title: 'Online Test',
      subtitle: 'Scheduled online tests will be listed here.',
      icon: Icons.desktop_windows_outlined,
    );
  }
}

class StudentChatScreen extends StatelessWidget {
  const StudentChatScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const StudentRaiseDoubtScreen();
  }
}

class StudentRaiseDoubtScreen extends ConsumerStatefulWidget {
  const StudentRaiseDoubtScreen({super.key});

  @override
  ConsumerState<StudentRaiseDoubtScreen> createState() =>
      _StudentRaiseDoubtScreenState();
}

class _StudentRaiseDoubtScreenState extends ConsumerState<StudentRaiseDoubtScreen> {
  bool _isLoading = true;
  String? _error;
  List<StudentCompletedLecture> _lectures = const [];
  Map<String, StudentDoubtThreadSummary> _doubtByLectureId = const {};

  String? get _token => ref.read(authControllerProvider).accessToken;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final token = _token;
    if (token == null || token.isEmpty) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        _error = 'Session expired. Please login again.';
      });
      return;
    }

    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final api = ref.read(studentApiProvider);
      final lecturesFuture = api.fetchCompletedLectures(accessToken: token);
      final doubtsFuture = api.fetchMyDoubts(accessToken: token);

      final lectures = await lecturesFuture;
      final doubts = await doubtsFuture;

      final doubtByLectureId = <String, StudentDoubtThreadSummary>{};
      for (final doubt in doubts) {
        if (doubt.lectureId.isNotEmpty && !doubtByLectureId.containsKey(doubt.lectureId)) {
          doubtByLectureId[doubt.lectureId] = doubt;
        }
      }

      if (!mounted) return;
      setState(() {
        _lectures = lectures;
        _doubtByLectureId = doubtByLectureId;
        _isLoading = false;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        _error = error.toString();
      });
    }
  }

  Future<void> _openLecture(StudentCompletedLecture lecture) async {
    final existing = _doubtByLectureId[lecture.lectureId];
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => _StudentDoubtThreadScreen(
          lecture: lecture,
          existingDoubtId: existing?.id,
        ),
      ),
    );
    await _load();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF130C2C),
      appBar: _featureAppBar('Raise Doubt'),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? _FeatureErrorState(
                  message: _error!,
                  onRetry: _load,
                )
              : _lectures.isEmpty
                  ? const Center(
                      child: Text(
                        'No completed lectures available yet.',
                        style: TextStyle(color: Colors.white70),
                      ),
                    )
                  : RefreshIndicator(
                      onRefresh: _load,
                      child: ListView.separated(
                        physics: const AlwaysScrollableScrollPhysics(),
                        padding: const EdgeInsets.fromLTRB(16, 14, 16, 20),
                        itemCount: _lectures.length,
                        separatorBuilder: (_, __) => const SizedBox(height: 12),
                        itemBuilder: (context, index) {
                          final item = _lectures[index];
                          final doubt = _doubtByLectureId[item.lectureId];

                          return InkWell(
                            borderRadius: BorderRadius.circular(16),
                            onTap: () => _openLecture(item),
                            child: Ink(
                              padding: const EdgeInsets.all(14),
                              decoration: BoxDecoration(
                                borderRadius: BorderRadius.circular(16),
                                gradient: const LinearGradient(
                                  begin: Alignment.topLeft,
                                  end: Alignment.bottomRight,
                                  colors: [
                                    Color(0xFF24153F),
                                    Color(0xFF1B1D44),
                                    Color(0xFF15254E),
                                  ],
                                ),
                                border: Border.all(color: const Color(0xFF4456A8), width: 1),
                              ),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    children: [
                                      Expanded(
                                        child: Text(
                                          item.topic,
                                          style: const TextStyle(
                                            color: Colors.white,
                                            fontSize: 16,
                                            fontWeight: FontWeight.w700,
                                          ),
                                        ),
                                      ),
                                      if (doubt != null)
                                        Container(
                                          padding: const EdgeInsets.symmetric(
                                              horizontal: 10, vertical: 4),
                                          decoration: BoxDecoration(
                                            color: const Color(0xFFDBEAFE),
                                            borderRadius: BorderRadius.circular(999),
                                          ),
                                          child: Text(
                                            doubt.status,
                                            style: const TextStyle(
                                              color: Color(0xFF1E3A8A),
                                              fontWeight: FontWeight.w600,
                                            ),
                                          ),
                                        ),
                                    ],
                                  ),
                                  const SizedBox(height: 8),
                                  Text(
                                    '${item.subjectName} • ${item.teacherName}',
                                    style: const TextStyle(color: Colors.white70),
                                  ),
                                  if (item.summary.isNotEmpty) ...[
                                    const SizedBox(height: 6),
                                    Text(
                                      item.summary,
                                      style: const TextStyle(color: Colors.white60),
                                    ),
                                  ],
                                  const SizedBox(height: 8),
                                  Text(
                                    'Completed: ${_formatDateTime(item.completedAt)}',
                                    style: const TextStyle(color: Colors.white54, fontSize: 12),
                                  ),
                                ],
                              ),
                            ),
                          );
                        },
                      ),
                    ),
    );
  }
}

class _StudentDoubtThreadScreen extends ConsumerStatefulWidget {
  const _StudentDoubtThreadScreen({
    required this.lecture,
    required this.existingDoubtId,
  });

  final StudentCompletedLecture lecture;
  final String? existingDoubtId;

  @override
  ConsumerState<_StudentDoubtThreadScreen> createState() =>
      _StudentDoubtThreadScreenState();
}

class _StudentDoubtThreadScreenState extends ConsumerState<_StudentDoubtThreadScreen> {
  final TextEditingController _topicController = TextEditingController();
  final TextEditingController _descriptionController = TextEditingController();
  final TextEditingController _messageController = TextEditingController();

  StudentDoubtThreadDetail? _detail;
  String? _doubtId;
  bool _isLoading = true;
  bool _isSubmitting = false;
  String? _error;
  Timer? _pollTimer;
  DateTime? _lastMessageAt;

  String? get _token => ref.read(authControllerProvider).accessToken;
  String? get _currentUserId => ref.read(authControllerProvider).userId;

  @override
  void initState() {
    super.initState();
    _topicController.text = widget.lecture.topic;
    _doubtId = widget.existingDoubtId;
    if (_doubtId != null && _doubtId!.isNotEmpty) {
      _loadThread(initial: true);
      _pollTimer = Timer.periodic(const Duration(seconds: 5), (_) {
        _pollMessages();
      });
    } else {
      _isLoading = false;
    }
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    _topicController.dispose();
    _descriptionController.dispose();
    _messageController.dispose();
    super.dispose();
  }

  Future<void> _loadThread({required bool initial}) async {
    final token = _token;
    final doubtId = _doubtId;
    if (token == null || token.isEmpty || doubtId == null || doubtId.isEmpty) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
      });
      return;
    }

    if (initial) {
      setState(() {
        _isLoading = true;
        _error = null;
      });
    }

    try {
      final detail = await ref.read(studentApiProvider).fetchDoubtDetail(
            accessToken: token,
            doubtId: doubtId,
          );
      if (!mounted) return;

      final sorted = List<StudentDoubtMessage>.from(detail.messages)
        ..sort((a, b) {
          final aMs = a.createdAt?.millisecondsSinceEpoch ?? 0;
          final bMs = b.createdAt?.millisecondsSinceEpoch ?? 0;
          return aMs.compareTo(bMs);
        });

      setState(() {
        _detail = StudentDoubtThreadDetail(
          doubt: detail.doubt,
          description: detail.description,
          messages: sorted,
        );
        _lastMessageAt =
            sorted.isEmpty ? null : sorted.last.createdAt?.toUtc();
        _isLoading = false;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.toString();
        _isLoading = false;
      });
    }
  }

  Future<void> _pollMessages() async {
    final token = _token;
    final doubtId = _doubtId;
    if (token == null || token.isEmpty || doubtId == null || _detail == null) {
      return;
    }

    try {
      final latest = await ref.read(studentApiProvider).fetchDoubtMessages(
            accessToken: token,
            doubtId: doubtId,
            since: _lastMessageAt,
          );
      if (latest.isEmpty || !mounted) return;

      setState(() {
        final merged = List<StudentDoubtMessage>.from(_detail!.messages)
          ..addAll(latest);
        merged.sort((a, b) {
          final aMs = a.createdAt?.millisecondsSinceEpoch ?? 0;
          final bMs = b.createdAt?.millisecondsSinceEpoch ?? 0;
          return aMs.compareTo(bMs);
        });

        _detail = StudentDoubtThreadDetail(
          doubt: _detail!.doubt,
          description: _detail!.description,
          messages: merged,
        );
        _lastMessageAt = merged.last.createdAt?.toUtc();
      });
    } catch (_) {
      // silent polling failure
    }
  }

  Future<void> _raiseDoubt() async {
    final token = _token;
    if (token == null || token.isEmpty) {
      if (!mounted) return;
      setState(() {
        _error = 'Session expired. Please login again.';
      });
      return;
    }

    final topic = _topicController.text.trim();
    final description = _descriptionController.text.trim();

    if (topic.length < 2 || description.length < 5) {
      setState(() {
        _error = 'Enter valid topic and doubt description.';
      });
      return;
    }

    setState(() {
      _isSubmitting = true;
      _error = null;
    });

    try {
      final doubt = await ref.read(studentApiProvider).raiseDoubtFromLecture(
            accessToken: token,
            lectureId: widget.lecture.lectureId,
            topic: topic,
            description: description,
          );

      _doubtId = doubt.id;
      _pollTimer?.cancel();
      _pollTimer = Timer.periodic(const Duration(seconds: 5), (_) {
        _pollMessages();
      });
      await _loadThread(initial: true);
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.toString();
      });
    } finally {
      if (mounted) {
        setState(() {
          _isSubmitting = false;
        });
      }
    }
  }

  Future<void> _sendMessage() async {
    final token = _token;
    final doubtId = _doubtId;
    if (_isSubmitting || token == null || token.isEmpty || doubtId == null) {
      return;
    }

    final text = _messageController.text.trim();
    if (text.isEmpty) return;

    setState(() {
      _isSubmitting = true;
      _error = null;
    });

    try {
      final message = await ref.read(studentApiProvider).sendDoubtMessage(
            accessToken: token,
            doubtId: doubtId,
            message: text,
          );

      if (!mounted) return;
      setState(() {
        _detail = StudentDoubtThreadDetail(
          doubt: _detail!.doubt,
          description: _detail!.description,
          messages: [..._detail!.messages, message],
        );
        _lastMessageAt = message.createdAt?.toUtc() ?? _lastMessageAt;
        _messageController.clear();
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.toString();
      });
    } finally {
      if (mounted) {
        setState(() {
          _isSubmitting = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF130C2C),
      appBar: _featureAppBar('Doubt Thread'),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.fromLTRB(16, 14, 16, 20),
              children: [
                Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: const Color(0xFF3A4F8B)),
                    color: const Color(0xFF1A1F42),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        widget.lecture.topic,
                        style: const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w700,
                          fontSize: 16,
                        ),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        '${widget.lecture.subjectName} • ${widget.lecture.teacherName}',
                        style: const TextStyle(color: Colors.white70),
                      ),
                      if (widget.lecture.summary.isNotEmpty) ...[
                        const SizedBox(height: 8),
                        Text(
                          widget.lecture.summary,
                          style: const TextStyle(color: Colors.white60),
                        ),
                      ],
                    ],
                  ),
                ),
                const SizedBox(height: 14),
                if (_doubtId == null) ...[
                  TextField(
                    controller: _topicController,
                    decoration: const InputDecoration(
                      labelText: 'Doubt Topic',
                      border: OutlineInputBorder(),
                      filled: true,
                    ),
                  ),
                  const SizedBox(height: 10),
                  TextField(
                    controller: _descriptionController,
                    minLines: 4,
                    maxLines: 8,
                    decoration: const InputDecoration(
                      labelText: 'Describe your doubt',
                      border: OutlineInputBorder(),
                      filled: true,
                    ),
                  ),
                  const SizedBox(height: 10),
                  FilledButton(
                    onPressed: _isSubmitting ? null : _raiseDoubt,
                    child: _isSubmitting
                        ? const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Text('Raise Doubt'),
                  ),
                ] else ...[
                  if (_detail != null)
                    Container(
                      margin: const EdgeInsets.only(bottom: 10),
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(12),
                        color: const Color(0xFFEDE9FE),
                      ),
                      child: Row(
                        children: [
                          const Text('Status: '),
                          Text(
                            _detail!.doubt.status,
                            style: const TextStyle(fontWeight: FontWeight.w700),
                          ),
                        ],
                      ),
                    ),
                  if (_detail != null)
                    ..._detail!.messages.map((item) {
                      final mine =
                          _currentUserId != null && _currentUserId == item.senderUserId;
                      return Align(
                        alignment:
                            mine ? Alignment.centerRight : Alignment.centerLeft,
                        child: Container(
                          margin: const EdgeInsets.only(bottom: 8),
                          constraints: const BoxConstraints(maxWidth: 320),
                          padding: const EdgeInsets.all(10),
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(12),
                            color: mine
                                ? const Color(0xFFDBEAFE)
                                : const Color(0xFFE2E8F0),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                item.senderName,
                                style: const TextStyle(
                                  fontSize: 12,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                              const SizedBox(height: 4),
                              Text(item.message),
                            ],
                          ),
                        ),
                      );
                    }),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _messageController,
                          minLines: 1,
                          maxLines: 4,
                          decoration: const InputDecoration(
                            hintText: 'Type your follow-up...',
                            border: OutlineInputBorder(),
                            filled: true,
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      FilledButton(
                        onPressed: _isSubmitting ? null : _sendMessage,
                        child: _isSubmitting
                            ? const SizedBox(
                                width: 16,
                                height: 16,
                                child: CircularProgressIndicator(strokeWidth: 2),
                              )
                            : const Text('Send'),
                      ),
                    ],
                  ),
                ],
                if (_error != null) ...[
                  const SizedBox(height: 8),
                  Text(
                    _error!,
                    style: TextStyle(color: Theme.of(context).colorScheme.error),
                  ),
                ],
              ],
            ),
    );
  }
}

class StudentAttendanceScreen extends ConsumerWidget {
  const StudentAttendanceScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final summary = ref.watch(studentHomeSummaryProvider);

    return Scaffold(
      backgroundColor: const Color(0xFF130C2C),
      appBar: _featureAppBar('Attendance'),
      body: summary.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => _FeatureErrorState(
          message: error.toString(),
          onRetry: () => ref.invalidate(studentHomeSummaryProvider),
        ),
        data: (data) => _FeatureBodyContainer(
          title: 'Attendance Overview',
          subtitle: 'Auto-synced from institute attendance feed.',
          icon: Icons.fact_check_outlined,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _MetricLine(
                label: 'Attendance',
                value:
                    '${data.attendance.attendancePercent.toStringAsFixed(1)}%',
              ),
              _MetricLine(
                label: 'Present',
                value: data.attendance.presentCount.toString(),
              ),
              _MetricLine(
                label: 'Absent',
                value: data.attendance.absentCount.toString(),
              ),
              _MetricLine(
                label: 'Late',
                value: data.attendance.lateCount.toString(),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class StudentHolidayScreen extends ConsumerWidget {
  const StudentHolidayScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final summary = ref.watch(studentHomeSummaryProvider);

    return Scaffold(
      backgroundColor: const Color(0xFF130C2C),
      appBar: _featureAppBar('Holiday'),
      body: summary.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => _FeatureErrorState(
          message: error.toString(),
          onRetry: () => ref.invalidate(studentHomeSummaryProvider),
        ),
        data: (data) => _FeatureBodyContainer(
          title: data.holiday.nextHolidayName,
          subtitle: data.holiday.subtitle,
          icon: Icons.beach_access_outlined,
          child: _MetricLine(
            label: 'Date',
            value: _formatDate(data.holiday.date),
          ),
        ),
      ),
    );
  }
}

class StudentHomeworkHubScreen extends StatelessWidget {
  const StudentHomeworkHubScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF130C2C),
      appBar: _featureAppBar('Homework'),
      body: const StudentHomeworkScreen(),
    );
  }
}

class _SimpleFeaturePage extends StatelessWidget {
  const _SimpleFeaturePage({
    required this.title,
    required this.subtitle,
    required this.icon,
  });

  final String title;
  final String subtitle;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF130C2C),
      appBar: _featureAppBar(title),
      body: _FeatureBodyContainer(
        title: title,
        subtitle: subtitle,
        icon: icon,
        child: Text(
          'Backend integration ready. This module is prepared for API wiring.',
          style: Theme.of(context).textTheme.bodyLarge,
        ),
      ),
    );
  }
}

class _FeatureBodyContainer extends StatelessWidget {
  const _FeatureBodyContainer({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.child,
  });

  final String title;
  final String subtitle;
  final IconData icon;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        const StudentPageBackgroundLayer(),
        ListView(
          padding: const EdgeInsets.fromLTRB(16, 14, 16, 20),
          children: [
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(18),
                gradient: const LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [
                    Color(0xFF24153F),
                    Color(0xFF1B1D44),
                    Color(0xFF15254E),
                  ],
                ),
                border: Border.all(color: const Color(0xFFFFD46A), width: 1.1),
              ),
              child: Row(
                children: [
                  Container(
                    width: 42,
                    height: 42,
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(12),
                      color: Colors.white.withValues(alpha: 0.14),
                    ),
                    alignment: Alignment.center,
                    child: Icon(icon, color: Colors.white),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          title,
                          style:
                              Theme.of(context).textTheme.titleMedium?.copyWith(
                                    color: Colors.white,
                                    fontWeight: FontWeight.w700,
                                  ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          subtitle,
                          style:
                              Theme.of(context).textTheme.bodySmall?.copyWith(
                                    color: Colors.white.withValues(alpha: 0.9),
                                  ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.97),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: const Color(0xFFDDE6F2)),
              ),
              child: child,
            ),
          ],
        ),
      ],
    );
  }
}

class _MetricLine extends StatelessWidget {
  const _MetricLine({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Expanded(
            child: Text(
              label,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: const Color(0xFF475569),
                  ),
            ),
          ),
          Text(
            value,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  fontWeight: FontWeight.w700,
                ),
          ),
        ],
      ),
    );
  }
}

class _FeatureErrorState extends StatelessWidget {
  const _FeatureErrorState({
    required this.message,
    required this.onRetry,
  });

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              'Unable to load this page',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    color: const Color(0xFFB42318),
                  ),
            ),
            const SizedBox(height: 8),
            Text(message, textAlign: TextAlign.center),
            const SizedBox(height: 12),
            FilledButton(
              onPressed: onRetry,
              child: const Text('Retry'),
            ),
          ],
        ),
      ),
    );
  }
}
