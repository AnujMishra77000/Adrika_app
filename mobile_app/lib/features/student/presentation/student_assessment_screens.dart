import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/network/app_exception.dart';
import '../models/student_assessment_models.dart';
import '../state/student_providers.dart';
import 'widgets/student_home_states.dart';
import 'widgets/student_page_background.dart';

enum StudentAssessmentViewType { practice, online }

String _formatDateTime(DateTime? value) {
  if (value == null) {
    return 'Not scheduled';
  }
  final local = value.toLocal();
  final hour = local.hour.toString().padLeft(2, '0');
  final minute = local.minute.toString().padLeft(2, '0');
  return '${local.day}/${local.month}/${local.year} $hour:$minute';
}

String _durationLabel(int minutes) {
  if (minutes < 60) {
    return '$minutes min';
  }
  final hours = minutes ~/ 60;
  final rem = minutes % 60;
  if (rem == 0) {
    return '$hours hr';
  }
  return '$hours hr $rem min';
}

String _remainingLabel(int seconds) {
  final clamped = seconds < 0 ? 0 : seconds;
  final minutes = clamped ~/ 60;
  final rem = clamped % 60;
  return '${minutes.toString().padLeft(2, '0')}:${rem.toString().padLeft(2, '0')}';
}

String _bucketTitle(StudentAssessmentViewType type) {
  return type == StudentAssessmentViewType.practice
      ? 'Practice Tests'
      : 'Online Tests';
}

Color _statusColor(String availability) {
  switch (availability) {
    case 'live':
      return const Color(0xFF22C55E);
    case 'scheduled':
      return const Color(0xFF60A5FA);
    case 'completed':
      return const Color(0xFFA78BFA);
    case 'missed':
      return const Color(0xFFF97316);
    default:
      return const Color(0xFF94A3B8);
  }
}

String _statusLabel(String availability) {
  switch (availability) {
    case 'live':
      return 'Live';
    case 'scheduled':
      return 'Scheduled';
    case 'completed':
      return 'Completed';
    case 'missed':
      return 'Missed';
    default:
      return availability;
  }
}

class StudentAssessmentListScreen extends ConsumerWidget {
  const StudentAssessmentListScreen({
    super.key,
    required this.type,
  });

  final StudentAssessmentViewType type;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final listAsync = type == StudentAssessmentViewType.practice
        ? ref.watch(studentPracticeTestsProvider)
        : ref.watch(studentOnlineTestsProvider);

    return Scaffold(
      backgroundColor: const Color(0xFF130C2C),
      appBar: AppBar(
        elevation: 0,
        scrolledUnderElevation: 0,
        backgroundColor: Colors.transparent,
        title: Text(_bucketTitle(type)),
      ),
      body: Stack(
        children: [
          const StudentPageBackgroundLayer(),
          listAsync.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (error, _) => StudentHomeErrorList(
              message: error.toString(),
              onRetry: () {
                ref.invalidate(studentAssessmentsProvider);
                ref.invalidate(studentPracticeTestsProvider);
                ref.invalidate(studentOnlineTestsProvider);
              },
            ),
            data: (items) {
              if (items.isEmpty) {
                return ListView(
                  padding: const EdgeInsets.fromLTRB(16, 14, 16, 20),
                  children: [
                    StudentHomeEmptyState(
                      title: 'No ${_bucketTitle(type).toLowerCase()} yet',
                      subtitle:
                          'Assigned tests will appear here automatically.',
                    ),
                  ],
                );
              }

              return RefreshIndicator(
                onRefresh: () async {
                  ref.invalidate(studentAssessmentsProvider);
                  ref.invalidate(studentPracticeTestsProvider);
                  ref.invalidate(studentOnlineTestsProvider);
                  await ref.read(studentAssessmentsProvider.future);
                },
                child: ListView.separated(
                  physics: const AlwaysScrollableScrollPhysics(),
                  padding: const EdgeInsets.fromLTRB(16, 14, 16, 20),
                  itemCount: items.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 12),
                  itemBuilder: (context, index) {
                    final item = items[index];
                    return _AssessmentListCard(item: item);
                  },
                ),
              );
            },
          ),
        ],
      ),
    );
  }
}

