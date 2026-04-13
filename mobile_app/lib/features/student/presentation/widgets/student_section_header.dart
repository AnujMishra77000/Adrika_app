import "package:flutter/material.dart";

import "student_home_palette.dart";

class StudentSectionHeader extends StatelessWidget {
  const StudentSectionHeader({
    super.key,
    required this.title,
    this.subtitle,
    this.actionLabel,
    this.onActionTap,
    this.titleColor,
    this.subtitleColor,
    this.actionColor,
  });

  final String title;
  final String? subtitle;
  final String? actionLabel;
  final VoidCallback? onActionTap;
  final Color? titleColor;
  final Color? subtitleColor;
  final Color? actionColor;

  @override
  Widget build(BuildContext context) {
    final showAction = actionLabel != null && onActionTap != null;

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w700,
                      color: titleColor ?? StudentHomePalette.textPrimary,
                    ),
              ),
              if (subtitle != null) ...[
                const SizedBox(height: 2),
                Text(
                  subtitle!,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: subtitleColor ?? StudentHomePalette.textMuted,
                      ),
                ),
              ],
            ],
          ),
        ),
        if (showAction)
          TextButton(
            onPressed: onActionTap,
            child: Text(
              actionLabel!,
              style: TextStyle(color: actionColor),
            ),
          ),
      ],
    );
  }
}
