import 'dart:async';

import 'package:flutter_blue_plus/flutter_blue_plus.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'helmet_state.dart';

final bleManagerProvider =
    StateNotifierProvider<HelmetBLEManager, BLEState>((ref) {
  return HelmetBLEManager();
});

class HelmetBLEManager extends StateNotifier<BLEState> {
  StreamSubscription<List<ScanResult>>? _scanSubscription;

  HelmetBLEManager() : super(const BLEState());

  Future<void> startScan() async {
    state = state.copyWith(isScanning: true);
    await FlutterBluePlus.startScan(timeout: const Duration(seconds: 8));

    _scanSubscription?.cancel();
    _scanSubscription = FlutterBluePlus.scanResults.listen((results) {
      if (results.isEmpty) {
        return;
      }

      final device = results.first.device;
      if (state.connectedDevice == null) {
        connectToDevice(device);
      }
    });
  }

  Future<void> stopScan() async {
    await FlutterBluePlus.stopScan();
    state = state.copyWith(isScanning: false);
  }

  Future<void> connectToDevice(BluetoothDevice device) async {
    try {
      await device.connect(timeout: const Duration(seconds: 10));
      state = state.copyWith(connectedDevice: device, isScanning: false);
    } catch (_) {
      state = state.copyWith(connectedDevice: null);
    }
  }

  Future<void> disconnect() async {
    final device = state.connectedDevice;
    if (device != null) {
      await device.disconnect();
    }
    state = state.copyWith(connectedDevice: null);
  }

  void setBatteryLevel(int level) {
    state = state.copyWith(batteryLevel: level.clamp(0, 100));
  }

  void setRecording(bool recording) {
    state = state.copyWith(isRecording: recording);
  }

  @override
  void dispose() {
    _scanSubscription?.cancel();
    super.dispose();
  }
}
