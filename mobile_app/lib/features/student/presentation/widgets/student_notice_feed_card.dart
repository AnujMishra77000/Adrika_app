import 'package:flutter/material.dart';

import '../../models/student_models.dart';
import 'student_home_palette.dart';
import 'student_status_chip.dart';
import 'student_surface_card.dart';

class StudentNoticeFeedCard extends StatelessWidget {
  const StudentNoticeFeedCard({
    super.key,
    required this.notice,
    required this.onTap,
    this.pinned = false,
  });

  final StudentNotice notice;
  final VoidCallback onTap;
  final bool pinned;

  String _formatDate(String? raw) {
    if (raw == null || raw.isEmpty) {
      return 'Now';
    }
    final dt = DateTime.tryParse(raw)?.toLocal();
    if (dt == null) {
      return raw;
    }
    final hour = dt.hour.toString().padLeft(2, '0');
    final minute = dt.minute.toString().padLeft(2, '0');
    return '${dt.day}/${dt.month}/${dt.year} $hour:$minute';
  }

  @override
  Widget build(BuildContext context) {
    final isUnread = !notice.isRead;

    return StudentSurfaceCard(
      onTap: onTap,
      borderColor: isUnread ? const Color(0xFFBFCBFF) : StudentHomePalette.line,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              StudentIconBadge(
                icon: isUnread
                    ? Icons.mark_email_unread_rounded
                    : Icons.mark_email_read_rounded,
                accent: isUnread
                    ? StudentHomePalette.softPink
                    : StudentHomePalette.accentBlue,
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  notice.title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        color: StudentHomePalette.textPrimary,
                        fontWeight: FontWeight.w700,
                      ),
                ),
              ),
              const SizedBox(width: 8),
              Text(
                _formatDate(notice.publishAt),
                style: Theme.of(context).textTheme.labelSmall?.copyWith(
                      color: StudentHomePalette.textMuted,
                    ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            notice.bodyPreview,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: StudentHomePalette.textSecondary,
                ),
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              if (pinned) ...[
                const StudentStatusChip(
                  label: 'Pinned',
                  tone: StudentChipTone.info,
                ),
                const SizedBox(width: 6),
              ],
              StudentStatusChip(
                label: isUnread ? 'Unread' : 'Read',
                tone: isUnread
                    ? StudentChipTone.warning
                    : StudentChipTone.neutral,
              ),
              const SizedBox(width: 6),
              const StudentStatusChip(
                label: 'Notice',
                tone: StudentChipTone.info,
              ),
              const Spacer(),
              const Icon(
                Icons.arrow_forward_rounded,
                size: 18,
                color: StudentHomePalette.textMuted,
              ),
            ],
          ),
        ],
      ),
    );
  }
}
