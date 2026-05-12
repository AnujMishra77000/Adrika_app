import "dart:async";

import "package:flutter/widgets.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";

import "../../features/auth/state/auth_controller.dart";
import "../../features/student/state/student_providers.dart";
import "../network/api_client.dart";
import "push_notification_service.dart";

class NotificationBootstrap extends ConsumerStatefulWidget {
  const NotificationBootstrap({
    super.key,
    required this.child,
  });

  final Widget child;

  @override
  ConsumerState<NotificationBootstrap> createState() =>
      _NotificationBootstrapState();
}

class _NotificationBootstrapState extends ConsumerState<NotificationBootstrap> {
  ProviderSubscription<AuthState>? _authSubscription;

  @override
  void initState() {
    super.initState();
    final service = PushNotificationService.instance;

    unawaited(
      service.initialize(onSignal: _handleNotificationSignal),
    );

    _authSubscription = ref.listenManual<AuthState>(
      authControllerProvider,
      (previous, next) {
        unawaited(
          service.syncAuthSession(
            apiClient: ref.read(apiClientProvider),
            accessToken: next.accessToken,
            userId: next.userId,
            roles: next.roles,
          ),
        );
      },
      fireImmediately: true,
    );
  }

  void _handleNotificationSignal() {
    if (!mounted) {
      return;
    }
    final roles = ref.read(authControllerProvider).roles;
    final isStudent = roles.any((role) => role.toLowerCase() == "student");
    if (!isStudent) {
      return;
    }

    ref.invalidate(studentNotificationsProvider);
    ref.invalidate(studentDashboardProvider);
    ref.invalidate(studentHomeSummaryProvider);
    ref.invalidate(studentAnnouncementsProvider);
  }

  @override
  void dispose() {
    _authSubscription?.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return widget.child;
  }
}
