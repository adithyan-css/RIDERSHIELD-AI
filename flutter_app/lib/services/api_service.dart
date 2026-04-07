import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/alert_model.dart';
import '../models/delivery_model.dart';
import '../models/hazard_model.dart';
import '../models/rider_model.dart';

class ApiService {
  static const String _apiBaseUrl = String.fromEnvironment('API_BASE_URL');
  static const Duration timeout = Duration(seconds: 10);

  static String get baseUrl {
    if (_apiBaseUrl.isEmpty) {
      throw StateError('Missing API_BASE_URL dart-define');
    }
    if (_apiBaseUrl.endsWith('/api')) {
      return _apiBaseUrl;
    }
    return '$_apiBaseUrl/api';
  }

  String? _authToken;

  void setToken(String token) {
    _authToken = token;
  }

  void clearToken() {
    _authToken = null;
  }

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        if (_authToken != null) 'Authorization': 'Bearer $_authToken',
      };

  Future<Rider> login(String phone, String password) async {
    final response = await http.post(
      Uri.parse('$baseUrl/rider/login'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'phone': phone,
        'password': password,
      }),
    ).timeout(timeout);

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      return Rider.fromJson(data);
    } else {
      throw Exception('Login failed: ${response.body}');
    }
  }

  Future<List<Hazard>> getHazards() async {
    final response = await http.get(
      Uri.parse('$baseUrl/hazards/verified'),
      headers: _headers,
    ).timeout(timeout);

    if (response.statusCode == 200) {
      final List<dynamic> data = jsonDecode(response.body);
      return data.map((e) => Hazard.fromJson(e)).toList();
    } else {
      throw Exception('Failed to fetch hazards');
    }
  }

  Future<void> updateLocation(
      String riderId, double lat, double lng, double speed) async {
    await http.post(
      Uri.parse('$baseUrl/rider/location'),
      headers: _headers,
      body: jsonEncode({
        'rider_id': riderId,
        'lat': lat,
        'lng': lng,
        'speed': speed,
        'timestamp': DateTime.now().toIso8601String(),
      }),
    ).timeout(timeout);
  }

  Future<Map<String, dynamic>> resolveDigipin(String digiPin) async {
    final response = await http.get(
      Uri.parse('$baseUrl/digipin/resolve?code=$digiPin'),
      headers: _headers,
    ).timeout(timeout);

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Invalid DIGIPIN');
    }
  }

  Future<Delivery> startDelivery({
    required String orderId,
    required String riderId,
    required String digipin,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/delivery/start'),
      headers: _headers,
      body: jsonEncode({
        'order_id': orderId,
        'rider_id': riderId,
        'digipin': digipin,
      }),
    ).timeout(timeout);

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      final normalized = {
        ...data,
        'id': data['order_id'],
        'status': data['status'] ?? 'enroute',
        'digi_pin': digipin,
      };
      return Delivery.fromJson(normalized);
    } else {
      throw Exception('Failed to start delivery');
    }
  }

  Future<void> verifyDelivery(
    String deliveryId, {
    required bool gpsMatch,
    String? clipId,
  }) async {
    final response = await http.patch(
      Uri.parse('$baseUrl/delivery/$deliveryId/verify'),
      headers: _headers,
      body: jsonEncode({
        'gps_match': gpsMatch,
        if (clipId != null) 'clip_id': clipId,
      }),
    ).timeout(timeout);

    if (response.statusCode != 200) {
      throw Exception('Verification failed');
    }
  }

  Future<Map<String, dynamic>> getRiderState(String riderId) async {
    final response = await http.get(
      Uri.parse('$baseUrl/rider/$riderId/state'),
      headers: _headers,
    ).timeout(timeout);

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    throw Exception('Failed to load rider state');
  }

  Future<Map<String, dynamic>> getRiderProfile(String riderId) async {
    final response = await http.get(
      Uri.parse('$baseUrl/rider/$riderId'),
      headers: _headers,
    ).timeout(timeout);

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to load profile');
    }
  }

  Future<List<Alert>> getRecentAiEvents({
    String? riderId,
    int limit = 25,
  }) async {
    final queryParams = <String, String>{
      'limit': '$limit',
      if (riderId != null && riderId.isNotEmpty) 'rider_id': riderId,
    };

    final uri = Uri.parse('$baseUrl/ai/events/recent').replace(queryParameters: queryParams);
    final response = await http.get(uri, headers: _headers).timeout(timeout);

    if (response.statusCode != 200) {
      throw Exception('Failed to fetch recent AI events');
    }

    final payload = jsonDecode(response.body) as Map<String, dynamic>;
    final items = (payload['items'] as List<dynamic>? ?? const []);
    return items
        .whereType<Map<String, dynamic>>()
        .map(_mapRecentEventToAlert)
        .toList(growable: false);
  }

  Alert _mapRecentEventToAlert(Map<String, dynamic> event) {
    final location = _asMap(event['location']);
    final metadata = _asMap(event['metadata']);
    final eventType = (event['event_type'] ?? metadata['hazard_type'] ?? 'hazard').toString();

    final alertJson = {
      'id': (metadata['event_id'] ?? event['id'] ?? DateTime.now().millisecondsSinceEpoch.toString()).toString(),
      'type': eventType,
      'hazard_type': (metadata['hazard_type'] ?? eventType).toString(),
      'lat': _toDouble(location['lat']) ?? _toDouble(event['lat']) ?? 0.0,
      'lng': _toDouble(location['lng']) ?? _toDouble(event['lng']) ?? 0.0,
      'message': (metadata['message'] ?? event['message'] ?? 'AI event detected').toString(),
    };
    return Alert.fromJson(alertJson);
  }

  static Map<String, dynamic> _asMap(dynamic value) {
    if (value is Map<String, dynamic>) {
      return value;
    }
    if (value is Map) {
      return value.map((k, v) => MapEntry(k.toString(), v));
    }
    return const <String, dynamic>{};
  }

  static double? _toDouble(dynamic value) {
    if (value is num) {
      return value.toDouble();
    }
    if (value is String) {
      return double.tryParse(value);
    }
    return null;
  }
}
