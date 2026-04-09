import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../state/student_providers.dart';
import 'student_homework_screen.dart';
import 'widgets/student_home_states.dart';

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

class StudentNotificationsScreen extends ConsumerWidget {
  const StudentNotificationsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final notifications = ref.watch(studentNotificationsProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Student Notifications')),
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
                    onTap: () =>
                        context.push('/student/notifications/${item.id}'),
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
      appBar: AppBar(title: const Text('Notification Detail')),
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
    final item = ref.watch(studentAnnouncementDetailProvider(announcementId));

    return Scaffold(
      appBar: AppBar(title: const Text('Announcement Detail')),
      body: item.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => _FeatureErrorState(
          message: error.toString(),
          onRetry: () =>
              ref.invalidate(studentAnnouncementDetailProvider(announcementId)),
        ),
        data: (announcement) {
          if (announcement == null) {
            return const Center(child: Text('Announcement not found'));
          }

          return _FeatureBodyContainer(
            title: announcement.title,
            subtitle: _formatDateTime(announcement.timestamp),
            icon: Icons.campaign_outlined,
            child: Text(
              announcement.body,
              style: Theme.of(context).textTheme.bodyLarge,
            ),
          );
        },
      ),
    );
  }
}

class StudentTodayLecturesScreen extends ConsumerWidget {
  const StudentTodayLecturesScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final summary = ref.watch(studentHomeSummaryProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Today\'s Lectures')),
      body: summary.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => _FeatureErrorState(
          message: error.toString(),
          onRetry: () => ref.invalidate(studentHomeSummaryProvider),
        ),
        data: (data) => _FeatureBodyContainer(
          title: data.todayLectures.title,
          subtitle: data.todayLectures.secondaryText,
          icon: Icons.menu_book_outlined,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _MetricLine(
                label: 'Planned sessions',
                value: data.todayLectures.primaryValue,
              ),
              _MetricLine(
                label: 'Next session',
                value: _formatDateTime(data.todayLectures.nextAt),
              ),
            ],
          ),
        ),
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
      appBar: AppBar(title: const Text('Upcoming Lecture')),
      body: summary.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => _FeatureErrorState(
          message: error.toString(),
          onRetry: () => ref.invalidate(studentHomeSummaryProvider),
        ),
        data: (data) => _FeatureBodyContainer(
          title: data.upcomingLecture.title,
          subtitle: data.upcomingLecture.secondaryText,
          icon: Icons.schedule_outlined,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _MetricLine(
                  label: 'Status', value: data.upcomingLecture.primaryValue),
              _MetricLine(
                label: 'Expected',
                value: _formatDateTime(data.upcomingLecture.nextAt),
              ),
            ],
          ),
        ),
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
      appBar: AppBar(title: const Text('Practice Test')),
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
      appBar: AppBar(title: const Text('Progress')),
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
    return const _SimpleFeaturePage(
      title: 'Chat App',
      subtitle: 'Structured communication channels will be integrated here.',
      icon: Icons.forum_outlined,
    );
  }
}

class StudentRaiseDoubtScreen extends StatelessWidget {
  const StudentRaiseDoubtScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const _SimpleFeaturePage(
      title: 'Raise Doubt',
      subtitle: 'Submit subject-topic doubts and track response lifecycle.',
      icon: Icons.help_center_outlined,
    );
  }
}

class StudentAttendanceScreen extends ConsumerWidget {
  const StudentAttendanceScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final summary = ref.watch(studentHomeSummaryProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Attendance')),
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
      appBar: AppBar(title: const Text('Holiday')),
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
      appBar: AppBar(title: const Text('Homework')),
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
      appBar: AppBar(title: Text(title)),
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
    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            Color(0xFFF2F6FF),
            Color(0xFFF8FAFF),
          ],
        ),
      ),
      child: ListView(
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
                  Color(0xFF1F2A64),
                  Color(0xFF1B3B82),
                ],
              ),
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
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
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
              color: Colors.white,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: const Color(0xFFDDE6F2)),
            ),
            child: child,
          ),
        ],
      ),
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
