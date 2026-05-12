import "package:flutter/material.dart";

import "../../models/student_models.dart";

class StudentTodaySchedulePanel extends StatelessWidget {
  const StudentTodaySchedulePanel({
    super.key,
    required this.items,
    required this.onTap,
  });

  final List<StudentTodayScheduleItem> items;
  final ValueChanged<String> onTap;

  String _formatTime(DateTime value) {
    final hour = value.hour % 12 == 0 ? 12 : value.hour % 12;
    final minute = value.minute.toString().padLeft(2, "0");
    final suffix = value.hour >= 12 ? "PM" : "AM";
    return "$hour:$minute $suffix";
  }

  IconData _kindIcon(String kind) {
    switch (kind.toLowerCase()) {
      case "lecture":
        return Icons.cast_for_education_rounded;
      case "test":
        return Icons.fact_check_rounded;
      case "homework":
        return Icons.assignment_rounded;
      default:
        return Icons.event_note_rounded;
    }
  }

  Color _badgeColor(String status) {
    switch (status) {
      case "Upcoming":
        return const Color(0xFFF59E0B);
      case "Live":
        return const Color(0xFF22C55E);
      case "Completed":
        return const Color(0xFFFCD34D);
      default:
        return const Color(0xFFF59E0B);
    }
  }

  String _statusFor(DateTime when) {
    final now = DateTime.now();
    final diff = when.difference(now);

    if (diff.inMinutes > 0) {
      return "Upcoming";
    }
    if (diff.inMinutes >= -59) {
      return "Live";
    }
    return "Completed";
  }

  @override
  Widget build(BuildContext context) {
    final sorted = [...items]
      ..sort((a, b) => a.scheduledAt.compareTo(b.scheduledAt));

    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(22),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            Color(0xFF7A3A09),
            Color(0xFF8C4510),
            Color(0xFFA65518),
          ],
        ),
        border:
            Border.all(color: const Color(0xFFC77737).withValues(alpha: 0.48)),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF4A1F07).withValues(alpha: 0.30),
            blurRadius: 26,
            spreadRadius: -8,
            offset: const Offset(0, 12),
          ),
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(14, 14, 14, 14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              "Today's Schedule",
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    color: const Color(0xFFFFF7ED),
                    fontWeight: FontWeight.w800,
                  ),
            ),
            const SizedBox(height: 10),
            if (sorted.isEmpty)
              Text(
                "No lectures or tests lined up for today.",
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: const Color(0xFFFFE9D4).withValues(alpha: 0.92),
                    ),
              )
            else
              ...List<Widget>.generate(sorted.length, (index) {
                final item = sorted[index];
                final status = _statusFor(item.scheduledAt);
                final statusColor = _badgeColor(status);

                return Padding(
                  padding: EdgeInsets.only(
                      bottom: index == sorted.length - 1 ? 0 : 8),
                  child: InkWell(
                    borderRadius: BorderRadius.circular(14),
                    onTap: () => onTap(item.route),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        SizedBox(
                          width: 12,
                          child: Column(
                            children: [
                              const SizedBox(height: 1),
                              if (index != sorted.length - 1)
                                Container(
                                  width: 2,
                                  height: 52,
                                  color: const Color(0xFFF59E0B)
                                      .withValues(alpha: 0.50),
                                ),
                            ],
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Container(
                            padding: const EdgeInsets.fromLTRB(10, 8, 10, 8),
                            decoration: BoxDecoration(
                              borderRadius: BorderRadius.circular(14),
                              color: const Color(0xFF5A2A08)
                                  .withValues(alpha: 0.93),
                              border: Border.all(
                                color: const Color(0xFFC77737)
                                    .withValues(alpha: 0.30),
                              ),
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Icon(
                                      _kindIcon(item.kind),
                                      size: 18,
                                      color: const Color(0xFFFFE9D4),
                                    ),
                                    const SizedBox(width: 8),
                                    Expanded(
                                      child: Text(
                                        item.title,
                                        maxLines: 1,
                                        overflow: TextOverflow.ellipsis,
                                        style: Theme.of(context)
                                            .textTheme
                                            .bodyMedium
                                            ?.copyWith(
                                              color: const Color(0xFFFFF7ED),
                                              fontWeight: FontWeight.w700,
                                            ),
                                      ),
                                    ),
                                    const SizedBox(width: 8),
                                    Text(
                                      _formatTime(item.scheduledAt),
                                      style: Theme.of(context)
                                          .textTheme
                                          .labelSmall
                                          ?.copyWith(
                                            color: const Color(0xFFFFE9D4),
                                            fontWeight: FontWeight.w800,
                                          ),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 3),
                                Row(
                                  children: [
                                    Expanded(
                                      child: Text(
                                        item.subtitle,
                                        maxLines: 1,
                                        overflow: TextOverflow.ellipsis,
                                        style: Theme.of(context)
                                            .textTheme
                                            .bodySmall
                                            ?.copyWith(
                                              color: const Color(0xFFFFE9D4)
                                                  .withValues(alpha: 0.88),
                                            ),
                                      ),
                                    ),
                                    const SizedBox(width: 8),
                                    Container(
                                      padding: const EdgeInsets.symmetric(
                                        horizontal: 8,
                                        vertical: 3,
                                      ),
                                      decoration: BoxDecoration(
                                        color:
                                            statusColor.withValues(alpha: 0.17),
                                        borderRadius:
                                            BorderRadius.circular(999),
                                        border: Border.all(
                                          color: statusColor.withValues(
                                              alpha: 0.34),
                                        ),
                                      ),
                                      child: Text(
                                        status,
                                        style: Theme.of(context)
                                            .textTheme
                                            .labelSmall
                                            ?.copyWith(
                                              color: statusColor,
                                              fontWeight: FontWeight.w700,
                                            ),
                                      ),
                                    ),
                                  ],
                                ),
                              ],
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                );
              }),
          ],
        ),
      ),
    );
  }
}
