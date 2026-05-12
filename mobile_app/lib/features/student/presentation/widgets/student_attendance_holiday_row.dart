import "dart:ui";

import "package:flutter/material.dart";

import "../../models/student_models.dart";

class StudentAttendanceHolidayRow extends StatelessWidget {
  const StudentAttendanceHolidayRow({
    super.key,
    required this.attendance,
    required this.holiday,
    required this.onAttendanceTap,
    required this.onHolidayTap,
  });

  final StudentAttendanceSummary attendance;
  final StudentHolidaySummary holiday;
  final VoidCallback onAttendanceTap;
  final VoidCallback onHolidayTap;

  String _holidaySubtitle() {
    final date = holiday.date;
    if (date == null) {
      return holiday.subtitle;
    }
    return "${date.day}/${date.month}/${date.year}";
  }

  String _holidayCountdown() {
    final date = holiday.date;
    if (date == null) {
      return "Date pending";
    }

    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final target = DateTime(date.year, date.month, date.day);
    final diff = target.difference(today).inDays;

    if (diff < 0) {
      return "Completed";
    }
    if (diff == 0) {
      return "Today";
    }
    if (diff == 1) {
      return "In 1 day";
    }
    return "In $diff days";
  }

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: SizedBox(
            height: 168,
            child: _GoldInfoCard(
              title: "Attendance",
              icon: Icons.fact_check_outlined,
              iconColor: const Color(0xFFEAF2FF),
              primaryText:
                  "${attendance.attendancePercent.toStringAsFixed(1)}%",
              secondaryText:
                  "Present ${attendance.presentCount} | Absent ${attendance.absentCount}",
              progress: (attendance.attendancePercent / 100).clamp(0.0, 1.0),
              onTap: onAttendanceTap,
            ),
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: SizedBox(
            height: 168,
            child: _GoldInfoCard(
              title: "Holiday",
              icon: Icons.celebration_outlined,
              iconColor: const Color(0xFFEAF2FF),
              primaryText: holiday.nextHolidayName,
              secondaryText: _holidaySubtitle(),
              chipText: _holidayCountdown(),
              onTap: onHolidayTap,
            ),
          ),
        ),
      ],
    );
  }
}

class _GoldInfoCard extends StatelessWidget {
  const _GoldInfoCard({
    required this.title,
    required this.icon,
    required this.iconColor,
    required this.primaryText,
    required this.secondaryText,
    required this.onTap,
    this.progress,
    this.chipText,
  });

  final String title;
  final IconData icon;
  final Color iconColor;
  final String primaryText;
  final String secondaryText;
  final VoidCallback onTap;
  final double? progress;
  final String? chipText;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      borderRadius: BorderRadius.circular(20),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(20),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(20),
          child: Stack(
            children: [
              BackdropFilter(
                filter: ImageFilter.blur(sigmaX: 8, sigmaY: 8),
                child: const SizedBox.expand(),
              ),
              Ink(
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(20),
                  color: const Color(0xFF090A0C).withValues(alpha: 0.92),
                  border: Border.all(
                      color: const Color(0xFF2A2F36).withValues(alpha: 0.92)),
                  boxShadow: [
                    BoxShadow(
                      color: const Color(0xFF000000).withValues(alpha: 0.42),
                      blurRadius: 22,
                      spreadRadius: -8,
                      offset: const Offset(0, 12),
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
                          Icon(icon, color: iconColor, size: 20),
                          const SizedBox(width: 6),
                          Text(
                            title,
                            style: Theme.of(context)
                                .textTheme
                                .labelLarge
                                ?.copyWith(
                                  color: const Color(0xFFF4F7FF),
                                  fontWeight: FontWeight.w700,
                                ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Text(
                        primaryText,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.titleSmall?.copyWith(
                              fontWeight: FontWeight.w800,
                              color: Colors.white,
                            ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        secondaryText,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: const Color(0xFFCBD5E1),
                              fontWeight: FontWeight.w600,
                            ),
                      ),
                      const Spacer(),
                      if (progress != null) ...[
                        ClipRRect(
                          borderRadius: BorderRadius.circular(999),
                          child: LinearProgressIndicator(
                            minHeight: 6,
                            value: progress,
                            backgroundColor:
                                const Color(0xFF2A2F36).withValues(alpha: 0.9),
                            valueColor: const AlwaysStoppedAnimation<Color>(
                              Color(0xFF6EA8FF),
                            ),
                          ),
                        ),
                      ],
                      if (chipText != null) ...[
                        Container(
                          margin: const EdgeInsets.only(top: 8),
                          padding: const EdgeInsets.symmetric(
                            horizontal: 9,
                            vertical: 4,
                          ),
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(999),
                            color:
                                const Color(0xFF1C222B).withValues(alpha: 0.95),
                          ),
                          child: Text(
                            chipText!,
                            style: Theme.of(context)
                                .textTheme
                                .labelSmall
                                ?.copyWith(
                                  color: const Color(0xFFE5EAF3),
                                  fontWeight: FontWeight.w700,
                                ),
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
