import "package:flutter/material.dart";

class StudentNotificationBell extends StatelessWidget {
  const StudentNotificationBell({
    super.key,
    required this.unreadCount,
    required this.onTap,
    this.iconSize = 22,
    this.iconPadding = 10,
  });

  final int unreadCount;
  final VoidCallback onTap;
  final double iconSize;
  final double iconPadding;

  @override
  Widget build(BuildContext context) {
    final radius = (iconPadding + (iconSize / 2)).clamp(12.0, 20.0);

    return Stack(
      clipBehavior: Clip.none,
      children: [
        Material(
          color: Colors.transparent,
          borderRadius: BorderRadius.circular(radius),
          child: InkWell(
            borderRadius: BorderRadius.circular(radius),
            onTap: onTap,
            child: Ink(
              padding: EdgeInsets.all(iconPadding),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(radius),
                gradient: const LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [
                    Color(0xFF3155DA),
                    Color(0xFF1C3FAF),
                  ],
                ),
                boxShadow: [
                  BoxShadow(
                    color: const Color(0xFF173690).withValues(alpha: 0.28),
                    blurRadius: 14,
                    spreadRadius: -6,
                    offset: const Offset(0, 8),
                  ),
                ],
              ),
              child: Icon(
                Icons.notifications_rounded,
                color: Colors.white,
                size: iconSize,
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
