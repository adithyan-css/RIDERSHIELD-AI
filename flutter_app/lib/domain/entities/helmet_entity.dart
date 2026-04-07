class HelmetEntity {
  final bool isConnected;
  final String? deviceName;
  final int batteryLevel;
  final bool isRecording;

  const HelmetEntity({
    required this.isConnected,
    required this.deviceName,
    required this.batteryLevel,
    required this.isRecording,
  });
}
