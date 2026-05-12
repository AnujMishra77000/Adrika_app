import 'package:flutter/material.dart';

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
        return const Color(0xFFDCFCE7);
      case StudentChipTone.warning:
        return const Color(0xFFFDE68A);
      case StudentChipTone.danger:
        return const Color(0xFFFDA4AF);
      case StudentChipTone.info:
        return const Color(0xFFBFDBFE);
      case StudentChipTone.neutral:
        return const Color(0xFFE2E8F0);
    }
  }

  Color _background() {
    switch (tone) {
      case StudentChipTone.success:
        return const Color(0x3322C55E);
      case StudentChipTone.warning:
        return const Color(0x33F59E0B);
      case StudentChipTone.danger:
        return const Color(0x33EF4444);
      case StudentChipTone.info:
        return const Color(0x333B82F6);
      case StudentChipTone.neutral:
        return const Color(0x33475569);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: _background(),
        border: Border.all(color: _foreground().withValues(alpha: 0.35)),
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
