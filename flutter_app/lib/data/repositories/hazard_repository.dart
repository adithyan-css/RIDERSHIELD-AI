import '../api/hazard_api.dart';
import '../models/hazard.dart';
import '../websocket/ws_client.dart';

class HazardRepository {
  final HazardApi api;
  final WSClient wsClient;

  HazardRepository({required this.api, required this.wsClient});

  Future<List<Hazard>> getActiveHazards() async {
    final apiHazards = await api.getVerifiedHazards();
    final wsHazards = wsClient.pendingAlerts.map((a) => a.toHazard()).toList();

    final all = [...wsHazards, ...apiHazards];
    all.sort((a, b) => b.confidence.compareTo(a.confidence));
    return all;
  }

  Stream<List<Alert>> watchPendingAlerts() async* {
    yield wsClient.pendingAlerts;
  }
}
