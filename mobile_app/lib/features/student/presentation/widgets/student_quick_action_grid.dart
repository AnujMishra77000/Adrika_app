import 'package:flutter/material.dart';

import '../../models/student_models.dart';

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
        final crossAxisCount = width < 360 ? 2 : 3;

        return GridView.builder(
          shrinkWrap: true,
          itemCount: items.length,
          physics: const NeverScrollableScrollPhysics(),
          gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: crossAxisCount,
            mainAxisSpacing: 10,
            crossAxisSpacing: 10,
            childAspectRatio: 1.18,
          ),
          itemBuilder: (context, index) {
            final item = items[index];
            return _QuickActionCard(
              item: item,
              onTap: () => onTap(item.route),
            );
          },
        );
      },
    );
  }
}

class _QuickActionCard extends StatelessWidget {
  const _QuickActionCard({
    required this.item,
    required this.onTap,
  });

  final StudentQuickActionItem item;
  final VoidCallback onTap;

  IconData _iconFromKey(String key) {
    switch (key) {
      case 'notes':
        return Icons.note_alt_rounded;
      case 'homework':
        return Icons.assignment_turned_in_rounded;
      case 'online_test':
        return Icons.desktop_windows_rounded;
      case 'practice':
        return Icons.quiz_rounded;
      case 'chat':
        return Icons.forum_rounded;
      default:
        return Icons.apps_rounded;
    }
  }

  Color _iconColorFromKey(String key) {
    switch (key) {
      case 'notes':
        return const Color(0xFFE754A6);
      case 'homework':
        return const Color(0xFF1DBB8A);
      case 'online_test':
        return const Color(0xFF0EA5E9);
      case 'practice':
        return const Color(0xFF7C5CFF);
      case 'chat':
        return const Color(0xFF2D84F4);
      default:
        return const Color(0xFF4B5563);
    }
  }

  @override
  Widget build(BuildContext context) {
    final iconColor = _iconColorFromKey(item.iconKey);

    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(16),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Ink(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: const Color(0xFFD9E3F1)),
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                item.accentColor.withValues(alpha: 0.11),
                Colors.white,
              ],
            ),
          ),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    color: iconColor.withValues(alpha: 0.16),
                    borderRadius: BorderRadius.circular(11),
                  ),
                  alignment: Alignment.center,
                  child: Icon(
                    _iconFromKey(item.iconKey),
                    size: 22,
                    color: iconColor,
                  ),
                ),
                const Spacer(),
                Text(
                  item.title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        fontWeight: FontWeight.w700,
                        color: const Color(0xFF1E293B),
                      ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
