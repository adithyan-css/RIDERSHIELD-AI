import 'package:flutter/material.dart';

import 'glass_container.dart';

enum GlassCardVariant { low, medium, high }

class GlassCard extends StatelessWidget {
  final Widget child;
  final GlassCardVariant variant;
  final EdgeInsets? padding;
  final EdgeInsets? margin;

  const GlassCard({
    super.key,
    required this.child,
    this.variant = GlassCardVariant.medium,
    this.padding,
    this.margin,
  });

  @override
  Widget build(BuildContext context) {
    final config = switch (variant) {
      GlassCardVariant.low => (blur: 12.0, opacity: 0.10),
      GlassCardVariant.medium => (blur: 18.0, opacity: 0.14),
      GlassCardVariant.high => (blur: 24.0, opacity: 0.20),
    };

    return GlassContainer(
      blur: config.blur,
      opacity: config.opacity,
      padding: padding ?? const EdgeInsets.all(16),
      margin: margin ?? EdgeInsets.zero,
      child: child,
    );
  }
}
