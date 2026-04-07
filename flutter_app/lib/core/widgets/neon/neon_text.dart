import 'package:flutter/material.dart';

import '../../constants/colors.dart';
import '../../constants/typography.dart';

class NeonText extends StatelessWidget {
  final String text;
  final Color color;
  final TextStyle? style;

  const NeonText(
    this.text, {
    super.key,
    this.color = AppColors.neonCyan,
    this.style,
  });

  @override
  Widget build(BuildContext context) {
    final base = style ?? AppTypography.displayMedium;
    return Text(
      text,
      style: base.copyWith(
        color: color,
        shadows: [
          Shadow(color: color.withOpacity(0.7), blurRadius: 14),
          Shadow(color: color.withOpacity(0.3), blurRadius: 26),
        ],
      ),
    );
  }
}
