import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/constants/colors.dart';
import '../../core/constants/typography.dart';
import '../../core/widgets/glass/glass_card.dart';
import '../providers/delivery_provider.dart';

class DeliveryQueueScreen extends ConsumerWidget {
  const DeliveryQueueScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final queueAsync = ref.watch(deliveryProvider);

    return Scaffold(
      backgroundColor: AppColors.deepBlack,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        title: const Text('Delivery Queue'),
      ),
      body: queueAsync.when(
        data: (queue) {
          if (queue.isEmpty) {
            return const Center(child: Text('No active deliveries'));
          }

          return ListView.separated(
            padding: const EdgeInsets.all(16),
            itemCount: queue.length,
            separatorBuilder: (_, __) => const SizedBox(height: 12),
            itemBuilder: (context, index) {
              final item = queue[index];
              return GlassCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(item.id, style: AppTypography.bodyLarge),
                    const SizedBox(height: 4),
                    Text('Status: ${item.status}'),
                    if (item.address != null) Text(item.address!),
                  ],
                ),
              );
            },
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (_, __) => const Center(child: Text('Could not load deliveries')),
      ),
    );
  }
}
