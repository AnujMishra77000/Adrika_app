import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../state/student_providers.dart";
import "student_dashboard_screen.dart";
import "student_homework_screen.dart";
import "student_notices_screen.dart";
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
    "Student Home",
    "Notice Center",
    "Homework Studio",
    "My Profile",
  ];

  static const _screens = <Widget>[
    StudentDashboardScreen(),
    StudentNoticesScreen(),
    StudentHomeworkScreen(),
    StudentProfileScreen(),
  ];

  static const _items = <_NavItem>[
    _NavItem(
      label: "Home",
      icon: Icons.home_outlined,
      selectedIcon: Icons.home_rounded,
      accent: Colors.white,
    ),
    _NavItem(
      label: "Notices",
      icon: Icons.campaign_outlined,
      selectedIcon: Icons.campaign_rounded,
      accent: Colors.white,
    ),
    _NavItem(
      label: "Homework",
      icon: Icons.assignment_outlined,
      selectedIcon: Icons.assignment_rounded,
      accent: Colors.white,
    ),
    _NavItem(
      label: "Profile",
      icon: Icons.person_outline_rounded,
      selectedIcon: Icons.person_rounded,
      accent: Colors.white,
    ),
  ];

  @override
  Widget build(BuildContext context) {
    final showAppBar = _currentIndex != 0;
    final homeworkBadge = ref.watch(studentDashboardProvider).maybeWhen(
          data: (dashboard) => dashboard.pendingHomeworkCount,
          orElse: () => 0,
        );

    return Scaffold(
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
          ? Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: FloatingActionButton(
                onPressed: () => context.push("/student/chat"),
                elevation: 6,
                backgroundColor: const Color(0xFF0E2E79),
                foregroundColor: Colors.white,
                child: const Icon(Icons.chat_rounded),
              ),
            )
          : null,
      floatingActionButtonLocation: FloatingActionButtonLocation.endFloat,
      bottomNavigationBar: DecoratedBox(
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
            top: BorderSide(color: Colors.white.withValues(alpha: 0.20)),
          ),
          boxShadow: [
            BoxShadow(
              color: const Color(0xFF090D1F).withValues(alpha: 0.40),
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
              height: 70,
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
                  final badgeCount = index == 2 ? homeworkBadge : 0;
                  return NavigationDestination(
                    icon: _NavIcon(
                      icon: item.icon,
                      accent: item.accent,
                      selected: false,
                      badgeCount: badgeCount,
                    ),
                    selectedIcon: _NavIcon(
                      icon: item.selectedIcon,
                      accent: item.accent,
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
    );
  }
}

class _NavIcon extends StatelessWidget {
  const _NavIcon({
    required this.icon,
    required this.accent,
    required this.selected,
    this.badgeCount = 0,
  });

  final IconData icon;
  final Color accent;
  final bool selected;
  final int badgeCount;

  @override
  Widget build(BuildContext context) {
    final color = selected ? accent : Colors.white.withValues(alpha: 0.72);

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
                ? Colors.white.withValues(alpha: 0.18)
                : Colors.transparent,
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

class _NavItem {
  const _NavItem({
    required this.label,
    required this.icon,
    required this.selectedIcon,
    required this.accent,
  });

  final String label;
  final IconData icon;
  final IconData selectedIcon;
  final Color accent;
}
