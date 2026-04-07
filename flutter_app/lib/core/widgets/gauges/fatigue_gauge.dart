import 'package:flutter/material.dart';

import '../../constants/colors.dart';
import '../../constants/typography.dart';
import '../glass/glass_container.dart';

class FatigueGauge extends StatelessWidget {
  final double level;
  final Duration duration;

  const FatigueGauge({
    super.key,
    required this.level,
    required this.duration,
  });

  @override
  Widget build(BuildContext context) {
    final value = level.clamp(0.0, 1.0);
    final color = value < 0.4
        ? AppColors.safe
        : value < 0.7
            ? AppColors.warning
            : AppColors.danger;

    return GlassContainer(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text('FATIGUE', style: AppTypography.label),
              const Spacer(),
              Text('${(value * 100).toInt()}%', style: AppTypography.bodyLarge),
            ],
          ),
          const SizedBox(height: 10),
          ClipRRect(
            borderRadius: BorderRadius.circular(6),
            child: LinearProgressIndicator(
              minHeight: 10,
              value: value,
              backgroundColor: AppColors.surfaceDark,
              valueColor: AlwaysStoppedAnimation<Color>(color),
            ),
          ),
          const SizedBox(height: 10),
          Text(
            'Ride duration: ${duration.inMinutes} min',
            style: AppTypography.bodyMedium,
          ),
        ],
      ),
    );
  }
}
