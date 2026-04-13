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
        final columns = width >= 460 ? 5 : (width >= 390 ? 4 : 3);
        const spacing = 8.0;
        final itemWidth =
            (width - (spacing * (columns - 1))).clamp(0, double.infinity) /
                columns;

        return Wrap(
          spacing: spacing,
          runSpacing: 14,
          children: items
              .map(
                (item) => SizedBox(
                  width: itemWidth,
                  child: _QuickActionIcon(
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

class _QuickActionIcon extends StatelessWidget {
  const _QuickActionIcon({
    required this.item,
    required this.onTap,
  });

  final StudentQuickActionItem item;
  final VoidCallback onTap;

  IconData _iconFromKey(String key) {
    switch (key) {
      case "notice":
        return Icons.campaign_rounded;
      case "notes":
        return Icons.edit_note_rounded;
      case "homework":
        return Icons.menu_book_rounded;
      case "online_test":
        return Icons.laptop_chromebook_rounded;
      case "practice":
        return Icons.fact_check_rounded;
      case "chat":
        return Icons.chat_bubble_rounded;
      default:
        return Icons.apps_rounded;
    }
  }

  @override
  Widget build(BuildContext context) {
    final icon = _iconFromKey(item.iconKey);

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(14),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 6),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              SizedBox(
                width: 38,
                height: 34,
                child: Stack(
                  clipBehavior: Clip.none,
                  children: [
                    Align(
                      alignment: Alignment.center,
                      child: Icon(
                        icon,
                        size: 30,
                        color: item.accentColor,
                      ),
                    ),
                    if (item.badgeCount > 0)
                      Positioned(
                        right: -8,
                        top: -4,
                        child: _CounterBadge(count: item.badgeCount),
                      ),
                  ],
                ),
              ),
              const SizedBox(height: 6),
              Text(
                item.title,
                maxLines: 2,
                textAlign: TextAlign.center,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.labelMedium?.copyWith(
                      color: const Color(0xFFE6E1FF),
                      fontWeight: FontWeight.w700,
                    ),
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
        padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1.5),
        constraints: const BoxConstraints(minWidth: 18),
        decoration: BoxDecoration(
          color: const Color(0xFFE11D48),
          borderRadius: BorderRadius.circular(999),
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
