import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../domain/entities/helmet_entity.dart';
import 'ble_manager.dart';
import 'helmet_state.dart';

final helmetServiceProvider = Provider<HelmetService>((ref) {
  return HelmetService(ref);
});

class HelmetService {
  final Ref ref;

  HelmetService(this.ref);

  BLEState get bleState => ref.read(bleManagerProvider);

  HelmetEntity getHelmetEntity() {
    final state = bleState;
    return HelmetEntity(
      isConnected: state.connectedDevice != null,
      deviceName: state.connectedDevice?.platformName,
      batteryLevel: state.batteryLevel,
      isRecording: state.isRecording,
    );
  }

  Future<void> startPairing() {
    return ref.read(bleManagerProvider.notifier).startScan();
  }

  Future<void> disconnect() {
    return ref.read(bleManagerProvider.notifier).disconnect();
  }
}
