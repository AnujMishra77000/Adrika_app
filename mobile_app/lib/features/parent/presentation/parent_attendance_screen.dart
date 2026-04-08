import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/parent_models.dart';
import '../state/parent_providers.dart';

class ParentAttendanceScreen extends ConsumerWidget {
  const ParentAttendanceScreen({super.key, required this.studentId});

  final String studentId;

  Future<void> _refresh(WidgetRef ref) async {
    ref.invalidate(parentAttendanceFeedByStudentProvider(studentId));
    await ref.read(parentAttendanceFeedByStudentProvider(studentId).future);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final attendance = ref.watch(parentAttendanceFeedByStudentProvider(studentId));

    return Scaffold(
      appBar: AppBar(title: const Text('Attendance History')),
      body: attendance.when(
        data: (feed) {
          return RefreshIndicator(
            onRefresh: () => _refresh(ref),
            child: ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              children: [
                _AttendanceSummaryCard(summary: feed.summary),
                const Divider(height: 1),
                if (feed.items.isEmpty)
                  const Padding(
                    padding: EdgeInsets.all(24),
                    child: Center(child: Text('No attendance records found.')),
                  )
                else
                  ...feed.items.map(
                    (item) => ListTile(
                      leading: const Icon(Icons.fact_check_outlined),
                      title: Text(item.attendanceDate),
                      subtitle: Text('Source: ${item.source}'),
                      trailing: Text(item.status),
                    ),
                  ),
              ],
            ),
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => _ErrorState(
          message: error.toString(),
          onRetry: () => ref.invalidate(parentAttendanceFeedByStudentProvider(studentId)),
        ),
      ),
    );
  }
}

class _AttendanceSummaryCard extends StatelessWidget {
  const _AttendanceSummaryCard({required this.summary});

  final ParentAttendanceSummary summary;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.all(16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Summary', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            Text('Total Days: ${summary.totalDays}'),
            Text('Present: ${summary.presentDays}'),
            Text('Absent: ${summary.absentDays}'),
            const SizedBox(height: 6),
            Text(
              'Attendance %: ${summary.attendancePercentage.toStringAsFixed(1)}',
              style: Theme.of(context).textTheme.titleSmall,
            ),
          ],
        ),
      ),
    );
  }
}

class _ErrorState extends StatelessWidget {
  const _ErrorState({required this.message, required this.onRetry});

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
              'Unable to load attendance',
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
            const SizedBox(height: 8),
            Text(message, textAlign: TextAlign.center),
            const SizedBox(height: 12),
            FilledButton(onPressed: onRetry, child: const Text('Retry')),
          ],
        ),
      ),
    );
  }
}
