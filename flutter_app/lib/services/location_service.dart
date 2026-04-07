import 'dart:async';
import 'package:geolocator/geolocator.dart';
import 'api_service.dart';
import 'ws_service.dart';

class LocationService {
  StreamSubscription<Position>? _sub;
  Position? lastPosition;

  Future<bool> requestPermission() async {
    LocationPermission perm = await Geolocator.checkPermission();
    if (perm == LocationPermission.denied) {
      perm = await Geolocator.requestPermission();
    }
    return perm == LocationPermission.always ||
        perm == LocationPermission.whileInUse;
  }

  void startTracking() {
    _sub = Geolocator.getPositionStream(
      locationSettings: const LocationSettings(
        accuracy: LocationAccuracy.high,
        distanceFilter: 5,
      ),
    ).listen((pos) {
      lastPosition = pos;
      wsService.sendLocation(pos.latitude, pos.longitude);
      // Fire and forget HTTP update every ~5s handled by distance filter
      ApiService.updateLocation(
          pos.latitude, pos.longitude, pos.speed * 3.6);
    });
  }

  void stopTracking() {
    _sub?.cancel();
    _sub = null;
  }
}

final locationService = LocationService();
