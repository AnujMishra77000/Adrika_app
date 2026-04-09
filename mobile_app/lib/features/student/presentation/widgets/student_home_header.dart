import 'package:flutter/material.dart';

import 'student_notification_bell.dart';

class StudentHomeHeader extends StatelessWidget {
  const StudentHomeHeader({
    super.key,
    required this.greeting,
    required this.subtitle,
    required this.unreadCount,
    required this.onNotificationTap,
  });

  final String greeting;
  final String subtitle;
  final int unreadCount;
  final VoidCallback onNotificationTap;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                greeting,
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.w700,
                      color: const Color(0xFF111827),
                    ),
              ),
              const SizedBox(height: 4),
              Text(
                subtitle,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: const Color(0xFF475569),
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
