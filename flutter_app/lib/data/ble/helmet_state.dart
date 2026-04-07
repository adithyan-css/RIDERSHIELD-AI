import 'package:flutter_blue_plus/flutter_blue_plus.dart';

class BLEState {
  final bool isScanning;
  final BluetoothDevice? connectedDevice;
  final int batteryLevel;
  final bool isRecording;

  const BLEState({
    this.isScanning = false,
    this.connectedDevice,
    this.batteryLevel = 0,
    this.isRecording = false,
  });

  BLEState copyWith({
    bool? isScanning,
    BluetoothDevice? connectedDevice,
    int? batteryLevel,
    bool? isRecording,
  }) {
    return BLEState(
      isScanning: isScanning ?? this.isScanning,
      connectedDevice: connectedDevice ?? this.connectedDevice,
      batteryLevel: batteryLevel ?? this.batteryLevel,
      isRecording: isRecording ?? this.isRecording,
    );
  }
}
