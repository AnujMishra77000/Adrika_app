import "package:flutter/material.dart";

import "student_home_palette.dart";

class StudentNotificationBell extends StatelessWidget {
  const StudentNotificationBell({
    super.key,
    required this.unreadCount,
    required this.onTap,
  });

  final int unreadCount;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Stack(
      clipBehavior: Clip.none,
      children: [
        Material(
          color: StudentHomePalette.surface,
          shadowColor: Colors.black.withValues(alpha: 0.12),
          elevation: 3,
          borderRadius: BorderRadius.circular(14),
          child: InkWell(
            borderRadius: BorderRadius.circular(14),
            onTap: onTap,
            child: const Padding(
              padding: EdgeInsets.all(10),
              child: Icon(
                Icons.notifications_none_rounded,
                color: StudentHomePalette.textPrimary,
              ),
            ),
          ),
        ),
        Positioned(
          top: -4,
          right: -4,
          child: AnimatedSwitcher(
            duration: const Duration(milliseconds: 260),
            switchInCurve: Curves.easeOutBack,
            switchOutCurve: Curves.easeIn,
            transitionBuilder: (child, animation) => ScaleTransition(
              scale: animation,
              child: child,
            ),
            child: unreadCount > 0
                ? Container(
                    key: ValueKey<int>(unreadCount),
                    padding: const EdgeInsets.symmetric(
                      horizontal: 6,
                      vertical: 2,
                    ),
                    decoration: BoxDecoration(
                      color: const Color(0xFFE11D48),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    constraints: const BoxConstraints(minWidth: 20),
                    child: Text(
                      unreadCount > 99 ? "99+" : "$unreadCount",
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                      ),
                      textAlign: TextAlign.center,
                    ),
                  )
                : const SizedBox.shrink(),
          ),
        ),
      ],
    );
  }
}
