import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../state/parent_providers.dart';

class ParentResultsScreen extends ConsumerWidget {
  const ParentResultsScreen({super.key, required this.studentId});

  final String studentId;

  Future<void> _refresh(WidgetRef ref) async {
    ref.invalidate(parentResultsByStudentProvider(studentId));
    await ref.read(parentResultsByStudentProvider(studentId).future);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final results = ref.watch(parentResultsByStudentProvider(studentId));

    return Scaffold(
      appBar: AppBar(title: const Text('Assessment Results')),
      body: results.when(
        data: (items) {
          if (items.isEmpty) {
            return RefreshIndicator(
              onRefresh: () => _refresh(ref),
              child: ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                children: const [
                  SizedBox(height: 240),
                  Center(child: Text('No results published yet.')),
                ],
              ),
            );
          }

          return RefreshIndicator(
            onRefresh: () => _refresh(ref),
            child: ListView.separated(
              physics: const AlwaysScrollableScrollPhysics(),
              itemCount: items.length,
              separatorBuilder: (_, __) => const Divider(height: 1),
              itemBuilder: (context, index) {
                final item = items[index];
                return ListTile(
                  leading: const Icon(Icons.assessment_outlined),
                  title: Text('Score ${item.score}/${item.totalMarks}'),
                  subtitle: Text('Assessment: ${item.assessmentId}'),
                  trailing: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Text(item.rank == null ? 'Rank: -' : 'Rank: ${item.rank}'),
                      Text(_formatDate(item.publishedAt)),
                    ],
                  ),
                );
              },
            ),
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => _ErrorState(
          message: error.toString(),
          onRetry: () => ref.invalidate(parentResultsByStudentProvider(studentId)),
        ),
      ),
    );
  }
}

String _formatDate(String? value) {
  if (value == null || value.isEmpty) {
    return '-';
  }
  return value.split('T').first;
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
              'Unable to load results',
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
