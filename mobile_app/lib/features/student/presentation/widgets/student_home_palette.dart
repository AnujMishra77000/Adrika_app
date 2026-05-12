import 'package:flutter/material.dart';

abstract final class StudentHomePalette {
  static const pageBackground = Color(0xFFF2F4FC);
  static const pageBackgroundSecondary = Color(0xFFF7F9FF);

  static const bannerTop = Color(0xFF241249);
  static const bannerBottom = Color(0xFF15172F);
  static const bannerGlow = Color(0xFF7D4BFF);

  static const accentPink = Color(0xFFFFAACF);
  static const accentGreen = Color(0xFF8AE5C8);
  static const accentBlue = Color(0xFF7FC9FF);
  static const accentPurple = Color(0xFFB39BFF);

  static const oceanBlue = Color(0xFF1E4B98);
  static const mintGreen = Color(0xFF4ABF9A);
  static const softPink = Color(0xFFE96BB1);

  static const surface = Colors.white;
  static const surfaceMuted = Color(0xFFF4F7FE);
  static const line = Color(0xFFD8E1EF);

  static const textPrimary = Color(0xFF0F172A);
  static const textSecondary = Color(0xFF475569);
  static const textMuted = Color(0xFF64748B);

  static const textPrimaryOnDark = Color(0xFFF9F5FF);
  static const textSecondaryOnDark = Color(0xFFC8C6DE);

  static const success = Color(0xFF129B6D);
  static const warning = Color(0xFFCD7B10);
  static const danger = Color(0xFFC3294A);
}

abstract final class StudentUiRadius {
  static const double card = 16;
  static const double cardLarge = 20;
  static const double chip = 999;
}

abstract final class StudentUiSpacing {
  static const EdgeInsets page = EdgeInsets.fromLTRB(14, 12, 14, 16);
  static const EdgeInsets card = EdgeInsets.all(12);
  static const double sectionGap = 12;
  static const double cardGap = 8;
}

abstract final class StudentUiShadow {
  static const List<BoxShadow> card = [
    BoxShadow(
      color: Color(0x120F172A),
      blurRadius: 18,
      offset: Offset(0, 8),
      spreadRadius: -10,
    ),
    BoxShadow(
      color: Color(0x080F172A),
      blurRadius: 6,
      offset: Offset(0, 2),
      spreadRadius: -4,
    ),
  ];
}
