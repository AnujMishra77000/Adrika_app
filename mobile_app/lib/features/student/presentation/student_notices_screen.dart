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

class StudentNoticesScreen extends ConsumerWidget {
  const StudentNoticesScreen({
    super.key,
    this.showStandaloneHeader = false,
  });

  final bool showStandaloneHeader;

  Future<void> _refresh(WidgetRef ref) async {
    ref.invalidate(studentNoticesProvider);
    await ref.read(studentNoticesProvider.future);
  }

  List<StudentNotice> _sortedNotices(List<StudentNotice> items) {
    DateTime parsePublishAt(String? value) =>
        DateTime.tryParse(value ?? "") ??
        DateTime.fromMillisecondsSinceEpoch(0);

    final records = List<StudentNotice>.from(items);
    records.sort((a, b) {
      final byTime =
          parsePublishAt(b.publishAt).compareTo(parsePublishAt(a.publishAt));
      if (byTime != 0) {
        return byTime;
      }
      if (a.isRead == b.isRead) {
        return 0;
      }
      return a.isRead ? 1 : -1;
    });
    return records;
  }

  List<Widget> _buildNoticeFeed(
    BuildContext context,
    List<StudentNotice> items,
  ) {
    final feed = <Widget>[];
    for (var i = 0; i < items.length; i += 1) {
      final notice = items[i];
      feed.add(
        StudentFadeSlideIn(
          delayMs: 35 + (i * 26),
          child: Padding(
            padding: const EdgeInsets.only(bottom: StudentUiSpacing.cardGap),
            child: StudentNoticeFeedCard(
              notice: notice,
              pinned: i == 0 && !notice.isRead,
              onTap: () => context.push("/student/announcements/${notice.id}"),
            ),
          ),
        ),
      );
    }
    return feed;
  }

  AppBar _quickAccessAppBar() {
    return AppBar(
      elevation: 0,
      scrolledUnderElevation: 0,
      backgroundColor: Colors.transparent,
      foregroundColor: Colors.white,
      iconTheme: const IconThemeData(color: Colors.white),
      flexibleSpace: const DecoratedBox(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              StudentQuickAccessTheme.appBarStart,
              StudentQuickAccessTheme.appBarEnd,
            ],
          ),
        ),
      ),
      title: const Text(
        "Notice Center",
        style: TextStyle(
          color: Colors.white,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final noticesAsync = ref.watch(studentNoticesProvider);

    final content = Stack(
      children: [
        const StudentQuickAccessBackgroundLayer(),
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
          data: (items) {
            final sortedItems = _sortedNotices(items);
            return RefreshIndicator(
              onRefresh: () => _refresh(ref),
              child: ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: StudentUiSpacing.page,
                children: [
                  if (!showStandaloneHeader)
                    StudentFadeSlideIn(
                      delayMs: 20,
                      child: const StudentModuleHeader(
                        title: "Notice Center",
                        subtitle: "",
                        icon: Icons.notifications_active_rounded,
                        accent: StudentHomePalette.softPink,
                      ),
                    ),
                  if (!showStandaloneHeader)
                    const SizedBox(height: StudentUiSpacing.sectionGap),
                  if (sortedItems.isEmpty)
                    const StudentHomeEmptyState(
                      title: "No notices published",
                      subtitle:
                          "Once faculty or admin shares new updates, you will see them here.",
                    )
                  else
                    ..._buildNoticeFeed(context, sortedItems),
                ],
              ),
            );
          },
        ),
      ],
    );

    if (showStandaloneHeader) {
      return Scaffold(
        backgroundColor: StudentQuickAccessTheme.scaffold,
        appBar: _quickAccessAppBar(),
        body: content,
      );
    }

    return content;
  }
}
