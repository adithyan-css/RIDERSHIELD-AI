import 'package:dio/dio.dart';

import '../models/delivery.dart';
import 'dio_client.dart';

class DeliveryApi {
  final Dio _dio;

  DeliveryApi({Dio? dio}) : _dio = dio ?? DioClient.instance;

  Future<Map<String, dynamic>> resolveDigipin(String pin) async {
    final res = await _dio.get('/digipin/resolve', queryParameters: {'pin': pin});
    return (res.data as Map?)?.cast<String, dynamic>() ?? <String, dynamic>{};
  }

  Future<DeliveryModel> startDelivery(String deliveryId) async {
    final res = await _dio.post('/delivery/start', data: {'delivery_id': deliveryId});
    return DeliveryModel.fromJson(
      (res.data as Map?)?.cast<String, dynamic>() ?? <String, dynamic>{},
    );
  }

  Future<DeliveryModel> verifyDelivery(String deliveryId, String digiPin) async {
    final res = await _dio.patch(
      '/delivery/$deliveryId/verify',
      data: {'digi_pin': digiPin},
    );
    return DeliveryModel.fromJson(
      (res.data as Map?)?.cast<String, dynamic>() ?? <String, dynamic>{},
    );
  }
}
