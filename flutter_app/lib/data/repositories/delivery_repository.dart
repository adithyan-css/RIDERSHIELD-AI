import '../api/delivery_api.dart';
import '../models/delivery.dart';

class DeliveryRepository {
  final DeliveryApi api;

  DeliveryRepository({required this.api});

  Future<Map<String, dynamic>> resolveDigipin(String pin) {
    return api.resolveDigipin(pin);
  }

  Future<DeliveryModel> startDelivery(String deliveryId) {
    return api.startDelivery(deliveryId);
  }

  Future<DeliveryModel> verifyDelivery(String deliveryId, String digiPin) {
    return api.verifyDelivery(deliveryId, digiPin);
  }

  Future<List<DeliveryModel>> getQueue() async {
    return const [];
  }
}
