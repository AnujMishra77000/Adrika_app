import 'dart:async';

import 'package:flutter/material.dart';

class TeacherPalette {
  static const Color oceanBlue = Color(0xFF1F5DA8);
  static const Color deepOcean = Color(0xFF183B73);
  static const Color violet = Color(0xFFA389F4);
  static const Color lightViolet = Color(0xFFD9CEFF);
  static const Color white = Color(0xFFFFFFFF);
  static const Color softWhite = Color(0xFFF3F7FF);
  static const Color textDark = Color(0xFF0F1A33);
}

Duration teacherStagger(
  int index, {
  int baseMs = 40,
  int stepMs = 70,
  int maxMs = 520,
}) {
  final raw = baseMs + (index * stepMs);
  final bounded = raw > maxMs ? maxMs : raw;
  return Duration(milliseconds: bounded);
}

class TeacherGradientBackground extends StatelessWidget {
  const TeacherGradientBackground({
    super.key,
    required this.child,
  });

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        Container(
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                Color(0xFF13345F),
                Color(0xFF2A4D84),
                Color(0xFF7D69D8),
              ],
            ),
          ),
        ),
        Positioned(
          top: -120,
          right: -60,
          child: Container(
            width: 260,
            height: 260,
            decoration: BoxDecoration(
              color: TeacherPalette.lightViolet.withValues(alpha: 0.14),
              shape: BoxShape.circle,
            ),
          ),
        ),
        Positioned(
          bottom: -120,
          left: -90,
          child: Container(
            width: 280,
            height: 280,
            decoration: BoxDecoration(
              color: TeacherPalette.white.withValues(alpha: 0.09),
              shape: BoxShape.circle,
            ),
          ),
        ),
        child,
      ],
    );
  }
}

class TeacherSurfaceCard extends StatelessWidget {
  const TeacherSurfaceCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(14),
    this.margin,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;
  final EdgeInsetsGeometry? margin;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: margin,
      padding: padding,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        color: TeacherPalette.white.withValues(alpha: 0.94),
        border: Border.all(
          color: TeacherPalette.white.withValues(alpha: 0.45),
        ),
        boxShadow: [
          BoxShadow(
            color: TeacherPalette.deepOcean.withValues(alpha: 0.18),
            blurRadius: 14,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: child,
    );
  }
}

class TeacherScreenHeader extends StatelessWidget {
  const TeacherScreenHeader({
    super.key,
    required this.title,
    required this.subtitle,
    this.icon,
  });

  final String title;
  final String subtitle;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    return TeacherSurfaceCard(
      margin: const EdgeInsets.only(bottom: 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (icon != null)
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(12),
                gradient: const LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [
                    TeacherPalette.oceanBlue,
                    TeacherPalette.violet,
                  ],
                ),
              ),
              child: Icon(icon, color: TeacherPalette.white),
            ),
          if (icon != null) const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    color: TeacherPalette.textDark,
                    fontSize: 20,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  subtitle,
                  style: TextStyle(
                    color: TeacherPalette.textDark.withValues(alpha: 0.75),
                    fontSize: 13,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class TeacherStatusChip extends StatelessWidget {
  const TeacherStatusChip({
    super.key,
    required this.label,
  });

  final String label;

  @override
  Widget build(BuildContext context) {
    final normalized = label.toLowerCase();
    Color background;
    Color foreground;

    switch (normalized) {
      case 'resolved':
      case 'closed':
      case 'read':
        background = const Color(0xFFDFF7E7);
        foreground = const Color(0xFF166534);
        break;
      case 'in_progress':
        background = const Color(0xFFE8EDFF);
        foreground = const Color(0xFF1E3A8A);
        break;
      case 'open':
      case 'unread':
        background = const Color(0xFFFFF4D8);
        foreground = const Color(0xFF9A6A00);
        break;
      default:
        background = TeacherPalette.softWhite;
        foreground = TeacherPalette.textDark;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: background,
      ),
      child: Text(
        label,
        style: TextStyle(
          color: foreground,
          fontWeight: FontWeight.w600,
          fontSize: 12,
        ),
      ),
    );
  }
}

class TeacherEntrance extends StatefulWidget {
  const TeacherEntrance({
    super.key,
    required this.child,
    this.delay = Duration.zero,
    this.duration = const Duration(milliseconds: 420),
    this.offsetY = 18,
    this.curve = Curves.easeOutCubic,
  });

  final Widget child;
  final Duration delay;
  final Duration duration;
  final double offsetY;
  final Curve curve;

  @override
  State<TeacherEntrance> createState() => _TeacherEntranceState();
}

class _TeacherEntranceState extends State<TeacherEntrance>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _animation;
  Timer? _delayTimer;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: widget.duration,
    );
    _animation = CurvedAnimation(parent: _controller, curve: widget.curve);

    if (widget.delay == Duration.zero) {
      _controller.forward();
    } else {
      _delayTimer = Timer(widget.delay, () {
        if (mounted) {
          _controller.forward();
        }
      });
    }
  }

  @override
  void dispose() {
    _delayTimer?.cancel();
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _animation,
      child: widget.child,
      builder: (context, child) {
        final value = _animation.value;
        return Opacity(
          opacity: value,
          child: Transform.translate(
            offset: Offset(0, (1 - value) * widget.offsetY),
            child: child,
          ),
        );
      },
    );
  }
}

class TeacherTapScale extends StatefulWidget {
  const TeacherTapScale({
    super.key,
    required this.child,
    this.onTap,
    this.borderRadius = const BorderRadius.all(Radius.circular(14)),
    this.scaleDown = 0.985,
  });

  final Widget child;
  final VoidCallback? onTap;
  final BorderRadius borderRadius;
  final double scaleDown;

  @override
  State<TeacherTapScale> createState() => _TeacherTapScaleState();
}

class _TeacherTapScaleState extends State<TeacherTapScale> {
  bool _pressed = false;

  void _setPressed(bool pressed) {
    if (!mounted || _pressed == pressed) {
      return;
    }
    setState(() {
      _pressed = pressed;
    });
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedScale(
      scale: _pressed ? widget.scaleDown : 1,
      duration: const Duration(milliseconds: 120),
      curve: Curves.easeOut,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: widget.borderRadius,
          onTap: widget.onTap,
          onTapDown: widget.onTap == null ? null : (_) => _setPressed(true),
          onTapCancel: widget.onTap == null ? null : () => _setPressed(false),
          onTapUp: widget.onTap == null ? null : (_) => _setPressed(false),
          child: widget.child,
        ),
      ),
    );
  }
}

class TeacherErrorView extends StatelessWidget {
  const TeacherErrorView({
    super.key,
    required this.title,
    required this.message,
    required this.onRetry,
  });

  final String title;
  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return TeacherGradientBackground(
      child: Center(
        child: Padding(
          padding: const EdgeInsets.all(18),
          child: TeacherSurfaceCard(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    color: TeacherPalette.textDark,
                    fontSize: 16,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  message,
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: TeacherPalette.textDark.withValues(alpha: 0.72),
                  ),
                ),
                const SizedBox(height: 14),
                FilledButton(
                  style: FilledButton.styleFrom(
                    backgroundColor: TeacherPalette.oceanBlue,
                    foregroundColor: TeacherPalette.white,
                  ),
                  onPressed: onRetry,
                  child: const Text('Retry'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class TeacherLoadingView extends StatelessWidget {
  const TeacherLoadingView({super.key});

  @override
  Widget build(BuildContext context) {
    return const TeacherGradientBackground(
      child: Center(
        child: CircularProgressIndicator(
          color: TeacherPalette.white,
        ),
      ),
    );
  }
}
