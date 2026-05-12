import 'package:flutter/material.dart';

import '../../models/student_models.dart';

class StudentAnnouncementCard extends StatelessWidget {
  const StudentAnnouncementCard({
    super.key,
    required this.item,
    required this.onTap,
  });

  final StudentAnnouncementItem item;
  final VoidCallback onTap;

  String _formatTime(DateTime? date) {
    if (date == null) {
      return 'Just now';
    }
    final minutes = DateTime.now().difference(date).inMinutes;
    if (minutes < 1) {
      return 'Just now';
    }
    if (minutes < 60) {
      return '$minutes min ago';
    }
    final hours = (minutes / 60).floor();
    if (hours < 24) {
      return '$hours h ago';
    }
    final days = (hours / 24).floor();
    return '$days d ago';
  }

  @override
  Widget build(BuildContext context) {
    final isUnread = !item.isRead;

    return Material(
      color: Colors.transparent,
      borderRadius: BorderRadius.circular(18),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(18),
        child: Ink(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(18),
            gradient: const LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                Color(0xFFF7F8FB),
                Color(0xFFE5E8EE),
                Color(0xFFD9DEE7),
              ],
              stops: [0.06, 0.52, 1.0],
            ),
            border: Border.all(color: const Color(0xFFCBD2DE), width: 1.1),
            boxShadow: [
              BoxShadow(
                color: const Color(0xFF111827).withValues(alpha: 0.16),
                blurRadius: 20,
                spreadRadius: -11,
                offset: const Offset(0, 10),
              ),
              BoxShadow(
                color: Colors.white.withValues(alpha: 0.72),
                blurRadius: 8,
                spreadRadius: -6,
                offset: const Offset(0, -2),
              ),
            ],
          ),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(14, 14, 14, 14),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 38,
                  height: 38,
                  decoration: BoxDecoration(
                    color: const Color(0xFFF1F4FA),
                    borderRadius: BorderRadius.circular(11),
                    border: Border.all(color: const Color(0xFFD5DBE6)),
                  ),
                  alignment: Alignment.center,
                  child: Icon(
                    Icons.campaign_rounded,
                    color: isUnread
                        ? const Color(0xFF0F172A)
                        : const Color(0xFF475569),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              item.title,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: Theme.of(context)
                                  .textTheme
                                  .titleSmall
                                  ?.copyWith(
                                    fontWeight: FontWeight.w800,
                                    color: const Color(0xFF0B1220),
                                  ),
                            ),
                          ),
                          const SizedBox(width: 8),
                          Text(
                            _formatTime(item.timestamp),
                            style: Theme.of(context)
                                .textTheme
                                .labelSmall
                                ?.copyWith(
                                  color: const Color(0xFF1F2937),
                                  fontWeight: FontWeight.w700,
                                ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 6),
                      Text(
                        item.previewText,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                              color: const Color(0xFF17212F),
                              fontWeight: FontWeight.w500,
                            ),
                      ),
                      const SizedBox(height: 10),
                      Row(
                        children: [
                          Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 8,
                              vertical: 4,
                            ),
                            decoration: BoxDecoration(
                              color: const Color(0xFFE6EAF2),
                              borderRadius: BorderRadius.circular(999),
                              border:
                                  Border.all(color: const Color(0xFFCBD4E1)),
                            ),
                            child: Text(
                              item.source.toUpperCase(),
                              style: Theme.of(context)
                                  .textTheme
                                  .labelSmall
                                  ?.copyWith(
                                    fontWeight: FontWeight.w800,
                                    color: const Color(0xFF0F172A),
                                  ),
                            ),
                          ),
                          const Spacer(),
                          Text(
                            'View Details',
                            style: Theme.of(context)
                                .textTheme
                                .labelMedium
                                ?.copyWith(
                                  color: const Color(0xFF0B1220),
                                  fontWeight: FontWeight.w800,
                                ),
                          ),
                          const SizedBox(width: 4),
                          const Icon(
                            Icons.arrow_forward_rounded,
                            size: 18,
                            color: Color(0xFF0B1220),
                          ),
                        ],
                      ),
                    ],
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
