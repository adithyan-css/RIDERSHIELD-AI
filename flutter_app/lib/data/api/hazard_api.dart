import 'package:dio/dio.dart';

import '../models/hazard.dart';
import 'dio_client.dart';

class HazardApi {
  final Dio _dio;

  HazardApi({Dio? dio}) : _dio = dio ?? DioClient.instance;

  Future<List<Hazard>> getVerifiedHazards() async {
    final res = await _dio.get('/hazards/verified');
    final data = (res.data as List?) ?? const [];
    return data
        .whereType<Map<String, dynamic>>()
        .map(Hazard.fromJson)
        .toList();
  }
}
