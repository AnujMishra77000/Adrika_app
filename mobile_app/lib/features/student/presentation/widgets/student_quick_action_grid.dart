import "package:flutter/material.dart";

import "../../models/student_models.dart";

class StudentQuickActionGrid extends StatelessWidget {
  const StudentQuickActionGrid({
    super.key,
    required this.items,
    required this.onTap,
  });

  final List<StudentQuickActionItem> items;
  final ValueChanged<String> onTap;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final width = constraints.maxWidth;
        final columns = width >= 420 ? 3 : 2;
        const spacing = 10.0;
        final itemWidth =
            (width - (spacing * (columns - 1))).clamp(0, double.infinity) /
                columns;

        return Wrap(
          spacing: spacing,
          runSpacing: spacing,
          children: items
              .map(
                (item) => SizedBox(
                  width: itemWidth,
                  child: _QuickActionButton(
                    item: item,
                    onTap: () => onTap(item.route),
                  ),
                ),
              )
              .toList(growable: false),
        );
      },
    );
  }
}

class _QuickActionButton extends StatelessWidget {
  const _QuickActionButton({
    required this.item,
    required this.onTap,
  });

  final StudentQuickActionItem item;
  final VoidCallback onTap;

  _ActionStyle _styleFor(String key) {
    switch (key) {
      case "notice":
        return const _ActionStyle(
          icon: Icons.notifications_active_rounded,
          gradient: [Color(0xFFFFD54A), Color(0xFFF2B705)],
          foreground: Color(0xFF3B2A00),
          secondaryForeground: Color(0xFF5B4300),
          outline: Color(0xFFE0A800),
        );
      case "notes":
        return const _ActionStyle(
          icon: Icons.menu_book_rounded,
          gradient: [Color(0xFF7C3AED), Color(0xFF5B21B6)],
          outline: Color(0xFF7C3AED),
        );
      case "homework":
        return const _ActionStyle(
          icon: Icons.auto_stories_rounded,
          gradient: [Color(0xFFEA580C), Color(0xFFB34107)],
          outline: Color(0xFFEA580C),
        );
      case "online_test":
        return const _ActionStyle(
          icon: Icons.computer_rounded,
          gradient: [Color(0xFF2563EB), Color(0xFF1D4ED8)],
          outline: Color(0xFF2563EB),
        );
      case "practice":
        return const _ActionStyle(
          icon: Icons.fact_check_rounded,
          gradient: [Color(0xFF43B66B), Color(0xFF2E8F50)],
          outline: Color(0xFF2E8F50),
        );
      case "suggestion":
        return const _ActionStyle(
          icon: Icons.lightbulb_rounded,
          gradient: [Color(0xFF0E7490), Color(0xFF155E75)],
          outline: Color(0xFF0E7490),
        );
      default:
        return const _ActionStyle(
          icon: Icons.apps_rounded,
          gradient: [Color(0xFF334155), Color(0xFF1E293B)],
          outline: Color(0xFF334155),
        );
    }
  }

  @override
  Widget build(BuildContext context) {
    final style = _styleFor(item.iconKey);

    return Material(
      color: Colors.transparent,
      borderRadius: BorderRadius.circular(22),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(22),
        child: Ink(
          padding: const EdgeInsets.fromLTRB(11, 10, 11, 9),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: style.gradient,
            ),
            borderRadius: BorderRadius.circular(22),
            border: Border.all(
                color: style.outline.withValues(alpha: 0.96), width: 1.5),
            boxShadow: [
              BoxShadow(
                color: style.outline.withValues(alpha: 0.32),
                blurRadius: 18,
                spreadRadius: -8,
                offset: const Offset(0, 10),
              ),
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.16),
                blurRadius: 10,
                spreadRadius: -8,
                offset: const Offset(0, 5),
              ),
            ],
          ),
          child: Stack(
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Container(
                        width: 36,
                        height: 36,
                        decoration: BoxDecoration(
                          color: Colors.white.withValues(alpha: 0.22),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(
                            color: style.outline.withValues(alpha: 0.62),
                            width: 1.0,
                          ),
                          boxShadow: [
                            BoxShadow(
                              color: style.outline.withValues(alpha: 0.24),
                              blurRadius: 10,
                              spreadRadius: -6,
                              offset: const Offset(0, 5),
                            ),
                          ],
                        ),
                        alignment: Alignment.center,
                        child: Icon(
                          style.icon,
                          size: 20,
                          color: style.foreground,
                        ),
                      ),
                      const Spacer(),
                      if (item.badgeCount > 0)
                        _CounterBadge(count: item.badgeCount),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    item.title,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: style.foreground,
                          fontWeight: FontWeight.w800,
                        ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    "Tap to open",
                    style: Theme.of(context).textTheme.labelSmall?.copyWith(
                          color: style.secondaryForeground,
                          fontWeight: FontWeight.w600,
                        ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _CounterBadge extends StatelessWidget {
  const _CounterBadge({required this.count});

  final int count;

  @override
  Widget build(BuildContext context) {
    final text = count > 99 ? "99+" : "$count";

    return AnimatedSwitcher(
      duration: const Duration(milliseconds: 220),
      transitionBuilder: (child, animation) => ScaleTransition(
        scale: animation,
        child: child,
      ),
      child: Container(
        key: ValueKey<String>(text),
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
        constraints: const BoxConstraints(minWidth: 18),
        decoration: BoxDecoration(
          color: const Color(0xFFE11D48),
          borderRadius: BorderRadius.circular(999),
          border: Border.all(
            color: Colors.white.withValues(alpha: 0.52),
          ),
        ),
        child: Text(
          text,
          textAlign: TextAlign.center,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 10,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
    );
  }
}

class _ActionStyle {
  const _ActionStyle({
    required this.icon,
    required this.gradient,
    this.foreground = Colors.white,
    this.secondaryForeground = const Color(0xE6FFFFFF),
    required this.outline,
  });

  final IconData icon;
  final List<Color> gradient;
  final Color foreground;
  final Color secondaryForeground;
  final Color outline;
}
