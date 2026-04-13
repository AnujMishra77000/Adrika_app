import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../state/teacher_providers.dart';
import 'widgets/teacher_ui.dart';

class TeacherNoticesScreen extends ConsumerWidget {
  const TeacherNoticesScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final notices = ref.watch(teacherNoticesProvider);

    return notices.when(
      data: (items) {
        return TeacherGradientBackground(
          child: RefreshIndicator(
            color: TeacherPalette.oceanBlue,
            onRefresh: () async {
              ref.invalidate(teacherNoticesProvider);
              await ref.read(teacherNoticesProvider.future);
            },
            child: ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.fromLTRB(16, 14, 16, 20),
              children: [
                TeacherEntrance(
                  delay: teacherStagger(0),
                  child: const TeacherScreenHeader(
                    title: 'Notices',
                    subtitle: 'Stay updated with all classroom announcements.',
                    icon: Icons.campaign_outlined,
                  ),
                ),
                if (items.isEmpty)
                  TeacherEntrance(
                    delay: teacherStagger(1),
                    child: const TeacherSurfaceCard(
                      child: Text(
                        'No notices available.',
                        style: TextStyle(color: TeacherPalette.textDark),
                      ),
                    ),
                  )
                else
                  ...items.asMap().entries.map(
                    (entry) {
                      final index = entry.key;
                      final item = entry.value;
                      return TeacherEntrance(
                        delay: teacherStagger(index + 1),
                        child: TeacherSurfaceCard(
                          margin: const EdgeInsets.only(bottom: 10),
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Container(
                                width: 42,
                                height: 42,
                                decoration: BoxDecoration(
                                  borderRadius: BorderRadius.circular(12),
                                  color: item.isRead
                                      ? const Color(0xFFE5E7EB)
                                      : const Color(0xFFDDEAFF),
                                ),
                                child: Icon(
                                  item.isRead
                                      ? Icons.mark_email_read_outlined
                                      : Icons.mark_email_unread_outlined,
                                  color: item.isRead
                                      ? const Color(0xFF475569)
                                      : TeacherPalette.oceanBlue,
                                ),
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Row(
                                      children: [
                                        Expanded(
                                          child: Text(
                                            item.title,
                                            style: const TextStyle(
                                              color: TeacherPalette.textDark,
                                              fontSize: 16,
                                              fontWeight: FontWeight.w700,
                                            ),
                                          ),
                                        ),
                                        TeacherStatusChip(
                                          label: item.isRead ? 'Read' : 'Unread',
                                        ),
                                      ],
                                    ),
                                    const SizedBox(height: 6),
                                    Text(
                                      item.bodyPreview,
                                      maxLines: 3,
                                      overflow: TextOverflow.ellipsis,
                                      style: TextStyle(
                                        color: TeacherPalette.textDark
                                            .withValues(alpha: 0.78),
                                      ),
                                    ),
                                    const SizedBox(height: 8),
                                    Text(
                                      item.publishAt?.split('T').first ?? '—',
                                      style: TextStyle(
                                        color: TeacherPalette.textDark
                                            .withValues(alpha: 0.62),
                                        fontSize: 12,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
              ],
            ),
          ),
        );
      },
      loading: () => const TeacherLoadingView(),
      error: (error, _) => TeacherErrorView(
        title: 'Failed to load notices',
        message: error.toString(),
        onRetry: () => ref.invalidate(teacherNoticesProvider),
      ),
    );
  }
}
