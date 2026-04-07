import 'package:flutter/material.dart';

import '../../constants/colors.dart';
import '../../constants/typography.dart';

enum RiskLevelView { low, medium, high }

class RiskIndicator extends StatelessWidget {
  final RiskLevelView level;

  const RiskIndicator({
    super.key,
    required this.level,
  });

  @override
  Widget build(BuildContext context) {
    final data = switch (level) {
      RiskLevelView.low => ('LOW', AppColors.safe),
      RiskLevelView.medium => ('MEDIUM', AppColors.warning),
      RiskLevelView.high => ('HIGH', AppColors.danger),
    };

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: data.$2.withOpacity(0.15),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: data.$2.withOpacity(0.5)),
      ),
      child: Text(
        'RISK: ${data.$1}',
        style: AppTypography.label.copyWith(color: data.$2),
      ),
    );
  }
}
