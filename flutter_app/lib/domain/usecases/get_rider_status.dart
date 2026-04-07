import '../../data/repositories/rider_repository.dart';
import '../entities/rider_entity.dart';

class GetRiderStatus {
  final RiderRepository repository;

  GetRiderStatus(this.repository);

  Future<RiderEntity> call(String riderId) async {
    final state = await repository.getCurrentState(riderId: riderId);
    return RiderEntity.fromModel(state);
  }
}
