import 'package:flutter/material.dart';

class FatigueGauge extends StatelessWidget {
  final int level; // 1-4

  const FatigueGauge({super.key, required this.level});

  Color get _color {
    switch (level) {
      case 1: return const Color(0xFF00C8A0);
      case 2: return const Color(0xFFFFB347);
      case 3: return const Color(0xFFFF6B35);
      case 4: return Colors.redAccent;
      default: return Colors.grey;
    }
  }

  String get _label {
    switch (level) {
      case 1: return 'Fresh';
      case 2: return 'Moderate';
      case 3: return 'Tired';
      case 4: return 'Critical';
      default: return 'Unknown';
    }
  }

  @override
  Widget build(BuildContext context) {
    return Row(children: [
      ...List.generate(4, (i) {
        final filled = i < level;
        return Expanded(
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 400),
            margin: const EdgeInsets.symmetric(horizontal: 3),
            height: 12,
            decoration: BoxDecoration(
              color: filled ? _color : Colors.white12,
              borderRadius: BorderRadius.circular(6),
              boxShadow: filled
                  ? [BoxShadow(color: _color.withOpacity(0.5), blurRadius: 6)]
                  : null,
            ),
          ),
        );
      }),
      const SizedBox(width: 12),
      Text(_label, style: TextStyle(color: _color, fontWeight: FontWeight.w700, fontSize: 13)),
    ]);
  }
}
