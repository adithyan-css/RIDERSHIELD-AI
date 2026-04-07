import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/ble/helmet_service.dart';
import '../../domain/entities/helmet_entity.dart';

final helmetProvider = Provider<HelmetEntity>((ref) {
  return ref.watch(helmetServiceProvider).getHelmetEntity();
});

final helmetActionsProvider = Provider<HelmetActions>((ref) {
  return HelmetActions(ref);
});

class HelmetActions {
  final Ref ref;

  HelmetActions(this.ref);

  Future<void> pair() {
    return ref.read(helmetServiceProvider).startPairing();
  }

  Future<void> disconnect() {
    return ref.read(helmetServiceProvider).disconnect();
  }
}
