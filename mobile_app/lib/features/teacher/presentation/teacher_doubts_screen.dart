import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../auth/state/auth_controller.dart';
import '../data/teacher_api.dart';
import '../models/teacher_models.dart';
import '../state/teacher_providers.dart';
import 'widgets/teacher_ui.dart';

class TeacherDoubtsScreen extends ConsumerWidget {
  const TeacherDoubtsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final doubts = ref.watch(teacherDoubtsProvider);

    return doubts.when(
      data: (items) {
        return TeacherGradientBackground(
          child: RefreshIndicator(
            color: TeacherPalette.oceanBlue,
            onRefresh: () async {
              ref.invalidate(teacherDoubtsProvider);
              await ref.read(teacherDoubtsProvider.future);
            },
            child: ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.fromLTRB(16, 14, 16, 20),
              children: [
                TeacherEntrance(
                  delay: teacherStagger(0),
                  child: const TeacherScreenHeader(
                    title: 'Doubts',
                    subtitle:
                        'Open student conversations, reply quickly, and track closure.',
                    icon: Icons.question_answer_outlined,
                  ),
                ),
                if (items.isEmpty)
                  TeacherEntrance(
                    delay: teacherStagger(1),
                    child: const TeacherSurfaceCard(
                      child: Text(
                        'No active doubt conversations.',
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
                          child: TeacherTapScale(
                            borderRadius: BorderRadius.circular(14),
                            onTap: () async {
                              await Navigator.of(context).push(
                                MaterialPageRoute<void>(
                                  builder: (_) =>
                                      TeacherDoubtThreadScreen(doubtId: item.id),
                                ),
                              );
                              ref.invalidate(teacherDoubtsProvider);
                            },
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
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
                                    Icons.record_voice_over_outlined,
                                    color: TeacherPalette.white,
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
                                              item.topic,
                                              style: const TextStyle(
                                                color: TeacherPalette.textDark,
                                                fontWeight: FontWeight.w700,
                                                fontSize: 16,
                                              ),
                                            ),
                                          ),
                                          TeacherStatusChip(label: item.status),
                                        ],
                                      ),
                                      const SizedBox(height: 4),
                                      Text(
                                        'Student: ${item.studentName}',
                                        style: TextStyle(
                                          color: TeacherPalette.textDark
                                              .withValues(alpha: 0.75),
                                          fontWeight: FontWeight.w600,
                                        ),
                                      ),
                                      if (item.lectureTopic.isNotEmpty) ...[
                                        const SizedBox(height: 4),
                                        Text(
                                          'Lecture: ${item.lectureTopic}',
                                          style: TextStyle(
                                            color: TeacherPalette.textDark
                                                .withValues(alpha: 0.72),
                                          ),
                                        ),
                                      ],
                                    ],
                                  ),
                                ),
                                const SizedBox(width: 6),
                                const Icon(
                                  Icons.arrow_forward_ios,
                                  size: 14,
                                  color: TeacherPalette.deepOcean,
                                ),
                              ],
                            ),
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
        title: 'Failed to load doubts',
        message: error.toString(),
        onRetry: () => ref.invalidate(teacherDoubtsProvider),
      ),
    );
  }
}

class TeacherDoubtThreadScreen extends ConsumerStatefulWidget {
  const TeacherDoubtThreadScreen({
    super.key,
    required this.doubtId,
  });

  final String doubtId;

  @override
  ConsumerState<TeacherDoubtThreadScreen> createState() =>
      _TeacherDoubtThreadScreenState();
}

