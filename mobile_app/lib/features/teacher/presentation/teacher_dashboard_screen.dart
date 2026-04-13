import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../auth/state/auth_controller.dart';
import '../state/teacher_providers.dart';
import 'widgets/teacher_ui.dart';

class TeacherDashboardScreen extends ConsumerWidget {
  const TeacherDashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dashboard = ref.watch(teacherDashboardProvider);
    final fullName =
        ref.watch(authControllerProvider.select((state) => state.fullName)) ??
            'Teacher';

    return dashboard.when(
      data: (data) => TeacherGradientBackground(
        child: RefreshIndicator(
          color: TeacherPalette.oceanBlue,
          onRefresh: () async {
            ref.invalidate(teacherDashboardProvider);
            await ref.read(teacherDashboardProvider.future);
          },
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.fromLTRB(16, 14, 16, 20),
            children: [
              TeacherEntrance(
                delay: teacherStagger(0),
                child: TeacherScreenHeader(
                  title: 'Welcome, $fullName',
                  subtitle: 'Live summary of your teaching operations today.',
                  icon: Icons.auto_awesome,
                ),
              ),
              TeacherEntrance(
                delay: teacherStagger(1),
                child: TeacherSurfaceCard(
                  margin: const EdgeInsets.only(bottom: 12),
                  child: Row(
                    children: [
                      _KpiPill(
                        label: 'Batches',
                        value: '${data.assignedBatchesCount}',
                      ),
                      const SizedBox(width: 8),
                      _KpiPill(
                        label: 'Subjects',
                        value: '${data.assignedSubjectsCount}',
                      ),
                      const SizedBox(width: 8),
                      _KpiPill(
                        label: 'Doubts',
                        value: '${data.openDoubtsCount}',
                      ),
                    ],
                  ),
                ),
              ),
              GridView.count(
                crossAxisCount: 2,
                crossAxisSpacing: 10,
                mainAxisSpacing: 10,
                childAspectRatio: 1.25,
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                children: [
                  TeacherEntrance(
                    delay: teacherStagger(2),
                    child: _MetricCard(
                      title: 'Open Doubts',
                      value: '${data.openDoubtsCount}',
                      icon: Icons.question_answer_outlined,
                    ),
                  ),
                  TeacherEntrance(
                    delay: teacherStagger(3),
                    child: _MetricCard(
                      title: 'Pending Homework',
                      value: '${data.pendingHomeworkCount}',
                      icon: Icons.assignment_late_outlined,
                    ),
                  ),
                  TeacherEntrance(
                    delay: teacherStagger(4),
                    child: _MetricCard(
                      title: 'Upcoming Tests',
                      value: '${data.upcomingTestsCount}',
                      icon: Icons.timer_outlined,
                    ),
                  ),
                  TeacherEntrance(
                    delay: teacherStagger(5),
                    child: _MetricCard(
                      title: 'Unread Alerts',
                      value: '${data.unreadNotifications}',
                      icon: Icons.notifications_active_outlined,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
      loading: () => const TeacherLoadingView(),
      error: (error, _) => TeacherErrorView(
        title: 'Failed to load dashboard',
        message: error.toString(),
        onRetry: () => ref.invalidate(teacherDashboardProvider),
      ),
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
    return TeacherSurfaceCard(
      padding: const EdgeInsets.all(12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(10),
              gradient: const LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [
                  TeacherPalette.oceanBlue,
                  TeacherPalette.violet,
                ],
              ),
            ),
            child: Icon(icon, color: TeacherPalette.white, size: 20),
          ),
          const Spacer(),
          Text(
            value,
            style: const TextStyle(
              fontSize: 24,
              fontWeight: FontWeight.w700,
              color: TeacherPalette.textDark,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            title,
            style: TextStyle(
              color: TeacherPalette.textDark.withValues(alpha: 0.75),
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}

class _KpiPill extends StatelessWidget {
  const _KpiPill({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(12),
          color: const Color(0xFFE6ECFF),
        ),
        child: Column(
          children: [
            Text(
              value,
              style: const TextStyle(
                color: TeacherPalette.deepOcean,
                fontWeight: FontWeight.w700,
                fontSize: 16,
              ),
            ),
            const SizedBox(height: 2),
            Text(
              label,
              style: const TextStyle(
                color: TeacherPalette.deepOcean,
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
