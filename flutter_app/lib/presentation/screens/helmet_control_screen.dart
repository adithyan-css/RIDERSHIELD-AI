import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/constants/colors.dart';
import '../../core/widgets/glass/glass_card.dart';
import '../components/helmet_status_tile.dart';
import '../providers/helmet_provider.dart';

class HelmetControlScreen extends ConsumerWidget {
  const HelmetControlScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final helmet = ref.watch(helmetProvider);
    final actions = ref.watch(helmetActionsProvider);

    return Scaffold(
      backgroundColor: AppColors.deepBlack,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        title: const Text('Helmet Control'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            HelmetStatusTile(helmet: helmet),
            const SizedBox(height: 16),
            GlassCard(
              child: Row(
                children: [
                  Expanded(
                    child: ElevatedButton(
                      onPressed: actions.pair,
                      child: const Text('Pair Helmet'),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: OutlinedButton(
                      onPressed: actions.disconnect,
                      child: const Text('Disconnect'),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
