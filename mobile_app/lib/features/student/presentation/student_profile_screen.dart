import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../auth/state/auth_controller.dart";
import "../../../core/config/app_env.dart";
import "../models/student_models.dart";
import "../state/student_providers.dart";
import "widgets/student_home_palette.dart";
import "widgets/student_home_states.dart";
import "widgets/student_page_background.dart";
import "widgets/student_section_header.dart";
import "widgets/student_status_chip.dart";
import "widgets/student_surface_card.dart";

class StudentProfileScreen extends ConsumerWidget {
  const StudentProfileScreen({super.key});

  Future<void> _refresh(WidgetRef ref) async {
    ref.invalidate(studentProfileProvider);
    await ref.read(studentProfileProvider.future);
  }

  Future<void> _logout(BuildContext context, WidgetRef ref) async {
    await ref.read(authControllerProvider.notifier).logout();
    if (context.mounted) {
      context.go("/login");
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final profileAsync = ref.watch(studentProfileProvider);

    return Stack(
      children: [
        const StudentPageBackgroundLayer(),
        profileAsync.when(
          loading: () => const StudentFeedLoadingList(itemCount: 4),
          error: (error, _) => ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: StudentUiSpacing.page,
            children: [
              StudentHomeErrorList(
                message: error.toString(),
                onRetry: () => ref.invalidate(studentProfileProvider),
              ),
            ],
          ),
          data: (profile) => RefreshIndicator(
            onRefresh: () => _refresh(ref),
            child: ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: StudentUiSpacing.page,
              children: [
                _ProfileHero(profile: profile),
                const SizedBox(height: StudentUiSpacing.sectionGap),
                const StudentSectionHeader(
                  title: "Academic Identity",
                  subtitle: "Core account identifiers used by the institute.",
                  titleColor: Color(0xFFECE8FF),
                  subtitleColor: Color(0xFFB6B1D6),
                ),
                const SizedBox(height: 10),
                StudentSurfaceCard(
                  child: Column(
                    children: [
                      _ProfileInfoLine(
                        label: "Admission Number",
                        value: profile.admissionNo,
                        icon: Icons.badge_outlined,
                      ),
                      const Divider(height: 22),
                      _ProfileInfoLine(
                        label: "Roll Number",
                        value: profile.rollNo,
                        icon: Icons.pin_outlined,
                      ),
                      const Divider(height: 22),
                      const _ProfileInfoLine(
                        label: "Class / Batch",
                        value: "Will sync from timetable service",
                        icon: Icons.groups_2_outlined,
                        muted: true,
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: StudentUiSpacing.sectionGap),
                const StudentSectionHeader(
                  title: "Guardian & Contact",
                  subtitle:
                      "Communication details visible for support operations.",
                  titleColor: Color(0xFFECE8FF),
                  subtitleColor: Color(0xFFB6B1D6),
                ),
                const SizedBox(height: 10),
                StudentSurfaceCard(
                  backgroundColor: StudentHomePalette.surfaceMuted,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: const [
                      _ProfileInfoLine(
                        label: "Primary Contact",
                        value: "Data will appear after onboarding sync",
                        icon: Icons.phone_in_talk_outlined,
                        muted: true,
                      ),
                      Divider(height: 22),
                      _ProfileInfoLine(
                        label: "Address",
                        value:
                            "Address is not available in this account payload",
                        icon: Icons.location_on_outlined,
                        muted: true,
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: StudentUiSpacing.sectionGap),
                StudentSurfaceCard(
                  backgroundColor: const Color(0xFFFFF7F8),
                  borderColor: const Color(0xFFFFDDE2),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: const [
                          StudentIconBadge(
                            icon: Icons.security_rounded,
                            accent: StudentHomePalette.softPink,
                            size: 36,
                          ),
                          SizedBox(width: 10),
                          Text(
                            "Session & Security",
                            style: TextStyle(
                              color: StudentHomePalette.textPrimary,
                              fontWeight: FontWeight.w700,
                              fontSize: 15,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 10),
                      Text(
                        "Logout clears this device session. Use this when switching devices or accounts.",
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                              color: StudentHomePalette.textSecondary,
                            ),
                      ),
                      const SizedBox(height: 14),
                      OutlinedButton.icon(
                        onPressed: () => _logout(context, ref),
                        icon: const Icon(Icons.logout_rounded),
                        label: const Text("Logout"),
                        style: OutlinedButton.styleFrom(
                          foregroundColor: StudentHomePalette.danger,
                          side: const BorderSide(color: Color(0xFFF4A6B5)),
                          padding: const EdgeInsets.symmetric(
                            horizontal: 14,
                            vertical: 12,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

class _ProfileHero extends StatelessWidget {
  const _ProfileHero({required this.profile});

  final StudentProfile profile;

  String get _initials {
    final parts = profile.fullName.trim().split(RegExp(r"\s+"));
    if (parts.isEmpty || parts.first.isEmpty) {
      return "S";
    }
    if (parts.length == 1) {
      return parts.first.substring(0, 1).toUpperCase();
    }
    return "${parts.first.substring(0, 1)}${parts.last.substring(0, 1)}"
        .toUpperCase();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(StudentUiRadius.cardLarge),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            StudentHomePalette.bannerTop,
            StudentHomePalette.bannerBottom,
          ],
        ),
        boxShadow: [
          BoxShadow(
            color: StudentHomePalette.bannerGlow.withValues(alpha: 0.22),
            blurRadius: 22,
            spreadRadius: -4,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Row(
        children: [
          _ProfileAvatar(photoUrl: profile.photoUrl, initials: _initials),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  profile.fullName,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        color: StudentHomePalette.textPrimaryOnDark,
                        fontWeight: FontWeight.w700,
                      ),
                ),
                const SizedBox(height: 4),
                Text(
                  "Student Account",
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: StudentHomePalette.textSecondaryOnDark,
                      ),
                ),
                const SizedBox(height: 8),
                const StudentStatusChip(
                  label: "Active Session",
                  tone: StudentChipTone.success,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ProfileAvatar extends StatelessWidget {
  const _ProfileAvatar({required this.photoUrl, required this.initials});

  final String? photoUrl;
  final String initials;

  @override
  Widget build(BuildContext context) {
    final resolvedPhoto = AppEnv.resolveServerUrl(photoUrl);

    return Container(
      width: 58,
      height: 58,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: Colors.white.withValues(alpha: 0.18),
        border: Border.all(color: Colors.white.withValues(alpha: 0.22)),
      ),
      alignment: Alignment.center,
      child: ClipOval(
        child: SizedBox(
          width: 54,
          height: 54,
          child: resolvedPhoto != null
              ? Image.network(
                  resolvedPhoto,
                  fit: BoxFit.cover,
                  errorBuilder: (_, __, ___) =>
                      _InitialsText(initials: initials),
                )
              : _InitialsText(initials: initials),
        ),
      ),
    );
  }
}

class _InitialsText extends StatelessWidget {
  const _InitialsText({required this.initials});

  final String initials;

  @override
  Widget build(BuildContext context) {
    return ColoredBox(
      color: Colors.transparent,
      child: Center(
        child: Text(
          initials,
          style: Theme.of(context).textTheme.titleLarge?.copyWith(
                color: Colors.white,
                fontWeight: FontWeight.w800,
              ),
        ),
      ),
    );
  }
}

class _ProfileInfoLine extends StatelessWidget {
  const _ProfileInfoLine({
    required this.label,
    required this.value,
    required this.icon,
    this.muted = false,
  });

  final String label;
  final String value;
  final IconData icon;
  final bool muted;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        StudentIconBadge(
          icon: icon,
          accent: muted
              ? StudentHomePalette.textMuted
              : StudentHomePalette.oceanBlue,
          size: 34,
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: Theme.of(context).textTheme.labelMedium?.copyWith(
                      color: StudentHomePalette.textMuted,
                      fontWeight: FontWeight.w600,
                    ),
              ),
              const SizedBox(height: 3),
              Text(
                value,
                style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                      color: muted
                          ? StudentHomePalette.textSecondary
                          : StudentHomePalette.textPrimary,
                      fontWeight: muted ? FontWeight.w500 : FontWeight.w600,
                    ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
