import '../../data/models/hazard.dart';

class HazardEntity {
  final String id;
  final String label;
  final Severity severity;
  final double distance;
  final double confidence;

  const HazardEntity({
    required this.id,
    required this.label,
    required this.severity,
    required this.distance,
    required this.confidence,
  });

  factory HazardEntity.fromModel(Hazard hazard) {
    return HazardEntity(
      id: hazard.id,
      label: hazard.description,
      severity: hazard.severity,
      distance: hazard.distance,
      confidence: hazard.confidence,
    );
  }
}
