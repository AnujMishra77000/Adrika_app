import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/config/app_env.dart';
import '../../../core/utils/attachment_opener.dart';
import '../../auth/state/auth_controller.dart';
import '../models/student_models.dart';
import '../state/student_providers.dart';
import 'widgets/student_fade_slide_in.dart';
import 'widgets/student_home_palette.dart';
import 'widgets/student_home_states.dart';
import 'widgets/student_homework_task_card.dart';
import 'widgets/student_module_header.dart';
import 'widgets/student_page_background.dart';
import 'widgets/student_section_header.dart';
import 'widgets/student_status_chip.dart';
import 'widgets/student_surface_card.dart';

class StudentHomeworkScreen extends ConsumerStatefulWidget {
  const StudentHomeworkScreen({super.key});

  @override
  ConsumerState<StudentHomeworkScreen> createState() =>
      _StudentHomeworkScreenState();
}

class _StudentHomeworkScreenState extends ConsumerState<StudentHomeworkScreen> {
  bool _syncInProgress = false;
  bool _initialSyncDone = false;
  final Set<String> _submittingHomeworkIds = <String>{};

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _markAllAsSeen();
    });
  }

  Future<void> _markAllAsSeen({bool force = false}) async {
    if (_syncInProgress) {
      return;
    }
    if (_initialSyncDone && !force) {
      return;
    }

    _syncInProgress = true;
    try {
      await markStudentHomeworkReadAll(ref);
      _initialSyncDone = true;
    } catch (_) {
      // Best effort only.
    } finally {
      _syncInProgress = false;
    }
  }

  Future<void> _refresh() async {
    ref.invalidate(studentHomeworkProvider);
    await ref.read(studentHomeworkProvider.future);
    await _markAllAsSeen(force: true);
  }

  Future<void> _openAttachment(
    BuildContext context, {
    required String fileUrl,
    required String fileName,
    required String contentType,
  }) async {
    final messenger = ScaffoldMessenger.of(context);
    final accessToken =
        ref.read(authControllerProvider.select((state) => state.accessToken));
    final resolvedUrl = AppEnv.resolveServerUrl(fileUrl) ?? fileUrl;

    messenger.showSnackBar(
      const SnackBar(
        content: Text('Opening attachment...'),
        duration: Duration(milliseconds: 900),
      ),
    );

    try {
      await AttachmentOpener.openFromUrl(
        url: resolvedUrl,
        fileName: fileName,
        contentType: contentType,
        accessToken: accessToken,
      );
    } catch (error) {
      if (!context.mounted) {
        return;
      }
      messenger.showSnackBar(
        SnackBar(
          content: Text('Unable to open attachment. $error'),
        ),
      );
    }
  }

  Future<void> _submitHomework(StudentHomework item) async {
    if (_submittingHomeworkIds.contains(item.id) || item.isSubmitted) {
      return;
    }

    final selected = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: const ['pdf'],
      withData: false,
      allowMultiple: false,
    );

    if (selected == null || selected.files.isEmpty) {
      return;
    }

    final picked = selected.files.first;
    final filePath = picked.path;
    if (filePath == null || filePath.isEmpty) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Unable to read selected PDF file.')),
      );
      return;
    }

    setState(() {
      _submittingHomeworkIds.add(item.id);
    });

    try {
      await submitStudentHomework(
        ref,
        homeworkId: item.id,
        filePath: filePath,
        fileName: picked.name,
      );
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Homework submitted successfully.')),
      );
      await _refresh();
    } catch (error) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(error.toString())),
      );
    } finally {
      if (mounted) {
        setState(() {
          _submittingHomeworkIds.remove(item.id);
        });
      }
    }
  }

  void _openHomeworkPreview(BuildContext context, StudentHomework item) {
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      backgroundColor: Colors.white,
      builder: (context) {
        final submission = item.submission;
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(18, 10, 18, 24),
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    item.title,
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(
                          color: StudentHomePalette.textPrimary,
                          fontWeight: FontWeight.w700,
                        ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    item.description.isEmpty
                        ? 'No additional instruction for this homework.'
                        : item.description,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: StudentHomePalette.textSecondary,
                        ),
                  ),
                  const SizedBox(height: 14),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      StudentStatusChip(
                        label: 'Status: ${item.isSubmitted ? 'Submitted' : item.status}',
                        tone: item.isSubmitted
                            ? StudentChipTone.success
                            : StudentChipTone.info,
                      ),
                      StudentStatusChip(
                        label: 'Due: ${item.dueDate}',
                        tone: StudentChipTone.warning,
                      ),
                      StudentStatusChip(
                        label: item.isRead ? 'Viewed' : 'New',
                        tone: item.isRead
                            ? StudentChipTone.neutral
                            : StudentChipTone.info,
                      ),
                    ],
                  ),
                  if (item.attachments.isNotEmpty) ...[
                    const SizedBox(height: 16),
                    Text(
                      'Homework Attachments',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            color: StudentHomePalette.textPrimary,
                            fontWeight: FontWeight.w700,
                          ),
                    ),
                    const SizedBox(height: 8),
                    ...item.attachments.map((attachment) {
                      final resolvedUrl =
                          AppEnv.resolveServerUrl(attachment.fileUrl) ??
                              attachment.fileUrl;

                      return Container(
                        margin: const EdgeInsets.only(bottom: 8),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(
                            color: const Color(0xFFD7D7E8),
                          ),
                        ),
                        child: ListTile(
                          onTap: () => _openAttachment(
                            context,
                            fileUrl: attachment.fileUrl,
                            fileName: attachment.fileName,
                            contentType: attachment.contentType,
                          ),
                          leading: const Icon(
                            Icons.picture_as_pdf_rounded,
                            color: Color(0xFF5A4BA0),
                          ),
                          title: Text(
                            attachment.fileName,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: Theme.of(context)
                                .textTheme
                                .bodyMedium
                                ?.copyWith(
                                  color: StudentHomePalette.textPrimary,
                                  fontWeight: FontWeight.w600,
                                ),
                          ),
                          subtitle: Text(
                            resolvedUrl,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: Theme.of(context)
                                .textTheme
                                .labelSmall
                                ?.copyWith(
                                  color: StudentHomePalette.textSecondary,
                                ),
                          ),
                          trailing: const Icon(
                            Icons.open_in_new_rounded,
                            color: Color(0xFF5A4BA0),
                          ),
                        ),
                      );
                    }),
                  ],
                  if (submission != null) ...[
                    const SizedBox(height: 16),
                    Text(
                      'Your Submission',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            color: StudentHomePalette.textPrimary,
                            fontWeight: FontWeight.w700,
                          ),
                    ),
                    const SizedBox(height: 8),
                    StudentStatusChip(
                      label: 'Submitted: ${submission.submittedAt?.toLocal().toString() ?? '-'}',
                      tone: submission.status.toLowerCase() == 'late'
                          ? StudentChipTone.warning
                          : StudentChipTone.success,
                    ),
                    if ((submission.notes ?? '').trim().isNotEmpty) ...[
                      const SizedBox(height: 8),
                      Text(
                        submission.notes!,
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: StudentHomePalette.textSecondary,
                            ),
                      ),
                    ],
                    if (submission.attachments.isNotEmpty) ...[
                      const SizedBox(height: 8),
                      ...submission.attachments.map((attachment) {
                        return Container(
                          margin: const EdgeInsets.only(bottom: 8),
                          decoration: BoxDecoration(
                            color: Colors.white,
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(
                              color: const Color(0xFFD7D7E8),
                            ),
                          ),
                          child: ListTile(
                            onTap: () => _openAttachment(
                              context,
                              fileUrl: attachment.fileUrl,
                              fileName: attachment.fileName,
                              contentType: attachment.contentType,
                            ),
                            leading: const Icon(
                              Icons.assignment_turned_in_rounded,
                              color: Color(0xFF0F9D58),
                            ),
                            title: Text(
                              attachment.fileName,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                            subtitle: Text(
                              '${(attachment.fileSizeBytes ~/ 1024)} KB',
                            ),
                            trailing: const Icon(Icons.open_in_new_rounded),
                          ),
                        );
                      }),
                    ],
                  ],
                  const SizedBox(height: 12),
                  if (!item.isSubmitted)
                    SizedBox(
                      width: double.infinity,
                      child: FilledButton.icon(
                        onPressed: _submittingHomeworkIds.contains(item.id)
                            ? null
                            : () => _submitHomework(item),
                        icon: const Icon(Icons.upload_file_rounded),
                        label: Text(_submittingHomeworkIds.contains(item.id)
                            ? 'Submitting...'
                            : 'Submit PDF'),
                      ),
                    )
                  else
                    const SizedBox.shrink(),
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final homeworkAsync = ref.watch(studentHomeworkProvider);

    return Stack(
      children: [
        const StudentPageBackgroundLayer(),
        homeworkAsync.when(
          loading: () => const StudentFeedLoadingList(itemCount: 5),
          error: (error, _) => ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: StudentUiSpacing.page,
            children: [
              StudentHomeErrorList(
                message: error.toString(),
                onRetry: () => ref.invalidate(studentHomeworkProvider),
              ),
            ],
          ),
          data: (items) {
            final submittedCount = items.where((item) => item.isSubmitted).length;
            final pendingCount = items.length - submittedCount;

            return RefreshIndicator(
              onRefresh: _refresh,
              child: ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: StudentUiSpacing.page,
                children: [
                  const StudentModuleHeader(
                    title: 'Homework Studio',
                    subtitle:
                        'Track assignments, submit PDF answers, and monitor completion status in one place.',
                    icon: Icons.assignment_rounded,
                    accent: StudentHomePalette.mintGreen,
                  ),
                  const SizedBox(height: StudentUiSpacing.sectionGap),
                  Row(
                    children: [
                      Expanded(
                        child: StudentSurfaceCard(
                          child: _HomeworkCountTile(
                            title: 'Pending',
                            value: pendingCount.toString(),
                            accent: StudentHomePalette.warning,
                            icon: Icons.pending_actions_rounded,
                          ),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: StudentSurfaceCard(
                          child: _HomeworkCountTile(
                            title: 'Submitted',
                            value: submittedCount.toString(),
                            accent: StudentHomePalette.success,
                            icon: Icons.check_circle_outline_rounded,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: StudentUiSpacing.sectionGap),
                  const StudentSectionHeader(
                    title: 'Assignments',
                    subtitle: 'Prioritized by urgency and due timeline.',
                    titleColor: Color(0xFFECE8FF),
                    subtitleColor: Color(0xFFB6B1D6),
                  ),
                  const SizedBox(height: 10),
                  if (items.isEmpty)
                    const StudentHomeEmptyState(
                      title: 'No homework assigned',
                      subtitle:
                          'When teachers publish new tasks, they will appear in this panel.',
                    )
                  else
                    ...List<Widget>.generate(
                      items.length,
                      (index) {
                        final item = items[index];
                        final delay = 80 + (index * 35);
                        return StudentFadeSlideIn(
                          delayMs: delay,
                          child: Padding(
                            padding: const EdgeInsets.only(
                              bottom: StudentUiSpacing.cardGap,
                            ),
                            child: StudentHomeworkTaskCard(
                              homework: item,
                              onTap: () => _openHomeworkPreview(context, item),
                              onSubmit: () => _submitHomework(item),
                              submitting:
                                  _submittingHomeworkIds.contains(item.id),
                            ),
                          ),
                        );
                      },
                    ),
                ],
              ),
            );
          },
        ),
      ],
    );
  }
}

class _HomeworkCountTile extends StatelessWidget {
  const _HomeworkCountTile({
    required this.title,
    required this.value,
    required this.accent,
    required this.icon,
  });

  final String title;
  final String value;
  final Color accent;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        StudentIconBadge(icon: icon, accent: accent, size: 36),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: Theme.of(context).textTheme.labelMedium?.copyWith(
                      color: StudentHomePalette.textMuted,
                      fontWeight: FontWeight.w600,
                    ),
              ),
              const SizedBox(height: 2),
              Text(
                value,
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      color: StudentHomePalette.textPrimary,
                      fontWeight: FontWeight.w800,
                    ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
