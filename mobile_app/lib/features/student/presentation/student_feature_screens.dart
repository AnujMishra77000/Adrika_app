import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:open_filex/open_filex.dart';
import 'package:path_provider/path_provider.dart';
import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;

import '../../../core/config/app_env.dart';
import '../../../core/network/app_exception.dart';
import '../../../core/utils/attachment_opener.dart';
import '../../auth/state/auth_controller.dart';
import '../data/student_api.dart';
import '../models/student_assessment_models.dart';
import '../models/student_models.dart';
import '../state/student_providers.dart';
import 'student_homework_screen.dart';
import 'widgets/student_fade_slide_in.dart';
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

String _formatTime(DateTime? value) {
  if (value == null) {
    return 'Not available';
  }
  final hour = value.hour.toString().padLeft(2, '0');
  final minute = value.minute.toString().padLeft(2, '0');
  return '$hour:$minute IST';
}

DateTime _startOfDay(DateTime value) {
  return DateTime(value.year, value.month, value.day);
}

DateTime _startOfWeek(DateTime value) {
  final dayStart = _startOfDay(value);
  final shift = dayStart.weekday - DateTime.monday;
  return dayStart.subtract(Duration(days: shift));
}

bool _isWithinRange(
  DateTime value,
  DateTime startInclusive,
  DateTime endExclusive,
) {
  return !value.isBefore(startInclusive) && value.isBefore(endExclusive);
}

int? _extractClassLevel(String? className) {
  final text = (className ?? '').toLowerCase();
  if (text.contains('10')) {
    return 10;
  }
  if (text.contains('11')) {
    return 11;
  }
  if (text.contains('12')) {
    return 12;
  }
  return null;
}

String _normalizeStream(String? stream) {
  final value = (stream ?? '').trim().toLowerCase();
  if (value.contains('science') || value == 'sci') {
    return 'science';
  }
  if (value.contains('commerce') || value == 'comm') {
    return 'commerce';
  }
  return 'common';
}

List<String> _defaultSubjectsForProfile(StudentProfile profile) {
  final classLevel = _extractClassLevel(profile.className);
  final stream = _normalizeStream(profile.stream);

  if (classLevel == 10) {
    return const [
      'English',
      'Hindi',
      'Marathi',
      'Mathematics',
      'Science',
      'Social Science',
      'Geography',
      'History',
      'Economics',
    ];
  }

  if (classLevel == 11 && stream == 'science') {
    return const [
      'English',
      'Hindi',
      'Algebra',
      'Geometry',
      'Physics',
      'Chemistry',
      'Biology',
    ];
  }

  if (classLevel == 11 && stream == 'commerce') {
    return const [
      'English',
      'Hindi',
      'Book Keeping',
      'Economics',
      'Organization of Commerce',
      'Secretarial Practice',
      'Maths & Statistics',
    ];
  }

  if (classLevel == 12 && stream == 'science') {
    return const [
      'English',
      'Physics',
      'Chemistry',
      'Mathematics',
      'Biology',
    ];
  }

  if (classLevel == 12 && stream == 'commerce') {
    return const [
      'English',
      'Book Keeping',
      'Economics',
      'Organization of Commerce',
      'Secretarial Practice',
      'Maths & Statistics',
    ];
  }

  return const ['General'];
}

IconData _iconForSubject(String subjectName) {
  final text = subjectName.toLowerCase();
  if (text.contains('physics')) {
    return Icons.science_outlined;
  }
  if (text.contains('chemistry')) {
    return Icons.biotech_outlined;
  }
  if (text.contains('biology')) {
    return Icons.local_florist_outlined;
  }
  if (text.contains('math') ||
      text.contains('algebra') ||
      text.contains('geometry')) {
    return Icons.calculate_outlined;
  }
  if (text.contains('english') ||
      text.contains('hindi') ||
      text.contains('marathi')) {
    return Icons.translate_outlined;
  }
  if (text.contains('history') ||
      text.contains('geography') ||
      text.contains('social')) {
    return Icons.public_outlined;
  }
  if (text.contains('economics') ||
      text.contains('commerce') ||
      text.contains('book')) {
    return Icons.account_balance_outlined;
  }
  return Icons.menu_book_outlined;
}

class _SubjectCardVisual {
  const _SubjectCardVisual({
    required this.background,
    required this.assetPath,
    required this.textColor,
    required this.subtitleColor,
  });

  final Color background;
  final String? assetPath;
  final Color textColor;
  final Color subtitleColor;
}

_SubjectCardVisual _subjectCardVisual(String subjectName) {
  final text = subjectName.toLowerCase();

  if (text.contains('physics')) {
    return const _SubjectCardVisual(
      background: Color(0xFF10B5D6),
      assetPath: 'assets/subject_progress/physics.png',
      textColor: Color(0xFFFFFFFF),
      subtitleColor: Color(0xFFE6FBFF),
    );
  }
  if (text.contains('chemistry')) {
    return const _SubjectCardVisual(
      background: Color(0xFFFFD43B),
      assetPath: 'assets/subject_progress/chemistry.png',
      textColor: Color(0xFF1F2937),
      subtitleColor: Color(0xFF374151),
    );
  }
  if (text.contains('biology')) {
    return const _SubjectCardVisual(
      background: Color(0xFF36B37E),
      assetPath: 'assets/subject_progress/biology.png',
      textColor: Color(0xFFFFFFFF),
      subtitleColor: Color(0xFFE8FFF4),
    );
  }
  if (text.contains('math') ||
      text.contains('algebra') ||
      text.contains('geometry')) {
    return const _SubjectCardVisual(
      background: Color(0xFFE6711B),
      assetPath: 'assets/subject_progress/mathematics.jpg',
      textColor: Color(0xFFFFFFFF),
      subtitleColor: Color(0xFFFFF0E3),
    );
  }
  if (text.contains('hindi')) {
    return const _SubjectCardVisual(
      background: Color(0xFF7C4DFF),
      assetPath: 'assets/subject_progress/hindi.png',
      textColor: Color(0xFFFFFFFF),
      subtitleColor: Color(0xFFEDE7FF),
    );
  }
  if (text.contains('english')) {
    return const _SubjectCardVisual(
      background: Color(0xFF42A5F5),
      assetPath: 'assets/subject_progress/english.webp',
      textColor: Color(0xFFFFFFFF),
      subtitleColor: Color(0xFFE9F6FF),
    );
  }

  return const _SubjectCardVisual(
    background: Color(0xFF2D5BDE),
    assetPath: null,
    textColor: Color(0xFFFFFFFF),
    subtitleColor: StudentQuickAccessTheme.surfaceBorder,
  );
}

