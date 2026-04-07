import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/constants/colors.dart';
import '../../core/constants/typography.dart';
import '../../core/widgets/gauges/risk_indicator.dart';
import '../components/rider_metrics_row.dart';
import '../providers/alert_provider.dart';
import '../providers/rider_provider.dart';

class RiderDashboardScreen extends ConsumerWidget {
  const RiderDashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final riderAsync = ref.watch(riderProvider);
    final alertAsync = ref.watch(alertProvider);

    return Scaffold(
      backgroundColor: AppColors.deepBlack,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        title: Text('Rider Dashboard', style: AppTypography.bodyLarge),
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: riderAsync.when(
            data: (rider) => ListView(
              children: [
                RiderMetricsRow(
                  speedKmh: rider.speedKmh,
                  fatigueLevel: rider.fatigueLevel,
                  riskLevel: rider.fatigueLevel >= 70
                      ? RiskLevelView.high
                      : rider.fatigueLevel >= 40
                          ? RiskLevelView.medium
                          : RiskLevelView.low,
                ),
                const SizedBox(height: 20),
                alertAsync.when(
                  data: (alerts) => Text(
                    'Active Alerts: ${alerts.length}',
                    style: AppTypography.bodyLarge,
                  ),
                  loading: () => const LinearProgressIndicator(),
                  error: (_, __) => const Text('Unable to load alerts'),
                ),
              ],
            ),
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (_, __) => const Center(child: Text('Could not load rider status')),
          ),
        ),
      ),
    );
  }
}
