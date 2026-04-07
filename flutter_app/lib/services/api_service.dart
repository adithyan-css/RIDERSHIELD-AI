import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/delivery_model.dart';
import '../models/hazard_model.dart';
import '../models/rider_model.dart';

class ApiService {
  static const String baseUrl = 'http://127.0.0.1:8000/api';
  static const Duration timeout = Duration(seconds: 10);

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
      Uri.parse('$baseUrl/digipin/resolve?pin=$digiPin'),
      headers: _headers,
    ).timeout(timeout);

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Invalid DIGIPIN');
    }
  }

  Future<Delivery> startDelivery(String deliveryId) async {
    final response = await http.post(
      Uri.parse('$baseUrl/delivery/start'),
      headers: _headers,
      body: jsonEncode({
        'delivery_id': deliveryId,
      }),
    ).timeout(timeout);

    if (response.statusCode == 200) {
      return Delivery.fromJson(jsonDecode(response.body));
    } else {
      throw Exception('Failed to start delivery');
    }
  }

  Future<Delivery> verifyDelivery(String deliveryId, String digiPin) async {
    final response = await http.patch(
      Uri.parse('$baseUrl/delivery/$deliveryId/verify'),
      headers: _headers,
      body: jsonEncode({
        'digi_pin': digiPin,
      }),
    ).timeout(timeout);

    if (response.statusCode == 200) {
      return Delivery.fromJson(jsonDecode(response.body));
    } else {
      throw Exception('Verification failed');
    }
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
}
