import "package:flutter/material.dart";

import "../../../../core/config/app_env.dart";
import "student_notification_bell.dart";

class StudentHomeHeader extends StatelessWidget {
  const StudentHomeHeader({
    super.key,
    required this.greeting,
    required this.unreadCount,
    required this.onNotificationTap,
    this.photoUrl,
    this.greetingColor = const Color(0xFF111827),
  });

  final String greeting;
  final int unreadCount;
  final VoidCallback onNotificationTap;
  final String? photoUrl;
  final Color greetingColor;

  @override
  Widget build(BuildContext context) {
    final effectivePhoto = AppEnv.resolveServerUrl(photoUrl);

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              ClipOval(
                child: Container(
                  width: 52,
                  height: 52,
                  decoration: BoxDecoration(
                    color: const Color(0xFFE8E8FF),
                    border: Border.all(
                      color: Colors.white.withValues(alpha: 0.85),
                      width: 2,
                    ),
                  ),
                  child: effectivePhoto != null
                      ? Image.network(
                          effectivePhoto,
                          fit: BoxFit.cover,
                          errorBuilder: (_, __, ___) => const Icon(
                            Icons.person_rounded,
                            color: Color(0xFF5A4BA0),
                            size: 28,
                          ),
                        )
                      : const Icon(
                          Icons.person_rounded,
                          color: Color(0xFF5A4BA0),
                          size: 28,
                        ),
                ),
              ),
              const SizedBox(height: 8),
              Text(
                greeting,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w800,
                      color: greetingColor,
                    ),
              ),
            ],
          ),
        ),
        const SizedBox(width: 12),
        StudentNotificationBell(
          unreadCount: unreadCount,
          onTap: onNotificationTap,
        ),
      ],
    );
  }
}
