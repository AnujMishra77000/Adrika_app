import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import 'package:adr_mobile_app/features/auth/presentation/login_screen.dart';

void main() {
  testWidgets('tapping Student Registration opens registration form', (tester) async {
    final router = GoRouter(
      initialLocation: '/login',
      routes: [
        GoRoute(
          path: '/login',
          builder: (context, state) => const LoginScreen(mode: AuthEntryMode.menu),
        ),
        GoRoute(
          path: '/register/student',
          builder: (context, state) => const LoginScreen(mode: AuthEntryMode.studentRegister),
        ),
      ],
    );

    await tester.pumpWidget(
      ProviderScope(
        child: MaterialApp.router(routerConfig: router),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('Student Registration'), findsOneWidget);

    await tester.tap(find.text('Student Registration').first);
    await tester.pumpAndSettle();

    expect(find.text('Register Student'), findsOneWidget);
    expect(find.text('Student Name'), findsOneWidget);
  });
}
