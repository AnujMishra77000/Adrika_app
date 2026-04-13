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
import '../features/student/presentation/student_assessment_screens.dart';
import '../features/student/presentation/student_feature_screens.dart';
import '../features/student/presentation/student_notices_screen.dart';
import '../features/student/presentation/student_shell_screen.dart';
import '../features/teacher/presentation/teacher_shell_screen.dart';

final appRouterProvider = Provider<GoRouter>((ref) {
  final isBootstrapping = ref
      .watch(authControllerProvider.select((state) => state.isBootstrapping));
  final isLoggedIn = ref
      .watch(authControllerProvider.select((state) => state.isAuthenticated));
  final roles =
      ref.watch(authControllerProvider.select((state) => state.roles));

  return GoRouter(
    initialLocation: '/boot',
    routes: [
      GoRoute(
        path: '/boot',
        builder: (context, state) => const _BootScreen(),
      ),
      GoRoute(
        path: '/login',
        builder: (context, state) =>
            const LoginScreen(mode: AuthEntryMode.menu),
      ),
      GoRoute(
        path: '/login/student',
        builder: (context, state) =>
            const LoginScreen(mode: AuthEntryMode.studentLogin),
      ),
      GoRoute(
        path: '/login/teacher',
        builder: (context, state) =>
            const LoginScreen(mode: AuthEntryMode.teacherLogin),
      ),
      GoRoute(
        path: '/register/student',
        builder: (context, state) =>
            const LoginScreen(mode: AuthEntryMode.studentRegister),
      ),
      GoRoute(
        path: '/register/teacher',
        builder: (context, state) =>
            const LoginScreen(mode: AuthEntryMode.teacherRegister),
      ),
      GoRoute(
        path: '/student',
        builder: (context, state) => const StudentShellScreen(),
      ),
      GoRoute(
        path: '/student/notices',
        pageBuilder: (context, state) =>
            _studentTransitionPage(state, const StudentNoticesScreen()),
      ),
      GoRoute(
        path: '/student/notifications',
        pageBuilder: (context, state) =>
            _studentTransitionPage(state, const StudentNotificationsScreen()),
      ),
      GoRoute(
        path: '/student/notifications/:notificationId',
        pageBuilder: (context, state) {
          final id = state.pathParameters['notificationId'] ?? '';
          return _studentTransitionPage(
            state,
            StudentNotificationDetailScreen(notificationId: id),
          );
        },
      ),
      GoRoute(
        path: '/student/announcements/:announcementId',
        pageBuilder: (context, state) {
          final id = state.pathParameters['announcementId'] ?? '';
          return _studentTransitionPage(
            state,
            StudentAnnouncementDetailScreen(announcementId: id),
          );
        },
      ),
      GoRoute(
        path: '/student/lectures/today',
        pageBuilder: (context, state) =>
            _studentTransitionPage(state, const StudentTodayLecturesScreen()),
      ),
      GoRoute(
        path: '/student/lectures/upcoming',
        pageBuilder: (context, state) =>
            _studentTransitionPage(state, const StudentUpcomingLectureScreen()),
      ),
      GoRoute(
        path: '/student/practice-tests',
        pageBuilder: (context, state) => _studentTransitionPage(
          state,
          const StudentAssessmentListScreen(
            type: StudentAssessmentViewType.practice,
          ),
        ),
      ),
      GoRoute(
        path: '/student/tests/attempts/:attemptId/result',
        pageBuilder: (context, state) {
          final attemptId = state.pathParameters['attemptId'] ?? '';
          return _studentTransitionPage(
            state,
            StudentAssessmentResultScreen(attemptId: attemptId),
          );
        },
      ),
      GoRoute(
        path: '/student/tests/attempts/:attemptId',
        pageBuilder: (context, state) {
          final attemptId = state.pathParameters['attemptId'] ?? '';
          return _studentTransitionPage(
            state,
            StudentAssessmentAttemptScreen(attemptId: attemptId),
          );
        },
      ),
      GoRoute(
        path: '/student/tests/:assessmentId',
        pageBuilder: (context, state) {
          final assessmentId = state.pathParameters['assessmentId'] ?? '';
          return _studentTransitionPage(
            state,
            StudentAssessmentDetailScreen(assessmentId: assessmentId),
          );
        },
      ),
      GoRoute(
        path: '/student/progress',
        pageBuilder: (context, state) =>
            _studentTransitionPage(state, const StudentProgressScreen()),
      ),
      GoRoute(
        path: '/student/notes',
        pageBuilder: (context, state) =>
            _studentTransitionPage(state, const StudentNotesScreen()),
      ),
      GoRoute(
        path: '/student/online-tests',
        pageBuilder: (context, state) => _studentTransitionPage(
          state,
          const StudentAssessmentListScreen(
            type: StudentAssessmentViewType.online,
          ),
        ),
      ),
      GoRoute(
        path: '/student/chat',
        pageBuilder: (context, state) =>
            _studentTransitionPage(state, const StudentChatScreen()),
      ),
      GoRoute(
        path: '/student/raise-doubt',
        pageBuilder: (context, state) =>
            _studentTransitionPage(state, const StudentRaiseDoubtScreen()),
      ),
      GoRoute(
        path: '/student/attendance',
        pageBuilder: (context, state) =>
            _studentTransitionPage(state, const StudentAttendanceScreen()),
      ),
      GoRoute(
        path: '/student/holidays',
        pageBuilder: (context, state) =>
            _studentTransitionPage(state, const StudentHolidayScreen()),
      ),
      GoRoute(
        path: '/student/homework',
        pageBuilder: (context, state) =>
            _studentTransitionPage(state, const StudentHomeworkHubScreen()),
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
      final homeRoute = _homeRouteForRoles(roles);
      final path = state.matchedLocation;

      if (isBootstrapping) {
        return path == '/boot' ? null : '/boot';
      }

      if (!isLoggedIn) {
        final isAuthPath = path == '/login' ||
            path.startsWith('/login/') ||
            path.startsWith('/register/');
        return isAuthPath ? null : '/login';
      }

      if (homeRoute == null) {
        return path == '/unsupported' ? null : '/unsupported';
      }

      if (path == '/boot' ||
          path == '/login' ||
          path.startsWith('/login/') ||
          path.startsWith('/register/') ||
          path == '/unsupported') {
        return homeRoute;
      }

      if (_belongsToHome(path, homeRoute)) {
        return null;
      }

      return homeRoute;
    },
  );
});

CustomTransitionPage<void> _studentTransitionPage(
  GoRouterState state,
  Widget child,
) {
  return CustomTransitionPage<void>(
    key: state.pageKey,
    child: child,
    transitionDuration: const Duration(milliseconds: 260),
    reverseTransitionDuration: const Duration(milliseconds: 220),
    transitionsBuilder: (context, animation, secondaryAnimation, widget) {
      final slide = Tween<Offset>(
        begin: const Offset(0.03, 0.0),
        end: Offset.zero,
      ).animate(CurvedAnimation(parent: animation, curve: Curves.easeOutCubic));

      final fade = CurvedAnimation(parent: animation, curve: Curves.easeOut);

      return FadeTransition(
        opacity: fade,
        child: SlideTransition(position: slide, child: widget),
      );
    },
  );
}

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
