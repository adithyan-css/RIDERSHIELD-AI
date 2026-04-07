import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/api/delivery_api.dart';
import '../../data/repositories/delivery_repository.dart';
import '../../domain/entities/delivery_entity.dart';
import '../../domain/usecases/get_delivery_queue.dart';

final deliveryRepositoryProvider = Provider<DeliveryRepository>((ref) {
  return DeliveryRepository(api: DeliveryApi());
});

final getDeliveryQueueProvider = Provider<GetDeliveryQueue>((ref) {
  return GetDeliveryQueue(ref.read(deliveryRepositoryProvider));
});

final deliveryProvider =
    StateNotifierProvider<DeliveryNotifier, AsyncValue<List<DeliveryEntity>>>((ref) {
  final notifier = DeliveryNotifier(ref.read(getDeliveryQueueProvider));
  notifier.load();
  return notifier;
});

class DeliveryNotifier extends StateNotifier<AsyncValue<List<DeliveryEntity>>> {
  final GetDeliveryQueue _getDeliveryQueue;

  DeliveryNotifier(this._getDeliveryQueue) : super(const AsyncValue.loading());

  Future<void> load() async {
    state = const AsyncValue.loading();
    try {
      final queue = await _getDeliveryQueue();
      state = AsyncValue.data(queue);
    } catch (error, stackTrace) {
      state = AsyncValue.error(error, stackTrace);
    }
  }
}
