import '../../data/repositories/hazard_repository.dart';
import '../entities/hazard_entity.dart';

class GetActiveAlerts {
  final HazardRepository repository;

  GetActiveAlerts(this.repository);

  Future<List<HazardEntity>> call() async {
    final hazards = await repository.getActiveHazards();
    return hazards.map(HazardEntity.fromModel).toList();
  }
}
