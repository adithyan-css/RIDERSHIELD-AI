import 'package:flutter/material.dart';

import '../../core/widgets/animations/alert_pulse.dart';
import '../../data/models/hazard.dart';
import 'hazard_alert_card.dart';

class MapOverlays extends StatelessWidget {
  final List<Alert> alerts;

  const MapOverlays({
    super.key,
    required this.alerts,
  });

  @override
  Widget build(BuildContext context) {
    if (alerts.isEmpty) {
      return const SizedBox.shrink();
    }

    final alert = alerts.first;

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        const AlertPulse(
          child: Icon(
            Icons.warning_rounded,
            size: 44,
            color: Colors.white,
          ),
        ),
        const SizedBox(height: 12),
        HazardAlertCard(
          title: alert.title,
          subtitle: alert.description,
          severity: alert.severity,
        ),
      ],
    );
  }
}
