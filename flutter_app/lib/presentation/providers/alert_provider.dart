import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/api/hazard_api.dart';
import '../../data/repositories/hazard_repository.dart';
import '../../data/websocket/ws_client.dart';
import '../../domain/entities/hazard_entity.dart';
import '../../domain/usecases/get_active_alerts.dart';

final hazardRepositoryProvider = Provider<HazardRepository>((ref) {
  return HazardRepository(
    api: HazardApi(),
    wsClient: ref.read(websocketProvider.notifier),
  );
});

final getActiveAlertsProvider = Provider<GetActiveAlerts>((ref) {
  return GetActiveAlerts(ref.read(hazardRepositoryProvider));
});

final alertProvider =
    StateNotifierProvider<AlertNotifier, AsyncValue<List<HazardEntity>>>((ref) {
  final notifier = AlertNotifier(ref.read(getActiveAlertsProvider));
  notifier.refresh();
  return notifier;
});

class AlertNotifier extends StateNotifier<AsyncValue<List<HazardEntity>>> {
  final GetActiveAlerts _getActiveAlerts;

  AlertNotifier(this._getActiveAlerts) : super(const AsyncValue.loading());

  Future<void> refresh() async {
    state = const AsyncValue.loading();
    try {
      final alerts = await _getActiveAlerts();
      state = AsyncValue.data(alerts);
    } catch (error, stackTrace) {
      state = AsyncValue.error(error, stackTrace);
    }
  }
}
