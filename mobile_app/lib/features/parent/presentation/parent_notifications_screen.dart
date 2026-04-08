import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/app_exception.dart';
import '../../auth/state/auth_controller.dart';
import '../data/parent_api.dart';
import '../state/parent_providers.dart';

class ParentNotificationsScreen extends ConsumerStatefulWidget {
  const ParentNotificationsScreen({super.key});

  @override
  ConsumerState<ParentNotificationsScreen> createState() =>
      _ParentNotificationsScreenState();
}

class _ParentNotificationsScreenState
    extends ConsumerState<ParentNotificationsScreen> {
  bool _markingAll = false;
  final Set<String> _markingIds = <String>{};

  Future<String?> _token() async {
    final token = ref.read(authControllerProvider).accessToken;
    if (token == null || token.isEmpty) {
      return null;
    }
    return token;
  }

  Future<void> _refresh() async {
    ref.invalidate(parentNotificationsProvider);
    ref.invalidate(parentDashboardProvider);
    await ref.read(parentNotificationsProvider.future);
  }

  Future<void> _markAllRead() async {
    final token = await _token();
    if (token == null) {
      return;
    }

    setState(() {
      _markingAll = true;
    });

    try {
      await ref
          .read(parentApiProvider)
          .markAllNotificationsRead(accessToken: token);
      await _refresh();

      if (!mounted) {
        return;
      }

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('All notifications marked as read.')),
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
          _markingAll = false;
        });
      }
    }
  }

  Future<void> _markOneRead(String notificationId) async {
    final token = await _token();
    if (token == null) {
      return;
    }

    setState(() {
      _markingIds.add(notificationId);
    });

    try {
      await ref.read(parentApiProvider).markNotificationRead(
            accessToken: token,
            notificationId: notificationId,
          );
      await _refresh();
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
          _markingIds.remove(notificationId);
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final notifications = ref.watch(parentNotificationsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Notifications'),
        actions: [
          TextButton(
            onPressed: _markingAll ? null : _markAllRead,
            child: _markingAll
                ? const SizedBox(
                    width: 14,
                    height: 14,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Text('Mark all read'),
          ),
        ],
      ),
      body: notifications.when(
        data: (data) {
          if (data.items.isEmpty) {
            return RefreshIndicator(
              onRefresh: _refresh,
              child: ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                children: const [
                  SizedBox(height: 240),
                  Center(child: Text('No notifications available.')),
                ],
              ),
            );
          }

          return RefreshIndicator(
            onRefresh: _refresh,
            child: ListView.builder(
              physics: const AlwaysScrollableScrollPhysics(),
              itemCount: data.items.length,
              itemBuilder: (context, index) {
                final item = data.items[index];
                final marking = _markingIds.contains(item.id);

                return ListTile(
                  leading: Icon(
                    item.isRead
                        ? Icons.mark_email_read_outlined
                        : Icons.mark_email_unread_outlined,
                  ),
                  title: Text(item.title),
                  subtitle: Text(item.body),
                  trailing: marking
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : item.isRead
                          ? Text(item.notificationType)
                          : TextButton(
                              onPressed: () => _markOneRead(item.id),
                              child: const Text('Mark read'),
                            ),
                );
              },
            ),
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => Center(
          child: Text(
            error.toString(),
            style: TextStyle(color: Theme.of(context).colorScheme.error),
            textAlign: TextAlign.center,
          ),
        ),
      ),
    );
  }
}
