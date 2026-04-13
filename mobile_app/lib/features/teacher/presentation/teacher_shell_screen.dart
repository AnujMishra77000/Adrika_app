import 'package:flutter/material.dart';

import 'teacher_assignments_screen.dart';
import 'teacher_dashboard_screen.dart';
import 'teacher_doubts_screen.dart';
import 'teacher_notices_screen.dart';
import 'teacher_profile_screen.dart';
import 'widgets/teacher_ui.dart';

class TeacherShellScreen extends StatefulWidget {
  const TeacherShellScreen({super.key});

  @override
  State<TeacherShellScreen> createState() => _TeacherShellScreenState();
}

class _TeacherShellScreenState extends State<TeacherShellScreen> {
  int _currentIndex = 0;

  static const _titles = <String>[
    'Teacher Home',
    'Assignments',
    'Doubts',
    'Notices',
    'Profile',
  ];

  static const _screens = <Widget>[
    TeacherDashboardScreen(),
    TeacherAssignmentsScreen(),
    TeacherDoubtsScreen(),
    TeacherNoticesScreen(),
    TeacherProfileScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: TeacherPalette.deepOcean,
      appBar: AppBar(
        elevation: 0,
        scrolledUnderElevation: 0,
        backgroundColor: Colors.transparent,
        flexibleSpace: const DecoratedBox(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                TeacherPalette.deepOcean,
                TeacherPalette.oceanBlue,
                TeacherPalette.violet,
              ],
            ),
          ),
        ),
        title: Text(
          _titles[_currentIndex],
          style: const TextStyle(
            color: TeacherPalette.white,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
      body: IndexedStack(
        index: _currentIndex,
        children: _screens,
      ),
      bottomNavigationBar: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.centerLeft,
            end: Alignment.centerRight,
            colors: [
              TeacherPalette.deepOcean,
              TeacherPalette.oceanBlue,
              TeacherPalette.violet,
            ],
          ),
        ),
        child: SafeArea(
          top: false,
          child: NavigationBarTheme(
            data: NavigationBarThemeData(
              backgroundColor: Colors.transparent,
              indicatorColor: TeacherPalette.white.withValues(alpha: 0.22),
              labelTextStyle: WidgetStateProperty.resolveWith((states) {
                final selected = states.contains(WidgetState.selected);
                return TextStyle(
                  color: TeacherPalette.white.withValues(
                    alpha: selected ? 1 : 0.82,
                  ),
                  fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
                );
              }),
              iconTheme: WidgetStateProperty.resolveWith((states) {
                final selected = states.contains(WidgetState.selected);
                return IconThemeData(
                  color: TeacherPalette.white.withValues(
                    alpha: selected ? 1 : 0.82,
                  ),
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
              destinations: const [
                NavigationDestination(
                  icon: Icon(Icons.dashboard_outlined),
                  selectedIcon: Icon(Icons.dashboard),
                  label: 'Home',
                ),
                NavigationDestination(
                  icon: Icon(Icons.assignment_outlined),
                  selectedIcon: Icon(Icons.assignment),
                  label: 'Assignments',
                ),
                NavigationDestination(
                  icon: Icon(Icons.question_answer_outlined),
                  selectedIcon: Icon(Icons.question_answer),
                  label: 'Doubts',
                ),
                NavigationDestination(
                  icon: Icon(Icons.campaign_outlined),
                  selectedIcon: Icon(Icons.campaign),
                  label: 'Notices',
                ),
                NavigationDestination(
                  icon: Icon(Icons.person_outline),
                  selectedIcon: Icon(Icons.person),
                  label: 'Profile',
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
