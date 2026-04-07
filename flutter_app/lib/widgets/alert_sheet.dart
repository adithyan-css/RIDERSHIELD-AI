import 'package:flutter/material.dart';

class AlertSheet extends StatelessWidget {
  final Map<String, dynamic> alert;
  const AlertSheet({super.key, required this.alert});

  String get _hazardType =>
      (alert['hazard_type'] ?? alert['hazard_class'] ?? 'hazard').toString();

  Color get _color {
    switch (_hazardType) {
      case 'flood': return const Color(0xFF3B8BD4);
      case 'pothole': return const Color(0xFFFF6B35);
      case 'rough': return const Color(0xFFFFB347);
      default: return Colors.orangeAccent;
    }
  }

  IconData get _icon {
    switch (_hazardType) {
      case 'flood': return Icons.water;
      case 'pothole': return Icons.report_problem;
      case 'rough': return Icons.terrain;
      default: return Icons.warning;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      decoration: BoxDecoration(
        color: const Color(0xF00D1526),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: _color.withOpacity(0.6), width: 1.5),
        boxShadow: [BoxShadow(color: _color.withOpacity(0.2), blurRadius: 20)],
      ),
      child: Row(children: [
        Container(
          width: 42, height: 42,
          decoration: BoxDecoration(color: _color.withOpacity(0.15), shape: BoxShape.circle),
          child: Icon(_icon, color: _color, size: 22),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(
              '⚠️ ${_hazardType.toUpperCase()} AHEAD',
              style: TextStyle(color: _color, fontWeight: FontWeight.w700, fontSize: 13),
            ),
            Text(
              '${alert['distance_m'] ?? '?'}m away · ${((alert['confidence'] ?? 0) * 100).toStringAsFixed(0)}% confidence',
              style: const TextStyle(color: Colors.white70, fontSize: 12),
            ),
          ]),
        ),
        Icon(Icons.volume_up, color: _color, size: 20),
      ]),
    );
  }
}
