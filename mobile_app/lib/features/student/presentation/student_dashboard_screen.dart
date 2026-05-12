import "package:flutter/material.dart";
import "package:flutter/services.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../models/student_models.dart";
import "../state/student_providers.dart";
import "widgets/student_announcement_card.dart";
import "widgets/student_attendance_holiday_row.dart";
import "widgets/student_auto_carousel_banner.dart";
import "widgets/student_doubt_cta_card.dart";
import "widgets/student_fade_slide_in.dart";
import "widgets/student_hero_banner.dart";
import "widgets/student_home_header.dart";
import "widgets/student_home_states.dart";
import "widgets/student_notification_bell.dart";
import "widgets/student_quick_action_grid.dart";
import "widgets/student_section_header.dart";
import "widgets/student_today_schedule_panel.dart";

class StudentDashboardScreen extends ConsumerWidget {
  const StudentDashboardScreen({super.key});

  Future<void> _refresh(WidgetRef ref) async {
    ref.invalidate(studentHomeSummaryProvider);
    ref.invalidate(studentNotificationsProvider);
    ref.invalidate(studentAnnouncementsProvider);
    await ref.read(studentHomeSummaryProvider.future);
  }

  String _upcomingLectureLabel(DateTime? value) {
    if (value == null) {
      return "Timetable sync pending";
    }

    final now = DateTime.now();
    final diff = value.difference(now);

    if (diff.inMinutes <= 0) {
      return "Starting shortly";
    }
    if (diff.inHours < 1) {
      return "Starts in ${diff.inMinutes} min";
    }
    if (diff.inHours < 24) {
      return "Starts in ${diff.inHours} hr";
    }
    return "Starts in ${diff.inDays} day";
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final summaryAsync = ref.watch(studentHomeSummaryProvider);

    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: const SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.light,
        statusBarBrightness: Brightness.dark,
      ),
      child: SafeArea(
        top: true,
        bottom: false,
        child: Stack(
          children: [
            const _RoyalBackdrop(),
            RefreshIndicator(
              onRefresh: () => _refresh(ref),
              child: summaryAsync.when(
                loading: () => const StudentHomeLoadingList(),
                error: (error, _) => StudentHomeErrorList(
                  message: error.toString(),
                  onRetry: () => ref.invalidate(studentHomeSummaryProvider),
                ),
                data: (summary) => _StudentHomeBody(
                  summary: summary,
                  upcomingLectureLabel:
                      _upcomingLectureLabel(summary.upcomingLecture.nextAt),
                  onRouteTap: (route) => context.push(route),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _RoyalBackdrop extends StatelessWidget {
  const _RoyalBackdrop();

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
        children: [
          Positioned(
            left: -90,
            top: -120,
            child: _GhostOrb(
              size: 310,
              color: const Color(0xFF92B7FF).withValues(alpha: 0.24),
            ),
          ),
          Positioned(
            right: -80,
            top: 130,
            child: _GhostOrb(
              size: 270,
              color: const Color(0xFF7C59F4).withValues(alpha: 0.24),
            ),
          ),
          Positioned(
            left: -40,
            bottom: -120,
            child: _GhostOrb(
              size: 260,
              color: const Color(0xFFBFD4FF).withValues(alpha: 0.18),
            ),
          ),
        ],
      ),
    );
  }
}

class _GhostOrb extends StatelessWidget {
  const _GhostOrb({required this.size, required this.color});

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

class _StudentHomeBody extends StatelessWidget {
  const _StudentHomeBody({
    required this.summary,
    required this.upcomingLectureLabel,
    required this.onRouteTap,
  });

  final StudentHomeSummary summary;
  final String upcomingLectureLabel;
  final ValueChanged<String> onRouteTap;

  String _classLabel() {
    final value = (summary.profile.className ?? "").trim();
    if (value.isEmpty) {
      return "Class not assigned";
    }
    return "Class $value";
  }

  String _streamLabel() {
    final value = (summary.profile.stream ?? "").trim();
    if (value.isEmpty) {
      return "General";
    }
    return value;
  }

  String _routeForAction({
    required String key,
    required String fallback,
  }) {
    for (final item in summary.quickActions) {
      if (item.iconKey == key && item.route.trim().isNotEmpty) {
        return item.route;
      }
    }
    return fallback;
  }

  int _badgeForAction(String key) {
    for (final item in summary.quickActions) {
      if (item.iconKey == key) {
        return item.badgeCount;
      }
    }
    return 0;
  }

  int _xpPoints() {
    final attendanceBoost = (summary.attendance.attendancePercent * 8).round();
    final testAttemptBoost = summary.progress.completedTestsCount * 45;
    final marksBoost = (summary.progress.overallScorePercent * 10).round();
    final disciplineBonus = (summary.attendance.attendancePercent >= 85 &&
            summary.progress.overallScorePercent >= 70)
        ? 250
        : 0;

    final xp =
        200 + attendanceBoost + testAttemptBoost + marksBoost + disciplineBonus;
    return xp.clamp(150, 99999);
  }

  String _levelName(int xp) {
    if (xp >= 5500) {
      return "Platinum";
    }
    if (xp >= 3000) {
      return "Gold";
    }
    return "Silver";
  }

  double _levelProgress(int xp) {
    return ((xp % 1000) / 1000).clamp(0.0, 1.0);
  }

  String _weeklyRankLabel() {
    final score = summary.progress.weeklyScorePercent;
    final attempts = summary.progress.completedTestsCount;
    final weighted = (score * 1.2) + (attempts * 1.8);
    final rank = (130 - weighted.round()).clamp(1, 120);
    return "Weekly #$rank";
  }

  String _overallRankLabel() {
    final score = summary.progress.overallScorePercent;
    final attendance = summary.attendance.attendancePercent;
    final weighted = (score * 1.0) + (attendance * 0.35);
    final rank = (150 - weighted.round()).clamp(1, 140);
    return "Overall #$rank";
  }

  List<StudentHeroCardData> _heroCards() {
    final todayValue = summary.todayLectures.primaryValue.trim();
    final normalizedToday = todayValue.isEmpty ? "0" : todayValue;

    return <StudentHeroCardData>[
      StudentHeroCardData(
        title: "Today's Lectures",
        value: normalizedToday,
        subtitle: "",
        route: "/student/lectures/today",
        icon: Icons.cast_for_education_rounded,
        accent: const Color(0xFF2563EB),
      ),
      StudentHeroCardData(
        title: "Weekly Schedule",
        value: "${summary.todaySchedule.length}",
        subtitle: "",
        route: "/student/lectures/upcoming",
        icon: Icons.event_note_rounded,
        accent: const Color(0xFF0EA5E9),
      ),
      StudentHeroCardData(
        title: "Study Materials",
        value: "${_badgeForAction("notes")}",
        subtitle: "",
        route: _routeForAction(key: "notes", fallback: "/student/notes"),
        icon: Icons.chrome_reader_mode_rounded,
        accent: const Color(0xFFF3E8FF),
      ),
      StudentHeroCardData(
        title: "Progress",
        value: "${summary.progress.scorePercent.toStringAsFixed(1)}%",
        subtitle: "",
        route: "/student/progress",
        icon: Icons.insights_rounded,
        accent: const Color(0xFFD1FAE5),
      ),
    ];
  }

  List<StudentQuickActionItem> _quickActions() {
    return <StudentQuickActionItem>[
      StudentQuickActionItem(
        id: "notice",
        title: "Notice",
        route: _routeForAction(key: "notice", fallback: "/student/notices"),
        iconKey: "notice",
        accentColor: const Color(0xFF16A34A),
        badgeCount: _badgeForAction("notice"),
      ),
      StudentQuickActionItem(
        id: "notes",
        title: "Notes",
        route: _routeForAction(key: "notes", fallback: "/student/notes"),
        iconKey: "notes",
        accentColor: const Color(0xFF7E52F7),
        badgeCount: _badgeForAction("notes"),
      ),
      StudentQuickActionItem(
        id: "homework",
        title: "Homework",
        route: _routeForAction(key: "homework", fallback: "/student/homework"),
        iconKey: "homework",
        accentColor: const Color(0xFFE06A00),
        badgeCount: _badgeForAction("homework"),
      ),
      StudentQuickActionItem(
        id: "online_test",
        title: "Online Test",
        route: _routeForAction(
          key: "online_test",
          fallback: "/student/online-tests",
        ),
        iconKey: "online_test",
        accentColor: const Color(0xFF2563EB),
        badgeCount: _badgeForAction("online_test"),
      ),
      StudentQuickActionItem(
        id: "practice_test",
        title: "Practice Test",
        route: _routeForAction(
          key: "practice",
          fallback: "/student/practice-tests",
        ),
        iconKey: "practice",
        accentColor: const Color(0xFFEF4444),
        badgeCount: _badgeForAction("practice"),
      ),
      StudentQuickActionItem(
        id: "suggestion_box",
        title: "Suggestion Box",
        route: _routeForAction(key: "suggestion", fallback: "/student/chat"),
        iconKey: "suggestion",
        accentColor: const Color(0xFF0E7490),
        badgeCount: _badgeForAction("suggestion"),
      ),
    ];
  }

  List<StudentCarouselBannerItem> _carouselItems() {
    if (summary.banners.isEmpty) {
      return const [
        StudentCarouselBannerItem(
          id: "fallback-banner",
          title: "Chapter Wise Test is Live!",
          imageUrl: "",
          actionRoute: "/student/online-tests",
        ),
      ];
    }

    return summary.banners
        .map(
          (item) => StudentCarouselBannerItem(
            id: item.id,
            title: item.title,
            imageUrl: item.mediaUrl,
            actionRoute:
                item.actionUrl != null && item.actionUrl!.trim().startsWith("/")
                    ? item.actionUrl!.trim()
                    : null,
          ),
        )
        .toList(growable: false);
  }

  @override
  Widget build(BuildContext context) {
    final heroCards = _heroCards();
    final quickActions = _quickActions();
    final xp = _xpPoints();

    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(0, 0, 0, 24),
      children: [
        StudentFadeSlideIn(
          delayMs: 0,
          child: _BrandHeader(
            unreadCount: summary.unreadNotificationCount,
            onNotificationTap: () => onRouteTap("/student/notifications"),
          ),
        ),
        const SizedBox(height: 8),
        const _HorizontalPad(
          child: StudentFadeSlideIn(
            delayMs: 20,
            child: _AdmissionOpenTicker(),
          ),
        ),
        const SizedBox(height: 10),
        _HorizontalPad(
          child: StudentFadeSlideIn(
            delayMs: 35,
            child: StudentHomeHeader(
              studentName: summary.profile.fullName,
              classLabel: _classLabel(),
              streamLabel: _streamLabel(),
              unreadCount: summary.unreadNotificationCount,
              onNotificationTap: () => onRouteTap("/student/notifications"),
              photoUrl: summary.profile.photoUrl,
              showNotificationBell: false,
              weeklyRankLabel: _weeklyRankLabel(),
              overallRankLabel: _overallRankLabel(),
              xpPoints: xp,
              levelName: _levelName(xp),
              levelProgress: _levelProgress(xp),
              serverMinuteOfDay: summary.serverMinuteOfDay,
              serverSyncedAt: summary.serverSyncedAt,
              serverTimezone: summary.serverTimezone,
            ),
          ),
        ),
        const SizedBox(height: 14),
        _HorizontalPad(
          child: StudentFadeSlideIn(
            delayMs: 70,
            child: StudentAutoCarouselBanner(
              items: _carouselItems(),
              onTap: onRouteTap,
            ),
          ),
        ),
        const SizedBox(height: 16),
        _HorizontalPad(
          child: StudentFadeSlideIn(
            delayMs: 110,
            child: StudentHeroBanner(
              cards: heroCards,
              onCardTap: onRouteTap,
            ),
          ),
        ),
        const SizedBox(height: 16),
        const _HorizontalPad(
          child: StudentFadeSlideIn(
            delayMs: 170,
            child: StudentSectionHeader(
              title: "Today's Schedule",
              titleColor: Color(0xFFF2F6FF),
            ),
          ),
        ),
        const SizedBox(height: 8),
        _HorizontalPad(
          child: StudentFadeSlideIn(
            delayMs: 200,
            child: StudentTodaySchedulePanel(
              items: summary.todaySchedule,
              onTap: onRouteTap,
            ),
          ),
        ),
        const SizedBox(height: 16),
        _HorizontalPad(
          child: StudentFadeSlideIn(
            delayMs: 230,
            child: StudentSectionHeader(
              title: "Announcement",
              actionLabel: "View Details",
              onActionTap: () => onRouteTap("/student/notifications"),
              titleColor: const Color(0xFFF2F6FF),
              actionColor: const Color(0xFFD4E3FF),
            ),
          ),
        ),
        const SizedBox(height: 8),
        _HorizontalPad(
          child: StudentFadeSlideIn(
            delayMs: 260,
            child: _AnnouncementList(
              items: summary.announcements,
              onTap: (id) => onRouteTap("/student/announcements/$id"),
            ),
          ),
        ),
        const SizedBox(height: 16),
        const _HorizontalPad(
          child: StudentFadeSlideIn(
            delayMs: 290,
            child: StudentSectionHeader(
              title: "Quick Access",
              titleColor: Color(0xFFF2F6FF),
            ),
          ),
        ),
        const SizedBox(height: 8),
        _HorizontalPad(
          child: StudentFadeSlideIn(
            delayMs: 320,
            child: StudentQuickActionGrid(
              items: quickActions,
              onTap: onRouteTap,
            ),
          ),
        ),
        const SizedBox(height: 16),
        _HorizontalPad(
          child: StudentFadeSlideIn(
            delayMs: 350,
            child: StudentDoubtCtaCard(
              data: summary.doubtCta,
              onTap: () => onRouteTap(summary.doubtCta.route),
            ),
          ),
        ),
        const SizedBox(height: 16),
        const _HorizontalPad(
          child: StudentFadeSlideIn(
            delayMs: 380,
            child: StudentSectionHeader(
              title: "Attendance & Holiday",
              titleColor: Color(0xFFF2F6FF),
            ),
          ),
        ),
        const SizedBox(height: 8),
        _HorizontalPad(
          child: StudentFadeSlideIn(
            delayMs: 410,
            child: StudentAttendanceHolidayRow(
              attendance: summary.attendance,
              holiday: summary.holiday,
              onAttendanceTap: () => onRouteTap("/student/attendance"),
              onHolidayTap: () => onRouteTap("/student/holidays"),
            ),
          ),
        ),
      ],
    );
  }
}

class _HorizontalPad extends StatelessWidget {
  const _HorizontalPad({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: child,
    );
  }
}

class _BrandHeader extends StatelessWidget {
  const _BrandHeader({
    required this.unreadCount,
    required this.onNotificationTap,
  });

  final int unreadCount;
  final VoidCallback onNotificationTap;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 10, 16, 10),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(20),
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            Colors.white.withValues(alpha: 0.90),
            Colors.white.withValues(alpha: 0.82),
            Colors.white.withValues(alpha: 0.88),
          ],
        ),
        border: Border.all(
          color: Colors.white.withValues(alpha: 0.94),
          width: 1,
        ),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF0A1F6A).withValues(alpha: 0.08),
            blurRadius: 16,
            spreadRadius: -8,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Row(
        children: [
          Container(
            width: 52,
            height: 52,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              border: Border.all(
                color: const Color(0xFFD3E1FF),
                width: 1.1,
              ),
              color: Colors.white.withValues(alpha: 0.94),
            ),
            alignment: Alignment.center,
            child: ClipOval(
              child: Image.asset(
                "assets/branding/adrika_logo.png",
                fit: BoxFit.cover,
                width: 46,
                height: 46,
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  "Adrika Coaching Classes",
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        color: const Color(0xFFD3202A),
                        fontWeight: FontWeight.w800,
                        letterSpacing: 0.0,
                        fontSize: 19.0,
                        height: 1.0,
                      ),
                ),
                const SizedBox(height: 1),
                Text(
                  "Your Success, Our Goal",
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(
                        color: const Color(0xFF233C93),
                        fontWeight: FontWeight.w700,
                        fontSize: 10.8,
                        height: 1.0,
                      ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 10),
          StudentNotificationBell(
            unreadCount: unreadCount,
            onTap: onNotificationTap,
            iconSize: 24,
            iconPadding: 11,
          ),
        ],
      ),
    );
  }
}

