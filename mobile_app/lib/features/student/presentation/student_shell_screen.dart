import "package:flutter/material.dart";
import "package:flutter/services.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../state/student_providers.dart";
import "student_assessment_screens.dart";
import "student_dashboard_screen.dart";
import "student_feature_screens.dart";
import "student_profile_screen.dart";
import "widgets/student_page_background.dart";

class StudentShellScreen extends ConsumerStatefulWidget {
  const StudentShellScreen({super.key});

  @override
  ConsumerState<StudentShellScreen> createState() => _StudentShellScreenState();
}

class _StudentShellScreenState extends ConsumerState<StudentShellScreen> {
  int _currentIndex = 0;

  static const _titles = <String>[
    "Home",
    "Today Lectures",
    "Online Tests",
    "My Profile",
  ];

  static const _screens = <Widget>[
    StudentDashboardScreen(),
    StudentTodayLecturesScreen(),
    StudentAssessmentListScreen(type: StudentAssessmentViewType.online),
    StudentProfileScreen(),
  ];

  static const _items = <_NavItem>[
    _NavItem(
      label: "Home",
      icon: Icons.home_outlined,
      selectedIcon: Icons.home_rounded,
    ),
    _NavItem(
      label: "Lectures",
      icon: Icons.ondemand_video_outlined,
      selectedIcon: Icons.ondemand_video_rounded,
    ),
    _NavItem(
      label: "Tests",
      icon: Icons.fact_check_outlined,
      selectedIcon: Icons.fact_check_rounded,
    ),
    _NavItem(
      label: "Profile",
      icon: Icons.person_outline_rounded,
      selectedIcon: Icons.person_rounded,
    ),
  ];

