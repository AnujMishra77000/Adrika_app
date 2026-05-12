import 'package:flutter/material.dart';

import '../../models/student_models.dart';
import 'student_home_palette.dart';
import 'student_page_background.dart';
import 'student_status_chip.dart';
import 'student_surface_card.dart';

class StudentNoticeFeedCard extends StatefulWidget {
  const StudentNoticeFeedCard({
    super.key,
    required this.notice,
    required this.onTap,
    this.pinned = false,
  });

  final StudentNotice notice;
  final VoidCallback onTap;
  final bool pinned;

  @override
  State<StudentNoticeFeedCard> createState() => _StudentNoticeFeedCardState();
}

class _StudentNoticeFeedCardState extends State<StudentNoticeFeedCard> {
  bool _pressed = false;

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
    return '${dt.day}/${dt.month}/${dt.year}  $hour:$minute';
  }

  Widget _solidChip({
    required String label,
    required Color background,
    Color foreground = Colors.white,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: foreground,
          fontSize: 10.8,
          fontWeight: FontWeight.w700,
          height: 1.0,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isUnread = !widget.notice.isRead;

    return Listener(
      onPointerDown: (_) => setState(() => _pressed = true),
      onPointerUp: (_) => setState(() => _pressed = false),
      onPointerCancel: (_) => setState(() => _pressed = false),
      child: AnimatedScale(
        duration: const Duration(milliseconds: 140),
        curve: Curves.easeOutCubic,
        scale: _pressed ? 0.992 : 1,
        child: StudentSurfaceCard(
          onTap: widget.onTap,
          padding: const EdgeInsets.fromLTRB(11, 10, 11, 10),
          backgroundColor: StudentQuickAccessTheme.surfaceAlt,
          borderColor: isUnread
              ? const Color(0xFFCBD5E1)
              : StudentQuickAccessTheme.surfaceBorder,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  StudentIconBadge(
                    icon: isUnread
                        ? Icons.mark_email_unread_rounded
                        : Icons.mark_email_read_rounded,
                    accent: isUnread
                        ? StudentHomePalette.softPink
                        : StudentHomePalette.accentBlue,
                    size: 32,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          widget.notice.title,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style:
                              Theme.of(context).textTheme.titleSmall?.copyWith(
                                    color: StudentQuickAccessTheme.textPrimary,
                                    fontWeight: FontWeight.w700,
                                    fontSize: 13,
                                    height: 1.1,
                                  ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          _formatDate(widget.notice.publishAt),
                          style:
                              Theme.of(context).textTheme.labelSmall?.copyWith(
                                    color: StudentQuickAccessTheme.textMuted,
                                    fontSize: 10.4,
                                    fontWeight: FontWeight.w600,
                                    height: 1.0,
                                  ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 6),
                  const Icon(
                    Icons.arrow_forward_ios_rounded,
                    size: 14,
                    color: StudentQuickAccessTheme.textMuted,
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                widget.notice.bodyPreview,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: StudentQuickAccessTheme.textSecondary,
                      fontSize: 12.2,
                      height: 1.22,
                    ),
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: [
                  if (widget.pinned)
                    const StudentStatusChip(
                      label: 'Pinned',
                      tone: StudentChipTone.info,
                    ),
                  _solidChip(
                    label: isUnread ? 'Unread' : 'Read',
                    background: isUnread
                        ? const Color(0xFFF59E0B)
                        : const Color(0xFF16A34A),
                    foreground: Colors.white,
                  ),
                  _solidChip(
                    label: 'Notice',
                    background: const Color(0xFF2563EB),
                    foreground: Colors.white,
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
