import 'package:adr_mobile_app/app/app.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('App bootstraps', (WidgetTester tester) async {
    await tester.pumpWidget(const ProviderScope(child: AdrApp()));
    expect(find.byType(CircularProgressIndicator), findsWidgets);
  });
}