AppBar _featureAppBar(String title) {
  return AppBar(
    elevation: 0,
    scrolledUnderElevation: 0,
    backgroundColor: Colors.transparent,
    foregroundColor: Colors.white,
    iconTheme: const IconThemeData(color: Colors.white),
    flexibleSpace: const DecoratedBox(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            StudentQuickAccessTheme.appBarStart,
            StudentQuickAccessTheme.appBarEnd,
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

class StudentNotificationsScreen extends ConsumerStatefulWidget {
  const StudentNotificationsScreen({super.key});

  @override
  ConsumerState<StudentNotificationsScreen> createState() =>
      _StudentNotificationsScreenState();
}

class _StudentNotificationsScreenState
    extends ConsumerState<StudentNotificationsScreen> {
  bool _markingAll = false;
  final Set<String> _markingIds = <String>{};
  final Set<String> _optimisticReadIds = <String>{};

  bool _isEffectivelyRead(StudentNotificationItem item) {
    return item.isRead || _optimisticReadIds.contains(item.id);
  }

  Future<void> _refresh() async {
    ref.invalidate(studentNotificationsProvider);
    ref.invalidate(studentHomeSummaryProvider);
    ref.invalidate(studentDashboardProvider);
    await ref.read(studentNotificationsProvider.future);
  }

  Future<void> _markOneRead(
    StudentNotificationItem item, {
    bool silentError = false,
  }) async {
    if (_isEffectivelyRead(item) || _markingIds.contains(item.id)) {
      return;
    }

    setState(() {
      _optimisticReadIds.add(item.id);
      _markingIds.add(item.id);
    });

    try {
      await markStudentNotificationRead(ref, notificationId: item.id);
    } on AppException catch (error) {
      if (mounted) {
        setState(() {
          _optimisticReadIds.remove(item.id);
        });
        if (!silentError) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(error.message)),
          );
        }
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _optimisticReadIds.remove(item.id);
        });
        if (!silentError) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
                content: Text('Unable to mark notification as read')),
          );
        }
      }
    } finally {
      if (mounted) {
        setState(() {
          _markingIds.remove(item.id);
        });
      }
    }
  }

  Future<void> _markAllRead(List<StudentNotificationItem> items) async {
    if (_markingAll) {
      return;
    }
    setState(() {
      _markingAll = true;
      _optimisticReadIds.addAll(items.map((e) => e.id));
    });

    try {
      await markAllStudentNotificationsRead(ref);
      await _refresh();
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('All notifications marked as read')),
      );
    } on AppException catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _optimisticReadIds.clear();
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(error.message)),
      );
    } catch (_) {
      if (!mounted) {
        return;
      }
      setState(() {
        _optimisticReadIds.clear();
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Unable to mark all as read')),
      );
    } finally {
      if (mounted) {
        setState(() {
          _markingAll = false;
        });
      }
    }
  }

  Future<void> _openNotification(StudentNotificationItem item) async {
    unawaited(_markOneRead(item, silentError: true));

    final noticeId = item.noticeId;
    if (noticeId != null && noticeId.isNotEmpty) {
      await context.push('/student/announcements/$noticeId');
    } else {
      await context.push('/student/notifications/${item.id}');
    }

    if (!mounted) {
      return;
    }
    await _refresh();
  }

  String _sourceLabel(String source) {
    if (source.trim().isEmpty) {
      return 'SYSTEM';
    }
    return source.trim().toUpperCase();
  }

  @override
  Widget build(BuildContext context) {
    final notifications = ref.watch(studentNotificationsProvider);

    return Scaffold(
      backgroundColor: StudentQuickAccessTheme.scaffold,
      appBar: AppBar(
        elevation: 0,
        scrolledUnderElevation: 0,
        backgroundColor: Colors.transparent,
        flexibleSpace: const DecoratedBox(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                StudentQuickAccessTheme.appBarStart,
                StudentQuickAccessTheme.appBarEnd,
              ],
            ),
          ),
        ),
        title: const Text(
          'Student Notifications',
          style: TextStyle(
            color: Colors.white,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
      body: notifications.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => _FeatureErrorState(
          message: error.toString(),
          onRetry: () => ref.invalidate(studentNotificationsProvider),
        ),
        data: (items) {
          final unreadCount =
              items.where((item) => !_isEffectivelyRead(item)).length;

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
            onRefresh: _refresh,
            child: ListView.builder(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.fromLTRB(16, 14, 16, 18),
              itemCount: items.length + 1,
              itemBuilder: (context, index) {
                if (index == 0) {
                  return StudentFadeSlideIn(
                    delayMs: 20,
                    child: Container(
                      margin: const EdgeInsets.only(bottom: 12),
                      padding: const EdgeInsets.fromLTRB(14, 12, 12, 12),
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(16),
                        gradient: const LinearGradient(
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                          colors: [
                            Color(0x2A8F7BFF),
                            Color(0x223CA6FF),
                          ],
                        ),
                        border: Border.all(
                          color: Colors.white,
                        ),
                      ),
                      child: Row(
                        children: [
                          Expanded(
                            child: Text(
                              unreadCount > 0
                                  ? '$unreadCount unread notifications'
                                  : 'All notifications are read',
                              style: Theme.of(context)
                                  .textTheme
                                  .titleSmall
                                  ?.copyWith(
                                    color: Colors.white,
                                    fontWeight: FontWeight.w700,
                                  ),
                            ),
                          ),
                          TextButton(
                            onPressed:
                                _markingAll ? null : () => _markAllRead(items),
                            style: TextButton.styleFrom(
                              foregroundColor: Colors.white,
                              backgroundColor: Colors.white.withValues(
                                alpha: 0.12,
                              ),
                              padding: const EdgeInsets.symmetric(
                                horizontal: 12,
                                vertical: 8,
                              ),
                            ),
                            child: _markingAll
                                ? const SizedBox(
                                    width: 14,
                                    height: 14,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
                                      color: Colors.white,
                                    ),
                                  )
                                : const Text('Mark all read'),
                          ),
                        ],
                      ),
                    ),
                  );
                }

                final item = items[index - 1];
                final isRead = _isEffectivelyRead(item);
                final marking = _markingIds.contains(item.id);
                return StudentFadeSlideIn(
                  delayMs: 40 + ((index % 8) * 35),
                  child: Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: _StudentNotificationCard(
                      item: item,
                      isRead: isRead,
                      marking: marking,
                      sourceLabel: _sourceLabel(item.source),
                      onTap: () => _openNotification(item),
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

class _StudentNotificationCard extends StatelessWidget {
  const _StudentNotificationCard({
    required this.item,
    required this.isRead,
    required this.marking,
    required this.sourceLabel,
    required this.onTap,
  });

  final StudentNotificationItem item;
  final bool isRead;
  final bool marking;
  final String sourceLabel;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 280),
      curve: Curves.easeOutCubic,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        color: isRead
            ? Colors.white.withValues(alpha: 0.92)
            : const Color(0xFFFDFBFF),
        border: Border.all(
          color: isRead ? const Color(0x33CCD5E4) : const Color(0x666A7BFF),
          width: isRead ? 1 : 1.2,
        ),
        boxShadow: [
          BoxShadow(
            color: isRead
                ? Colors.black.withValues(alpha: 0.05)
                : const Color(0xFF6E7BFF).withValues(alpha: 0.20),
            blurRadius: isRead ? 12 : 16,
            spreadRadius: isRead ? -8 : -6,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Material(
        color: Colors.transparent,
        borderRadius: BorderRadius.circular(16),
        child: InkWell(
          borderRadius: BorderRadius.circular(16),
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    AnimatedContainer(
                      duration: const Duration(milliseconds: 260),
                      width: 28,
                      height: 28,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: isRead
                            ? const Color(0xFFE2E8F0)
                            : const Color(0xFFE7E6FF),
                      ),
                      child: Icon(
                        isRead
                            ? Icons.mark_email_read_outlined
                            : Icons.mark_email_unread_outlined,
                        size: 16,
                        color: isRead
                            ? StudentQuickAccessTheme.textMuted
                            : const Color(0xFF5148CC),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        item.title,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.titleSmall?.copyWith(
                              fontWeight: FontWeight.w700,
                              color: Color(0xFF1F2937),
                            ),
                      ),
                    ),
                    AnimatedSwitcher(
                      duration: const Duration(milliseconds: 180),
                      child: marking
                          ? const SizedBox(
                              key: ValueKey<String>('loading'),
                              width: 16,
                              height: 16,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : Icon(
                              key: ValueKey<bool>(isRead),
                              isRead
                                  ? Icons.check_circle_rounded
                                  : Icons.fiber_manual_record_rounded,
                              size: isRead ? 18 : 10,
                              color: isRead
                                  ? const Color(0xFF22C55E)
                                  : const Color(0xFF6366F1),
                            ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                Text(
                  item.previewText,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: const Color(0xFF334155),
                        height: 1.34,
                      ),
                ),
                const SizedBox(height: 10),
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 3,
                      ),
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(999),
                        color: const Color(0xFFE8F2FF),
                      ),
                      child: Text(
                        sourceLabel,
                        style: const TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.w700,
                          color: Color(0xFF1D4ED8),
                          letterSpacing: 0.2,
                        ),
                      ),
                    ),
                    const Spacer(),
                    Text(
                      _formatDateTime(item.timestamp),
                      style: Theme.of(context).textTheme.labelMedium?.copyWith(
                            color: Color(0xFF6B7280),
                          ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class StudentNotificationDetailScreen extends ConsumerStatefulWidget {
  const StudentNotificationDetailScreen({
    super.key,
    required this.notificationId,
  });

  final String notificationId;

  @override
  ConsumerState<StudentNotificationDetailScreen> createState() =>
      _StudentNotificationDetailScreenState();
}

class _StudentNotificationDetailScreenState
    extends ConsumerState<StudentNotificationDetailScreen> {
  bool _markTriggered = false;

  @override
  Widget build(BuildContext context) {
    final item =
        ref.watch(studentNotificationDetailProvider(widget.notificationId));

    return Scaffold(
      backgroundColor: StudentQuickAccessTheme.scaffold,
      appBar: _featureAppBar('Notification Detail'),
      body: item.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => _FeatureErrorState(
          message: error.toString(),
          onRetry: () => ref.invalidate(
            studentNotificationDetailProvider(widget.notificationId),
          ),
        ),
        data: (notification) {
          if (notification == null) {
            return const Center(child: Text('Notification not found'));
          }

          if (!notification.isRead && !_markTriggered) {
            _markTriggered = true;
            WidgetsBinding.instance.addPostFrameCallback((_) async {
              try {
                await markStudentNotificationRead(
                  ref,
                  notificationId: notification.id,
                );
              } catch (_) {
                // Best-effort. Detail should remain accessible.
              }
            });
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
      backgroundColor: StudentQuickAccessTheme.scaffold,
      appBar: _featureAppBar('Announcement Detail'),
      body: detail.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => _FeatureErrorState(
          message: error.toString(),
          onRetry: () =>
              ref.invalidate(studentNoticeDetailProvider(announcementId)),
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
                  'Announcement',
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        color: Color(0xFF1F2937),
                        fontWeight: FontWeight.w800,
                      ),
                ),
                const SizedBox(height: 8),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: const Color(0xFFF8FAFF),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0xFFDEE7F7)),
                  ),
                  child: Text(
                    notice.body,
                    style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                          color: const Color(0xFF1E293B),
                          height: 1.4,
                        ),
                  ),
                ),
                if (notice.attachments.isNotEmpty) ...[
                  const SizedBox(height: 16),
                  _NoticeAttachmentList(
                    attachments: notice.attachments,
                    accessToken: ref.watch(
                      authControllerProvider
                          .select((state) => state.accessToken),
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
                fontWeight: FontWeight.w800,
                color: Color(0xFF1F2937),
              ),
        ),
        const SizedBox(height: 10),
        ...attachments.asMap().entries.map(
          (entry) {
            final index = entry.key;
            final attachment = entry.value;
            final resolvedUrl = AppEnv.resolveServerUrl(attachment.fileUrl) ??
                attachment.fileUrl;
            final icon = attachment.attachmentType == 'pdf'
                ? Icons.picture_as_pdf_rounded
                : Icons.image_outlined;
            final typeLabel = attachment.attachmentType.toLowerCase() == 'pdf'
                ? 'PDF'
                : 'IMAGE';

            return StudentFadeSlideIn(
              delayMs: 50 + (index * 35),
              child: Container(
                margin: const EdgeInsets.only(bottom: 10),
                decoration: BoxDecoration(
                  color: const Color(0xFFF8FAFF),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: const Color(0xFFDCE5F7)),
                ),
                child: ListTile(
                  onTap: () =>
                      _openAttachment(context, attachment, resolvedUrl),
                  onLongPress: () async {
                    await Clipboard.setData(ClipboardData(text: resolvedUrl));
                    if (context.mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Attachment link copied')),
                      );
                    }
                  },
                  leading: Container(
                    width: 36,
                    height: 36,
                    decoration: BoxDecoration(
                      color: const Color(0xFFEEF4FF),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    alignment: Alignment.center,
                    child: Icon(icon, color: const Color(0xFF1F2937), size: 20),
                  ),
                  title: Text(
                    attachment.fileName,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: Color(0xFF1F2937),
                          fontWeight: FontWeight.w700,
                        ),
                  ),
                  subtitle: Text(
                    resolvedUrl,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.labelSmall?.copyWith(
                          color: Color(0xFF6B7280),
                        ),
                  ),
                  trailing: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 8, vertical: 2),
                        decoration: BoxDecoration(
                          color: const Color(0xFF2F2461),
                          borderRadius: BorderRadius.circular(999),
                        ),
                        child: Text(
                          typeLabel,
                          style: const TextStyle(
                            color: Color(0xFFE9DEFF),
                            fontSize: 10,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                      const SizedBox(height: 4),
                      const Icon(
                        Icons.open_in_new_rounded,
                        color: Color(0xFFE9DEFF),
                        size: 18,
                      ),
                    ],
                  ),
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
      backgroundColor: StudentQuickAccessTheme.scaffold,
      appBar: _featureAppBar("Today's Lectures"),
      body: summary.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => _FeatureErrorState(
          message: error.toString(),
          onRetry: () => ref.invalidate(studentHomeSummaryProvider),
        ),
        data: (data) {
          final now = DateTime.now();
          final today = _startOfDay(now);

          final todayItems = data.scheduledLectures
              .where((item) => item.scheduledAt != null)
              .where((item) => _isWithinRange(
                    item.scheduledAt!,
                    today,
                    today.add(const Duration(days: 1)),
                  ))
              .toList(growable: false)
            ..sort((a, b) =>
                (a.scheduledAt ?? now).compareTo(b.scheduledAt ?? now));

          return _FeatureBodyContainer(
            title: "Today's Lectures",
            subtitle: 'Asia/Kolkata live lecture timeline',
            icon: Icons.menu_book_outlined,
            contentBackgroundColor: Colors.white,
            child: todayItems.isEmpty
                ? const StudentHomeEmptyState(
                    title: 'No lecture is scheduled for today',
                    subtitle:
                        'Your next classes will appear here automatically.',
                  )
                : Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: List.generate(todayItems.length, (index) {
                      final lecture = todayItems[index];
                      return StudentFadeSlideIn(
                        delayMs: 50 * index,
                        child: _StudentLectureCard(
                          lecture: lecture,
                          onTap: () {
                            Navigator.of(context).push(
                              MaterialPageRoute<void>(
                                builder: (_) => StudentLectureDetailScreen(
                                  lecture: lecture,
                                ),
                              ),
                            );
                          },
                        ),
                      );
                    }),
                  ),
          );
        },
      ),
    );
  }
}

class StudentUpcomingLectureScreen extends ConsumerWidget {
  const StudentUpcomingLectureScreen({super.key});

  String _assessmentOpenRoute(StudentAssessmentItem item) {
    final attemptId = item.latestAttemptId?.trim() ?? '';
    final canOpenResult = attemptId.isNotEmpty &&
        (item.hasSubmitted || item.isCompleted || item.score != null);
    if (canOpenResult) {
      return '/student/tests/attempts/$attemptId/result';
    }
    return '/student/tests/${item.id}';
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final summary = ref.watch(studentHomeSummaryProvider);
    final assessments = ref.watch(studentAssessmentsProvider);

    return Scaffold(
      backgroundColor: StudentQuickAccessTheme.scaffold,
      appBar: _featureAppBar('Weekly Schedule'),
      body: summary.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => _FeatureErrorState(
          message: error.toString(),
          onRetry: () => ref.invalidate(studentHomeSummaryProvider),
        ),
        data: (data) => assessments.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (error, _) => _FeatureErrorState(
            message: error.toString(),
            onRetry: () => ref.invalidate(studentAssessmentsProvider),
          ),
          data: (tests) {
            final now = DateTime.now();
            final weekStart = _startOfWeek(now);
            final weekEnd = weekStart.add(const Duration(days: 7));

            final events = <_ScheduleTimelineItem>[
              ...data.scheduledLectures
                  .where((item) => item.scheduledAt != null)
                  .where((item) =>
                      _isWithinRange(item.scheduledAt!, weekStart, weekEnd))
                  .map(_ScheduleTimelineItem.fromLecture),
              ...tests
                  .where((item) => item.startsAt != null)
                  .where((item) =>
                      _isWithinRange(item.startsAt!, weekStart, weekEnd))
                  .map(_ScheduleTimelineItem.fromAssessment),
            ]..sort((a, b) => a.at.compareTo(b.at));

            return _FeatureBodyContainer(
              title: 'Weekly Schedule',
              subtitle:
                  '${_formatDate(weekStart)} - ${_formatDate(weekEnd.subtract(const Duration(days: 1)))}',
              icon: Icons.calendar_month_rounded,
              contentBackgroundColor: Colors.white,
              child: events.isEmpty
                  ? const StudentHomeEmptyState(
                      title: 'No lecture or test scheduled this week',
                      subtitle:
                          'Weekly timeline will update as admin publishes schedules.',
                    )
                  : Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: List.generate(events.length, (index) {
                        final event = events[index];
                        return StudentFadeSlideIn(
                          delayMs: 40 * index,
                          child: _StudentScheduleTimelineCard(
                            item: event,
                            onTap: () {
                              if (event.lecture != null) {
                                Navigator.of(context).push(
                                  MaterialPageRoute<void>(
                                    builder: (_) => StudentLectureDetailScreen(
                                      lecture: event.lecture!,
                                    ),
                                  ),
                                );
                                return;
                              }
                              if (event.assessment != null) {
                                context.push(
                                    _assessmentOpenRoute(event.assessment!));
                              }
                            },
                          ),
                        );
                      }),
                    ),
            );
          },
        ),
      ),
    );
  }
}

class _ScheduleTimelineItem {
  const _ScheduleTimelineItem({
    required this.id,
    required this.kind,
    required this.title,
    required this.subtitle,
    required this.at,
    required this.icon,
    required this.accent,
    this.lecture,
    this.assessment,
  });

  final String id;
  final String kind;
  final String title;
  final String subtitle;
  final DateTime at;
  final IconData icon;
  final Color accent;
  final StudentScheduledLecture? lecture;
  final StudentAssessmentItem? assessment;

  factory _ScheduleTimelineItem.fromLecture(StudentScheduledLecture lecture) {
    final subtitle = lecture.subjectName.isEmpty
        ? (lecture.teacherName.isEmpty ? 'Lecture' : lecture.teacherName)
        : '${lecture.subjectName} • ${lecture.teacherName}';

    return _ScheduleTimelineItem(
      id: 'lecture-${lecture.id}',
      kind: 'Lecture',
      title: lecture.topic,
      subtitle: subtitle,
      at: lecture.scheduledAt ?? DateTime.now(),
      icon: Icons.menu_book_outlined,
      accent: const Color(0xFF73D6FF),
      lecture: lecture,
    );
  }

  factory _ScheduleTimelineItem.fromAssessment(StudentAssessmentItem test) {
    final typeLabel =
        test.assessmentType == 'scheduled' ? 'Online Test' : 'Practice Test';
    final subtitle = (test.subjectName ?? '').trim().isEmpty
        ? typeLabel
        : '${test.subjectName} • $typeLabel';

    return _ScheduleTimelineItem(
      id: 'test-${test.id}',
      kind: 'Test',
      title: test.title,
      subtitle: subtitle,
      at: test.startsAt ?? DateTime.now(),
      icon: Icons.quiz_outlined,
      accent: const Color(0xFFFFC857),
      assessment: test,
    );
  }
}

class _StudentScheduleTimelineCard extends StatelessWidget {
  const _StudentScheduleTimelineCard({
    required this.item,
    required this.onTap,
  });

  final _ScheduleTimelineItem item;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final iconColor = const Color(0xFF1F2937);

    return Container(
      margin: const EdgeInsets.only(bottom: 7),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(14),
        color: Colors.white,
        border: Border.all(color: const Color(0xFFE2E8F0), width: 1.1),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF0F172A).withValues(alpha: 0.08),
            blurRadius: 14,
            spreadRadius: -9,
            offset: const Offset(0, 7),
          ),
        ],
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(14),
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 32,
                  height: 32,
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(10),
                    color: const Color(0xFFF8FAFC),
                    border: Border.all(color: const Color(0xFFE2E8F0)),
                  ),
                  alignment: Alignment.center,
                  child: Icon(
                    item.icon,
                    color: iconColor,
                    size: 17,
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        item.title,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          color: Color(0xFF0F172A),
                          fontWeight: FontWeight.w700,
                          fontSize: 12.8,
                        ),
                      ),
                      const SizedBox(height: 1.5),
                      Text(
                        item.subtitle,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          color: Color(0xFF64748B),
                          fontSize: 10.8,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Row(
                        children: [
                          Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 7, vertical: 2.5),
                            decoration: BoxDecoration(
                              color: const Color(0xFFF8FAFC),
                              borderRadius: BorderRadius.circular(999),
                              border: Border.all(
                                color: const Color(0xFFE2E8F0),
                              ),
                            ),
                            child: Text(
                              item.kind,
                              style: const TextStyle(
                                color: Color(0xFF334155),
                                fontWeight: FontWeight.w700,
                                fontSize: 10.4,
                              ),
                            ),
                          ),
                          const SizedBox(width: 7),
                          Text(
                            _formatDateTime(item.at),
                            style: const TextStyle(
                              color: Color(0xFF6B7280),
                              fontSize: 10.7,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                const Icon(
                  Icons.chevron_right_rounded,
                  color: Color(0xFF94A3B8),
                  size: 18,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _StudentLectureCard extends StatelessWidget {
  const _StudentLectureCard({
    required this.lecture,
    required this.onTap,
  });

  final StudentScheduledLecture lecture;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final subtitle = lecture.subjectName.isEmpty
        ? (lecture.teacherName.isEmpty
            ? 'Scheduled lecture'
            : lecture.teacherName)
        : '${lecture.subjectName} • ${lecture.teacherName}';

    return Container(
      margin: const EdgeInsets.only(bottom: 7),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(14),
        color: Colors.white,
        border: Border.all(color: const Color(0xFFE2E8F0), width: 1.1),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF0F172A).withValues(alpha: 0.08),
            blurRadius: 14,
            spreadRadius: -9,
            offset: const Offset(0, 7),
          ),
        ],
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(14),
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 32,
                  height: 32,
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(10),
                    color: const Color(0xFFF8FAFC),
                    border: Border.all(color: const Color(0xFFE2E8F0)),
                  ),
                  alignment: Alignment.center,
                  child: const Icon(
                    Icons.schedule_rounded,
                    color: Color(0xFF1F2937),
                    size: 17,
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        lecture.topic,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          color: Color(0xFF0F172A),
                          fontWeight: FontWeight.w700,
                          fontSize: 12.8,
                        ),
                      ),
                      const SizedBox(height: 1.5),
                      Text(
                        subtitle,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          color: Color(0xFF64748B),
                          fontSize: 10.8,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        _formatDateTime(lecture.scheduledAt),
                        style: const TextStyle(
                          color: Color(0xFF6B7280),
                          fontSize: 10.7,
                        ),
                      ),
                    ],
                  ),
                ),
                const Icon(
                  Icons.chevron_right_rounded,
                  color: Color(0xFF94A3B8),
                  size: 18,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class StudentLectureDetailScreen extends StatelessWidget {
  const StudentLectureDetailScreen({
    super.key,
    required this.lecture,
  });

  final StudentScheduledLecture lecture;

  DateTime? get _endsAt {
    final start = lecture.scheduledAt;
    if (start == null) {
      return null;
    }
    final duration = lecture.durationMinutes > 0 ? lecture.durationMinutes : 60;
    return start.add(Duration(minutes: duration));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: StudentQuickAccessTheme.scaffold,
      appBar: _featureAppBar('Lecture Details'),
      body: Stack(
        children: [
          const StudentQuickAccessBackgroundLayer(),
          ListView(
            padding: const EdgeInsets.fromLTRB(14, 12, 14, 16),
            children: [
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(14),
                  color: Colors.white,
                  border: Border.all(
                    color: const Color(0xFFE2E8F0),
                    width: 1.1,
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: const Color(0xFF0F172A).withValues(alpha: 0.08),
                      blurRadius: 14,
                      spreadRadius: -9,
                      offset: const Offset(0, 7),
                    ),
                  ],
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      lecture.topic,
                      style: const TextStyle(
                        color: Color(0xFF111827),
                        fontWeight: FontWeight.w700,
                        fontSize: 14.5,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      '${lecture.subjectName} • ${lecture.teacherName}',
                      style: const TextStyle(
                        color: Color(0xFF64748B),
                        fontSize: 12,
                      ),
                    ),
                    const SizedBox(height: 10),
                    _MetricLine(
                      label: 'Start',
                      value: _formatDateTime(lecture.scheduledAt),
                    ),
                    _MetricLine(
                      label: 'End',
                      value: _formatDateTime(_endsAt),
                    ),
                    _MetricLine(
                      label: 'Duration',
                      value: '${lecture.durationMinutes} min',
                    ),
                    if (lecture.lectureNotes.trim().isNotEmpty) ...[
                      const SizedBox(height: 10),
                      const Text(
                        'Lecture Notes',
                        style: TextStyle(
                          color: Color(0xFF111827),
                          fontWeight: FontWeight.w700,
                          fontSize: 12.5,
                        ),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        lecture.lectureNotes.trim(),
                        style: const TextStyle(
                          color: Color(0xFF334155),
                          fontSize: 12,
                          height: 1.35,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
        ],
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
      backgroundColor: StudentQuickAccessTheme.scaffold,
      appBar: _featureAppBar('Progress'),
      body: summary.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => _FeatureErrorState(
          message: error.toString(),
          onRetry: () => ref.invalidate(studentHomeSummaryProvider),
        ),
        data: (data) => _FeatureBodyContainer(
          title: 'Subject Progress',
          subtitle: data.progress.trendLabel,
          icon: Icons.auto_graph_rounded,
          contentBackgroundColor: Colors.white,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _MetricLine(
                label: 'Average score',
                value: '${data.progress.scorePercent.toStringAsFixed(1)}%',
              ),
              _MetricLine(
                label: 'Overall score',
                value:
                    '${data.progress.overallScorePercent.toStringAsFixed(1)}%',
              ),
              _MetricLine(
                label: 'Attendance',
                value: '${data.progress.attendancePercent.toStringAsFixed(1)}%',
              ),
              _MetricLine(
                label: 'Completed tests',
                value: data.progress.completedTestsCount.toString(),
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
      title: 'Study Materials',
      subtitle: 'Subject-wise notes and PDFs will appear here.',
      icon: Icons.chrome_reader_mode_rounded,
    );
  }
}

class StudentChatScreen extends StatelessWidget {
  const StudentChatScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const _SimpleFeaturePage(
      title: 'Suggestion Box',
      subtitle: 'Share your suggestions and feedback with the institute.',
      icon: Icons.lightbulb_outline_rounded,
    );
  }
}

class StudentRaiseDoubtScreen extends ConsumerStatefulWidget {
  const StudentRaiseDoubtScreen({
    super.key,
    this.appBarTitle = 'Raise Doubt',
  });

  final String appBarTitle;

  @override
  ConsumerState<StudentRaiseDoubtScreen> createState() =>
      _StudentRaiseDoubtScreenState();
}

class _StudentRaiseDoubtScreenState
    extends ConsumerState<StudentRaiseDoubtScreen> {
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
        if (doubt.lectureId.isNotEmpty &&
            !doubtByLectureId.containsKey(doubt.lectureId)) {
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
    final listBody = _isLoading
        ? const Center(child: CircularProgressIndicator())
        : _error != null
            ? _FeatureErrorState(
                message: _error!,
                onRetry: _load,
              )
            : _lectures.isEmpty
                ? ListView(
                    physics: const AlwaysScrollableScrollPhysics(),
                    padding: const EdgeInsets.fromLTRB(14, 12, 14, 16),
                    children: const [
                      StudentHomeEmptyState(
                        title: 'No completed lectures available yet',
                        subtitle:
                            'Completed lectures will appear here for doubt discussion.',
                      ),
                    ],
                  )
                : RefreshIndicator(
                    onRefresh: _load,
                    child: ListView.separated(
                      physics: const AlwaysScrollableScrollPhysics(),
                      padding: const EdgeInsets.fromLTRB(14, 12, 14, 16),
                      itemCount: _lectures.length,
                      separatorBuilder: (_, __) => const SizedBox(height: 8),
                      itemBuilder: (context, index) {
                        final item = _lectures[index];
                        final doubt = _doubtByLectureId[item.lectureId];
                        return StudentFadeSlideIn(
                          delayMs: 40 + (index * 24),
                          child: Material(
                            color: Colors.transparent,
                            borderRadius: BorderRadius.circular(14),
                            child: InkWell(
                              borderRadius: BorderRadius.circular(14),
                              onTap: () => _openLecture(item),
                              child: Ink(
                                padding:
                                    const EdgeInsets.fromLTRB(11, 10, 11, 10),
                                decoration: BoxDecoration(
                                  borderRadius: BorderRadius.circular(14),
                                  color: Colors.white,
                                  border: Border.all(
                                    color: const Color(0xFFE2E8F0),
                                    width: 1.1,
                                  ),
                                  boxShadow: [
                                    BoxShadow(
                                      color: const Color(0xFF0F172A)
                                          .withValues(alpha: 0.08),
                                      blurRadius: 14,
                                      spreadRadius: -9,
                                      offset: const Offset(0, 7),
                                    ),
                                  ],
                                ),
                                child: Row(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Container(
                                      width: 32,
                                      height: 32,
                                      decoration: BoxDecoration(
                                        color: const Color(0xFFF8FAFC),
                                        borderRadius: BorderRadius.circular(10),
                                        border: Border.all(
                                          color: const Color(0xFFE2E8F0),
                                        ),
                                      ),
                                      alignment: Alignment.center,
                                      child: const Icon(
                                        Icons.menu_book_rounded,
                                        size: 18,
                                        color: Color(0xFF1F2937),
                                      ),
                                    ),
                                    const SizedBox(width: 8),
                                    Expanded(
                                      child: Column(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.start,
                                        children: [
                                          Row(
                                            children: [
                                              Expanded(
                                                child: Text(
                                                  item.topic,
                                                  maxLines: 1,
                                                  overflow:
                                                      TextOverflow.ellipsis,
                                                  style: const TextStyle(
                                                    color: Color(0xFF111827),
                                                    fontWeight: FontWeight.w700,
                                                    fontSize: 13,
                                                  ),
                                                ),
                                              ),
                                              if (doubt != null)
                                                Container(
                                                  padding: const EdgeInsets
                                                      .symmetric(
                                                    horizontal: 8,
                                                    vertical: 3,
                                                  ),
                                                  decoration: BoxDecoration(
                                                    color:
                                                        const Color(0xFFF8FAFC),
                                                    borderRadius:
                                                        BorderRadius.circular(
                                                            999),
                                                    border: Border.all(
                                                      color: const Color(
                                                          0xFFE2E8F0),
                                                    ),
                                                  ),
                                                  child: Text(
                                                    doubt.status,
                                                    style: const TextStyle(
                                                      color: Color(0xFF334155),
                                                      fontWeight:
                                                          FontWeight.w700,
                                                      fontSize: 10.8,
                                                    ),
                                                  ),
                                                ),
                                            ],
                                          ),
                                          const SizedBox(height: 2),
                                          Text(
                                            '${item.subjectName} • ${item.teacherName}',
                                            maxLines: 1,
                                            overflow: TextOverflow.ellipsis,
                                            style: const TextStyle(
                                              color: Color(0xFF64748B),
                                              fontSize: 10.8,
                                            ),
                                          ),
                                          if (item.summary.isNotEmpty) ...[
                                            const SizedBox(height: 4),
                                            Text(
                                              item.summary,
                                              maxLines: 2,
                                              overflow: TextOverflow.ellipsis,
                                              style: const TextStyle(
                                                color: Color(0xFF475569),
                                                fontSize: 11,
                                                height: 1.25,
                                              ),
                                            ),
                                          ],
                                          const SizedBox(height: 5),
                                          Text(
                                            'Completed: ${_formatDateTime(item.completedAt)}',
                                            style: const TextStyle(
                                              color: Color(0xFF6B7280),
                                              fontSize: 10.6,
                                            ),
                                          ),
                                        ],
                                      ),
                                    ),
                                    const SizedBox(width: 6),
                                    const Icon(
                                      Icons.arrow_forward_ios_rounded,
                                      size: 14,
                                      color: Color(0xFF94A3B8),
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

    return Scaffold(
      backgroundColor: StudentQuickAccessTheme.scaffold,
      appBar: _featureAppBar(widget.appBarTitle),
      body: Stack(
        children: [
          const StudentQuickAccessBackgroundLayer(),
          listBody,
        ],
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

class _StudentDoubtThreadScreenState
    extends ConsumerState<_StudentDoubtThreadScreen> {
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
  String? _lastMessageId;

  String? get _token => ref.read(authControllerProvider).accessToken;
  String? get _currentUserId => ref.read(authControllerProvider).userId;

  List<StudentDoubtMessage> _sortedUniqueMessages(
    Iterable<StudentDoubtMessage> messages,
  ) {
    final map = <String, StudentDoubtMessage>{};
    for (final item in messages) {
      if (item.id.isEmpty) {
        continue;
      }
      map[item.id] = item;
    }
    final sorted = map.values.toList(growable: false)
      ..sort((a, b) {
        final aMs = a.createdAt?.millisecondsSinceEpoch ?? 0;
        final bMs = b.createdAt?.millisecondsSinceEpoch ?? 0;
        if (aMs != bMs) {
          return aMs.compareTo(bMs);
        }
        return a.id.compareTo(b.id);
      });
    return sorted;
  }

  void _syncCursorFromMessages(List<StudentDoubtMessage> messages) {
    if (messages.isEmpty) {
      _lastMessageAt = null;
      _lastMessageId = null;
      return;
    }

    final latest = messages.last;
    _lastMessageAt = latest.createdAt?.toUtc();
    _lastMessageId = latest.id;
  }

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

      final sorted = _sortedUniqueMessages(detail.messages);

      setState(() {
        _detail = StudentDoubtThreadDetail(
          doubt: detail.doubt,
          description: detail.description,
          messages: sorted,
        );
        _syncCursorFromMessages(sorted);
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
            sinceId: _lastMessageId,
          );
      if (latest.isEmpty || !mounted) return;

      setState(() {
        final merged = _sortedUniqueMessages([..._detail!.messages, ...latest]);

        _detail = StudentDoubtThreadDetail(
          doubt: _detail!.doubt,
          description: _detail!.description,
          messages: merged,
        );
        _syncCursorFromMessages(merged);
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
        final merged = _sortedUniqueMessages([..._detail!.messages, message]);
        _detail = StudentDoubtThreadDetail(
          doubt: _detail!.doubt,
          description: _detail!.description,
          messages: merged,
        );
        _syncCursorFromMessages(merged);
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
    final threadBody = _isLoading
        ? const Center(child: CircularProgressIndicator())
        : ListView(
            padding: const EdgeInsets.fromLTRB(14, 12, 14, 16),
            children: [
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(14),
                  color: Colors.white,
                  border:
                      Border.all(color: const Color(0xFFE2E8F0), width: 1.1),
                  boxShadow: [
                    BoxShadow(
                      color: const Color(0xFF0F172A).withValues(alpha: 0.08),
                      blurRadius: 14,
                      spreadRadius: -9,
                      offset: const Offset(0, 7),
                    ),
                  ],
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      widget.lecture.topic,
                      style: const TextStyle(
                        color: Color(0xFF111827),
                        fontWeight: FontWeight.w700,
                        fontSize: 13,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '${widget.lecture.subjectName} • ${widget.lecture.teacherName}',
                      style: const TextStyle(
                          color: Color(0xFF64748B), fontSize: 11),
                    ),
                    if (widget.lecture.summary.isNotEmpty) ...[
                      const SizedBox(height: 6),
                      Text(
                        widget.lecture.summary,
                        style: const TextStyle(
                            color: Color(0xFF475569), fontSize: 11),
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: 10),
              if (_doubtId == null) ...[
                TextField(
                  controller: _topicController,
                  decoration: InputDecoration(
                    labelText: 'Doubt Topic',
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                    enabledBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                      borderSide: const BorderSide(color: Color(0xFFE2E8F0)),
                    ),
                    filled: true,
                    fillColor: Colors.white,
                  ),
                ),
                const SizedBox(height: 8),
                TextField(
                  controller: _descriptionController,
                  minLines: 4,
                  maxLines: 8,
                  decoration: InputDecoration(
                    labelText: 'Describe your doubt',
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                    enabledBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                      borderSide: const BorderSide(color: Color(0xFFE2E8F0)),
                    ),
                    filled: true,
                    fillColor: Colors.white,
                  ),
                ),
                const SizedBox(height: 8),
                FilledButton(
                  onPressed: _isSubmitting ? null : _raiseDoubt,
                  style: FilledButton.styleFrom(
                    backgroundColor: const Color(0xFF2563EB),
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(10),
                    ),
                    padding: const EdgeInsets.symmetric(
                        horizontal: 14, vertical: 10),
                  ),
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
                    margin: const EdgeInsets.only(bottom: 8),
                    padding: const EdgeInsets.all(9),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(12),
                      color: Colors.white,
                      border: Border.all(color: const Color(0xFFE2E8F0)),
                    ),
                    child: Row(
                      children: [
                        const Text('Status: ',
                            style: TextStyle(
                                color: Color(0xFF64748B), fontSize: 11.2)),
                        Text(
                          _detail!.doubt.status,
                          style: const TextStyle(
                            fontWeight: FontWeight.w700,
                            color: Color(0xFF334155),
                            fontSize: 11.2,
                          ),
                        ),
                      ],
                    ),
                  ),
                if (_detail != null)
                  ..._detail!.messages.map((item) {
                    final mine = _currentUserId != null &&
                        _currentUserId == item.senderUserId;
                    return Align(
                      alignment:
                          mine ? Alignment.centerRight : Alignment.centerLeft,
                      child: Container(
                        margin: const EdgeInsets.only(bottom: 7),
                        constraints: const BoxConstraints(maxWidth: 320),
                        padding: const EdgeInsets.all(9),
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(12),
                          color: Colors.white,
                          border: Border.all(
                            color: mine
                                ? const Color(0xFFBFD5FF)
                                : const Color(0xFFE2E8F0),
                          ),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              item.senderName,
                              style: const TextStyle(
                                fontSize: 11,
                                fontWeight: FontWeight.w600,
                                color: Color(0xFF334155),
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              item.message,
                              style: const TextStyle(
                                color: Color(0xFF0F172A),
                                fontSize: 12,
                              ),
                            ),
                          ],
                        ),
                      ),
                    );
                  }),
                const SizedBox(height: 6),
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _messageController,
                        minLines: 1,
                        maxLines: 4,
                        decoration: InputDecoration(
                          hintText: 'Type your follow-up...',
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(12),
                          ),
                          enabledBorder: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(12),
                            borderSide:
                                const BorderSide(color: Color(0xFFE2E8F0)),
                          ),
                          filled: true,
                          fillColor: Colors.white,
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    FilledButton(
                      onPressed: _isSubmitting ? null : _sendMessage,
                      style: FilledButton.styleFrom(
                        backgroundColor: const Color(0xFF2563EB),
                        foregroundColor: Colors.white,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(10),
                        ),
                        padding: const EdgeInsets.symmetric(
                          horizontal: 12,
                          vertical: 10,
                        ),
                      ),
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
          );

    return Scaffold(
      backgroundColor: StudentQuickAccessTheme.scaffold,
      appBar: _featureAppBar('Doubt Thread'),
      body: Stack(
        children: [
          const StudentQuickAccessBackgroundLayer(),
          threadBody,
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
      backgroundColor: StudentQuickAccessTheme.scaffold,
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
      backgroundColor: StudentQuickAccessTheme.scaffold,
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
      backgroundColor: StudentQuickAccessTheme.scaffold,
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
      backgroundColor: StudentQuickAccessTheme.scaffold,
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
    this.contentBackgroundColor = StudentQuickAccessTheme.surfaceAlt,
  });

  final String title;
  final String subtitle;
  final IconData icon;
  final Widget child;
  final Color contentBackgroundColor;

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        const StudentQuickAccessBackgroundLayer(),
        ListView(
          padding: const EdgeInsets.fromLTRB(14, 12, 14, 16),
          children: [
            StudentFadeSlideIn(
              delayMs: 20,
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(14),
                  color: Colors.white,
                  boxShadow: [
                    BoxShadow(
                      color: const Color(0xFF0F172A).withValues(alpha: 0.08),
                      blurRadius: 14,
                      spreadRadius: -9,
                      offset: const Offset(0, 7),
                    ),
                  ],
                  border:
                      Border.all(color: const Color(0xFFE2E8F0), width: 1.1),
                ),
                child: LayoutBuilder(
                  builder: (context, constraints) {
                    final compact = constraints.maxWidth < 360;
                    return Row(
                      children: [
                        Container(
                          width: compact ? 30 : 33,
                          height: compact ? 30 : 33,
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(10),
                            color: const Color(0xFFF8FAFC),
                            border: Border.all(color: const Color(0xFFE2E8F0)),
                          ),
                          alignment: Alignment.center,
                          child: Icon(
                            icon,
                            color: const Color(0xFF1F2937),
                            size: compact ? 15 : 17,
                          ),
                        ),
                        const SizedBox(width: 9),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Text(
                                title,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: Theme.of(context)
                                    .textTheme
                                    .titleMedium
                                    ?.copyWith(
                                      color: const Color(0xFF111827),
                                      fontWeight: FontWeight.w700,
                                      fontSize: compact ? 13 : 13.6,
                                    ),
                              ),
                              const SizedBox(height: 1.5),
                              Text(
                                subtitle,
                                maxLines: 2,
                                overflow: TextOverflow.ellipsis,
                                style: Theme.of(context)
                                    .textTheme
                                    .bodySmall
                                    ?.copyWith(
                                      color: const Color(0xFF64748B),
                                      fontSize: compact ? 10 : 10.6,
                                    ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    );
                  },
                ),
              ),
            ),
            const SizedBox(height: 10),
            StudentFadeSlideIn(
              delayMs: 90,
              child: Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(16),
                  border:
                      Border.all(color: const Color(0xFFE2E8F0), width: 1.1),
                  boxShadow: [
                    BoxShadow(
                      color: const Color(0xFF0F172A).withValues(alpha: 0.09),
                      blurRadius: 16,
                      spreadRadius: -10,
                      offset: const Offset(0, 7),
                    ),
                  ],
                ),
                child: Theme(
                  data: Theme.of(context).copyWith(
                    textTheme: Theme.of(context).textTheme.apply(
                          bodyColor: const Color(0xFF0F172A),
                          displayColor: const Color(0xFF0F172A),
                        ),
                  ),
                  child: child,
                ),
              ),
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
                    color: Color(0xFF64748B),
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
            Text(
              message,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Color(0xFF64748B),
                  ),
            ),
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