class _AssessmentListCard extends StatelessWidget {
  const _AssessmentListCard({required this.item});

  final StudentAssessmentItem item;

  @override
  Widget build(BuildContext context) {
    final color = _statusColor(item.availability);
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: () => context.push('/student/tests/${item.id}'),
        borderRadius: BorderRadius.circular(18),
        child: Ink(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: Colors.white.withValues(alpha: 0.10)),
            gradient: const LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                Color(0xFF231544),
                Color(0xFF1A1E4B),
                Color(0xFF162A57),
              ],
            ),
          ),
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        item.title,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.titleSmall?.copyWith(
                              color: const Color(0xFFF8F6FF),
                              fontWeight: FontWeight.w700,
                            ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 10,
                        vertical: 4,
                      ),
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(999),
                        color: color.withValues(alpha: 0.18),
                        border:
                            Border.all(color: color.withValues(alpha: 0.45)),
                      ),
                      child: Text(
                        _statusLabel(item.availability),
                        style: Theme.of(context).textTheme.labelSmall?.copyWith(
                              color: color,
                              fontWeight: FontWeight.w700,
                            ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 6,
                  children: [
                    _MetaPill(
                      icon: Icons.menu_book_outlined,
                      text: item.subjectName ?? 'Subject',
                    ),
                    _MetaPill(
                      icon: Icons.grade_outlined,
                      text: '${item.totalMarks.toStringAsFixed(0)} marks',
                    ),
                    _MetaPill(
                      icon: Icons.timer_outlined,
                      text: _durationLabel(item.durationMinutes),
                    ),
                    if (item.topic != null && item.topic!.isNotEmpty)
                      _MetaPill(
                        icon: Icons.label_outline,
                        text: item.topic!,
                      ),
                  ],
                ),
                const SizedBox(height: 10),
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        item.isScheduled
                            ? 'Starts: ${_formatDateTime(item.startsAt)}'
                            : 'Ends: ${_formatDateTime(item.endsAt)}',
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: const Color(0xFFCBD5E1),
                            ),
                      ),
                    ),
                    const Icon(
                      Icons.arrow_forward_ios_rounded,
                      color: Color(0xFFC7BFFF),
                      size: 16,
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class StudentAssessmentDetailScreen extends ConsumerStatefulWidget {
  const StudentAssessmentDetailScreen({
    super.key,
    required this.assessmentId,
  });

  final String assessmentId;

  @override
  ConsumerState<StudentAssessmentDetailScreen> createState() =>
      _StudentAssessmentDetailScreenState();
}

class _StudentAssessmentDetailScreenState
    extends ConsumerState<StudentAssessmentDetailScreen> {
  bool _starting = false;

  Future<void> _start() async {
    if (_starting) {
      return;
    }
    setState(() => _starting = true);
    try {
      final attemptId = await startStudentAssessmentAttempt(
        ref,
        assessmentId: widget.assessmentId,
      );
      if (!mounted) {
        return;
      }
      ref.invalidate(studentAssessmentsProvider);
      context.go('/student/tests/attempts/$attemptId');
    } on AppException catch (error) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(error.message)),
      );
      ref.invalidate(studentAssessmentDetailProvider(widget.assessmentId));
      ref.invalidate(studentAssessmentsProvider);
    } catch (error) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Unable to start test: $error')),
      );
    } finally {
      if (mounted) {
        setState(() => _starting = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final detailAsync = ref.watch(
      studentAssessmentDetailProvider(widget.assessmentId),
    );

    return Scaffold(
      backgroundColor: const Color(0xFF130C2C),
      appBar: AppBar(
        elevation: 0,
        scrolledUnderElevation: 0,
        backgroundColor: Colors.transparent,
        title: const Text('Test Overview'),
      ),
      body: Stack(
        children: [
          const StudentPageBackgroundLayer(),
          detailAsync.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (error, _) => StudentHomeErrorList(
              message: error.toString(),
              onRetry: () => ref.invalidate(
                studentAssessmentDetailProvider(widget.assessmentId),
              ),
            ),
            data: (detail) {
              final canStart = detail.isLive;
              final statusColor = _statusColor(detail.availability);

              return ListView(
                padding: const EdgeInsets.fromLTRB(16, 14, 16, 20),
                children: [
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(18),
                      gradient: const LinearGradient(
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                        colors: [
                          Color(0xFF28154E),
                          Color(0xFF1A2758),
                        ],
                      ),
                      border: Border.all(
                        color: Colors.white.withValues(alpha: 0.16),
                      ),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          detail.title,
                          style:
                              Theme.of(context).textTheme.titleLarge?.copyWith(
                                    color: const Color(0xFFF8F6FF),
                                    fontWeight: FontWeight.w800,
                                  ),
                        ),
                        if (detail.description.trim().isNotEmpty) ...[
                          const SizedBox(height: 8),
                          Text(
                            detail.description,
                            style: Theme.of(context)
                                .textTheme
                                .bodyMedium
                                ?.copyWith(
                                  color: const Color(0xFFD7D5E9),
                                ),
                          ),
                        ],
                        const SizedBox(height: 12),
                        Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 10,
                                vertical: 5,
                              ),
                              decoration: BoxDecoration(
                                color: statusColor.withValues(alpha: 0.17),
                                borderRadius: BorderRadius.circular(999),
                                border: Border.all(
                                  color: statusColor.withValues(alpha: 0.40),
                                ),
                              ),
                              child: Text(
                                _statusLabel(detail.availability),
                                style: Theme.of(context)
                                    .textTheme
                                    .labelMedium
                                    ?.copyWith(
                                      color: statusColor,
                                      fontWeight: FontWeight.w700,
                                    ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 12),
                        _MetaGrid(detail: detail),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),
                  if (detail.isCompleted &&
                      detail.latestAttemptId != null &&
                      detail.latestAttemptId!.isNotEmpty)
                    FilledButton.icon(
                      onPressed: () => context.push(
                        '/student/tests/attempts/${detail.latestAttemptId}/result',
                      ),
                      icon: const Icon(Icons.verified_outlined),
                      label: const Text('View Result'),
                    )
                  else if (canStart)
                    FilledButton.icon(
                      onPressed: _starting ? null : _start,
                      icon: _starting
                          ? const SizedBox(
                              width: 16,
                              height: 16,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Icon(Icons.play_arrow_rounded),
                      label: Text(_starting ? 'Starting...' : 'Start Test'),
                    )
                  else
                    FilledButton.tonalIcon(
                      onPressed: null,
                      icon: const Icon(Icons.info_outline),
                      label: Text(
                        detail.isScheduled
                            ? 'Test unlocks at ${_formatDateTime(detail.startsAt)}'
                            : detail.isMissed
                                ? 'Test window closed'
                                : 'Test is not available',
                      ),
                    ),
                ],
              );
            },
          ),
        ],
      ),
    );
  }
}

