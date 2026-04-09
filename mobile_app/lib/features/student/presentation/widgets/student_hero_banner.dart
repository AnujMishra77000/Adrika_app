import 'package:flutter/material.dart';

import 'student_home_palette.dart';

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
            StudentHomePalette.bannerTop,
            StudentHomePalette.bannerBottom,
          ],
        ),
        boxShadow: [
          BoxShadow(
            color: StudentHomePalette.bannerGlow.withValues(alpha: 0.28),
            blurRadius: 26,
            spreadRadius: -4,
            offset: const Offset(0, 14),
          ),
        ],
      ),
      child: Stack(
        children: [
          Positioned(
            right: -20,
            top: -30,
            child: Container(
              width: 130,
              height: 130,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: StudentHomePalette.accentPurple.withValues(alpha: 0.16),
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
      color: Colors.white.withValues(alpha: 0.06),
      borderRadius: BorderRadius.circular(16),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Ink(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: Colors.white.withValues(alpha: 0.12),
            ),
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                data.accent.withValues(alpha: 0.18),
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
                      color: StudentHomePalette.textSecondaryOnDark,
                    ),
                  ],
                ),
                const Spacer(),
                Text(
                  data.value,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        color: StudentHomePalette.textPrimaryOnDark,
                        fontWeight: FontWeight.w700,
                      ),
                ),
                const SizedBox(height: 2),
                Text(
                  data.title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: StudentHomePalette.textPrimaryOnDark,
                        fontWeight: FontWeight.w600,
                      ),
                ),
                Text(
                  data.subtitle,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: StudentHomePalette.textSecondaryOnDark,
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
