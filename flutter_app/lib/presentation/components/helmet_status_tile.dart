import 'package:flutter/material.dart';

import '../../core/constants/colors.dart';
import '../../core/constants/typography.dart';
import '../../core/widgets/glass/glass_card.dart';
import '../../domain/entities/helmet_entity.dart';

class HelmetStatusTile extends StatelessWidget {
  final HelmetEntity helmet;

  const HelmetStatusTile({
    super.key,
    required this.helmet,
  });

  @override
  Widget build(BuildContext context) {
    final statusColor = helmet.isConnected ? AppColors.safe : AppColors.danger;

    return GlassCard(
      child: Row(
        children: [
          Icon(Icons.headset, color: statusColor),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  helmet.deviceName ?? 'Helmet Not Paired',
                  style: AppTypography.bodyLarge,
                ),
                Text(
                  'Battery ${helmet.batteryLevel}%',
                  style: AppTypography.bodyMedium,
                ),
              ],
            ),
          ),
          Text(
            helmet.isConnected ? 'Connected' : 'Offline',
            style: AppTypography.label.copyWith(color: statusColor),
          ),
        ],
      ),
    );
  }
}
