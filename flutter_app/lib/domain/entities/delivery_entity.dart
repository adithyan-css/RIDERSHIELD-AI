import '../../data/models/delivery.dart';

class DeliveryEntity {
  final String id;
  final String status;
  final String? address;

  const DeliveryEntity({
    required this.id,
    required this.status,
    this.address,
  });

  factory DeliveryEntity.fromModel(DeliveryModel model) {
    return DeliveryEntity(
      id: model.id,
      status: model.status,
      address: model.address,
    );
  }
}
