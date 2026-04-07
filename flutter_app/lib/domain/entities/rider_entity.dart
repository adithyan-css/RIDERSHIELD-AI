import '../../data/models/rider_state.dart';

class RiderEntity {
  final String riderId;
  final double speedKmh;
  final double tiltAngle;
  final double acceleration;
  final int fatigueLevel;

  const RiderEntity({
    required this.riderId,
    required this.speedKmh,
    required this.tiltAngle,
    required this.acceleration,
    required this.fatigueLevel,
  });

  factory RiderEntity.fromModel(RiderStateModel model) {
    return RiderEntity(
      riderId: model.riderId,
      speedKmh: model.speedKmh,
      tiltAngle: model.tiltAngle,
      acceleration: model.acceleration,
      fatigueLevel: model.fatigueLevel,
    );
  }
}
