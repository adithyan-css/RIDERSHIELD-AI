class RiderStateModel {
  final String riderId;
  final double speedKmh;
  final double tiltAngle;
  final double acceleration;
  final int fatigueLevel;

  const RiderStateModel({
    required this.riderId,
    required this.speedKmh,
    required this.tiltAngle,
    required this.acceleration,
    required this.fatigueLevel,
  });
}