class _AdmissionOpenTicker extends StatelessWidget {
  const _AdmissionOpenTicker();

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          "Admission Open",
          style: Theme.of(context).textTheme.titleSmall?.copyWith(
                color: const Color(0xFFFFF7D6),
                fontWeight: FontWeight.w800,
                letterSpacing: 0.0,
              ),
        ),
        const SizedBox(height: 6),
        const _AdmissionTickerStrip(),
      ],
    );
  }
}

class _AdmissionTickerStrip extends StatefulWidget {
  const _AdmissionTickerStrip();

  @override
  State<_AdmissionTickerStrip> createState() => _AdmissionTickerStripState();
}

class _AdmissionTickerStripState extends State<_AdmissionTickerStrip>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  static const String _tickerText =
      "10th SSC/CBSC • 11th (Science/Commerce) • 12th (Science/Commerce) • ";

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 18),
    )..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  double _measureTextWidth(TextStyle style) {
    final painter = TextPainter(
      text: TextSpan(text: _tickerText, style: style),
      maxLines: 1,
      textDirection: TextDirection.ltr,
    )..layout();
    return painter.width;
  }

  @override
  Widget build(BuildContext context) {
    final textStyle = Theme.of(context).textTheme.bodyMedium?.copyWith(
              color: const Color(0xFFC41818),
              fontWeight: FontWeight.w800,
              letterSpacing: 0.0,
            ) ??
        const TextStyle(
          color: Color(0xFFC41818),
          fontWeight: FontWeight.w800,
          fontSize: 13.2,
        );

    return Container(
      height: 36,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(12),
        gradient: const LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            Color(0xFFFFF078),
            Color(0xFFFFDF3D),
          ],
        ),
        border: Border.all(
          color: const Color(0xFFFFF8B3),
          width: 1.0,
        ),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFFFFDE59).withValues(alpha: 0.35),
            blurRadius: 12,
            spreadRadius: -6,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(12),
        child: LayoutBuilder(
          builder: (context, constraints) {
            final segmentWidth = _measureTextWidth(textStyle);

            return AnimatedBuilder(
              animation: _controller,
              builder: (context, child) {
                final shift = _controller.value * segmentWidth;

                return ClipRect(
                  child: SizedBox(
                    width: constraints.maxWidth,
                    child: Transform.translate(
                      offset: Offset(-shift, 0),
                      child: Align(
                        alignment: Alignment.centerLeft,
                        child: OverflowBox(
                          alignment: Alignment.centerLeft,
                          minWidth: 0,
                          maxWidth: double.infinity,
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Text(
                                _tickerText,
                                style: textStyle,
                                maxLines: 1,
                                softWrap: false,
                              ),
                              Text(
                                _tickerText,
                                style: textStyle,
                                maxLines: 1,
                                softWrap: false,
                              ),
                              Text(
                                _tickerText,
                                style: textStyle,
                                maxLines: 1,
                                softWrap: false,
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                  ),
                );
              },
            );
          },
        ),
      ),
    );
  }
}

class _AnnouncementList extends StatelessWidget {
  const _AnnouncementList({
    required this.items,
    required this.onTap,
  });

  final List<StudentAnnouncementItem> items;
  final ValueChanged<String> onTap;

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) {
      return Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: const Color(0xFFD6DCEA)),
          color: const Color(0xFFA9B2C4),
        ),
        child: Text(
          "No announcements yet. Important updates will appear here.",
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: const Color(0xFF1E293B),
                fontWeight: FontWeight.w500,
              ),
        ),
      );
    }

    final sortedItems = [...items]..sort((a, b) {
        final aTime = a.timestamp;
        final bTime = b.timestamp;
        if (aTime == null && bTime == null) {
          return 0;
        }
        if (aTime == null) {
          return 1;
        }
        if (bTime == null) {
          return -1;
        }
        return bTime.compareTo(aTime);
      });

    final latest = sortedItems.first;

    return StudentAnnouncementCard(
      item: latest,
      onTap: () => onTap(latest.id),
    );
  }
}
