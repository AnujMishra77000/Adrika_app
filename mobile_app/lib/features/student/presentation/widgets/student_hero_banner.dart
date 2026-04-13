import "package:flutter/material.dart";

class StudentHeroCardData {
  const StudentHeroCardData({
    required this.title,
    required this.value,
    required this.subtitle,
    required this.route,
    required this.icon,
    required this.accent,
  });

  final String title;
  final String value;
  final String subtitle;
  final String route;
  final IconData icon;
  final Color accent;
}

class StudentHeroBanner extends StatelessWidget {
  const StudentHeroBanner({
    super.key,
    required this.cards,
    required this.onCardTap,
  });

  final List<StudentHeroCardData> cards;
  final ValueChanged<String> onCardTap;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(24),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            Color(0xFF24153F),
            Color(0xFF1B1D44),
            Color(0xFF15254E),
          ],
          stops: [0.0, 0.52, 1.0],
        ),
        border: Border.all(color: const Color(0xFFFFE698), width: 1.6),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFFFFD96A).withValues(alpha: 0.32),
            blurRadius: 28,
            spreadRadius: -6,
            offset: const Offset(0, 12),
          ),
          BoxShadow(
            color: const Color(0xFFFFF2C4).withValues(alpha: 0.22),
            blurRadius: 10,
            spreadRadius: -8,
            offset: const Offset(0, -1),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(24),
        child: Stack(
          children: [
            Positioned(
              left: -30,
              top: -80,
              child: _GlowOrb(
                size: 220,
                color: const Color(0xFFFFDA71).withValues(alpha: 0.34),
              ),
            ),
            Positioned(
              right: -26,
              bottom: -62,
              child: _GlowOrb(
                size: 170,
                color: const Color(0xFF5F80FF).withValues(alpha: 0.22),
              ),
            ),
            Positioned(
              left: 0,
              right: 0,
              top: 0,
              child: Container(
                height: 74,
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [
                      const Color(0xFFFFF0C1).withValues(alpha: 0.28),
                      Colors.transparent,
                    ],
                  ),
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(14),
              child: GridView.builder(
                shrinkWrap: true,
                itemCount: cards.length,
                physics: const NeverScrollableScrollPhysics(),
                gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 2,
                  mainAxisSpacing: 10,
                  crossAxisSpacing: 10,
                  childAspectRatio: 1.45,
                ),
                itemBuilder: (context, index) {
                  final card = cards[index];
                  return _HeroQuickCard(
                    data: card,
                    onTap: () => onCardTap(card.route),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _GlowOrb extends StatelessWidget {
  const _GlowOrb({required this.size, required this.color});

  final double size;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: RadialGradient(
          colors: [
            color,
            color.withValues(alpha: 0),
          ],
        ),
      ),
    );
  }
}

class _HeroQuickCard extends StatelessWidget {
  const _HeroQuickCard({
    required this.data,
    required this.onTap,
  });

  final StudentHeroCardData data;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.white.withValues(alpha: 0.04),
      borderRadius: BorderRadius.circular(16),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Ink(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: Colors.white.withValues(alpha: 0.14)),
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                data.accent.withValues(alpha: 0.20),
                Colors.white.withValues(alpha: 0.02),
              ],
            ),
          ),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(data.icon, size: 18, color: data.accent),
                    const Spacer(),
                    const Icon(
                      Icons.arrow_forward_ios_rounded,
                      size: 13,
                      color: Color(0xFFB8B3D9),
                    ),
                  ],
                ),
                const Spacer(),
                Text(
                  data.value,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        color: const Color(0xFFF6F4FF),
                        fontWeight: FontWeight.w800,
                      ),
                ),
                const SizedBox(height: 2),
                Text(
                  data.title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: const Color(0xFFE1DDFF),
                        fontWeight: FontWeight.w700,
                      ),
                ),
                Text(
                  data.subtitle,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: const Color(0xFFAFAAD0),
                      ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
