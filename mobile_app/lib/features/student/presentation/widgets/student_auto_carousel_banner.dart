import "dart:async";

import "package:flutter/material.dart";

import "../../../../core/config/app_env.dart";

class StudentCarouselBannerItem {
  const StudentCarouselBannerItem({
    required this.id,
    required this.title,
    required this.imageUrl,
    this.actionRoute,
  });

  final String id;
  final String title;
  final String imageUrl;
  final String? actionRoute;
}

class StudentAutoCarouselBanner extends StatefulWidget {
  const StudentAutoCarouselBanner({
    super.key,
    required this.items,
    required this.onTap,
  });

  final List<StudentCarouselBannerItem> items;
  final ValueChanged<String> onTap;

  @override
  State<StudentAutoCarouselBanner> createState() =>
      _StudentAutoCarouselBannerState();
}

class _StudentAutoCarouselBannerState extends State<StudentAutoCarouselBanner> {
  final PageController _controller = PageController(viewportFraction: 1);
  Timer? _timer;
  int _index = 0;

  @override
  void initState() {
    super.initState();
    _startAutoSlide();
  }

  @override
  void didUpdateWidget(covariant StudentAutoCarouselBanner oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.items.length != widget.items.length) {
      _index = 0;
      _startAutoSlide();
    }
  }

  void _startAutoSlide() {
    _timer?.cancel();
    if (widget.items.length <= 1) {
      return;
    }

    _timer = Timer.periodic(const Duration(seconds: 4), (_) {
      if (!mounted || !_controller.hasClients || widget.items.isEmpty) {
        return;
      }

      final next = (_index + 1) % widget.items.length;
      _controller.animateToPage(
        next,
        duration: const Duration(milliseconds: 420),
        curve: Curves.easeOutCubic,
      );
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (widget.items.isEmpty) {
      return const SizedBox.shrink();
    }

    return Column(
      children: [
        Container(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(24),
            border: Border.all(color: Colors.white.withValues(alpha: 0.20)),
            boxShadow: [
              BoxShadow(
                color: const Color(0xFF0A1F6A).withValues(alpha: 0.34),
                blurRadius: 26,
                spreadRadius: -8,
                offset: const Offset(0, 12),
              ),
            ],
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(24),
            child: AspectRatio(
              aspectRatio: 16 / 9,
              child: PageView.builder(
                controller: _controller,
                itemCount: widget.items.length,
                onPageChanged: (value) {
                  if (!mounted) {
                    return;
                  }
                  setState(() {
                    _index = value;
                  });
                },
                itemBuilder: (context, idx) {
                  final item = widget.items[idx];
                  return _BannerCard(
                    item: item,
                    onTap: () {
                      final route = item.actionRoute?.trim();
                      if (route != null && route.isNotEmpty) {
                        widget.onTap(route);
                        return;
                      }
                      widget.onTap("/student/online-tests");
                    },
                  );
                },
              ),
            ),
          ),
        ),
        const SizedBox(height: 10),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: List<Widget>.generate(
            widget.items.length,
            (idx) => AnimatedContainer(
              duration: const Duration(milliseconds: 220),
              curve: Curves.easeOut,
              margin: const EdgeInsets.symmetric(horizontal: 3),
              width: idx == _index ? 20 : 8,
              height: 8,
              decoration: BoxDecoration(
                color: idx == _index
                    ? const Color(0xFFFFE6A3)
                    : Colors.white.withValues(alpha: 0.42),
                borderRadius: BorderRadius.circular(999),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _BannerCard extends StatelessWidget {
  const _BannerCard({required this.item, required this.onTap});

  final StudentCarouselBannerItem item;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final resolved = AppEnv.resolveServerUrl(item.imageUrl);

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        child: Stack(
          fit: StackFit.expand,
          children: [
            if (resolved != null)
              Image.network(
                resolved,
                fit: BoxFit.cover,
                errorBuilder: (_, __, ___) => const _BannerFallback(),
                loadingBuilder: (context, child, progress) {
                  if (progress == null) {
                    return child;
                  }
                  return const _BannerFallback();
                },
              )
            else
              const _BannerFallback(),
            Container(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [
                    Colors.white.withValues(alpha: 0.22),
                    Colors.transparent,
                    const Color(0xE1121B3F),
                  ],
                  stops: const [0.0, 0.28, 1.0],
                ),
              ),
            ),
            Positioned(
              left: 14,
              right: 14,
              bottom: 14,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    item.title.trim().isEmpty
                        ? "Chapter Wise Test is Live!"
                        : item.title,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          color: Colors.white,
                          fontWeight: FontWeight.w800,
                        ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    "Test your preparation and improve your rank",
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Colors.white.withValues(alpha: 0.86),
                          fontWeight: FontWeight.w500,
                        ),
                  ),
                  const SizedBox(height: 8),
                  FilledButton.icon(
                    onPressed: onTap,
                    icon: const Icon(Icons.play_circle_fill_rounded, size: 18),
                    label: const Text("Start Test Now"),
                    style: FilledButton.styleFrom(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 12,
                        vertical: 9,
                      ),
                      backgroundColor: const Color(0xFF2457E5),
                      foregroundColor: Colors.white,
                      textStyle: const TextStyle(fontWeight: FontWeight.w700),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _BannerFallback extends StatelessWidget {
  const _BannerFallback();

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            Color(0xFF5B2BD9),
            Color(0xFF2B56D8),
            Color(0xFF1A2A5F),
          ],
        ),
      ),
      child: Stack(
        children: [
          Positioned(
            right: -40,
            top: -30,
            child: Container(
              width: 190,
              height: 190,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: Colors.white.withValues(alpha: 0.11),
              ),
            ),
          ),
          Positioned(
            left: -36,
            bottom: -46,
            child: Container(
              width: 150,
              height: 150,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: Colors.white.withValues(alpha: 0.08),
              ),
            ),
          ),
          const Center(
            child: Icon(
              Icons.monitor_heart_rounded,
              size: 56,
              color: Color(0xFFEFF3FF),
            ),
          ),
        ],
      ),
    );
  }
}
