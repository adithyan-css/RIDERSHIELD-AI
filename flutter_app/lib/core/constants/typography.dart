import 'package:flutter/material.dart';

import 'colors.dart';

class AppTypography {
  static const String displayFont = 'Rajdhani';
  static const String bodyFont = 'DM Sans';

  static TextStyle get displayLarge => const TextStyle(
        fontFamily: displayFont,
        fontSize: 48,
        fontWeight: FontWeight.bold,
        color: AppColors.glassWhite,
        letterSpacing: -0.5,
      );

  static TextStyle get displayMedium => const TextStyle(
        fontFamily: displayFont,
        fontSize: 32,
        fontWeight: FontWeight.w600,
        color: AppColors.glassWhite,
      );

  static TextStyle get speedometer => const TextStyle(
        fontFamily: displayFont,
        fontSize: 72,
        fontWeight: FontWeight.bold,
        color: AppColors.neonCyan,
        shadows: [
          Shadow(
            color: AppColors.neonCyan,
            blurRadius: 20,
            offset: Offset(0, 0),
          ),
        ],
      );

  static TextStyle get bodyLarge => const TextStyle(
        fontFamily: bodyFont,
        fontSize: 16,
        fontWeight: FontWeight.w500,
        color: AppColors.glassWhite,
      );

  static TextStyle get bodyMedium => const TextStyle(
        fontFamily: bodyFont,
        fontSize: 14,
        fontWeight: FontWeight.normal,
        color: Color(0xB3FFFFFF),
      );

  static TextStyle get label => const TextStyle(
        fontFamily: bodyFont,
        fontSize: 12,
        fontWeight: FontWeight.w600,
        letterSpacing: 0.5,
        color: AppColors.neonBlue,
      );
}
