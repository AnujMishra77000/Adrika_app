import 'package:flutter/material.dart';

import 'student_home_palette.dart';
import 'student_page_background.dart';
import 'student_surface_card.dart';

class StudentModuleHeader extends StatelessWidget {
  const StudentModuleHeader({
    super.key,
    required this.title,
    required this.subtitle,
    required this.icon,
    this.accent = StudentHomePalette.accentBlue,
  });

  final String title;
  final String subtitle;
  final IconData icon;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return StudentSurfaceCard(
      backgroundColor: StudentQuickAccessTheme.surface,
      borderColor: StudentQuickAccessTheme.surfaceBorder,
      child: Row(
        children: [
          StudentIconBadge(icon: icon, accent: accent),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        color: StudentQuickAccessTheme.textPrimary,
                        fontWeight: FontWeight.w700,
                      ),
                ),
                if (subtitle.trim().isNotEmpty) ...[
                  const SizedBox(height: 3),
                  Text(
                    subtitle,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: StudentQuickAccessTheme.textSecondary,
                        ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}