class _MetaGrid extends StatelessWidget {
  const _MetaGrid({required this.detail});

  final StudentAssessmentDetail detail;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: [
        _MetaPill(
          icon: Icons.menu_book_outlined,
          text: detail.subjectName ?? 'Subject',
        ),
        if (detail.topic != null && detail.topic!.trim().isNotEmpty)
          _MetaPill(
            icon: Icons.label_outline,
            text: detail.topic!,
          ),
        _MetaPill(
          icon: Icons.task_alt_outlined,
          text: '${detail.totalMarks.toStringAsFixed(0)} marks',
        ),
        _MetaPill(
          icon: Icons.check_circle_outline,
          text: 'Pass ${detail.passingMarks.toStringAsFixed(0)}',
        ),
        _MetaPill(
          icon: Icons.timer_outlined,
          text: _durationLabel(detail.durationMinutes),
        ),
        _MetaPill(
          icon: Icons.question_answer_outlined,
          text: '${detail.questionCount} questions',
        ),
        _MetaPill(
          icon: Icons.schedule_outlined,
          text: 'Start ${_formatDateTime(detail.startsAt)}',
        ),
        _MetaPill(
          icon: Icons.event_busy_outlined,
          text: 'End ${_formatDateTime(detail.endsAt)}',
        ),
      ],
    );
  }
}

