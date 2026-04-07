import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../features/auth/presentation/login_screen.dart';
import '../features/auth/state/auth_controller.dart';
import '../features/parent/presentation/parent_notifications_screen.dart';
import '../features/parent/presentation/parent_shell_screen.dart';

final appRouterProvider = Provider<GoRouter>((ref) {
  final authState = ref.watch(authControllerProvider);

  return GoRouter(
    initialLocation: '/boot',
    routes: [
      GoRoute(
        path: '/boot',
        builder: (context, state) => const _BootScreen(),
      ),
      GoRoute(
        path: '/login',
        builder: (context, state) => const LoginScreen(),
      ),
      GoRoute(
        path: '/parent',
        builder: (context, state) => const ParentShellScreen(),
        routes: [
          GoRoute(
            path: 'notifications',
            builder: (context, state) => const ParentNotificationsScreen(),
          ),
        ],
      ),
      GoRoute(
        path: '/unsupported',
        builder: (context, state) => const _UnsupportedRoleScreen(),
      ),
    ],
    redirect: (_, state) {
      final isBootstrapping = authState.isBootstrapping;
      final isLoggedIn = authState.isAuthenticated;
      final isParent = authState.roles.contains('parent');
      final path = state.matchedLocation;

      if (isBootstrapping) {
        return path == '/boot' ? null : '/boot';
      }

      if (!isLoggedIn) {
        return path == '/login' ? null : '/login';
      }

      if (!isParent) {
        return path == '/unsupported' ? null : '/unsupported';
      }

      if (path == '/boot' || path == '/login' || path == '/unsupported') {
        return '/parent';
      }

      if (path.startsWith('/parent')) {
        return null;
      }

      return '/parent';
    },
  );
});

class _BootScreen extends StatelessWidget {
  const _BootScreen();

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      body: Center(
        child: CircularProgressIndicator(),
      ),
    );
  }
}

class _UnsupportedRoleScreen extends ConsumerWidget {
  const _UnsupportedRoleScreen();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      appBar: AppBar(title: const Text('Role Not Supported')),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text(
                'This mobile app build currently includes parent screens. '
                'Please use a parent account for this phase.',
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 16),
              FilledButton(
                onPressed: () {
                  ref.read(authControllerProvider.notifier).logout();
                  context.go('/login');
                },
                child: const Text('Back To Login'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
