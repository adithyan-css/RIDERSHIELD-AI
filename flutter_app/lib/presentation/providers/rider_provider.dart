import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/api/rider_api.dart';
import '../../data/repositories/rider_repository.dart';
import '../../domain/entities/rider_entity.dart';
import '../../domain/usecases/get_rider_status.dart';

final riderRepositoryProvider = Provider<RiderRepository>((ref) {
  return RiderRepository(api: RiderApi());
});

final getRiderStatusProvider = Provider<GetRiderStatus>((ref) {
  return GetRiderStatus(ref.read(riderRepositoryProvider));
});

final riderProvider = StateNotifierProvider<RiderNotifier, AsyncValue<RiderEntity>>((ref) {
  final notifier = RiderNotifier(ref.read(getRiderStatusProvider));
  notifier.load('demo_rider');
  return notifier;
});

class RiderNotifier extends StateNotifier<AsyncValue<RiderEntity>> {
  final GetRiderStatus _getRiderStatus;

  RiderNotifier(this._getRiderStatus) : super(const AsyncValue.loading());

  Future<void> load(String riderId) async {
    state = const AsyncValue.loading();
    try {
      final rider = await _getRiderStatus(riderId);
      state = AsyncValue.data(rider);
    } catch (error, stackTrace) {
      state = AsyncValue.error(error, stackTrace);
    }
  }
}
