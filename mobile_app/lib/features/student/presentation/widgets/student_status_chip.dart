import 'package:flutter/material.dart';

import 'student_home_palette.dart';

enum StudentChipTone {
  neutral,
  success,
  warning,
  danger,
  info,
}

class StudentStatusChip extends StatelessWidget {
  const StudentStatusChip({
    super.key,
    required this.label,
    this.tone = StudentChipTone.neutral,
  });

  final String label;
  final StudentChipTone tone;

  Color _foreground() {
    switch (tone) {
      case StudentChipTone.success:
        return const Color(0xFF0F7A58);
      case StudentChipTone.warning:
        return const Color(0xFF8A5C09);
      case StudentChipTone.danger:
        return const Color(0xFFA02045);
      case StudentChipTone.info:
        return const Color(0xFF1E4B98);
      case StudentChipTone.neutral:
        return StudentHomePalette.textSecondary;
    }
  }

  Color _background() {
    switch (tone) {
      case StudentChipTone.success:
        return const Color(0xFFDDF7EC);
      case StudentChipTone.warning:
        return const Color(0xFFFFF1D9);
      case StudentChipTone.danger:
        return const Color(0xFFFFE2EA);
      case StudentChipTone.info:
        return const Color(0xFFE1ECFF);
      case StudentChipTone.neutral:
        return const Color(0xFFF1F5F9);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(StudentUiRadius.chip),
        color: _background(),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelSmall?.copyWith(
              color: _foreground(),
              fontWeight: FontWeight.w700,
            ),
      ),
    );
  }
}
