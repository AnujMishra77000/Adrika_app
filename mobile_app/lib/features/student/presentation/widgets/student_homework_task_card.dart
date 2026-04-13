import 'package:flutter/material.dart';

import '../../models/student_models.dart';
import 'student_home_palette.dart';
import 'student_status_chip.dart';
import 'student_surface_card.dart';

class StudentHomeworkTaskCard extends StatelessWidget {
  const StudentHomeworkTaskCard({
    super.key,
    required this.homework,
    required this.onTap,
    this.onSubmit,
    this.submitting = false,
  });

  final StudentHomework homework;
  final VoidCallback onTap;
  final VoidCallback? onSubmit;
  final bool submitting;

  DateTime? _dueDate() =>
      homework.dueAt ?? DateTime.tryParse(homework.dueDate)?.toLocal();

  String _dueLabel() {
    final due = _dueDate();
    if (due == null) {
      return 'Due date pending';
    }

    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final dueDay = DateTime(due.year, due.month, due.day);
    final diff = dueDay.difference(today).inDays;

    if (diff < 0) {
      return 'Overdue by ${diff.abs()} day${diff.abs() == 1 ? '' : 's'}';
    }
    if (diff == 0) {
      return 'Due today';
    }
    if (diff == 1) {
      return 'Due tomorrow';
    }
    return 'Due in $diff days';
  }

  StudentChipTone _dueTone() {
    final due = _dueDate();
    if (due == null) {
      return StudentChipTone.neutral;
    }

    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final dueDay = DateTime(due.year, due.month, due.day);
    final diff = dueDay.difference(today).inDays;

    if (diff < 0) {
      return StudentChipTone.danger;
    }
    if (diff <= 1) {
      return StudentChipTone.warning;
    }
    return StudentChipTone.success;
  }

  String _formattedDate() {
    final due = _dueDate();
    if (due == null) {
      return 'Not available';
    }
    return '${due.day}/${due.month}/${due.year}';
  }

  String _subjectHint() {
    final title = homework.title.trim();
    if (title.isEmpty) {
      return 'General';
    }
    final firstWord = title.split(' ').first;
    return firstWord[0].toUpperCase() + firstWord.substring(1).toLowerCase();
  }

  @override
  Widget build(BuildContext context) {
    final dueTone = _dueTone();

    return StudentSurfaceCard(
      onTap: onTap,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              StudentIconBadge(
                icon: Icons.assignment_rounded,
                accent: StudentHomePalette.oceanBlue,
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _subjectHint(),
                      style: Theme.of(context).textTheme.labelMedium?.copyWith(
                            color: StudentHomePalette.textMuted,
                            fontWeight: FontWeight.w700,
                          ),
                    ),
                    Text(
                      homework.title,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                            color: StudentHomePalette.textPrimary,
                            fontWeight: FontWeight.w700,
                          ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              if (!homework.isRead)
                Container(
                  width: 8,
                  height: 8,
                  margin: const EdgeInsets.only(right: 8),
                  decoration: const BoxDecoration(
                    color: Color(0xFFE11D48),
                    shape: BoxShape.circle,
                  ),
                ),
              StudentStatusChip(
                label: homework.isSubmitted
                    ? 'Submitted'
                    : (homework.status.isEmpty ? 'Assigned' : homework.status),
                tone: homework.isSubmitted
                    ? StudentChipTone.success
                    : StudentChipTone.warning,
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            homework.description.isEmpty
                ? 'No additional instruction for this homework.'
                : homework.description,
            maxLines: 3,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: StudentHomePalette.textSecondary,
                ),
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              StudentStatusChip(
                label: _dueLabel(),
                tone: dueTone,
              ),
              const SizedBox(width: 6),
              StudentStatusChip(
                label: homework.isRead ? 'Viewed' : 'New',
                tone: homework.isRead
                    ? StudentChipTone.neutral
                    : StudentChipTone.info,
              ),
              if (homework.attachmentCount > 0) ...[
                const SizedBox(width: 6),
                StudentStatusChip(
                  label: '${homework.attachmentCount} file${homework.attachmentCount == 1 ? '' : 's'}',
                  tone: StudentChipTone.info,
                ),
              ],
            ],
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Text(
                _formattedDate(),
                style: Theme.of(context).textTheme.labelMedium?.copyWith(
                      color: StudentHomePalette.textMuted,
                      fontWeight: FontWeight.w600,
                    ),
              ),
              if (homework.attachmentCount > 0) ...[
                const SizedBox(width: 8),
                const Icon(
                  Icons.attach_file_rounded,
                  size: 18,
                  color: StudentHomePalette.textMuted,
                ),
              ],
              const Spacer(),
              if (!homework.isSubmitted)
                FilledButton.tonalIcon(
                  onPressed: submitting ? null : onSubmit,
                  style: FilledButton.styleFrom(
                    backgroundColor: const Color(0xFF2A4CA3),
                    foregroundColor: Colors.white,
                    visualDensity: VisualDensity.compact,
                    padding:
                        const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(10),
                    ),
                  ),
                  icon: submitting
                      ? const SizedBox(
                          width: 14,
                          height: 14,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            valueColor:
                                AlwaysStoppedAnimation<Color>(Colors.white),
                          ),
                        )
                      : const Icon(Icons.upload_file_rounded, size: 16),
                  label: Text(submitting ? 'Submitting...' : 'Submit'),
                )
              else
                const StudentStatusChip(
                  label: 'Completed',
                  tone: StudentChipTone.success,
                ),
            ],
          ),
        ],
      ),
    );
  }
}
