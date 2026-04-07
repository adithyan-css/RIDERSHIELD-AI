import 'package:dio/dio.dart';

import 'dio_client.dart';

class RiderApi {
  final Dio _dio;

  RiderApi({Dio? dio}) : _dio = dio ?? DioClient.instance;

  Future<Map<String, dynamic>> login(String phone, String password) async {
    final res = await _dio.post(
      '/rider/login',
      data: {'phone': phone, 'password': password},
    );
    return (res.data as Map?)?.cast<String, dynamic>() ?? <String, dynamic>{};
  }

  Future<void> updateLocation({
    required String riderId,
    required double lat,
    required double lng,
    required double speed,
  }) async {
    await _dio.post(
      '/rider/location',
      data: {
        'rider_id': riderId,
        'lat': lat,
        'lng': lng,
        'speed': speed,
      },
    );
  }
}
