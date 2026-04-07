import 'package:flutter/material.dart';
import '../services/api_service.dart';

class HazardProvider extends ChangeNotifier {
  List<dynamic> verifiedHazards = [];
  Map<String, dynamic>? gpSurface;
  bool loading = false;

  Future<void> fetchNearby(double lat, double lng) async {
    loading = true;
    notifyListeners();
    try {
      final results = await Future.wait([
        ApiService.getVerifiedHazards(lat, lng),
        ApiService.getGPSurface(lat, lng),
      ]);
      verifiedHazards = results[0] as List<dynamic>;
      gpSurface = results[1] as Map<String, dynamic>;
    } catch (e) {
      debugPrint('HazardProvider fetchNearby error: $e');
    }
    loading = false;
    notifyListeners();
  }
}
