import 'package:flutter/material.dart';

import 'glass_container.dart';

class GlassBottomSheet extends StatelessWidget {
  final Widget child;

  const GlassBottomSheet({
    super.key,
    required this.child,
  });

  @override
  Widget build(BuildContext context) {
    return GlassContainer(
      borderRadius: 24,
      padding: const EdgeInsets.all(16),
      child: child,
    );
  }
}
