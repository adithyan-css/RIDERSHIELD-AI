import 'package:flutter/material.dart';

import '../../core/constants/colors.dart';
import '../../core/constants/typography.dart';
import '../../core/widgets/glass/glass_card.dart';
import '../../core/widgets/neon/neon_text.dart';
import '../../data/models/hazard.dart';

class HazardAlertCard extends StatelessWidget {
  final String title;
  final String subtitle;
  final Severity severity;

  const HazardAlertCard({
    super.key,
    required this.title,
    required this.subtitle,
    required this.severity,
  });

  @override
  Widget build(BuildContext context) {
    final tone = switch (severity) {
      Severity.low => AppColors.safe,
      Severity.medium => AppColors.warning,
      Severity.high => AppColors.neonOrange,
      Severity.critical => AppColors.danger,
    };

    return GlassCard(
      variant: GlassCardVariant.high,
      child: Row(
        children: [
          Container(
            width: 10,
            height: 52,
            decoration: BoxDecoration(
              color: tone,
              borderRadius: BorderRadius.circular(8),
              boxShadow: [
                BoxShadow(color: tone.withOpacity(0.8), blurRadius: 18),
              ],
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                NeonText(
                  title,
                  color: tone,
                  style: AppTypography.bodyLarge,
                ),
                const SizedBox(height: 4),
                Text(subtitle, style: AppTypography.bodyMedium),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
