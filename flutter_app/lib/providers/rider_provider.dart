import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../services/api_service.dart';
import '../services/ws_service.dart';
import '../services/location_service.dart';

class RiderProvider extends ChangeNotifier {
  String? riderId;
  String? name;
  String? token;
  bool isLoggedIn = false;

  int fatigueLevel = 1;
  double rideDurationH = 0.0;
  int helmetBatteryPct = 100;
  bool helmetConnected = false;

  final List<Map<String, dynamic>> recentAlerts = [];

  Future<void> loadFromStorage() async {
    final prefs = await SharedPreferences.getInstance();
    riderId = prefs.getString('rider_id');
    token = prefs.getString('token');
    name = prefs.getString('name');
    if (riderId != null && token != null) {
      isLoggedIn = true;
      ApiService.setAuth(token!, riderId!);
      await _initServices();
    }
    notifyListeners();
  }

  Future<void> login(String phone, String otp) async {
    final res = await ApiService.login(phone, otp);
    await _persistAndInit(res['rider_id'], res['token'], phone);
  }

  Future<void> register(
      String name, String phone, String companyId) async {
    final res = await ApiService.register(name, phone, companyId);
    await _persistAndInit(res['rider_id'], res['token'], name);
  }

  Future<void> _persistAndInit(
      String id, String tok, String displayName) async {
    riderId = id;
    token = tok;
    name = displayName;
    isLoggedIn = true;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('rider_id', id);
    await prefs.setString('token', tok);
    await prefs.setString('name', displayName);
    ApiService.setAuth(tok, id);
    await _initServices();
    notifyListeners();
  }

  Future<void> _initServices() async {
    await wsService.connect(riderId!);
    wsService.addListener(_onWsMessage);
    final ok = await locationService.requestPermission();
    if (ok) locationService.startTracking();
  }

  void _onWsMessage(Map<String, dynamic> msg) {
    if (msg['type'] == 'peer_alert') {
      recentAlerts.insert(0, msg);
      if (recentAlerts.length > 20) recentAlerts.removeLast();
      notifyListeners();
    }
  }

  Future<void> logout() async {
    wsService.disconnect();
    locationService.stopTracking();
    final prefs = await SharedPreferences.getInstance();
    await prefs.clear();
    riderId = null;
    token = null;
    name = null;
    isLoggedIn = false;
    notifyListeners();
  }
}
