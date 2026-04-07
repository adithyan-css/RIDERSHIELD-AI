import 'package:flutter/material.dart';

class AppColors {
  // Primary neon palette
  static const Color neonCyan = Color(0xFF00E5B8);
  static const Color neonBlue = Color(0xFF4DA6FF);
  static const Color neonOrange = Color(0xFFFF6B35);
  static const Color neonRed = Color(0xFFFF2D55);

  // Dark backgrounds
  static const Color deepBlack = Color(0xFF060A0D);
  static const Color surfaceDark = Color(0xFF0F161E);
  static const Color surfaceElevated = Color(0xFF1A2332);

  // Glass effects
  static const Color glassWhite = Colors.white;
  static const Color glassOverlay = Color(0x20FFFFFF);
  static const Color glassBorder = Color(0x40FFFFFF);

  // Semantic colors
  static const Color safe = neonCyan;
  static const Color warning = neonOrange;
  static const Color danger = neonRed;
  static const Color info = neonBlue;

  static const LinearGradient neonGradient = LinearGradient(
    colors: [neonCyan, neonBlue],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient dangerGradient = LinearGradient(
    colors: [neonOrange, neonRed],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );
}
