import 'package:flutter/material.dart';

class StudentSectionHeader extends StatelessWidget {
  const StudentSectionHeader({
    super.key,
    required this.title,
    this.actionLabel,
    this.onActionTap,
  });

  final String title;
  final String? actionLabel;
  final VoidCallback? onActionTap;

  @override
  Widget build(BuildContext context) {
    final showAction = actionLabel != null && onActionTap != null;

    return Row(
      children: [
        Expanded(
          child: Text(
            title,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.w700,
                  color: const Color(0xFF0F172A),
                ),
          ),
        ),
        if (showAction)
          TextButton(
            onPressed: onActionTap,
            child: Text(actionLabel!),
          ),
      ],
    );
  }
}
