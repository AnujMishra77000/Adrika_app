import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/parent_models.dart';
import '../state/parent_providers.dart';

class ParentDashboardScreen extends ConsumerWidget {
  const ParentDashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final students = ref.watch(linkedStudentsProvider);

    return students.when(
      data: (items) {
        if (items.isEmpty) {
          return const _EmptyState(
              message: 'No linked students found for this parent account.');
        }

        final selected = ref.watch(selectedStudentIdProvider);
        final activeStudentId = selected ?? items.first.studentId;

        if (selected == null) {
          Future.microtask(() {
            ref.read(selectedStudentIdProvider.notifier).state =
                items.first.studentId;
          });
        }

        final dashboard = ref.watch(parentDashboardProvider);

        return ListView(
          padding: const EdgeInsets.all(16),
          children: [
            _StudentSelector(
              students: items,
              selectedStudentId: activeStudentId,
            ),
            const SizedBox(height: 12),
            dashboard.when(
              data: (data) => _DashboardMetrics(data: data),
              loading: () => const Center(
                  child: Padding(
                padding: EdgeInsets.all(24),
                child: CircularProgressIndicator(),
              )),
              error: (error, _) => _ErrorState(message: error.toString()),
            ),
          ],
        );
      },
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (error, _) => _ErrorState(message: error.toString()),
    );
  }
}

class _StudentSelector extends ConsumerWidget {
  const _StudentSelector({
    required this.students,
    required this.selectedStudentId,
  });

  final List<LinkedStudent> students;
  final String selectedStudentId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Selected Student',
                style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            DropdownButtonFormField<String>(
              key: ValueKey(selectedStudentId),
              initialValue: selectedStudentId,
              isExpanded: true,
              decoration: const InputDecoration(border: OutlineInputBorder()),
              items: students
                  .map(
                    (student) => DropdownMenuItem<String>(
                      value: student.studentId,
                      child: Text('${student.fullName} (${student.rollNo})'),
                    ),
                  )
                  .toList(growable: false),
              onChanged: (value) {
                if (value != null) {
                  ref.read(selectedStudentIdProvider.notifier).state = value;
                }
              },
            ),
          ],
        ),
      ),
    );
  }
}

class _DashboardMetrics extends StatelessWidget {
  const _DashboardMetrics({required this.data});

  final ParentDashboard data;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 12,
      runSpacing: 12,
      children: [
        _MetricCard(
          title: 'Unread Notifications',
          value: '${data.unreadNotifications}',
          icon: Icons.notifications_active_outlined,
        ),
        _MetricCard(
          title: 'Pending Homework',
          value: '${data.pendingHomeworkCount}',
          icon: Icons.assignment_outlined,
        ),
        _MetricCard(
          title: 'Attendance',
          value: '${data.attendancePercentage.toStringAsFixed(1)}%',
          icon: Icons.fact_check_outlined,
        ),
        _MetricCard(
          title: 'Upcoming Tests',
          value: '${data.upcomingTestsCount}',
          icon: Icons.quiz_outlined,
        ),
        _MetricCard(
          title: 'Pending Fee Invoices',
          value: '${data.pendingFeeInvoices}',
          icon: Icons.receipt_long_outlined,
        ),
      ],
    );
  }
}

class _MetricCard extends StatelessWidget {
  const _MetricCard({
    required this.title,
    required this.value,
    required this.icon,
  });

  final String title;
  final String value;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 170,
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(icon),
              const SizedBox(height: 8),
              Text(value, style: Theme.of(context).textTheme.headlineSmall),
              const SizedBox(height: 4),
              Text(title),
            ],
          ),
        ),
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Text(message, textAlign: TextAlign.center),
      ),
    );
  }
}

class _ErrorState extends StatelessWidget {
  const _ErrorState({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Text(
          message,
          style: TextStyle(color: Theme.of(context).colorScheme.error),
          textAlign: TextAlign.center,
        ),
      ),
    );
  }
}
