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
      borderRadius: BorderRadius.circular(16),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Ink(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: isUnread
                  ? const [Color(0xFF63CFAE), Color(0xFF46BA96)]
                  : const [Color(0xFF7FD8BE), Color(0xFF66C8AC)],
            ),
            border: Border.all(
              color:
                  isUnread ? const Color(0xFFBDF5E0) : const Color(0xFFD6F9EC),
            ),
            boxShadow: [
              BoxShadow(
                color: const Color(0xFF1D8C6B).withValues(alpha: 0.24),
                blurRadius: 16,
                offset: const Offset(0, 8),
              ),
            ],
          ),
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      width: 8,
                      height: 8,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: Colors.white.withValues(
                          alpha: isUnread ? 0.95 : 0.75,
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        item.title,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.titleSmall?.copyWith(
                              fontWeight:
                                  isUnread ? FontWeight.w700 : FontWeight.w600,
                              color: Colors.white,
                            ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      _formatTime(item.timestamp),
                      style: Theme.of(context).textTheme.labelSmall?.copyWith(
                            color: Colors.white.withValues(alpha: 0.92),
                          ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                Text(
                  item.previewText,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: Colors.white,
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
                        color: Colors.white.withValues(alpha: 0.2),
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: Text(
                        item.source.toUpperCase(),
                        style: Theme.of(context).textTheme.labelSmall?.copyWith(
                              fontWeight: FontWeight.w700,
                              color: Colors.white,
                            ),
                      ),
                    ),
                    const Spacer(),
                    const Icon(
                      Icons.arrow_forward_rounded,
                      size: 18,
                      color: Colors.white,
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
