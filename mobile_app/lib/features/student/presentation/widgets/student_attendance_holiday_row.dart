import 'package:flutter/material.dart';

import '../../models/student_models.dart';

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
    return '${date.day}/${date.month}/${date.year}';
  }

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: _InfoCard(
            title: 'Attendance',
            value: '${attendance.attendancePercent.toStringAsFixed(1)}%',
            subtitle:
                'Present ${attendance.presentCount}, Absent ${attendance.absentCount}',
            icon: Icons.fact_check_outlined,
            accent: const Color(0xFF89E2C4),
            onTap: onAttendanceTap,
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: _InfoCard(
            title: 'Holiday',
            value: holiday.nextHolidayName,
            subtitle: _holidaySubtitle(),
            icon: Icons.beach_access_outlined,
            accent: const Color(0xFFFFA8D0),
            onTap: onHolidayTap,
          ),
        ),
      ],
    );
  }
}

class _InfoCard extends StatelessWidget {
  const _InfoCard({
    required this.title,
    required this.value,
    required this.subtitle,
    required this.icon,
    required this.accent,
    required this.onTap,
  });

  final String title;
  final String value;
  final String subtitle;
  final IconData icon;
  final Color accent;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(18),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(18),
        child: Ink(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: const Color(0xFFDCE4F1)),
          ),
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 34,
                  height: 34,
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(10),
                    color: accent.withValues(alpha: 0.22),
                  ),
                  alignment: Alignment.center,
                  child: Icon(icon, size: 18, color: const Color(0xFF0F172A)),
                ),
                const SizedBox(height: 10),
                Text(
                  title,
                  style: Theme.of(context).textTheme.labelLarge?.copyWith(
                        color: const Color(0xFF475569),
                      ),
                ),
                const SizedBox(height: 2),
                Text(
                  value,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                ),
                const SizedBox(height: 6),
                Text(
                  subtitle,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: const Color(0xFF64748B),
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
