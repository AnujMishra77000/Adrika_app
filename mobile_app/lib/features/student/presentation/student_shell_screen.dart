import 'package:flutter/material.dart';

import 'student_dashboard_screen.dart';
import 'student_homework_screen.dart';
import 'student_notices_screen.dart';
import 'student_profile_screen.dart';

class StudentShellScreen extends StatefulWidget {
  const StudentShellScreen({super.key});

  @override
  State<StudentShellScreen> createState() => _StudentShellScreenState();
}

class _StudentShellScreenState extends State<StudentShellScreen> {
  int _currentIndex = 0;

  static const _titles = <String>[
    'Student Home',
    'Notices',
    'Homework',
    'Profile',
  ];

  static const _screens = <Widget>[
    StudentDashboardScreen(),
    StudentNoticesScreen(),
    StudentHomeworkScreen(),
    StudentProfileScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    final appBar = _currentIndex == 0
        ? null
        : AppBar(
            title: Text(_titles[_currentIndex]),
          );

    return Scaffold(
      appBar: appBar,
      body: IndexedStack(
        index: _currentIndex,
        children: _screens,
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _currentIndex,
        onDestinationSelected: (index) {
          setState(() {
            _currentIndex = index;
          });
        },
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.home_outlined),
            selectedIcon: Icon(Icons.home_rounded),
            label: 'Home',
          ),
          NavigationDestination(
            icon: Icon(Icons.campaign_outlined),
            selectedIcon: Icon(Icons.campaign),
            label: 'Notices',
          ),
          NavigationDestination(
            icon: Icon(Icons.menu_book_outlined),
            selectedIcon: Icon(Icons.menu_book),
            label: 'Homework',
          ),
          NavigationDestination(
            icon: Icon(Icons.person_outline),
            selectedIcon: Icon(Icons.person),
            label: 'Profile',
          ),
        ],
      ),
    );
  }
}
