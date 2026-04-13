import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../models/student_models.dart";
import "../state/student_providers.dart";
import "widgets/student_fade_slide_in.dart";
import "widgets/student_home_palette.dart";
import "widgets/student_home_states.dart";
import "widgets/student_module_header.dart";
import "widgets/student_notice_feed_card.dart";
import "widgets/student_page_background.dart";
import "widgets/student_section_header.dart";

class StudentNoticesScreen extends ConsumerWidget {
  const StudentNoticesScreen({super.key});

  Future<void> _refresh(WidgetRef ref) async {
    ref.invalidate(studentNoticesProvider);
    await ref.read(studentNoticesProvider.future);
  }

  List<Widget> _buildSections(
    BuildContext context,
    List<StudentNotice> items,
  ) {
    final unread = items.where((item) => !item.isRead).toList(growable: false);
    final read = items.where((item) => item.isRead).toList(growable: false);

    final pinned = unread.take(1).toList(growable: false);
    final unreadStream = unread.skip(pinned.length).toList(growable: false);

    final content = <Widget>[];
    var sequence = 0;

    void addGroup({
      required String title,
      required String subtitle,
      required List<StudentNotice> records,
      bool isPinned = false,
    }) {
      if (records.isEmpty) {
        return;
      }

      if (content.isNotEmpty) {
        content.add(const SizedBox(height: StudentUiSpacing.sectionGap));
      }

      content.add(
        StudentSectionHeader(
          title: title,
          subtitle: subtitle,
          titleColor: const Color(0xFFECE8FF),
          subtitleColor: const Color(0xFFB6B1D6),
        ),
      );
      content.add(const SizedBox(height: 10));

      for (final notice in records) {
        final delay = 80 + (sequence * 40);
        sequence += 1;
        content.add(
          StudentFadeSlideIn(
            delayMs: delay,
            child: Padding(
              padding: const EdgeInsets.only(bottom: StudentUiSpacing.cardGap),
              child: StudentNoticeFeedCard(
                notice: notice,
                pinned: isPinned,
                onTap: () =>
                    context.push("/student/announcements/${notice.id}"),
              ),
            ),
          ),
        );
      }
    }

    addGroup(
      title: "Pinned Notice",
      subtitle: "Priority communication requiring immediate attention.",
      records: pinned,
      isPinned: true,
    );

    addGroup(
      title: "Unread",
      subtitle: "Latest institute updates not reviewed yet.",
      records: unreadStream,
    );

    addGroup(
      title: "Earlier Notices",
      subtitle: "Recently reviewed communication history.",
      records: read,
    );

    return content;
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final noticesAsync = ref.watch(studentNoticesProvider);

    return Stack(
      children: [
        const StudentPageBackgroundLayer(),
        noticesAsync.when(
          loading: () => const StudentFeedLoadingList(itemCount: 5),
          error: (error, _) => ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: StudentUiSpacing.page,
            children: [
              StudentHomeErrorList(
                message: error.toString(),
                onRetry: () => ref.invalidate(studentNoticesProvider),
              ),
            ],
          ),
          data: (items) => RefreshIndicator(
            onRefresh: () => _refresh(ref),
            child: ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: StudentUiSpacing.page,
              children: [
                const StudentModuleHeader(
                  title: "Notice Center",
                  subtitle:
                      "Announcements, policy updates, and class-wide alerts from the institute.",
                  icon: Icons.campaign_rounded,
                  accent: StudentHomePalette.softPink,
                ),
                const SizedBox(height: StudentUiSpacing.sectionGap),
                if (items.isEmpty)
                  const StudentHomeEmptyState(
                    title: "No notices published",
                    subtitle:
                        "Once faculty or admin shares new updates, you will see them here.",
                  )
                else
                  ..._buildSections(context, items),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
