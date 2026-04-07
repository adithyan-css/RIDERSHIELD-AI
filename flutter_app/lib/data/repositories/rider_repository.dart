import '../api/rider_api.dart';
import '../models/rider_state.dart';

class RiderRepository {
  final RiderApi api;

  RiderRepository({required this.api});

  Future<Map<String, dynamic>> login(String phone, String password) {
    return api.login(phone, password);
  }

  Future<void> updateLocation({
    required String riderId,
    required double lat,
    required double lng,
    required double speed,
  }) {
    return api.updateLocation(
      riderId: riderId,
      lat: lat,
      lng: lng,
      speed: speed,
    );
  }

  Future<RiderStateModel> getCurrentState({required String riderId}) async {
    return RiderStateModel(
      riderId: riderId,
      speedKmh: 0,
      tiltAngle: 0,
      acceleration: 0,
      fatigueLevel: 0,
    );
  }
}
