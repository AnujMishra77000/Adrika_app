import "package:flutter/material.dart";

import "../../models/student_models.dart";

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
            Color(0xFF24153F),
            Color(0xFF1B1D44),
            Color(0xFF15254E),
          ],
          stops: [0.0, 0.52, 1.0],
        ),
        border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF36216D).withValues(alpha: 0.44),
            blurRadius: 28,
            spreadRadius: -7,
            offset: const Offset(0, 12),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(20),
        child: Stack(
          children: [
            Positioned(
              left: -48,
              top: -64,
              child: _GlowOrb(
                size: 210,
                color: const Color(0xFF9A75FF).withValues(alpha: 0.28),
              ),
            ),
            Positioned(
              right: -32,
              bottom: -54,
              child: _GlowOrb(
                size: 165,
                color: const Color(0xFF5F80FF).withValues(alpha: 0.24),
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  Container(
                    width: 44,
                    height: 44,
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.10),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: Colors.white.withValues(alpha: 0.18),
                      ),
                    ),
                    alignment: Alignment.center,
                    child: const Icon(
                      Icons.help_outline_rounded,
                      color: Color(0xFFDDDAFF),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          data.title,
                          style:
                              Theme.of(context).textTheme.titleSmall?.copyWith(
                                    color: const Color(0xFFF6F4FF),
                                    fontWeight: FontWeight.w800,
                                  ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          data.subtitle,
                          style:
                              Theme.of(context).textTheme.bodySmall?.copyWith(
                                    color: const Color(0xFFB7B2D7),
                                  ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 12),
                  FilledButton.tonal(
                    onPressed: onTap,
                    style: FilledButton.styleFrom(
                      backgroundColor: const Color(0xFF1E3D8F),
                      foregroundColor: Colors.white,
                    ),
                    child: Text(data.actionLabel),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _GlowOrb extends StatelessWidget {
  const _GlowOrb({required this.size, required this.color});

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