class _MetaPill extends StatelessWidget {
  const _MetaPill({
    required this.icon,
    required this.text,
  });

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: Colors.white.withValues(alpha: 0.08),
        border: Border.all(color: Colors.white.withValues(alpha: 0.13)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: const Color(0xFFB9C6FF)),
          const SizedBox(width: 6),
          Text(
            text,
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
                  color: const Color(0xFFE7E4FF),
                  fontWeight: FontWeight.w600,
                ),
          ),
        ],
      ),
    );
  }
}

class StudentAssessmentAttemptScreen extends ConsumerStatefulWidget {
  const StudentAssessmentAttemptScreen({
    super.key,
    required this.attemptId,
  });

  final String attemptId;

  @override
  ConsumerState<StudentAssessmentAttemptScreen> createState() =>
      _StudentAssessmentAttemptScreenState();
}

class _StudentAssessmentAttemptScreenState
    extends ConsumerState<StudentAssessmentAttemptScreen> {
  final Map<String, String> _selectedAnswers = <String, String>{};
  final Set<String> _savingQuestionIds = <String>{};

  Timer? _ticker;
  String? _boundAttemptId;
  int _currentQuestionIndex = 0;
  int? _remainingSeconds;
  bool _submitting = false;
  bool _autoSubmitTriggered = false;

  void _bindAttempt(StudentAssessmentAttemptDetail detail) {
    if (_boundAttemptId != detail.attemptId) {
      _boundAttemptId = detail.attemptId;
      _selectedAnswers
        ..clear()
        ..addEntries(
          detail.questions
              .where((question) => question.selectedKey != null)
              .map(
                (question) => MapEntry(
                  question.questionId,
                  question.selectedKey!,
                ),
              ),
        );
      _remainingSeconds = detail.remainingSeconds;
      _currentQuestionIndex = 0;
      _autoSubmitTriggered = false;
    }

    if (detail.isCompleted || !detail.isStarted) {
      _ticker?.cancel();
      _ticker = null;
      return;
    }

    _ticker ??= Timer.periodic(const Duration(seconds: 1), (timer) {
      if (!mounted) {
        timer.cancel();
        return;
      }
      final remaining = _remainingSeconds ?? 0;
      if (remaining <= 1) {
        timer.cancel();
        _ticker = null;
        setState(() => _remainingSeconds = 0);
        if (!_autoSubmitTriggered) {
          _autoSubmitTriggered = true;
          _submitAttempt(auto: true);
        }
        return;
      }
      setState(() => _remainingSeconds = remaining - 1);
    });
  }

  @override
  void dispose() {
    _ticker?.cancel();
    super.dispose();
  }

  Future<void> _saveAnswer({
    required String questionId,
    required String selectedKey,
  }) async {
    if (_savingQuestionIds.contains(questionId) || _submitting) {
      return;
    }

    setState(() {
      _selectedAnswers[questionId] = selectedKey;
      _savingQuestionIds.add(questionId);
    });

    try {
      await saveStudentAssessmentAnswer(
        ref,
        attemptId: widget.attemptId,
        questionId: questionId,
        selectedKey: selectedKey,
      );
    } on AppException catch (error) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(error.message)),
      );
    } catch (error) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Unable to save answer: $error')),
      );
    } finally {
      if (mounted) {
        setState(() => _savingQuestionIds.remove(questionId));
      }
    }
  }

  Future<void> _submitAttempt({required bool auto}) async {
    if (_submitting) {
      return;
    }

    setState(() => _submitting = true);
    _ticker?.cancel();
    _ticker = null;

    try {
      await submitStudentAssessmentAttempt(ref, attemptId: widget.attemptId);
      if (!mounted) {
        return;
      }
      context.go('/student/tests/attempts/${widget.attemptId}/result');
    } on AppException catch (error) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(error.message)),
      );
      ref.invalidate(studentAssessmentAttemptDetailProvider(widget.attemptId));
    } catch (error) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Unable to submit attempt: $error')),
      );
    } finally {
      if (mounted) {
        setState(() => _submitting = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final attemptAsync = ref.watch(
      studentAssessmentAttemptDetailProvider(widget.attemptId),
    );

    return Scaffold(
      backgroundColor: const Color(0xFF130C2C),
      appBar: AppBar(
        elevation: 0,
        scrolledUnderElevation: 0,
        backgroundColor: Colors.transparent,
        title: const Text('Live Test'),
      ),
      body: Stack(
        children: [
          const StudentPageBackgroundLayer(),
          attemptAsync.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (error, _) => StudentHomeErrorList(
              message: error.toString(),
              onRetry: () => ref.invalidate(
                  studentAssessmentAttemptDetailProvider(widget.attemptId)),
            ),
            data: (attempt) {
              _bindAttempt(attempt);

              if (attempt.isCompleted) {
                return ListView(
                  padding: const EdgeInsets.fromLTRB(16, 14, 16, 20),
                  children: [
                    StudentHomeEmptyState(
                      title: 'Attempt already submitted',
                      subtitle:
                          'Open the result view to check score and question-wise analysis.',
                    ),
                    const SizedBox(height: 12),
                    FilledButton.icon(
                      onPressed: () => context.go(
                        '/student/tests/attempts/${widget.attemptId}/result',
                      ),
                      icon: const Icon(Icons.visibility_outlined),
                      label: const Text('Open Result'),
                    ),
                  ],
                );
              }

              if (attempt.questions.isEmpty) {
                return const Center(
                  child: StudentHomeEmptyState(
                    title: 'No questions in this test',
                    subtitle:
                        'Please contact admin. This test does not contain question items.',
                  ),
                );
              }

              final totalQuestions = attempt.questions.length;
              if (_currentQuestionIndex >= totalQuestions) {
                _currentQuestionIndex = totalQuestions - 1;
              }
              final current = attempt.questions[_currentQuestionIndex];
              final answeredCount = _selectedAnswers.length;
              final remaining = _remainingSeconds ?? attempt.remainingSeconds;

              return Column(
                children: [
                  Container(
                    margin: const EdgeInsets.fromLTRB(16, 14, 16, 0),
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(16),
                      color: Colors.white.withValues(alpha: 0.08),
                      border: Border.all(
                          color: Colors.white.withValues(alpha: 0.14)),
                    ),
                    child: Row(
                      children: [
                        _InfoTile(
                          label: 'Time Left',
                          value: _remainingLabel(remaining),
                          color: remaining <= 120
                              ? const Color(0xFFF97316)
                              : const Color(0xFF93C5FD),
                        ),
                        const SizedBox(width: 10),
                        _InfoTile(
                          label: 'Answered',
                          value: '$answeredCount/$totalQuestions',
                          color: const Color(0xFF86EFAC),
                        ),
                      ],
                    ),
                  ),
                  Expanded(
                    child: ListView(
                      padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
                      children: [
                        LinearProgressIndicator(
                          value: (_currentQuestionIndex + 1) / totalQuestions,
                          minHeight: 6,
                          borderRadius: BorderRadius.circular(999),
                          backgroundColor: Colors.white.withValues(alpha: 0.12),
                          color: const Color(0xFF8EA2FF),
                        ),
                        const SizedBox(height: 10),
                        Wrap(
                          spacing: 6,
                          runSpacing: 6,
                          children: attempt.questions.map((question) {
                            final idx = question.seqNo - 1;
                            final selected = _selectedAnswers
                                .containsKey(question.questionId);
                            final isCurrent = idx == _currentQuestionIndex;
                            return InkWell(
                              onTap: () =>
                                  setState(() => _currentQuestionIndex = idx),
                              borderRadius: BorderRadius.circular(10),
                              child: Ink(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 10,
                                  vertical: 5,
                                ),
                                decoration: BoxDecoration(
                                  borderRadius: BorderRadius.circular(10),
                                  color: isCurrent
                                      ? const Color(0xFF8EA2FF)
                                      : selected
                                          ? const Color(0xFF166534)
                                              .withValues(alpha: 0.35)
                                          : Colors.white
                                              .withValues(alpha: 0.08),
                                  border: Border.all(
                                    color: isCurrent
                                        ? const Color(0xFFCBD5FF)
                                        : selected
                                            ? const Color(0xFF86EFAC)
                                            : Colors.white
                                                .withValues(alpha: 0.14),
                                  ),
                                ),
                                child: Text(
                                  '${question.seqNo}',
                                  style: Theme.of(context)
                                      .textTheme
                                      .labelMedium
                                      ?.copyWith(
                                        color: const Color(0xFFF8F6FF),
                                        fontWeight: FontWeight.w700,
                                      ),
                                ),
                              ),
                            );
                          }).toList(growable: false),
                        ),
                        const SizedBox(height: 12),
                        Container(
                          padding: const EdgeInsets.all(16),
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(18),
                            gradient: const LinearGradient(
                              begin: Alignment.topLeft,
                              end: Alignment.bottomRight,
                              colors: [
                                Color(0xFF24154A),
                                Color(0xFF162A57),
                              ],
                            ),
                            border: Border.all(
                              color: Colors.white.withValues(alpha: 0.16),
                            ),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Question ${current.seqNo}',
                                style: Theme.of(context)
                                    .textTheme
                                    .labelLarge
                                    ?.copyWith(
                                      color: const Color(0xFFC7D2FE),
                                      fontWeight: FontWeight.w700,
                                    ),
                              ),
                              const SizedBox(height: 8),
                              Text(
                                current.prompt,
                                style: Theme.of(context)
                                    .textTheme
                                    .titleMedium
                                    ?.copyWith(
                                      color: const Color(0xFFF8F6FF),
                                      fontWeight: FontWeight.w700,
                                    ),
                              ),
                              const SizedBox(height: 12),
                              ...current.options.map((option) {
                                final isSelected =
                                    _selectedAnswers[current.questionId] ==
                                        option.key;
                                final isSaving = _savingQuestionIds
                                    .contains(current.questionId);
                                return Container(
                                  margin: const EdgeInsets.only(bottom: 8),
                                  decoration: BoxDecoration(
                                    borderRadius: BorderRadius.circular(12),
                                    color: isSelected
                                        ? const Color(0xFF1D4ED8)
                                            .withValues(alpha: 0.32)
                                        : Colors.white.withValues(alpha: 0.06),
                                    border: Border.all(
                                      color: isSelected
                                          ? const Color(0xFF93C5FD)
                                          : Colors.white
                                              .withValues(alpha: 0.13),
                                    ),
                                  ),
                                  child: ListTile(
                                    onTap: () => _saveAnswer(
                                      questionId: current.questionId,
                                      selectedKey: option.key,
                                    ),
                                    dense: true,
                                    leading: CircleAvatar(
                                      radius: 14,
                                      backgroundColor: isSelected
                                          ? const Color(0xFF60A5FA)
                                          : Colors.white
                                              .withValues(alpha: 0.12),
                                      child: Text(
                                        option.key,
                                        style: const TextStyle(
                                          color: Colors.white,
                                          fontWeight: FontWeight.w700,
                                          fontSize: 12,
                                        ),
                                      ),
                                    ),
                                    title: Text(
                                      option.text,
                                      style: Theme.of(context)
                                          .textTheme
                                          .bodyMedium
                                          ?.copyWith(
                                            color: const Color(0xFFF8F6FF),
                                          ),
                                    ),
                                    trailing: isSaving && isSelected
                                        ? const SizedBox(
                                            width: 16,
                                            height: 16,
                                            child: CircularProgressIndicator(
                                              strokeWidth: 2,
                                            ),
                                          )
                                        : isSelected
                                            ? const Icon(
                                                Icons.check_circle,
                                                color: Color(0xFF86EFAC),
                                              )
                                            : null,
                                  ),
                                );
                              }),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
                    child: Row(
                      children: [
                        Expanded(
                          child: OutlinedButton(
                            onPressed: _currentQuestionIndex == 0
                                ? null
                                : () => setState(() => _currentQuestionIndex--),
                            child: const Text('Previous'),
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: _currentQuestionIndex == totalQuestions - 1
                              ? FilledButton(
                                  onPressed: _submitting
                                      ? null
                                      : () => _submitAttempt(auto: false),
                                  child: Text(
                                    _submitting
                                        ? 'Submitting...'
                                        : 'Submit Test',
                                  ),
                                )
                              : FilledButton(
                                  onPressed: () =>
                                      setState(() => _currentQuestionIndex++),
                                  child: const Text('Next'),
                                ),
                        ),
                      ],
                    ),
                  ),
                ],
              );
            },
          ),
        ],
      ),
    );
  }
}

class _InfoTile extends StatelessWidget {
  const _InfoTile({
    required this.label,
    required this.value,
    required this.color,
  });

  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(12),
          color: Colors.white.withValues(alpha: 0.06),
          border: Border.all(color: Colors.white.withValues(alpha: 0.13)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              label,
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: const Color(0xFFCBD5E1),
                  ),
            ),
            const SizedBox(height: 4),
            Text(
              value,
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    color: color,
                    fontWeight: FontWeight.w800,
                  ),
            ),
          ],
        ),
      ),
    );
  }
}

