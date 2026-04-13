import "package:flutter/material.dart";

class StudentPageBackgroundLayer extends StatelessWidget {
  const StudentPageBackgroundLayer({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            Color(0xFF130C2C),
            Color(0xFF1B1240),
            Color(0xFF111E46),
            Color(0xFF0C1738),
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
              color: Color(0x4D7F54F9),
            ),
          ),
          Positioned(
            right: -80,
            top: 120,
            child: _GlowOrb(
              size: 270,
              color: Color(0x383B7BFF),
            ),
          ),
          Positioned(
            left: -40,
            bottom: -120,
            child: _GlowOrb(
              size: 260,
              color: Color(0x2E925CFF),
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
