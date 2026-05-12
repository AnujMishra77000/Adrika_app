import "package:flutter/material.dart";

abstract final class StudentQuickAccessTheme {
  static const scaffold = Color(0xFF0E1F58);

  static const appBarStart = Color(0xFF50208F);
  static const appBarEnd = Color(0xFF2D1D79);

  static const surface = Color(0xFFFFFFFF);
  static const surfaceAlt = Color(0xFFFFFFFF);
  static const surfaceBorder = Color(0xFFE2E8F0);

  static const textPrimary = Color(0xFF0F172A);
  static const textSecondary = Color(0xFF334155);
  static const textMuted = Color(0xFF64748B);
}

class StudentPageBackgroundLayer extends StatelessWidget {
  const StudentPageBackgroundLayer({super.key});

  @override
  Widget build(BuildContext context) {
    return const _RoyalStudentBackground();
  }
}

class StudentQuickAccessBackgroundLayer extends StatelessWidget {
  const StudentQuickAccessBackgroundLayer({super.key});

  @override
  Widget build(BuildContext context) {
    return const _RoyalStudentBackground();
  }
}

class _RoyalStudentBackground extends StatelessWidget {
  const _RoyalStudentBackground();

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            Color(0xFF0E1F58),
            Color(0xFF132E7D),
            Color(0xFF1A3F9A),
            Color(0xFF0E295F),
          ],
        ),
      ),
      child: Stack(
        children: const [
          Positioned(
            left: -90,
            top: -120,
            child: _GlowOrb(
              size: 310,
              color: Color(0x3D92B7FF),
            ),
          ),
          Positioned(
            right: -80,
            top: 130,
            child: _GlowOrb(
              size: 270,
              color: Color(0x3D7C59F4),
            ),
          ),
          Positioned(
            left: -40,
            bottom: -120,
            child: _GlowOrb(
              size: 260,
              color: Color(0x2EBFD4FF),
            ),
          ),
        ],
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
