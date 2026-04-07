class Alert {
  final String id;
  final String type;
  final String hazardType;
  final double lat;
  final double lng;
  final String message;
  final DateTime receivedAt;
  final bool isRead;

  Alert({
    required this.id,
    required this.type,
    required this.hazardType,
    required this.lat,
    required this.lng,
    required this.message,
    required this.receivedAt,
    this.isRead = false,
  });

  factory Alert.fromJson(Map<String, dynamic> json) {
    return Alert(
      id: json['id'] ?? DateTime.now().millisecondsSinceEpoch.toString(),
      type: json['type'],
      hazardType: json['hazard_type'],
      lat: json['lat'].toDouble(),
      lng: json['lng'].toDouble(),
      message: json['message'] ?? 'Hazard detected ahead!',
      receivedAt: DateTime.now(),
    );
  }
}
