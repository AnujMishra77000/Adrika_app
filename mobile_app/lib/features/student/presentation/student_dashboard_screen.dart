import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../state/student_providers.dart';

class StudentDashboardScreen extends ConsumerWidget {
  const StudentDashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dashboard = ref.watch(studentDashboardProvider);
    final attendance = ref.watch(studentAttendanceSummaryProvider);

    return RefreshIndicator(
      onRefresh: () async {
        ref.invalidate(studentDashboardProvider);
        ref.invalidate(studentAttendanceSummaryProvider);
        await ref.read(studentDashboardProvider.future);
        await ref.read(studentAttendanceSummaryProvider.future);
      },
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        children: [
          dashboard.when(
            data: (data) => Wrap(
              spacing: 12,
              runSpacing: 12,
              children: [
                _MetricCard(
                  title: 'Unread Notifications',
                  value: '${data.unreadNotifications}',
                ),
                _MetricCard(
                  title: 'Pending Homework',
                  value: '${data.pendingHomeworkCount}',
                ),
                _MetricCard(
                  title: 'Upcoming Tests',
                  value: '${data.upcomingTestsCount}',
                ),
                _MetricCard(
                  title: 'Attendance %',
                  value: data.attendancePercentage.toStringAsFixed(1),
                ),
              ],
            ),
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (error, _) => _ErrorView(
              message: error.toString(),
              onRetry: () => ref.invalidate(studentDashboardProvider),
            ),
          ),
          const SizedBox(height: 16),
          attendance.when(
            data: (data) {
              final present = data['present_count']?.toString() ?? '0';
              final absent = data['absent_count']?.toString() ?? '0';
              final late = data['late_count']?.toString() ?? '0';

              return Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Attendance Summary',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 8),
                      Text('Present: $present'),
                      Text('Absent: $absent'),
                      Text('Late: $late'),
                    ],
                  ),
                ),
              );
            },
            loading: () => const SizedBox.shrink(),
            error: (error, _) => _ErrorView(
              message: error.toString(),
              onRetry: () => ref.invalidate(studentAttendanceSummaryProvider),
            ),
          ),
        ],
      ),
    );
  }
}

class _MetricCard extends StatelessWidget {
  const _MetricCard({required this.title, required this.value});

  final String title;
  final String value;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 165,
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                value,
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: 8),
              Text(title),
            ],
          ),
        ),
      ),
    );
  }
}

class _ErrorView extends StatelessWidget {
  const _ErrorView({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Unable to load dashboard',
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
            const SizedBox(height: 8),
            Text(message),
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
