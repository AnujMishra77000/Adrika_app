import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../auth/state/auth_controller.dart';
import '../data/teacher_api.dart';
import '../models/teacher_models.dart';
import '../state/teacher_providers.dart';
import 'widgets/teacher_ui.dart';

class TeacherAssignmentsScreen extends ConsumerStatefulWidget {
  const TeacherAssignmentsScreen({super.key});

  @override
  ConsumerState<TeacherAssignmentsScreen> createState() =>
      _TeacherAssignmentsScreenState();
}

class _TeacherAssignmentsScreenState
    extends ConsumerState<TeacherAssignmentsScreen> {
  bool _isCreating = false;

  Future<void> _refreshAll() async {
    ref.invalidate(teacherAssignmentsProvider);
    ref.invalidate(teacherScheduledLecturesProvider);
    ref.invalidate(teacherCompletedLecturesProvider);
    await Future.wait([
      ref.read(teacherAssignmentsProvider.future),
      ref.read(teacherScheduledLecturesProvider.future),
      ref.read(teacherCompletedLecturesProvider.future),
    ]);
  }

  Future<void> _openLectureDoneSheet(List<TeacherAssignment> assignments) async {
    if (assignments.isEmpty) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('No assignment mapping found. Contact admin first.'),
        ),
      );
      return;
    }

    final payload = await showModalBottomSheet<_CreateLecturePayload>(
      context: context,
      isScrollControlled: true,
      backgroundColor: const Color(0xFFF4F8FF),
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (_) => _CreateLectureSheet(assignments: assignments),
    );

    if (payload == null) {
      return;
    }

    final token = ref.read(authControllerProvider).accessToken;
    if (token == null || token.isEmpty) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Session expired. Please login again.')),
      );
      return;
    }

    setState(() {
      _isCreating = true;
    });

    try {
      await ref.read(teacherApiProvider).createCompletedLecture(
            accessToken: token,
            subjectId: payload.subjectId,
            topic: payload.topic,
            classLevel: payload.classLevel,
            batchId: payload.batchId,
            stream: payload.stream,
            summary: payload.summary,
          );

      ref.invalidate(teacherCompletedLecturesProvider);
      ref.invalidate(teacherDashboardProvider);

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Lecture marked as done. Students can now raise doubts.'),
          backgroundColor: Color(0xFF166534),
        ),
      );
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Could not mark lecture done: $error'),
          backgroundColor: const Color(0xFFB91C1C),
        ),
      );
    } finally {
      if (mounted) {
        setState(() {
          _isCreating = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final assignmentsAsync = ref.watch(teacherAssignmentsProvider);
    final scheduledAsync = ref.watch(teacherScheduledLecturesProvider);
    final completedAsync = ref.watch(teacherCompletedLecturesProvider);

    return assignmentsAsync.when(
      loading: () => const TeacherLoadingView(),
      error: (error, _) => TeacherErrorView(
        title: 'Failed to load assignments',
        message: error.toString(),
        onRetry: () => ref.invalidate(teacherAssignmentsProvider),
      ),
      data: (assignments) {
        return completedAsync.when(
          loading: () => _AssignmentsBody(
            assignments: assignments,
            completedLectures: const [],
            scheduledLectures: const [],
            isCreating: _isCreating,
            loadingCompleted: true,
            onRefresh: _refreshAll,
            onOpenLectureDone: () => _openLectureDoneSheet(assignments),
          ),
          error: (error, _) => _AssignmentsBody(
            assignments: assignments,
            completedLectures: const [],
            scheduledLectures: const [],
            isCreating: _isCreating,
            completedError: error.toString(),
            onRefresh: _refreshAll,
            onOpenLectureDone: () => _openLectureDoneSheet(assignments),
          ),
          data: (completedLectures) => scheduledAsync.when(
            loading: () => _AssignmentsBody(
              assignments: assignments,
              completedLectures: completedLectures,
              scheduledLectures: const [],
              isCreating: _isCreating,
              loadingScheduled: true,
              onRefresh: _refreshAll,
              onOpenLectureDone: () => _openLectureDoneSheet(assignments),
            ),
            error: (error, _) => _AssignmentsBody(
              assignments: assignments,
              completedLectures: completedLectures,
              scheduledLectures: const [],
              isCreating: _isCreating,
              scheduledError: error.toString(),
              onRefresh: _refreshAll,
              onOpenLectureDone: () => _openLectureDoneSheet(assignments),
            ),
            data: (scheduledLectures) => _AssignmentsBody(
              assignments: assignments,
              completedLectures: completedLectures,
              scheduledLectures: scheduledLectures,
              isCreating: _isCreating,
              onRefresh: _refreshAll,
              onOpenLectureDone: () => _openLectureDoneSheet(assignments),
            ),
          ),
        );
      },
    );
  }
}

class _AssignmentsBody extends StatelessWidget {
  const _AssignmentsBody({
    required this.assignments,
    required this.completedLectures,
    required this.scheduledLectures,
    required this.isCreating,
    required this.onRefresh,
    required this.onOpenLectureDone,
    this.loadingCompleted = false,
    this.completedError,
    this.loadingScheduled = false,
    this.scheduledError,
  });

  final List<TeacherAssignment> assignments;
  final List<TeacherCompletedLecture> completedLectures;
  final List<TeacherScheduledLecture> scheduledLectures;
  final bool isCreating;
  final Future<void> Function() onRefresh;
  final VoidCallback onOpenLectureDone;
  final bool loadingCompleted;
  final String? completedError;
  final bool loadingScheduled;
  final String? scheduledError;

  @override
  Widget build(BuildContext context) {
    return TeacherGradientBackground(
      child: RefreshIndicator(
        color: TeacherPalette.oceanBlue,
        onRefresh: onRefresh,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.fromLTRB(16, 14, 16, 20),
          children: [
            TeacherEntrance(
              delay: teacherStagger(0),
              child: const TeacherScreenHeader(
                title: 'Assignments',
                subtitle:
                    'Mark lectures completed so students can open and raise doubts.',
                icon: Icons.assignment_outlined,
              ),
            ),
            TeacherEntrance(
              delay: teacherStagger(1),
              child: TeacherSurfaceCard(
                margin: const EdgeInsets.only(bottom: 12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Lecture Done Studio',
                      style: TextStyle(
                        color: TeacherPalette.textDark,
                        fontWeight: FontWeight.w700,
                        fontSize: 16,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      assignments.isEmpty
                          ? 'No mapped classes found yet. Ask admin to assign batches/subjects.'
                          : 'Publish completed lecture topic for your class in one tap.',
                      style: TextStyle(
                        color: TeacherPalette.textDark.withValues(alpha: 0.75),
                      ),
                    ),
                    const SizedBox(height: 12),
                    TeacherTapScale(
                      borderRadius: BorderRadius.circular(12),
                      onTap: isCreating ? null : onOpenLectureDone,
                      child: FilledButton.icon(
                        onPressed: isCreating ? null : onOpenLectureDone,
                        style: FilledButton.styleFrom(
                          backgroundColor: TeacherPalette.oceanBlue,
                          foregroundColor: TeacherPalette.white,
                          minimumSize: const Size.fromHeight(46),
                        ),
                        icon: isCreating
                            ? const SizedBox(
                                width: 16,
                                height: 16,
                                child: CircularProgressIndicator(strokeWidth: 2),
                              )
                            : const Icon(Icons.task_alt_outlined),
                        label: Text(
                          isCreating
                              ? 'Saving Lecture...'
                              : 'Mark Lecture Done',
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            TeacherEntrance(
              delay: teacherStagger(2),
              child: const _SectionTitle(
                title: 'Upcoming Scheduled Lectures',
                icon: Icons.schedule_outlined,
              ),
            ),
            if (loadingScheduled)
              TeacherEntrance(
                delay: teacherStagger(3),
                child: const TeacherSurfaceCard(
                  margin: EdgeInsets.only(bottom: 12),
                  child: Text(
                    'Loading scheduled lectures...',
                    style: TextStyle(color: TeacherPalette.textDark),
                  ),
                ),
              )
            else if (scheduledError != null)
              TeacherEntrance(
                delay: teacherStagger(3),
                child: TeacherSurfaceCard(
                  margin: const EdgeInsets.only(bottom: 12),
                  child: Text(
                    scheduledError!,
                    style: const TextStyle(color: Color(0xFFB91C1C)),
                  ),
                ),
              )
            else if (scheduledLectures.isEmpty)
              TeacherEntrance(
                delay: teacherStagger(3),
                child: const TeacherSurfaceCard(
                  margin: EdgeInsets.only(bottom: 12),
                  child: Text(
                    'No upcoming lectures from admin schedule yet.',
                    style: TextStyle(color: TeacherPalette.textDark),
                  ),
                ),
              )
            else
              ...scheduledLectures.asMap().entries.map((entry) {
                final index = entry.key;
                final lecture = entry.value;
                return TeacherEntrance(
                  delay: teacherStagger(index + 3),
                  child: _ScheduledLectureCard(lecture: lecture),
                );
              }),
            const SizedBox(height: 6),
            TeacherEntrance(
              delay: teacherStagger(8),
              child: const _SectionTitle(
                title: 'Recent Completed Lectures',
                icon: Icons.history_edu,
              ),
            ),
            if (loadingCompleted)
              TeacherEntrance(
                delay: teacherStagger(3),
                child: const TeacherSurfaceCard(
                  margin: EdgeInsets.only(bottom: 12),
                  child: Text(
                    'Loading completed lectures...',
                    style: TextStyle(color: TeacherPalette.textDark),
                  ),
                ),
              )
            else if (completedError != null)
              TeacherEntrance(
                delay: teacherStagger(3),
                child: TeacherSurfaceCard(
                  margin: const EdgeInsets.only(bottom: 12),
                  child: Text(
                    completedError!,
                    style: const TextStyle(color: Color(0xFFB91C1C)),
                  ),
                ),
              )
            else if (completedLectures.isEmpty)
              TeacherEntrance(
                delay: teacherStagger(3),
                child: const TeacherSurfaceCard(
                  margin: EdgeInsets.only(bottom: 12),
                  child: Text(
                    'No completed lectures yet. Start by marking one lecture done.',
                    style: TextStyle(color: TeacherPalette.textDark),
                  ),
                ),
              )
            else
              ...completedLectures.asMap().entries.map((entry) {
                final index = entry.key;
                final lecture = entry.value;
                return TeacherEntrance(
                  delay: teacherStagger(index + 3),
                  child: _CompletedLectureCard(lecture: lecture),
                );
              }),
            const SizedBox(height: 6),
            TeacherEntrance(
              delay: teacherStagger(9),
              child: const _SectionTitle(
                title: 'Your Subject Assignments',
                icon: Icons.menu_book_outlined,
              ),
            ),
            if (assignments.isEmpty)
              TeacherEntrance(
                delay: teacherStagger(10),
                child: const TeacherSurfaceCard(
                  child: Text(
                    'No assignments found yet.',
                    style: TextStyle(color: TeacherPalette.textDark),
                  ),
                ),
              )
            else
              ...assignments.asMap().entries.map(
                (entry) {
                  final index = entry.key;
                  final item = entry.value;
                  return TeacherEntrance(
                    delay: teacherStagger(index + 10),
                    child: TeacherSurfaceCard(
                      margin: const EdgeInsets.only(bottom: 10),
                      child: Row(
                        children: [
                          Container(
                            width: 42,
                            height: 42,
                            decoration: BoxDecoration(
                              borderRadius: BorderRadius.circular(12),
                              gradient: const LinearGradient(
                                begin: Alignment.topLeft,
                                end: Alignment.bottomRight,
                                colors: [
                                  TeacherPalette.oceanBlue,
                                  TeacherPalette.violet,
                                ],
                              ),
                            ),
                            child: const Icon(
                              Icons.menu_book_outlined,
                              color: TeacherPalette.white,
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  item.subjectName,
                                  style: const TextStyle(
                                    fontSize: 16,
                                    fontWeight: FontWeight.w700,
                                    color: TeacherPalette.textDark,
                                  ),
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  '${item.standardName} • Batch ${item.batchName}',
                                  style: TextStyle(
                                    color: TeacherPalette.textDark
                                        .withValues(alpha: 0.72),
                                  ),
                                ),
                              ],
                            ),
                          ),
                          const Icon(
                            Icons.check_circle_outline,
                            size: 18,
                            color: Color(0xFF0F766E),
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
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle({
    required this.title,
    required this.icon,
  });

  final String title;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        children: [
          Icon(icon, color: TeacherPalette.white, size: 18),
          const SizedBox(width: 8),
          Text(
            title,
            style: const TextStyle(
              color: TeacherPalette.white,
              fontSize: 15,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}

class _ScheduledLectureCard extends StatelessWidget {
  const _ScheduledLectureCard({required this.lecture});

  final TeacherScheduledLecture lecture;

  String _formatDateTime(DateTime? value) {
    if (value == null) {
      return 'Not scheduled';
    }
    final month = value.month.toString().padLeft(2, '0');
    final day = value.day.toString().padLeft(2, '0');
    final hour = value.hour.toString().padLeft(2, '0');
    final minute = value.minute.toString().padLeft(2, '0');
    return '$day/$month/${value.year} $hour:$minute';
  }

  String _scopeText() {
    final classPart = 'Class ${lecture.classLevel}';
    final normalizedStream = lecture.stream.trim().toLowerCase();
    if (normalizedStream.isEmpty || normalizedStream == 'common') {
      return classPart;
    }
    return '$classPart • ${_capitalize(normalizedStream)}';
  }

  String _capitalize(String value) {
    if (value.isEmpty) {
      return value;
    }
    return '${value[0].toUpperCase()}${value.substring(1)}';
  }

  @override
  Widget build(BuildContext context) {
    return TeacherSurfaceCard(
      margin: const EdgeInsets.only(bottom: 10),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(12),
              color: const Color(0xFFD9F2FF),
            ),
            child: const Icon(
              Icons.schedule_outlined,
              color: TeacherPalette.deepOcean,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  lecture.topic,
                  style: const TextStyle(
                    color: TeacherPalette.textDark,
                    fontWeight: FontWeight.w700,
                    fontSize: 15,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  lecture.subjectName.isEmpty
                      ? _scopeText()
                      : '${lecture.subjectName} • ${_scopeText()}',
                  style: TextStyle(
                    color: TeacherPalette.textDark.withValues(alpha: 0.74),
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  'Scheduled: ${_formatDateTime(lecture.scheduledAt)}',
                  style: TextStyle(
                    color: TeacherPalette.textDark.withValues(alpha: 0.66),
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _CompletedLectureCard extends StatelessWidget {

  const _CompletedLectureCard({required this.lecture});

  final TeacherCompletedLecture lecture;

  String _formatDateTime(DateTime? value) {
    if (value == null) {
      return 'Not available';
    }
    final month = value.month.toString().padLeft(2, '0');
    final day = value.day.toString().padLeft(2, '0');
    final hour = value.hour.toString().padLeft(2, '0');
    final minute = value.minute.toString().padLeft(2, '0');
    return '$day/$month/${value.year} $hour:$minute';
  }

  String _scopeText() {
    final classPart = lecture.classLevel == null
        ? 'Class —'
        : 'Class ${lecture.classLevel}';
    final normalizedStream = lecture.stream.trim().toLowerCase();
    if (normalizedStream.isEmpty || normalizedStream == 'common') {
      return classPart;
    }
    return '$classPart • ${_capitalize(normalizedStream)}';
  }

  String _capitalize(String value) {
    if (value.isEmpty) {
      return value;
    }
    return '${value[0].toUpperCase()}${value.substring(1)}';
  }

  @override
  Widget build(BuildContext context) {
    return TeacherSurfaceCard(
      margin: const EdgeInsets.only(bottom: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 42,
                height: 42,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(12),
                  color: const Color(0xFFDDEBFF),
                ),
                child: const Icon(
                  Icons.task_alt_outlined,
                  color: TeacherPalette.deepOcean,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      lecture.topic,
                      style: const TextStyle(
                        color: TeacherPalette.textDark,
                        fontWeight: FontWeight.w700,
                        fontSize: 15,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      lecture.subjectName.isEmpty
                          ? _scopeText()
                          : '${lecture.subjectName} • ${_scopeText()}',
                      style: TextStyle(
                        color: TeacherPalette.textDark.withValues(alpha: 0.74),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          if (lecture.summary.trim().isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              lecture.summary,
              style: TextStyle(
                color: TeacherPalette.textDark.withValues(alpha: 0.78),
              ),
            ),
          ],
          const SizedBox(height: 8),
          Text(
            'Completed: ${_formatDateTime(lecture.completedAt)}',
            style: TextStyle(
              color: TeacherPalette.textDark.withValues(alpha: 0.64),
              fontSize: 12,
            ),
          ),
        ],
      ),
    );
  }
}

class _CreateLecturePayload {
  const _CreateLecturePayload({
    required this.subjectId,
    required this.batchId,
    required this.classLevel,
    required this.stream,
    required this.topic,
    required this.summary,
  });

  final String subjectId;
  final String? batchId;
  final int classLevel;
  final String? stream;
  final String topic;
  final String? summary;
}

class _CreateLectureSheet extends StatefulWidget {
  const _CreateLectureSheet({required this.assignments});

  final List<TeacherAssignment> assignments;

  @override
  State<_CreateLectureSheet> createState() => _CreateLectureSheetState();
}

class _CreateLectureSheetState extends State<_CreateLectureSheet> {
  final TextEditingController _topicController = TextEditingController();
  final TextEditingController _summaryController = TextEditingController();

  late TeacherAssignment _selectedAssignment;
  int _classLevel = 10;
  String _stream = 'science';
  String? _error;

  @override
  void initState() {
    super.initState();
    _selectedAssignment = widget.assignments.first;
    _syncAcademicFromAssignment(_selectedAssignment);
  }

  @override
  void dispose() {
    _topicController.dispose();
    _summaryController.dispose();
    super.dispose();
  }

  int _extractClassLevel(String standardName) {
    final match = RegExp(r'(10|11|12)').firstMatch(standardName);
    final parsed = int.tryParse(match?.group(1) ?? '');
    if (parsed == null || parsed < 10 || parsed > 12) {
      return 10;
    }
    return parsed;
  }

  String _defaultStreamFor(int classLevel, String standardName) {
    if (classLevel == 10) {
      return 'common';
    }
    final lower = standardName.toLowerCase();
    if (lower.contains('commerce')) {
      return 'commerce';
    }
    return 'science';
  }

  void _syncAcademicFromAssignment(TeacherAssignment assignment) {
    final classLevel = _extractClassLevel(assignment.standardName);
    final stream = _defaultStreamFor(classLevel, assignment.standardName);
    setState(() {
      _classLevel = classLevel;
      _stream = stream;
      _error = null;
    });
  }

  void _submit() {
    final topic = _topicController.text.trim();
    final summary = _summaryController.text.trim();

    if (topic.length < 2) {
      setState(() {
        _error = 'Topic must be at least 2 characters.';
      });
      return;
    }

    if (_classLevel > 10 && _stream.trim().isEmpty) {
      setState(() {
        _error = 'Please select stream for class $_classLevel.';
      });
      return;
    }

    final payload = _CreateLecturePayload(
      subjectId: _selectedAssignment.subjectId,
      batchId: _selectedAssignment.batchId,
      classLevel: _classLevel,
      stream: _classLevel == 10 ? null : _stream,
      topic: topic,
      summary: summary.isEmpty ? null : summary,
    );

    Navigator.of(context).pop(payload);
  }

  @override
  Widget build(BuildContext context) {
    final bottomInset = MediaQuery.of(context).viewInsets.bottom;

    return SafeArea(
      top: false,
      child: Padding(
        padding: EdgeInsets.fromLTRB(16, 14, 16, bottomInset + 16),
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text(
                'Mark Lecture Done',
                style: TextStyle(
                  fontWeight: FontWeight.w700,
                  fontSize: 18,
                  color: TeacherPalette.textDark,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                'This will be visible to students in Raise Doubt lecture list.',
                style: TextStyle(
                  color: TeacherPalette.textDark.withValues(alpha: 0.7),
                ),
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<TeacherAssignment>(
                initialValue: _selectedAssignment,
                decoration: const InputDecoration(
                  labelText: 'Assignment',
                  border: OutlineInputBorder(),
                ),
                items: widget.assignments
                    .map(
                      (assignment) => DropdownMenuItem<TeacherAssignment>(
                        value: assignment,
                        child: Text(
                          '${assignment.subjectName} • ${assignment.standardName} (${assignment.batchName})',
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    )
                    .toList(growable: false),
                onChanged: (value) {
                  if (value == null) {
                    return;
                  }
                  _selectedAssignment = value;
                  _syncAcademicFromAssignment(value);
                },
              ),
              const SizedBox(height: 10),
              Row(
                children: [
                  Expanded(
                    child: DropdownButtonFormField<int>(
                      initialValue: _classLevel,
                      decoration: const InputDecoration(
                        labelText: 'Class',
                        border: OutlineInputBorder(),
                      ),
                      items: const [
                        DropdownMenuItem(value: 10, child: Text('10th')),
                        DropdownMenuItem(value: 11, child: Text('11th')),
                        DropdownMenuItem(value: 12, child: Text('12th')),
                      ],
                      onChanged: (value) {
                        if (value == null) {
                          return;
                        }
                        setState(() {
                          _classLevel = value;
                          if (_classLevel == 10) {
                            _stream = 'common';
                          } else if (_stream == 'common') {
                            _stream = 'science';
                          }
                        });
                      },
                    ),
                  ),
                  if (_classLevel > 10) ...[
                    const SizedBox(width: 10),
                    Expanded(
                      child: DropdownButtonFormField<String>(
                        initialValue: _stream,
                        decoration: const InputDecoration(
                          labelText: 'Stream',
                          border: OutlineInputBorder(),
                        ),
                        items: const [
                          DropdownMenuItem(
                            value: 'science',
                            child: Text('Science'),
                          ),
                          DropdownMenuItem(
                            value: 'commerce',
                            child: Text('Commerce'),
                          ),
                        ],
                        onChanged: (value) {
                          if (value == null) {
                            return;
                          }
                          setState(() {
                            _stream = value;
                          });
                        },
                      ),
                    ),
                  ],
                ],
              ),
              const SizedBox(height: 10),
              TextField(
                controller: _topicController,
                maxLength: 160,
                decoration: const InputDecoration(
                  labelText: 'Lecture Topic',
                  hintText: 'e.g. Quadratic equations revision',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: _summaryController,
                minLines: 3,
                maxLines: 5,
                maxLength: 600,
                decoration: const InputDecoration(
                  labelText: 'Lecture Summary (optional)',
                  border: OutlineInputBorder(),
                ),
              ),
              if (_error != null) ...[
                const SizedBox(height: 6),
                Text(
                  _error!,
                  style: const TextStyle(
                    color: Color(0xFFB91C1C),
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
              const SizedBox(height: 10),
              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  onPressed: _submit,
                  icon: const Icon(Icons.task_alt),
                  style: FilledButton.styleFrom(
                    backgroundColor: TeacherPalette.oceanBlue,
                    foregroundColor: TeacherPalette.white,
                    minimumSize: const Size.fromHeight(46),
                  ),
                  label: const Text('Publish Completed Lecture'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
