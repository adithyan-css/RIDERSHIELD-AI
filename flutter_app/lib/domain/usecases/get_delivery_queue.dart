import '../../data/repositories/delivery_repository.dart';
import '../entities/delivery_entity.dart';

class GetDeliveryQueue {
  final DeliveryRepository repository;

  GetDeliveryQueue(this.repository);

  Future<List<DeliveryEntity>> call() async {
    final queue = await repository.getQueue();
    return queue.map(DeliveryEntity.fromModel).toList();
  }
}
