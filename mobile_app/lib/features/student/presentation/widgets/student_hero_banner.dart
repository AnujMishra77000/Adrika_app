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
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            const Color(0xFF102A6B).withValues(alpha: 0.68),
            const Color(0xFF1B4895).withValues(alpha: 0.56),
            const Color(0xFF38A7FF).withValues(alpha: 0.34),
          ],
        ),
        border:
            Border.all(color: Colors.white.withValues(alpha: 0.28), width: 1.1),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF102A6B).withValues(alpha: 0.34),
            blurRadius: 22,
            spreadRadius: -10,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.all(7),
        child: GridView.builder(
          shrinkWrap: true,
          itemCount: cards.length,
          physics: const NeverScrollableScrollPhysics(),
          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: 2,
            mainAxisSpacing: 7,
            crossAxisSpacing: 7,
            childAspectRatio: 1.62,
          ),
          itemBuilder: (context, index) {
            final card = cards[index];
            return _HeroFeatureCard(
              data: card,
              onTap: () => onCardTap(card.route),
            );
          },
        ),
      ),
    );
  }
}

class _HeroFeatureCard extends StatelessWidget {
  const _HeroFeatureCard({
    required this.data,
    required this.onTap,
  });

  final StudentHeroCardData data;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    const gradient = <Color>[
      Color(0xFFF2F7FF),
      Color(0xFFE4EEFF),
    ];

    final accent = data.accent;
    final titleColor = HSLColor.fromColor(accent).withLightness(0.34).toColor();

    return Material(
      color: Colors.transparent,
      borderRadius: BorderRadius.circular(18),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(18),
        child: Ink(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(18),
            gradient: const LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: gradient,
            ),
            border:
                Border.all(color: accent.withValues(alpha: 0.82), width: 1.5),
            boxShadow: [
              BoxShadow(
                color: accent.withValues(alpha: 0.30),
                blurRadius: 14,
                spreadRadius: -5,
                offset: const Offset(0, 6),
              ),
            ],
          ),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(7, 7, 7, 7),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                Container(
                  width: 42,
                  height: 42,
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(13),
                    border: Border.all(
                        color: accent.withValues(alpha: 0.75), width: 1.2),
                    boxShadow: [
                      BoxShadow(
                        color: accent.withValues(alpha: 0.30),
                        blurRadius: 9,
                        spreadRadius: -3,
                        offset: const Offset(0, 4),
                      ),
                    ],
                  ),
                  alignment: Alignment.center,
                  child: Icon(
                    data.icon,
                    size: 24,
                    color: titleColor,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  data.title,
                  textAlign: TextAlign.center,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        color: titleColor,
                        shadows: [
                          Shadow(
                            color: accent.withValues(alpha: 0.22),
                            blurRadius: 5,
                            offset: const Offset(0, 1.5),
                          ),
                        ],
                        fontFamily: "InstrumentSerif",
                        fontFamilyFallback: const [
                          "Canela",
                          "PlayfairDisplay",
                          "Noto Serif",
                          "serif",
                        ],
                        letterSpacing: 0.35,
                        fontWeight: FontWeight.w800,
                        fontSize: 13.5,
                        height: 1.0,
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
