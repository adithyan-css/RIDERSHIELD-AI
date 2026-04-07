import 'package:flutter/material.dart';

extension BuildContextX on BuildContext {
  Size get screenSize => MediaQuery.of(this).size;
  double get width => screenSize.width;
  double get height => screenSize.height;
}

extension DurationX on num {
  Duration get ms => Duration(milliseconds: round());
}

extension PercentOpacityX on Color {
  Color withPercentOpacity(double value) {
    final clamped = value.clamp(0.0, 1.0);
    return withOpacity(clamped);
  }
}
