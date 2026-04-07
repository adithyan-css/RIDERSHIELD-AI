enum Severity { low, medium, high, critical }

enum HazardType { pothole, construction, traffic, weather }

class Hazard {
  final String id;
  final HazardType type;
  final Severity severity;
  final String description;
  final double confidence;
  final double distance;
  final double lat;
  final double lng;

  const Hazard({
    required this.id,
    required this.type,
    required this.severity,
    required this.description,
    required this.confidence,
    required this.distance,
    required this.lat,
    required this.lng,
  });

  factory Hazard.fromJson(Map<String, dynamic> json) {
    HazardType parseType(String value) {
      switch (value) {
        case 'pothole':
          return HazardType.pothole;
        case 'construction':
          return HazardType.construction;
        case 'traffic':
          return HazardType.traffic;
        default:
          return HazardType.weather;
      }
    }

    Severity parseSeverity(String value) {
      switch (value) {
        case 'low':
          return Severity.low;
        case 'high':
          return Severity.high;
        case 'critical':
          return Severity.critical;
        default:
          return Severity.medium;
      }
    }

    return Hazard(
      id: (json['id'] ?? json['_id'] ?? '').toString(),
      type: parseType((json['type'] ?? json['hazard_type'] ?? 'weather').toString()),
      severity: parseSeverity((json['severity'] ?? 'medium').toString()),
      description: (json['description'] ?? 'Hazard detected').toString(),
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0.5,
      distance: (json['distance'] as num?)?.toDouble() ?? 0,
      lat: (json['lat'] as num?)?.toDouble() ?? 0,
      lng: (json['lng'] as num?)?.toDouble() ?? 0,
    );
  }
}

class Alert {
  final String title;
  final HazardType hazardType;
  final Severity severity;
  final String direction;
  final double distance;
  final String description;
  final bool hasVoice;
  final double voiceProgress;
  final bool suggestsReroute;
  final double lat;
  final double lng;
  final double confidence;

  const Alert({
    required this.title,
    required this.hazardType,
    required this.severity,
    required this.direction,
    required this.distance,
    required this.description,
    required this.hasVoice,
    required this.voiceProgress,
    required this.suggestsReroute,
    required this.lat,
    required this.lng,
    required this.confidence,
  });

  factory Alert.fromJson(Map<String, dynamic> json) {
    final hazardTypeRaw = (json['hazard_type'] ?? json['type'] ?? 'weather').toString();
    final severityRaw = (json['severity'] ?? 'medium').toString();

    HazardType parsedType;
    switch (hazardTypeRaw) {
      case 'pothole':
        parsedType = HazardType.pothole;
        break;
      case 'construction':
        parsedType = HazardType.construction;
        break;
      case 'traffic':
        parsedType = HazardType.traffic;
        break;
      default:
        parsedType = HazardType.weather;
    }

    Severity parsedSeverity;
    switch (severityRaw) {
      case 'low':
        parsedSeverity = Severity.low;
        break;
      case 'high':
        parsedSeverity = Severity.high;
        break;
      case 'critical':
        parsedSeverity = Severity.critical;
        break;
      default:
        parsedSeverity = Severity.medium;
    }

    return Alert(
      title: (json['title'] ?? 'Hazard Alert').toString(),
      hazardType: parsedType,
      severity: parsedSeverity,
      direction: (json['direction'] ?? 'ahead').toString(),
      distance: (json['distance'] as num?)?.toDouble() ?? 0,
      description: (json['description'] ?? 'Drive carefully').toString(),
      hasVoice: (json['has_voice'] as bool?) ?? true,
      voiceProgress: (json['voice_progress'] as num?)?.toDouble() ?? 0,
      suggestsReroute: (json['suggests_reroute'] as bool?) ?? false,
      lat: (json['lat'] as num?)?.toDouble() ?? 0,
      lng: (json['lng'] as num?)?.toDouble() ?? 0,
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0.5,
    );
  }

  Hazard toHazard() {
    return Hazard(
      id: DateTime.now().microsecondsSinceEpoch.toString(),
      type: hazardType,
      severity: severity,
      description: description,
      confidence: confidence,
      distance: distance,
      lat: lat,
      lng: lng,
    );
  }
}
