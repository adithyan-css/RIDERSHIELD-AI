import 'package:flutter/material.dart';

class BleDevice {
  final String id;
  final String name;
  bool connected;
  int batteryPct;
  bool cameraActive;

  BleDevice({
    required this.id,
    required this.name,
    this.connected = false,
    this.batteryPct = 100,
    this.cameraActive = false,
  });
}

class BleProvider extends ChangeNotifier {
  BleDevice? connectedHelmet;
  List<BleDevice> scannedDevices = [];
  bool scanning = false;

  Future<void> startScan() async {
    scanning = true;
    notifyListeners();
    // Simulate scan — in real app use flutter_blue_plus
    await Future.delayed(const Duration(seconds: 3));
    scannedDevices = [
      BleDevice(id: 'AA:BB:CC:DD:EE:FF', name: 'RiderShield Helmet'),
    ];
    scanning = false;
    notifyListeners();
  }

  Future<void> connect(BleDevice device) async {
    // In real app: FlutterBluePlus.connect(device)
    await Future.delayed(const Duration(milliseconds: 800));
    device.connected = true;
    connectedHelmet = device;
    notifyListeners();
  }

  void disconnect() {
    connectedHelmet?.connected = false;
    connectedHelmet = null;
    notifyListeners();
  }

  void updateHelmetStatus({int? battery, bool? camera}) {
    if (connectedHelmet == null) return;
    if (battery != null) connectedHelmet!.batteryPct = battery;
    if (camera != null) connectedHelmet!.cameraActive = camera;
    notifyListeners();
  }
}