  @override
  Widget build(BuildContext context) {
    final showAppBar = _currentIndex != 0;
    final testBadge = ref.watch(studentDashboardProvider).maybeWhen(
          data: (dashboard) => dashboard.upcomingTestsCount,
          orElse: () => 0,
        );

    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: const SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.light,
        statusBarBrightness: Brightness.dark,
        systemNavigationBarColor: Color(0xFF162C5C),
        systemNavigationBarIconBrightness: Brightness.light,
        systemNavigationBarDividerColor: Color(0xFF162C5C),
      ),
      child: Scaffold(
        backgroundColor: const Color(0xFF130C2C),
        appBar: showAppBar
            ? AppBar(
                elevation: 0,
                scrolledUnderElevation: 0,
                titleSpacing: 18,
                backgroundColor: Colors.transparent,
                flexibleSpace: const DecoratedBox(
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [
                        Color(0xFF27154A),
                        Color(0xFF162C5C),
                      ],
                    ),
                  ),
                ),
                title: Text(
                  _titles[_currentIndex],
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        color: Colors.white,
                        fontWeight: FontWeight.w800,
                      ),
                ),
              )
            : null,
        body: Stack(
          children: [
            const StudentPageBackgroundLayer(),
            IndexedStack(
              index: _currentIndex,
              children: _screens,
            ),
          ],
        ),
        floatingActionButton: _currentIndex == 0
            ? _PulsingChatFab(
                onPressed: () => context.push("/student/chat"),
              )
            : null,
        floatingActionButtonLocation: FloatingActionButtonLocation.endFloat,
        bottomNavigationBar: ColoredBox(
          color: const Color(0xFF162C5C),
          child: DecoratedBox(
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [
                  Color(0xFF27154A),
                  Color(0xFF162C5C),
                ],
              ),
              border: Border(
                top: BorderSide(color: Colors.white.withValues(alpha: 0.18)),
              ),
              boxShadow: [
                BoxShadow(
                  color: const Color(0xFF090D1F).withValues(alpha: 0.38),
                  blurRadius: 20,
                  spreadRadius: -8,
                  offset: const Offset(0, -2),
                ),
              ],
            ),
            child: SafeArea(
              top: false,
              left: false,
              right: false,
              child: NavigationBarTheme(
                data: NavigationBarThemeData(
                  height: 72,
                  backgroundColor: Colors.transparent,
                  indicatorColor: Colors.transparent,
                  labelBehavior:
                      NavigationDestinationLabelBehavior.onlyShowSelected,
                  labelTextStyle: WidgetStateProperty.resolveWith((states) {
                    final selected = states.contains(WidgetState.selected);
                    return TextStyle(
                      color: selected
                          ? Colors.white
                          : Colors.white.withValues(alpha: 0.72),
                      fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
                      fontSize: 12,
                    );
                  }),
                ),
                child: NavigationBar(
                  selectedIndex: _currentIndex,
                  onDestinationSelected: (index) {
                    setState(() {
                      _currentIndex = index;
                    });
                  },
                  destinations: List<NavigationDestination>.generate(
                    _items.length,
                    (index) {
                      final item = _items[index];
                      final badgeCount = index == 2 ? testBadge : 0;
                      return NavigationDestination(
                        icon: _NavIcon(
                          icon: item.icon,
                          selected: false,
                          badgeCount: badgeCount,
                        ),
                        selectedIcon: _NavIcon(
                          icon: item.selectedIcon,
                          selected: true,
                          badgeCount: badgeCount,
                        ),
                        label: item.label,
                      );
                    },
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _NavIcon extends StatelessWidget {
  const _NavIcon({
    required this.icon,
    required this.selected,
    this.badgeCount = 0,
  });

  final IconData icon;
  final bool selected;
  final int badgeCount;

  @override
  Widget build(BuildContext context) {
    final color =
        selected ? Colors.white : Colors.white.withValues(alpha: 0.72);

    return Stack(
      clipBehavior: Clip.none,
      children: [
        AnimatedContainer(
          duration: const Duration(milliseconds: 180),
          curve: Curves.easeOutCubic,
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(12),
            color: selected
                ? Colors.white.withValues(alpha: 0.20)
                : Colors.transparent,
            boxShadow: selected
                ? [
                    BoxShadow(
                      color: const Color(0xFFAEC4FF).withValues(alpha: 0.36),
                      blurRadius: 14,
                      spreadRadius: -8,
                    ),
                  ]
                : null,
          ),
          child: Icon(
            icon,
            size: 22,
            color: color,
          ),
        ),
        if (badgeCount > 0)
          Positioned(
            right: -8,
            top: -2,
            child: Container(
              constraints: const BoxConstraints(minWidth: 18),
              padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
              decoration: BoxDecoration(
                color: const Color(0xFFE11D48),
                borderRadius: BorderRadius.circular(999),
              ),
              child: Text(
                badgeCount > 99 ? "99+" : "$badgeCount",
                textAlign: TextAlign.center,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 10,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ),
      ],
    );
  }
}

class _PulsingChatFab extends StatefulWidget {
  const _PulsingChatFab({required this.onPressed});

  final VoidCallback onPressed;

  @override
  State<_PulsingChatFab> createState() => _PulsingChatFabState();
}

class _PulsingChatFabState extends State<_PulsingChatFab>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1700),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: Tween<double>(begin: 0.88, end: 1).animate(
        CurvedAnimation(parent: _controller, curve: Curves.easeInOut),
      ),
      child: ScaleTransition(
        scale: Tween<double>(begin: 0.96, end: 1.03).animate(
          CurvedAnimation(parent: _controller, curve: Curves.easeInOut),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Container(
              margin: const EdgeInsets.only(bottom: 8),
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(999),
                boxShadow: [
                  BoxShadow(
                    color: const Color(0xFF0A1F6A).withValues(alpha: 0.18),
                    blurRadius: 12,
                    spreadRadius: -6,
                    offset: const Offset(0, 8),
                  ),
                ],
              ),
              child: const Text(
                "Need Help?",
                style: TextStyle(
                  color: Color(0xFF123B9E),
                  fontWeight: FontWeight.w700,
                  fontSize: 12,
                ),
              ),
            ),
            FloatingActionButton(
              onPressed: widget.onPressed,
              elevation: 6,
              backgroundColor: const Color(0xFF0E2E79),
              foregroundColor: Colors.white,
              child: const Icon(Icons.chat_rounded),
            ),
          ],
        ),
      ),
    );
  }
}

class _NavItem {
  const _NavItem({
    required this.label,
    required this.icon,
    required this.selectedIcon,
  });

  final String label;
  final IconData icon;
  final IconData selectedIcon;
}
