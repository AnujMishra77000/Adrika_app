import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../auth/state/auth_controller.dart';
import '../state/teacher_providers.dart';
import 'widgets/teacher_ui.dart';

class TeacherProfileScreen extends ConsumerWidget {
  const TeacherProfileScreen({super.key});

  String _valueOrDash(String? value) {
    final trimmed = (value ?? '').trim();
    return trimmed.isEmpty ? '—' : trimmed;
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final profile = ref.watch(teacherProfileProvider);

    return profile.when(
      data: (data) => TeacherGradientBackground(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 14, 16, 20),
          children: [
            TeacherEntrance(
              delay: teacherStagger(0),
              child: const TeacherScreenHeader(
                title: 'Profile',
                subtitle: 'Your account and academic identity details.',
                icon: Icons.person_outline,
              ),
            ),
            TeacherEntrance(
              delay: teacherStagger(1),
              child: TeacherSurfaceCard(
                margin: const EdgeInsets.only(bottom: 12),
                child: Row(
                  children: [
                    Container(
                      width: 66,
                      height: 66,
                      decoration: const BoxDecoration(
                        shape: BoxShape.circle,
                        gradient: LinearGradient(
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                          colors: [
                            TeacherPalette.oceanBlue,
                            TeacherPalette.violet,
                          ],
                        ),
                      ),
                      child: const Icon(
                        Icons.school_outlined,
                        color: TeacherPalette.white,
                        size: 30,
                      ),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            data.fullName,
                            style: const TextStyle(
                              color: TeacherPalette.textDark,
                              fontSize: 20,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            _valueOrDash(data.designation),
                            style: TextStyle(
                              color:
                                  TeacherPalette.textDark.withValues(alpha: 0.72),
                            ),
                          ),
                          const SizedBox(height: 8),
                          Wrap(
                            spacing: 8,
                            runSpacing: 8,
                            children: [
                              _InfoChip(
                                label: 'Code',
                                value: data.employeeCode,
                              ),
                              _InfoChip(
                                label: 'Specialization',
                                value: _valueOrDash(data.specialization),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
            TeacherEntrance(
              delay: teacherStagger(2),
              child: TeacherSurfaceCard(
                margin: const EdgeInsets.only(bottom: 12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Professional Details',
                      style: TextStyle(
                        color: TeacherPalette.textDark,
                        fontWeight: FontWeight.w700,
                        fontSize: 16,
                      ),
                    ),
                    const SizedBox(height: 10),
                    _DetailRow(
                      label: 'Qualification',
                      value: _valueOrDash(data.qualification),
                    ),
                    _DetailRow(label: 'Gender', value: _valueOrDash(data.gender)),
                    _DetailRow(label: 'Age', value: data.age?.toString() ?? '—'),
                    _DetailRow(
                      label: 'School/College',
                      value: _valueOrDash(data.schoolCollege),
                    ),
                    _DetailRow(
                      label: 'Address',
                      value: _valueOrDash(data.address),
                    ),
                  ],
                ),
              ),
            ),
            TeacherEntrance(
              delay: teacherStagger(3),
              child: TeacherSurfaceCard(
                child: Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: () => ref.invalidate(teacherProfileProvider),
                        icon: const Icon(Icons.refresh_rounded),
                        label: const Text('Refresh'),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: FilledButton.icon(
                        style: FilledButton.styleFrom(
                          backgroundColor: TeacherPalette.deepOcean,
                          foregroundColor: TeacherPalette.white,
                        ),
                        onPressed: () async {
                          await ref.read(authControllerProvider.notifier).logout();
                          if (context.mounted) {
                            context.go('/login');
                          }
                        },
                        icon: const Icon(Icons.logout_rounded),
                        label: const Text('Logout'),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
      loading: () => const TeacherLoadingView(),
      error: (error, _) => TeacherErrorView(
        title: 'Failed to load profile',
        message: error.toString(),
        onRetry: () => ref.invalidate(teacherProfileProvider),
      ),
    );
  }
}

class _InfoChip extends StatelessWidget {
  const _InfoChip({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: const Color(0xFFE8EEFF),
      ),
      child: Text(
        '$label: $value',
        style: const TextStyle(
          color: TeacherPalette.deepOcean,
          fontWeight: FontWeight.w600,
          fontSize: 12,
        ),
      ),
    );
  }
}

class _DetailRow extends StatelessWidget {
  const _DetailRow({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        children: [
          SizedBox(
            width: 130,
            child: Text(
              label,
              style: TextStyle(
                color: TeacherPalette.textDark.withValues(alpha: 0.75),
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(
                color: TeacherPalette.textDark,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
