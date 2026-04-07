import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/constants/colors.dart';
import '../../core/widgets/glass/glass_card.dart';
import '../../data/models/hazard.dart';
import '../components/map_overlays.dart';
import '../providers/alert_provider.dart';

class LiveMapScreen extends ConsumerWidget {
  const LiveMapScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final alertAsync = ref.watch(alertProvider);

    return Scaffold(
      backgroundColor: AppColors.deepBlack,
      body: Stack(
        children: [
          const Positioned.fill(
            child: DecoratedBox(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [Color(0xFF0A1118), Color(0xFF101E2B)],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
              ),
            ),
          ),
          Positioned(
            left: 16,
            right: 16,
            top: 56,
            child: GlassCard(
              child: Row(
                children: const [
                  Icon(Icons.gps_fixed, color: AppColors.neonCyan),
                  SizedBox(width: 8),
                  Text('Live Fleet Map'),
                ],
              ),
            ),
          ),
          Positioned(
            left: 16,
            right: 16,
            bottom: 24,
            child: alertAsync.when(
              data: (alerts) => MapOverlays(
                alerts: alerts
                    .map(
                      (entity) => Alert(
                        title: entity.label,
                        hazardType: HazardType.weather,
                        severity: entity.severity,
                        direction: 'ahead',
                        distance: entity.distance,
                        description: entity.label,
                        hasVoice: true,
                        voiceProgress: 0,
                        suggestsReroute: false,
                        lat: 0,
                        lng: 0,
                        confidence: entity.confidence,
                      ),
                    )
                    .toList(),
              ),
              loading: () => const SizedBox.shrink(),
              error: (_, __) => const SizedBox.shrink(),
            ),
          ),
        ],
      ),
    );
  }
}
