import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../models/parent_models.dart';
import '../state/parent_providers.dart';

class ParentStudentsScreen extends ConsumerWidget {
  const ParentStudentsScreen({super.key});

  Future<void> _refresh(WidgetRef ref, String studentId) async {
    ref.invalidate(linkedStudentsProvider);
    ref.invalidate(parentNoticesByStudentProvider(studentId));
    ref.invalidate(parentHomeworkByStudentProvider(studentId));
    ref.invalidate(parentAttendanceFeedByStudentProvider(studentId));
    ref.invalidate(parentResultsByStudentProvider(studentId));
    ref.invalidate(parentProgressByStudentProvider(studentId));

    await Future.wait([
      ref.read(parentNoticesByStudentProvider(studentId).future),
      ref.read(parentHomeworkByStudentProvider(studentId).future),
      ref.read(parentAttendanceFeedByStudentProvider(studentId).future),
      ref.read(parentResultsByStudentProvider(studentId).future),
      ref.read(parentProgressByStudentProvider(studentId).future),
    ]);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final students = ref.watch(linkedStudentsProvider);

    return students.when(
      data: (items) {
        if (items.isEmpty) {
          return const Center(child: Text('No linked students found.'));
        }

        final selectedId = ref.watch(activeStudentIdProvider) ?? items.first.studentId;

        final notices = ref.watch(noticesPreviewProvider);
        final homework = ref.watch(homeworkPreviewProvider);
        final attendance = ref.watch(attendancePreviewProvider);
        final results = ref.watch(resultsPreviewProvider);
        final progress = ref.watch(progressPreviewProvider);

        return RefreshIndicator(
          onRefresh: () => _refresh(ref, selectedId),
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.all(16),
            children: [
              Text('Linked Students', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 8),
              ...items.map(
                (student) => Card(
                  child: ListTile(
                    title: Text(student.fullName),
                    subtitle: Text(
                      'Admission: ${student.admissionNo} | Roll: ${student.rollNo} | Relation: ${student.relationType}',
                    ),
                    trailing: student.studentId == selectedId
                        ? const Icon(Icons.check_circle, color: Colors.green)
                        : null,
                    onTap: () {
                      ref.read(selectedStudentIdProvider.notifier).state = student.studentId;
                    },
                  ),
                ),
              ),
              const SizedBox(height: 8),
              Text('Student Snapshot', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 8),
              _SectionCard<ParentNotice>(
                title: 'Notices',
                actionLabel: 'View all',
                onActionTap: () => context.push('/parent/students/$selectedId/notices'),
                asyncValue: notices,
                itemTitle: (item) => item.title,
                itemSubtitle: (item) => item.bodyPreview,
              ),
              _SectionCard<ParentHomework>(
                title: 'Homework',
                actionLabel: 'View all',
                onActionTap: () => context.push('/parent/students/$selectedId/homework'),
                asyncValue: homework,
                itemTitle: (item) => item.title,
                itemSubtitle: (item) => 'Due: ${item.dueDate} | ${item.status}',
              ),
              _SectionCard<ParentAttendance>(
                title: 'Attendance',
                actionLabel: 'View all',
                onActionTap: () => context.push('/parent/students/$selectedId/attendance'),
                asyncValue: attendance,
                itemTitle: (item) => item.attendanceDate,
                itemSubtitle: (item) => '${item.status} | ${item.source}',
              ),
              _SectionCard<ParentResult>(
                title: 'Recent Results',
                actionLabel: 'View all',
                onActionTap: () => context.push('/parent/students/$selectedId/results'),
                asyncValue: results,
                itemTitle: (item) => 'Score ${item.score}/${item.totalMarks}',
                itemSubtitle: (item) => 'Published: ${item.publishedAt ?? '-'}',
              ),
              _SectionCard<ParentProgress>(
                title: 'Progress',
                actionLabel: 'View all',
                onActionTap: () => context.push('/parent/students/$selectedId/progress'),
                asyncValue: progress,
                itemTitle: (item) => '${item.periodType} (${item.periodStart})',
                itemSubtitle: (item) => item.metrics.entries
                    .map((entry) => '${entry.key}: ${entry.value}')
                    .join(' | '),
              ),
            ],
          ),
        );
      },
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (error, _) => Center(
        child: Text(
          error.toString(),
          style: TextStyle(color: Theme.of(context).colorScheme.error),
        ),
      ),
    );
  }
}

class _SectionCard<T> extends StatelessWidget {
  const _SectionCard({
    required this.title,
    required this.asyncValue,
    required this.itemTitle,
    required this.itemSubtitle,
    this.actionLabel,
    this.onActionTap,
  });

  final String title;
  final String? actionLabel;
  final VoidCallback? onActionTap;
  final AsyncValue<List<T>> asyncValue;
  final String Function(T item) itemTitle;
  final String Function(T item) itemSubtitle;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(title, style: Theme.of(context).textTheme.titleSmall),
                if (actionLabel != null && onActionTap != null)
                  TextButton(onPressed: onActionTap, child: Text(actionLabel!)),
              ],
            ),
            const Divider(),
            asyncValue.when(
              data: (items) {
                if (items.isEmpty) {
                  return const Text('No records found.');
                }

                return Column(
                  children: items
                      .take(3)
                      .map(
                        (item) => ListTile(
                          dense: true,
                          contentPadding: EdgeInsets.zero,
                          title: Text(itemTitle(item)),
                          subtitle: Text(itemSubtitle(item)),
                        ),
                      )
                      .toList(growable: false),
                );
              },
              loading: () => const Padding(
                padding: EdgeInsets.all(8),
                child: CircularProgressIndicator(strokeWidth: 2),
              ),
              error: (error, _) => Text(
                error.toString(),
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
