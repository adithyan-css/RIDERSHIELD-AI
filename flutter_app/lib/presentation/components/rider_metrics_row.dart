import 'package:flutter/material.dart';

import '../../core/widgets/gauges/fatigue_gauge.dart';
import '../../core/widgets/gauges/risk_indicator.dart';
import '../../core/widgets/gauges/speedometer.dart';

class RiderMetricsRow extends StatelessWidget {
  final double speedKmh;
  final int fatigueLevel;
  final RiskLevelView riskLevel;

  const RiderMetricsRow({
    super.key,
    required this.speedKmh,
    required this.fatigueLevel,
    required this.riskLevel,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Speedometer(speed: speedKmh, size: 180),
        const SizedBox(height: 16),
        FatigueGauge(
          level: fatigueLevel.clamp(0, 100) / 100,
          duration: const Duration(minutes: 42),
        ),
        const SizedBox(height: 12),
        RiskIndicator(level: riskLevel),
      ],
    );
  }
}
