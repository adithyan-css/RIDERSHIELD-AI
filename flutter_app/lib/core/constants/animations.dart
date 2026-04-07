import 'package:flutter/animation.dart';

class AppAnimations {
  static const Duration fast = Duration(milliseconds: 180);
  static const Duration medium = Duration(milliseconds: 320);
  static const Duration slow = Duration(milliseconds: 700);

  static const Duration glowPulse = Duration(milliseconds: 1500);
  static const Duration alertPulse = Duration(milliseconds: 900);
  static const Duration floating = Duration(milliseconds: 2200);

  static const Curve emphasized = Curves.easeOutCubic;
  static const Curve smooth = Curves.easeInOut;
  static const Curve spring = Curves.elasticOut;
}
