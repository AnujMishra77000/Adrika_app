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

  Color _kindColor(String kind) {
    switch (kind.toLowerCase()) {
      case "lecture":
        return const Color(0xFF0B4CC2);
      case "test":
        return const Color(0xFF0277BD);
      case "homework":
        return const Color(0xFF1B5E9B);
      default:
        return const Color(0xFF1565C0);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(22),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            Color(0xFF8FD3FF),
            Color(0xFF6ABEFF),
            Color(0xFF56AFFF),
          ],
          stops: [0.0, 0.55, 1.0],
        ),
        border: Border.all(color: const Color(0xFFD9F0FF)),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF3E96D9).withValues(alpha: 0.30),
            blurRadius: 22,
            spreadRadius: -8,
            offset: const Offset(0, 12),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(22),
        child: Stack(
          children: [
            Positioned(
              left: -40,
              top: -64,
              child: _BlurOrb(
                size: 220,
                color: const Color(0xFFDAF1FF).withValues(alpha: 0.55),
              ),
            ),
            Positioned(
              right: -30,
              bottom: -64,
              child: _BlurOrb(
                size: 180,
                color: const Color(0xFF4AA7FF).withValues(alpha: 0.24),
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(14, 14, 14, 14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    "Today Schedule",
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          color: const Color(0xFF042B64),
                          fontWeight: FontWeight.w800,
                        ),
                  ),
                  const SizedBox(height: 10),
                  ...List<Widget>.generate(items.length, (index) {
                    final item = items[index];
                    final kindColor = _kindColor(item.kind);
                    return Padding(
                      padding: EdgeInsets.only(
                          bottom: index == items.length - 1 ? 0 : 10),
                      child: Material(
                        color: Colors.transparent,
                        borderRadius: BorderRadius.circular(14),
                        child: InkWell(
                          borderRadius: BorderRadius.circular(14),
                          onTap: () => onTap(item.route),
                          child: Ink(
                            decoration: BoxDecoration(
                              borderRadius: BorderRadius.circular(14),
                              border: Border.all(
                                color: Colors.white.withValues(alpha: 0.65),
                              ),
                              gradient: LinearGradient(
                                begin: Alignment.topLeft,
                                end: Alignment.bottomRight,
                                colors: [
                                  Colors.white.withValues(alpha: 0.45),
                                  Colors.white.withValues(alpha: 0.23),
                                ],
                              ),
                            ),
                            child: Padding(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 11,
                                vertical: 10,
                              ),
                              child: Row(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    _formatTime(item.scheduledAt),
                                    style: Theme.of(context)
                                        .textTheme
                                        .labelMedium
                                        ?.copyWith(
                                          color: const Color(0xFF05316E),
                                          fontWeight: FontWeight.w700,
                                        ),
                                  ),
                                  const SizedBox(width: 10),
                                  Icon(
                                    _kindIcon(item.kind),
                                    size: 18,
                                    color: kindColor,
                                  ),
                                  const SizedBox(width: 8),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: [
                                        Text(
                                          item.title,
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis,
                                          style: Theme.of(context)
                                              .textTheme
                                              .bodyMedium
                                              ?.copyWith(
                                                color: const Color(0xFF072F67),
                                                fontWeight: FontWeight.w700,
                                              ),
                                        ),
                                        const SizedBox(height: 2),
                                        Text(
                                          item.subtitle,
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis,
                                          style: Theme.of(context)
                                              .textTheme
                                              .bodySmall
                                              ?.copyWith(
                                                color: const Color(0xFF144D88),
                                              ),
                                        ),
                                      ],
                                    ),
                                  ),
                                  const SizedBox(width: 8),
                                  Text(
                                    item.kind,
                                    style: Theme.of(context)
                                        .textTheme
                                        .labelSmall
                                        ?.copyWith(
                                          color: kindColor,
                                          fontWeight: FontWeight.w700,
                                        ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                      ),
                    );
                  }),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _BlurOrb extends StatelessWidget {
  const _BlurOrb({required this.size, required this.color});

  final double size;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: RadialGradient(
          colors: [
            color,
            color.withValues(alpha: 0),
          ],
        ),
      ),
    );
  }
}
