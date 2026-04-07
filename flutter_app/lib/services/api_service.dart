import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiService {
  static const String baseUrl = 'http://10.0.2.2:8000/api'; // Android emulator
  // static const String baseUrl = 'http://localhost:8000/api'; // iOS simulator

  static String? _token;
  static String? _riderId;

  static void setAuth(String token, String riderId) {
    _token = token;
    _riderId = riderId;
  }

  static Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        if (_token != null) 'Authorization': 'Bearer $_token',
      };

  // --- Auth ---
  static Future<Map<String, dynamic>> register(
      String name, String phone, String companyId) async {
    final res = await http.post(
      Uri.parse('$baseUrl/rider/register'),
      headers: _headers,
      body: jsonEncode({'name': name, 'phone': phone, 'company_id': companyId}),
    );
    return jsonDecode(res.body);
  }

  static Future<Map<String, dynamic>> login(String phone, String otp) async {
    final res = await http.post(
      Uri.parse('$baseUrl/rider/login'),
      headers: _headers,
      body: jsonEncode({'phone': phone, 'otp': otp}),
    );
    return jsonDecode(res.body);
  }

  // --- Location ---
  static Future<void> updateLocation(
      double lat, double lng, double speedKmh) async {
    await http.post(
      Uri.parse('$baseUrl/rider/location'),
      headers: _headers,
      body: jsonEncode({
        'rider_id': _riderId,
        'lat': lat,
        'lng': lng,
        'speed_kmh': speedKmh,
      }),
    );
  }

  // --- HFV ---
  static Future<void> submitHFV(Map<String, dynamic> hfv) async {
    await http.post(
      Uri.parse('$baseUrl/hfv'),
      headers: _headers,
      body: jsonEncode(hfv),
    );
  }

  // --- Hazard surface ---
  static Future<Map<String, dynamic>> getGPSurface(
      double lat, double lng) async {
    final res = await http.get(
      Uri.parse('$baseUrl/hazards/surface?lat=$lat&lng=$lng&radius_m=500'),
      headers: _headers,
    );
    return jsonDecode(res.body);
  }

  static Future<List<dynamic>> getVerifiedHazards(
      double lat, double lng) async {
    final res = await http.get(
      Uri.parse(
          '$baseUrl/hazards/verified?lat=$lat&lng=$lng&radius_m=1000&limit=20'),
      headers: _headers,
    );
    return jsonDecode(res.body);
  }

  // --- DIGIPIN ---
  static Future<Map<String, dynamic>> resolveDigipin(String code) async {
    final res = await http.get(
      Uri.parse('$baseUrl/digipin/resolve?code=$code'),
      headers: _headers,
    );
    return jsonDecode(res.body);
  }

  static Future<Map<String, dynamic>> encodeDigipin(
      double lat, double lng) async {
    final res = await http.get(
      Uri.parse('$baseUrl/digipin/encode?lat=$lat&lng=$lng'),
      headers: _headers,
    );
    return jsonDecode(res.body);
  }

  // --- Delivery ---
  static Future<Map<String, dynamic>> startDelivery(
      String orderId, String digipin, String pickupDigipin) async {
    final res = await http.post(
      Uri.parse('$baseUrl/delivery/start'),
      headers: _headers,
      body: jsonEncode({
        'order_id': orderId,
        'rider_id': _riderId,
        'digipin': digipin,
        'pickup_digipin': pickupDigipin,
      }),
    );
    return jsonDecode(res.body);
  }

  static Future<Map<String, dynamic>> verifyDelivery(
      String deliveryId, bool gpsMatch, String? clipId) async {
    final res = await http.patch(
      Uri.parse('$baseUrl/delivery/$deliveryId/verify'),
      headers: _headers,
      body: jsonEncode({'gps_match': gpsMatch, 'clip_id': clipId}),
    );
    return jsonDecode(res.body);
  }

  // --- Rider state ---
  static Future<Map<String, dynamic>> getRiderState() async {
    final res = await http.get(
      Uri.parse('$baseUrl/rider/$_riderId/state'),
      headers: _headers,
    );
    return jsonDecode(res.body);
  }

  static Future<Map<String, dynamic>> getRiderHistory() async {
    final res = await http.get(
      Uri.parse('$baseUrl/rider/$_riderId/history'),
      headers: _headers,
    );
    return jsonDecode(res.body);
  }
}
