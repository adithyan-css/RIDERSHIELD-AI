import 'package:flutter/material.dart';

class Hazard {
  final String id;
  final String type;
  final double lat;
  final double lng;
  final String severity;
  final String? description;
  final DateTime reportedAt;
  final int? confirmations;

  Hazard({
    required this.id,
    required this.type,
    required this.lat,
    required this.lng,
    required this.severity,
    this.description,
    required this.reportedAt,
    this.confirmations,
  });

  factory Hazard.fromJson(Map<String, dynamic> json) {
    return Hazard(
      id: json['id'] ?? json['_id'],
      type: json['type'] ?? json['hazard_type'],
      lat: json['lat'].toDouble(),
      lng: json['lng'].toDouble(),
      severity: json['severity'] ?? 'medium',
      description: json['description'],
      reportedAt: DateTime.parse(json['reported_at'] ?? json['created_at']),
      confirmations: json['confirmations'],
    );
  }

  String get iconAsset {
    switch (type.toLowerCase()) {
      case 'pothole':
        return '🕳️';
      case 'accident':
        return '💥';
      case 'construction':
        return '🚧';
      case 'traffic':
        return '🚦';
      case 'weather':
        return '🌧️';
      default:
        return '⚠️';
    }
  }

  Color get severityColor {
    switch (severity.toLowerCase()) {
      case 'high':
        return Colors.red;
      case 'medium':
        return Colors.orange;
      default:
        return Colors.yellow;
    }
  }
}