class StudentAssessmentResultScreen extends ConsumerWidget {
  const StudentAssessmentResultScreen({
    super.key,
    required this.attemptId,
  });

  final String attemptId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final attemptAsync =
        ref.watch(studentAssessmentAttemptDetailProvider(attemptId));

    return Scaffold(
      backgroundColor: const Color(0xFF130C2C),
      appBar: AppBar(
        elevation: 0,
        scrolledUnderElevation: 0,
        backgroundColor: Colors.transparent,
        title: const Text('Test Result'),
      ),
      body: Stack(
        children: [
          const StudentPageBackgroundLayer(),
          attemptAsync.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (error, _) => StudentHomeErrorList(
              message: error.toString(),
              onRetry: () => ref.invalidate(
                  studentAssessmentAttemptDetailProvider(attemptId)),
            ),
            data: (attempt) {
              if (!attempt.isCompleted) {
                return ListView(
                  padding: const EdgeInsets.fromLTRB(16, 14, 16, 20),
                  children: [
                    const StudentHomeEmptyState(
                      title: 'Result is not ready yet',
                      subtitle:
                          'Complete and submit the test to view analysis.',
                    ),
                    const SizedBox(height: 12),
                    FilledButton.icon(
                      onPressed: () =>
                          context.go('/student/tests/attempts/$attemptId'),
                      icon: const Icon(Icons.play_arrow_rounded),
                      label: const Text('Continue Attempt'),
                    ),
                  ],
                );
              }

              final score = attempt.score ?? 0;
              final isPassed = attempt.isPassed ?? false;
              final headerColor =
                  isPassed ? const Color(0xFF16A34A) : const Color(0xFFDC2626);

              return ListView.separated(
                padding: const EdgeInsets.fromLTRB(16, 14, 16, 20),
                itemCount: attempt.questions.length + 1,
                separatorBuilder: (_, __) => const SizedBox(height: 10),
                itemBuilder: (context, index) {
                  if (index == 0) {
                    return Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(18),
                        gradient: const LinearGradient(
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                          colors: [
                            Color(0xFF28154E),
                            Color(0xFF132F58),
                          ],
                        ),
                        border: Border.all(
                            color: headerColor.withValues(alpha: 0.45)),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Icon(
                                isPassed
                                    ? Icons.verified_rounded
                                    : Icons.cancel_rounded,
                                color: headerColor,
                              ),
                              const SizedBox(width: 8),
                              Text(
                                isPassed ? 'Passed' : 'Needs Improvement',
                                style: Theme.of(context)
                                    .textTheme
                                    .titleMedium
                                    ?.copyWith(
                                      color: const Color(0xFFF8F6FF),
                                      fontWeight: FontWeight.w800,
                                    ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 10),
                          Text(
                            'Score: ${score.toStringAsFixed(1)} / ${attempt.totalMarks.toStringAsFixed(1)}',
                            style: Theme.of(context)
                                .textTheme
                                .titleLarge
                                ?.copyWith(
                                  color: const Color(0xFFF8F6FF),
                                  fontWeight: FontWeight.w800,
                                ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            'Passing marks: ${attempt.passingMarks.toStringAsFixed(1)}',
                            style: Theme.of(context)
                                .textTheme
                                .bodyMedium
                                ?.copyWith(
                                  color: const Color(0xFFD8D6EA),
                                ),
                          ),
                          if (attempt.autoSubmitted) ...[
                            const SizedBox(height: 8),
                            Text(
                              'Auto-submitted on time expiry.',
                              style: Theme.of(context)
                                  .textTheme
                                  .labelMedium
                                  ?.copyWith(color: const Color(0xFFFACB8C)),
                            ),
                          ],
                        ],
                      ),
                    );
                  }

                  final question = attempt.questions[index - 1];
                  final isCorrect = question.isCorrect ?? false;
                  final color = isCorrect
                      ? const Color(0xFF22C55E)
                      : const Color(0xFFEF4444);
                  return Container(
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(16),
                      color: Colors.white.withValues(alpha: 0.06),
                      border: Border.all(color: color.withValues(alpha: 0.42)),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Icon(
                              isCorrect
                                  ? Icons.check_circle_rounded
                                  : Icons.cancel_rounded,
                              color: color,
                              size: 18,
                            ),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                'Q${question.seqNo}  ${question.prompt}',
                                style: Theme.of(context)
                                    .textTheme
                                    .titleSmall
                                    ?.copyWith(
                                      color: const Color(0xFFF8F6FF),
                                      fontWeight: FontWeight.w700,
                                    ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'Your answer: ${question.selectedKey ?? 'Not answered'}',
                          style:
                              Theme.of(context).textTheme.bodySmall?.copyWith(
                                    color: const Color(0xFFD5D8EA),
                                  ),
                        ),
                        Text(
                          'Correct answer: ${question.correctKey ?? '-'}',
                          style:
                              Theme.of(context).textTheme.bodySmall?.copyWith(
                                    color: const Color(0xFFD5D8EA),
                                  ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'Marks: ${(question.marksAwarded ?? 0).toStringAsFixed(1)} / ${question.maxMarks.toStringAsFixed(1)}',
                          style:
                              Theme.of(context).textTheme.labelMedium?.copyWith(
                                    color: color,
                                    fontWeight: FontWeight.w700,
                                  ),
                        ),
                      ],
                    ),
                  );
                },
              );
            },
          ),
        ],
      ),
    );
  }
}
