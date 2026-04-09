import 'package:flutter/material.dart';

import '../../models/student_models.dart';

class StudentDoubtCtaCard extends StatelessWidget {
  const StudentDoubtCtaCard({
    super.key,
    required this.data,
    required this.onTap,
  });

  final StudentDoubtCtaData data;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(20),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            Color(0xFF0F2B5F),
            Color(0xFF123C7E),
          ],
        ),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF123C7E).withValues(alpha: 0.28),
            blurRadius: 20,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(12),
              ),
              alignment: Alignment.center,
              child: const Icon(
                Icons.help_outline_rounded,
                color: Colors.white,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    data.title,
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                          color: Colors.white,
                          fontWeight: FontWeight.w700,
                        ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    data.subtitle,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Colors.white.withValues(alpha: 0.88),
                        ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 12),
            FilledButton.tonal(
              onPressed: onTap,
              style: FilledButton.styleFrom(
                backgroundColor: Colors.white,
                foregroundColor: const Color(0xFF123C7E),
              ),
              child: Text(data.actionLabel),
            ),
          ],
        ),
      ),
    );
  }
}
