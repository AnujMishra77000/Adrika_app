import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/app_exception.dart';
import '../../auth/state/auth_controller.dart';
import '../data/parent_api.dart';
import '../models/parent_models.dart';
import '../state/parent_providers.dart';

class ParentNoticesScreen extends ConsumerStatefulWidget {
  const ParentNoticesScreen({super.key, required this.studentId});

  final String studentId;

  @override
  ConsumerState<ParentNoticesScreen> createState() => _ParentNoticesScreenState();
}

class _ParentNoticesScreenState extends ConsumerState<ParentNoticesScreen> {
  String? _loadingNoticeId;

  Future<void> _refresh() async {
    ref.invalidate(parentNoticesByStudentProvider(widget.studentId));
    await ref.read(parentNoticesByStudentProvider(widget.studentId).future);
  }

  Future<void> _openNotice(ParentNotice notice) async {
    final token = ref.read(authControllerProvider).accessToken;
    if (token == null || token.isEmpty) {
      return;
    }

    setState(() {
      _loadingNoticeId = notice.id;
    });

    try {
      final detail = await ref.read(parentApiProvider).fetchNoticeDetail(
            accessToken: token,
            studentId: widget.studentId,
            noticeId: notice.id,
          );

      if (!mounted) {
        return;
      }

      await showModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        builder: (context) => Padding(
          padding: EdgeInsets.only(
            left: 16,
            right: 16,
            top: 16,
            bottom: MediaQuery.of(context).viewInsets.bottom + 16,
          ),
          child: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(detail.title, style: Theme.of(context).textTheme.titleLarge),
                const SizedBox(height: 8),
                Text('Priority: ${detail.priority}'),
                Text('Published: ${_formatDateTime(detail.publishAt)}'),
                const SizedBox(height: 12),
                Text(detail.body),
                const SizedBox(height: 16),
                Row(
                  children: [
                    OutlinedButton(
                      onPressed: () => Navigator.of(context).pop(),
                      child: const Text('Close'),
                    ),
                    const SizedBox(width: 8),
                    if (!detail.isRead)
                      FilledButton(
                        onPressed: () async {
                          await _markNoticeRead(noticeId: detail.id, withSnack: false);
                          if (context.mounted) {
                            Navigator.of(context).pop();
                          }
                        },
                        child: const Text('Mark As Read'),
                      ),
                  ],
                ),
              ],
            ),
          ),
        ),
      );
    } on AppException catch (error) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(error.message)),
      );
    } finally {
      if (mounted) {
        setState(() {
          _loadingNoticeId = null;
        });
      }
    }
  }

  Future<void> _markNoticeRead({
    required String noticeId,
    bool withSnack = true,
  }) async {
    final token = ref.read(authControllerProvider).accessToken;
    if (token == null || token.isEmpty) {
      return;
    }

    try {
      await ref.read(parentApiProvider).markNoticeRead(
            accessToken: token,
            studentId: widget.studentId,
            noticeId: noticeId,
          );

      ref.invalidate(parentNoticesByStudentProvider(widget.studentId));
      ref.invalidate(noticesPreviewProvider);

      if (!mounted || !withSnack) {
        return;
      }

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Notice marked as read.')),
      );
    } on AppException catch (error) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(error.message)),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final notices = ref.watch(parentNoticesByStudentProvider(widget.studentId));

    return Scaffold(
      appBar: AppBar(
        title: const Text('Student Notices'),
      ),
      body: notices.when(
        data: (items) {
          if (items.isEmpty) {
            return RefreshIndicator(
              onRefresh: _refresh,
              child: ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                children: const [
                  SizedBox(height: 240),
                  Center(child: Text('No notices found for this student.')),
                ],
              ),
            );
          }

          return RefreshIndicator(
            onRefresh: _refresh,
            child: ListView.separated(
              physics: const AlwaysScrollableScrollPhysics(),
              itemCount: items.length,
              separatorBuilder: (_, __) => const Divider(height: 1),
              itemBuilder: (context, index) {
                final item = items[index];
                final isLoading = _loadingNoticeId == item.id;
                return ListTile(
                  leading: Icon(
                    item.isRead
                        ? Icons.mark_email_read_outlined
                        : Icons.mark_email_unread_outlined,
                  ),
                  title: Text(item.title),
                  subtitle: Text(item.bodyPreview),
                  trailing: isLoading
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          crossAxisAlignment: CrossAxisAlignment.end,
                          children: [
                            Text(_formatDate(item.publishAt)),
                            if (!item.isRead)
                              TextButton(
                                onPressed: () => _markNoticeRead(noticeId: item.id),
                                child: const Text('Mark read'),
                              ),
                          ],
                        ),
                  onTap: isLoading ? null : () => _openNotice(item),
                );
              },
            ),
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => _ErrorState(
          message: error.toString(),
          onRetry: () => ref.invalidate(parentNoticesByStudentProvider(widget.studentId)),
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

String _formatDateTime(String? value) {
  if (value == null || value.isEmpty) {
    return '-';
  }
  return value.replaceFirst('T', ' ').split('.').first;
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
              'Unable to load notices',
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
