import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../features/auth/presentation/login_screen.dart';
import '../features/auth/state/auth_controller.dart';
import '../features/parent/presentation/parent_attendance_screen.dart';
import '../features/parent/presentation/parent_homework_screen.dart';
import '../features/parent/presentation/parent_notifications_screen.dart';
import '../features/parent/presentation/parent_notices_screen.dart';
import '../features/parent/presentation/parent_progress_screen.dart';
import '../features/parent/presentation/parent_results_screen.dart';
import '../features/parent/presentation/parent_shell_screen.dart';
import '../features/student/presentation/student_shell_screen.dart';
import '../features/teacher/presentation/teacher_shell_screen.dart';

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
        path: '/student',
        builder: (context, state) => const StudentShellScreen(),
      ),
      GoRoute(
        path: '/teacher',
        builder: (context, state) => const TeacherShellScreen(),
      ),
      GoRoute(
        path: '/parent',
        builder: (context, state) => const ParentShellScreen(),
        routes: [
          GoRoute(
            path: 'notifications',
            builder: (context, state) => const ParentNotificationsScreen(),
          ),
          GoRoute(
            path: 'students/:studentId/notices',
            builder: (context, state) {
              final studentId = state.pathParameters['studentId'] ?? '';
              return ParentNoticesScreen(studentId: studentId);
            },
          ),
          GoRoute(
            path: 'students/:studentId/homework',
            builder: (context, state) {
              final studentId = state.pathParameters['studentId'] ?? '';
              return ParentHomeworkScreen(studentId: studentId);
            },
          ),
          GoRoute(
            path: 'students/:studentId/attendance',
            builder: (context, state) {
              final studentId = state.pathParameters['studentId'] ?? '';
              return ParentAttendanceScreen(studentId: studentId);
            },
          ),
          GoRoute(
            path: 'students/:studentId/results',
            builder: (context, state) {
              final studentId = state.pathParameters['studentId'] ?? '';
              return ParentResultsScreen(studentId: studentId);
            },
          ),
          GoRoute(
            path: 'students/:studentId/progress',
            builder: (context, state) {
              final studentId = state.pathParameters['studentId'] ?? '';
              return ParentProgressScreen(studentId: studentId);
            },
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
      final homeRoute = _homeRouteForRoles(authState.roles);
      final path = state.matchedLocation;

      if (isBootstrapping) {
        return path == '/boot' ? null : '/boot';
      }

      if (!isLoggedIn) {
        return path == '/login' ? null : '/login';
      }

      if (homeRoute == null) {
        return path == '/unsupported' ? null : '/unsupported';
      }

      if (path == '/boot' || path == '/login' || path == '/unsupported') {
        return homeRoute;
      }

      if (_belongsToHome(path, homeRoute)) {
        return null;
      }

      return homeRoute;
    },
  );
});

String? _homeRouteForRoles(List<String> roles) {
  if (roles.contains('student')) {
    return '/student';
  }
  if (roles.contains('teacher')) {
    return '/teacher';
  }
  if (roles.contains('parent')) {
    return '/parent';
  }
  return null;
}

bool _belongsToHome(String path, String homeRoute) {
  return path == homeRoute || path.startsWith('$homeRoute/');
}

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
                'This mobile build currently supports student, teacher, and parent roles only.',
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