class _TeacherDoubtThreadScreenState
    extends ConsumerState<TeacherDoubtThreadScreen> {
  final TextEditingController _messageController = TextEditingController();

  TeacherDoubtDetail? _detail;
  bool _isLoading = true;
  bool _isSending = false;
  String? _error;
  Timer? _pollTimer;
  DateTime? _lastMessageAt;

  String? get _token => ref.read(authControllerProvider).accessToken;
  String? get _currentUserId => ref.read(authControllerProvider).userId;

  @override
  void initState() {
    super.initState();
    _loadThread(initial: true);
    _pollTimer = Timer.periodic(const Duration(seconds: 5), (_) {
      _pollNewMessages();
    });
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    _messageController.dispose();
    super.dispose();
  }

  Future<void> _loadThread({required bool initial}) async {
    final token = _token;
    if (token == null || token.isEmpty) {
      if (!mounted) return;
      setState(() {
        _error = 'Session expired. Please login again.';
        _isLoading = false;
      });
      return;
    }

    if (initial) {
      setState(() {
        _isLoading = true;
        _error = null;
      });
    }

    try {
      final detail = await ref.read(teacherApiProvider).fetchDoubtDetail(
            accessToken: token,
            doubtId: widget.doubtId,
          );
      if (!mounted) return;

      final sortedMessages = List<TeacherDoubtMessage>.from(detail.messages)
        ..sort((a, b) {
          final aMs = a.createdAt?.millisecondsSinceEpoch ?? 0;
          final bMs = b.createdAt?.millisecondsSinceEpoch ?? 0;
          return aMs.compareTo(bMs);
        });

      setState(() {
        _detail = TeacherDoubtDetail(
          doubt: detail.doubt,
          description: detail.description,
          messages: sortedMessages,
        );
        _lastMessageAt =
            sortedMessages.isEmpty ? null : sortedMessages.last.createdAt?.toUtc();
        _error = null;
        _isLoading = false;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.toString();
        _isLoading = false;
      });
    }
  }

  Future<void> _pollNewMessages() async {
    final token = _token;
    if (token == null || token.isEmpty || _detail == null) {
      return;
    }

    try {
      final latest = await ref.read(teacherApiProvider).fetchDoubtMessages(
            accessToken: token,
            doubtId: widget.doubtId,
            since: _lastMessageAt,
          );
      if (latest.isEmpty || !mounted) {
        return;
      }

      setState(() {
        final merged = List<TeacherDoubtMessage>.from(_detail!.messages)
          ..addAll(latest);
        merged.sort((a, b) {
          final aMs = a.createdAt?.millisecondsSinceEpoch ?? 0;
          final bMs = b.createdAt?.millisecondsSinceEpoch ?? 0;
          return aMs.compareTo(bMs);
        });

        _detail = TeacherDoubtDetail(
          doubt: _detail!.doubt,
          description: _detail!.description,
          messages: merged,
        );
        _lastMessageAt = merged.last.createdAt?.toUtc();
      });
    } catch (_) {
      // silent polling failure
    }
  }

  Future<void> _sendMessage() async {
    if (_isSending || _detail == null) {
      return;
    }

    final text = _messageController.text.trim();
    if (text.isEmpty) {
      return;
    }

    final token = _token;
    if (token == null || token.isEmpty) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Session expired. Please login again.')),
      );
      return;
    }

    setState(() {
      _isSending = true;
      _error = null;
    });

    try {
      final message = await ref.read(teacherApiProvider).sendDoubtMessage(
            accessToken: token,
            doubtId: widget.doubtId,
            message: text,
          );

      if (!mounted) return;
      setState(() {
        _detail = TeacherDoubtDetail(
          doubt: _detail!.doubt,
          description: _detail!.description,
          messages: [..._detail!.messages, message],
        );
        _lastMessageAt = message.createdAt?.toUtc() ?? _lastMessageAt;
        _messageController.clear();
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.toString();
      });
    } finally {
      if (mounted) {
        setState(() {
          _isSending = false;
        });
      }
    }
  }

  Future<void> _updateStatus(String status) async {
    final token = _token;
    if (token == null || token.isEmpty || _detail == null) {
      return;
    }

    try {
      await ref.read(teacherApiProvider).updateDoubtStatus(
            accessToken: token,
            doubtId: widget.doubtId,
            status: status,
          );

      if (!mounted) return;
      setState(() {
        _detail = TeacherDoubtDetail(
          doubt: TeacherDoubtItem(
            id: _detail!.doubt.id,
            studentId: _detail!.doubt.studentId,
            studentName: _detail!.doubt.studentName,
            lectureId: _detail!.doubt.lectureId,
            lectureTopic: _detail!.doubt.lectureTopic,
            topic: _detail!.doubt.topic,
            status: status,
            priority: _detail!.doubt.priority,
            createdAt: _detail!.doubt.createdAt,
          ),
          description: _detail!.description,
          messages: _detail!.messages,
        );
      });

      await _loadThread(initial: false);
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.toString();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Scaffold(
        body: TeacherLoadingView(),
      );
    }

    if (_detail == null) {
      return Scaffold(
        appBar: AppBar(
          title: const Text('Doubt Thread'),
        ),
        body: TeacherErrorView(
          title: 'Unable to load thread',
          message: _error ?? 'Unknown error occurred.',
          onRetry: () => _loadThread(initial: true),
        ),
      );
    }

    return Scaffold(
      backgroundColor: TeacherPalette.deepOcean,
      appBar: AppBar(
        elevation: 0,
        scrolledUnderElevation: 0,
        backgroundColor: Colors.transparent,
        flexibleSpace: const DecoratedBox(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                TeacherPalette.deepOcean,
                TeacherPalette.oceanBlue,
                TeacherPalette.violet,
              ],
            ),
          ),
        ),
        title: Text(
          _detail!.doubt.topic,
          style: const TextStyle(color: TeacherPalette.white),
        ),
        actions: [
          PopupMenuButton<String>(
            initialValue: _detail!.doubt.status,
            onSelected: _updateStatus,
            itemBuilder: (_) => const [
              PopupMenuItem(value: 'open', child: Text('Open')),
              PopupMenuItem(value: 'in_progress', child: Text('In Progress')),
              PopupMenuItem(value: 'resolved', child: Text('Resolved')),
              PopupMenuItem(value: 'closed', child: Text('Closed')),
            ],
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 14),
              child: Center(
                child: TeacherStatusChip(label: _detail!.doubt.status),
              ),
            ),
          ),
        ],
      ),
      body: TeacherGradientBackground(
        child: Column(
          children: [
            TeacherEntrance(
              delay: teacherStagger(0),
              child: TeacherSurfaceCard(
                margin: const EdgeInsets.fromLTRB(12, 12, 12, 8),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _detail!.doubt.studentName,
                      style: const TextStyle(
                        color: TeacherPalette.textDark,
                        fontWeight: FontWeight.w700,
                        fontSize: 16,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      _detail!.description,
                      style: const TextStyle(color: TeacherPalette.textDark),
                    ),
                    if (_detail!.doubt.lectureTopic.isNotEmpty) ...[
                      const SizedBox(height: 8),
                      Text(
                        'Lecture: ${_detail!.doubt.lectureTopic}',
                        style: TextStyle(
                          color: TeacherPalette.textDark.withValues(alpha: 0.72),
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ),
            Expanded(
              child: ListView.builder(
                padding: const EdgeInsets.fromLTRB(12, 8, 12, 8),
                itemCount: _detail!.messages.length,
                itemBuilder: (context, index) {
                  final item = _detail!.messages[index];
                  final mine =
                      _currentUserId != null && _currentUserId == item.senderUserId;
                  return Align(
                    alignment:
                        mine ? Alignment.centerRight : Alignment.centerLeft,
                    child: AnimatedContainer(
                      duration: const Duration(milliseconds: 220),
                      curve: Curves.easeOut,
                      margin: const EdgeInsets.only(bottom: 8),
                      constraints: const BoxConstraints(maxWidth: 320),
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: mine
                            ? const Color(0xFFDAE9FF)
                            : TeacherPalette.white.withValues(alpha: 0.92),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            item.senderName,
                            style: const TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w700,
                              color: TeacherPalette.deepOcean,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            item.message,
                            style:
                                const TextStyle(color: TeacherPalette.textDark),
                          ),
                        ],
                      ),
                    ),
                  );
                },
              ),
            ),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 12),
                child: Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    _error!,
                    style: const TextStyle(color: Color(0xFFFEE2E2)),
                  ),
                ),
              ),
            SafeArea(
              top: false,
              child: Padding(
                padding: const EdgeInsets.fromLTRB(12, 8, 12, 12),
                child: Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _messageController,
                        minLines: 1,
                        maxLines: 4,
                        style: const TextStyle(color: TeacherPalette.textDark),
                        decoration: InputDecoration(
                          hintText: 'Type reply for student...',
                          hintStyle: TextStyle(
                            color: TeacherPalette.textDark.withValues(alpha: 0.56),
                          ),
                          filled: true,
                          fillColor: TeacherPalette.white.withValues(alpha: 0.95),
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(12),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    TeacherTapScale(
                      borderRadius: BorderRadius.circular(12),
                      onTap: _isSending ? null : _sendMessage,
                      child: FilledButton(
                        style: FilledButton.styleFrom(
                          backgroundColor: TeacherPalette.oceanBlue,
                          foregroundColor: TeacherPalette.white,
                        ),
                        onPressed: _isSending ? null : _sendMessage,
                        child: AnimatedSwitcher(
                          duration: const Duration(milliseconds: 180),
                          switchInCurve: Curves.easeOut,
                          switchOutCurve: Curves.easeIn,
                          child: _isSending
                              ? const SizedBox(
                                  key: ValueKey('sending'),
                                  width: 16,
                                  height: 16,
                                  child: CircularProgressIndicator(strokeWidth: 2),
                                )
                              : const Text(
                                  'Send',
                                  key: ValueKey('send'),
                                ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
