import 'package:flutter/material.dart';

import 'student_home_palette.dart';
import 'student_page_background.dart';
import 'student_surface_card.dart';

class StudentHomeLoadingList extends StatelessWidget {
  const StudentHomeLoadingList({super.key});

  @override
  Widget build(BuildContext context) {
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 18),
      children: const [
        _SkeletonBox(height: 72),
        SizedBox(height: 14),
        _SkeletonBox(height: 228),
        SizedBox(height: 14),
        _SkeletonBox(height: 120),
        SizedBox(height: 14),
        _SkeletonBox(height: 140),
        SizedBox(height: 14),
        _SkeletonBox(height: 112),
      ],
    );
  }
}

class StudentFeedLoadingList extends StatelessWidget {
  const StudentFeedLoadingList({
    super.key,
    this.itemCount = 4,
  });

  final int itemCount;

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: StudentUiSpacing.page,
      itemBuilder: (context, index) => const _SkeletonBox(height: 132),
      separatorBuilder: (_, __) => const SizedBox(height: 10),
      itemCount: itemCount,
    );
  }
}

class StudentHomeEmptyState extends StatelessWidget {
  const StudentHomeEmptyState({
    super.key,
    required this.title,
    required this.subtitle,
  });

  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    return StudentSurfaceCard(
      backgroundColor: StudentQuickAccessTheme.surfaceAlt,
      borderColor: StudentQuickAccessTheme.surfaceBorder,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  fontWeight: FontWeight.w700,
                  color: StudentQuickAccessTheme.textPrimary,
                ),
          ),
          const SizedBox(height: 6),
          Text(
            subtitle,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: StudentQuickAccessTheme.textSecondary,
                ),
          ),
        ],
      ),
    );
  }
}

class StudentHomeErrorList extends StatelessWidget {
  const StudentHomeErrorList({
    super.key,
    required this.message,
    required this.onRetry,
  });

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.all(20),
      children: [
        StudentSurfaceCard(
          backgroundColor: StudentQuickAccessTheme.surfaceAlt,
          borderColor: const Color(0x66EF9A9A),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Unable to load student home',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      color: const Color(0xFFFFB4BC),
                      fontWeight: FontWeight.w700,
                    ),
              ),
              const SizedBox(height: 8),
              Text(
                message,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: StudentQuickAccessTheme.textSecondary,
                    ),
              ),
              const SizedBox(height: 14),
              FilledButton.icon(
                onPressed: onRetry,
                icon: const Icon(Icons.refresh_rounded),
                label: const Text('Retry'),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _SkeletonBox extends StatelessWidget {
  const _SkeletonBox({required this.height});

  final double height;

  @override
  Widget build(BuildContext context) {
    return Container(
      height: height,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(StudentUiRadius.card),
        color: const Color(0x3D8F85B9),
      ),
    );
  }
}
