import "dart:async";
import "package:flutter/material.dart";

import "../../../../core/config/app_env.dart";
import "student_notification_bell.dart";

class StudentHomeHeader extends StatelessWidget {
  const StudentHomeHeader({
    super.key,
    required this.studentName,
    required this.classLabel,
    required this.streamLabel,
    required this.unreadCount,
    required this.onNotificationTap,
    this.photoUrl,
    this.textColor = Colors.white,
    this.showNotificationBell = true,
    this.weeklyRankLabel = "Weekly #18",
    this.overallRankLabel = "Overall #42",
    this.xpPoints = 1250,
    this.levelName = "Silver",
    this.levelProgress = 0.62,
    this.serverMinuteOfDay,
    this.serverSyncedAt,
    this.serverTimezone = "Asia/Kolkata",
  });

  final String studentName;
  final String classLabel;
  final String streamLabel;
  final int unreadCount;
  final VoidCallback onNotificationTap;
  final String? photoUrl;
  final Color textColor;
  final bool showNotificationBell;
  final String weeklyRankLabel;
  final String overallRankLabel;
  final int xpPoints;
  final String levelName;
  final double levelProgress;
  final int? serverMinuteOfDay;
  final DateTime? serverSyncedAt;
  final String serverTimezone;

  @override
  Widget build(BuildContext context) {
    final effectivePhoto = AppEnv.resolveServerUrl(photoUrl);

    return ClipRRect(
      borderRadius: BorderRadius.circular(22),
      child: Stack(
        children: [
          Positioned.fill(
            child: DecoratedBox(
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(22),
                gradient: const LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [
                    Color(0xFF8A00FF),
                    Color(0xFFB100FF),
                    Color(0xFF6A00F4),
                  ],
                ),
                border: Border.all(
                  color: Colors.white.withValues(alpha: 0.22),
                ),
                boxShadow: [
                  BoxShadow(
                    color: const Color(0xFF6A00F4).withValues(alpha: 0.44),
                    blurRadius: 22,
                    spreadRadius: -10,
                    offset: const Offset(0, 10),
                  ),
                ],
              ),
            ),
          ),
          Positioned(
            left: -34,
            top: -56,
            child: _TextureOrb(
              size: 170,
              color: const Color(0xFFC084FC).withValues(alpha: 0.32),
            ),
          ),
          Positioned(
            right: -50,
            bottom: -60,
            child: _TextureOrb(
              size: 180,
              color: const Color(0xFFE879F9).withValues(alpha: 0.30),
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
            child: Column(
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      width: 58,
                      height: 58,
                      padding: const EdgeInsets.all(2.8),
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        gradient: const LinearGradient(
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                          colors: [
                            Color(0xFFFFF1B0),
                            Color(0xFFF7CF62),
                            Color(0xFFDEAA2A),
                          ],
                        ),
                        boxShadow: [
                          BoxShadow(
                            color:
                                const Color(0xFFFFD86B).withValues(alpha: 0.35),
                            blurRadius: 14,
                            spreadRadius: -8,
                            offset: const Offset(0, 8),
                          ),
                        ],
                      ),
                      child: ClipOval(
                        child: Container(
                          color: const Color(0xFFE9EEFF),
                          child: effectivePhoto != null
                              ? Image.network(
                                  effectivePhoto,
                                  fit: BoxFit.cover,
                                  errorBuilder: (_, __, ___) =>
                                      const _AvatarFallback(),
                                )
                              : const _AvatarFallback(),
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          _TimeAwareGreetingText(
                            serverMinuteOfDay: serverMinuteOfDay,
                            serverSyncedAt: serverSyncedAt,
                            serverTimezone: serverTimezone,
                          ),
                          const SizedBox(height: 2),
                          Text(
                            studentName,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: Theme.of(context)
                                .textTheme
                                .titleSmall
                                ?.copyWith(
                                  color: textColor,
                                  fontWeight: FontWeight.w800,
                                  height: 1.0,
                                ),
                          ),
                          const SizedBox(height: 6),
                          Wrap(
                            spacing: 6,
                            runSpacing: 6,
                            children: [
                              _InfoTag(label: classLabel),
                              _InfoTag(label: streamLabel),
                            ],
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 8),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        if (showNotificationBell) ...[
                          StudentNotificationBell(
                            unreadCount: unreadCount,
                            onTap: onNotificationTap,
                          ),
                          const SizedBox(height: 6),
                        ],
                        _XpTopCard(
                          xpPoints: xpPoints,
                          levelName: levelName,
                          levelProgress: levelProgress,
                        ),
                      ],
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Align(
                  alignment: Alignment.centerLeft,
                  child: Wrap(
                    spacing: 6,
                    runSpacing: 6,
                    children: [
                      _TinyStatChip(
                        icon: Icons.leaderboard_rounded,
                        label: weeklyRankLabel,
                        color: const Color(0xFF93C5FD),
                      ),
                      _TinyStatChip(
                        icon: Icons.workspace_premium_rounded,
                        label: overallRankLabel,
                        color: const Color(0xFFFCD34D),
                      ),
                    ],
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

class _TimeAwareGreetingText extends StatefulWidget {
  const _TimeAwareGreetingText({
    required this.serverMinuteOfDay,
    required this.serverSyncedAt,
    required this.serverTimezone,
  });

  final int? serverMinuteOfDay;
  final DateTime? serverSyncedAt;
  final String serverTimezone;

  @override
  State<_TimeAwareGreetingText> createState() => _TimeAwareGreetingTextState();
}

class _TimeAwareGreetingTextState extends State<_TimeAwareGreetingText> {
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _timer = Timer.periodic(const Duration(seconds: 30), (_) {
      if (mounted) {
        setState(() {});
      }
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  int _resolvedMinuteOfDay() {
    final syncedAt = widget.serverSyncedAt;
    final minuteFromServer = widget.serverMinuteOfDay;
    final _ = widget.serverTimezone;

    if (syncedAt == null || minuteFromServer == null) {
      final localNow = DateTime.now();
      return (localNow.hour * 60) + localNow.minute;
    }

    final elapsedMinutes = DateTime.now().difference(syncedAt).inMinutes;
    final totalMinutes = minuteFromServer + elapsedMinutes;
    final normalized = totalMinutes % 1440;
    return normalized < 0 ? normalized + 1440 : normalized;
  }

  String _greetingLabel() {
    final minute = _resolvedMinuteOfDay();
    if (minute < 12 * 60) {
      return "Good Morning";
    }
    if (minute < 17 * 60) {
      return "Good Afternoon";
    }
    return "Good Evening";
  }

  @override
  Widget build(BuildContext context) {
    return Text(
      _greetingLabel(),
      style: Theme.of(context).textTheme.labelLarge?.copyWith(
            color: Colors.white.withValues(alpha: 0.90),
            fontWeight: FontWeight.w700,
            height: 1.0,
          ),
    );
  }
}

class _TextureOrb extends StatelessWidget {
  const _TextureOrb({required this.size, required this.color});

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

class _AvatarFallback extends StatelessWidget {
  const _AvatarFallback();

  @override
  Widget build(BuildContext context) {
    return const Icon(
      Icons.person_rounded,
      color: Color(0xFF4D58A9),
      size: 30,
    );
  }
}

class _InfoTag extends StatelessWidget {
  const _InfoTag({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: Colors.white.withValues(alpha: 0.16),
        border: Border.all(color: Colors.white.withValues(alpha: 0.22)),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelSmall?.copyWith(
              color: Colors.white,
              fontWeight: FontWeight.w700,
            ),
      ),
    );
  }
}

class _TinyStatChip extends StatelessWidget {
  const _TinyStatChip({
    required this.icon,
    required this.label,
    required this.color,
  });

  final IconData icon;
  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(11),
        color: Colors.black.withValues(alpha: 0.17),
        border: Border.all(color: Colors.white.withValues(alpha: 0.16)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: color),
          const SizedBox(width: 4),
          Text(
            label,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
                  color: Colors.white.withValues(alpha: 0.96),
                  fontWeight: FontWeight.w700,
                ),
          ),
        ],
      ),
    );
  }
}

class _XpTopCard extends StatelessWidget {
  const _XpTopCard({
    required this.xpPoints,
    required this.levelName,
    required this.levelProgress,
  });

  final int xpPoints;
  final String levelName;
  final double levelProgress;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 102,
      padding: const EdgeInsets.fromLTRB(8, 7, 8, 7),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(12),
        color: Colors.white.withValues(alpha: 0.16),
        border: Border.all(color: Colors.white.withValues(alpha: 0.24)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            "XP",
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
                  color: Colors.white.withValues(alpha: 0.90),
                  fontWeight: FontWeight.w700,
                ),
          ),
          const SizedBox(height: 2),
          Text(
            "$xpPoints",
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  color: Colors.white,
                  fontWeight: FontWeight.w800,
                  height: 1.0,
                ),
          ),
          const SizedBox(height: 3),
          Text(
            levelName,
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
                  color: const Color(0xFFFFF4B8),
                  fontWeight: FontWeight.w700,
                  height: 1.0,
                ),
          ),
          const SizedBox(height: 5),
          ClipRRect(
            borderRadius: BorderRadius.circular(999),
            child: LinearProgressIndicator(
              minHeight: 4,
              value: levelProgress.clamp(0.0, 1.0),
              backgroundColor: Colors.white.withValues(alpha: 0.20),
              valueColor: const AlwaysStoppedAnimation<Color>(
                Color(0xFFF3D77A),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
