import 'package:flutter/material.dart';

import 'student_home_palette.dart';

class StudentSurfaceCard extends StatelessWidget {
  const StudentSurfaceCard({
    super.key,
    required this.child,
    this.onTap,
    this.padding = StudentUiSpacing.card,
    this.backgroundColor = StudentHomePalette.surface,
    this.borderColor = StudentHomePalette.line,
    this.radius = StudentUiRadius.card,
  });

  final Widget child;
  final VoidCallback? onTap;
  final EdgeInsetsGeometry padding;
  final Color backgroundColor;
  final Color borderColor;
  final double radius;

  @override
  Widget build(BuildContext context) {
    final body = Container(
      decoration: BoxDecoration(
        color: backgroundColor,
        borderRadius: BorderRadius.circular(radius),
        border: Border.all(color: borderColor),
        boxShadow: StudentUiShadow.card,
      ),
      child: Padding(
        padding: padding,
        child: child,
      ),
    );

    if (onTap == null) {
      return body;
    }

    return Material(
      color: Colors.transparent,
      borderRadius: BorderRadius.circular(radius),
      child: InkWell(
        borderRadius: BorderRadius.circular(radius),
        onTap: onTap,
        child: body,
      ),
    );
  }
}

class StudentIconBadge extends StatelessWidget {
  const StudentIconBadge({
    super.key,
    required this.icon,
    required this.accent,
    this.size = 38,
  });

  final IconData icon;
  final Color accent;
  final double size;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(11),
        color: accent.withValues(alpha: 0.16),
      ),
      alignment: Alignment.center,
      child: Icon(
        icon,
        size: size * 0.52,
        color: accent,
      ),
    );
  }
}
