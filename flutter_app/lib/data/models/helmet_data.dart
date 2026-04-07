enum RiskLevel { low, medium, high }

class HelmetData {
  final bool isConnected;
  final String? deviceName;
  final int batteryLevel;
  final RiskLevel riskLevel;
  final bool voiceEnabled;
  final bool signalEnabled;
  final bool cameraEnabled;
  final bool sosEnabled;

  const HelmetData({
    required this.isConnected,
    required this.deviceName,
    required this.batteryLevel,
    required this.riskLevel,
    required this.voiceEnabled,
    required this.signalEnabled,
    required this.cameraEnabled,
    required this.sosEnabled,
  });

  HelmetData copyWith({
    bool? isConnected,
    String? deviceName,
    int? batteryLevel,
    RiskLevel? riskLevel,
    bool? voiceEnabled,
    bool? signalEnabled,
    bool? cameraEnabled,
    bool? sosEnabled,
  }) {
    return HelmetData(
      isConnected: isConnected ?? this.isConnected,
      deviceName: deviceName ?? this.deviceName,
      batteryLevel: batteryLevel ?? this.batteryLevel,
      riskLevel: riskLevel ?? this.riskLevel,
      voiceEnabled: voiceEnabled ?? this.voiceEnabled,
      signalEnabled: signalEnabled ?? this.signalEnabled,
      cameraEnabled: cameraEnabled ?? this.cameraEnabled,
      sosEnabled: sosEnabled ?? this.sosEnabled,
    );
  }
}
