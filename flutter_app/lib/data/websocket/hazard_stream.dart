import 'dart:async';

import '../models/hazard.dart';

class HazardStream {
  final StreamController<Alert> _controller = StreamController.broadcast();

  Stream<Alert> get stream => _controller.stream;

  void add(Alert alert) => _controller.add(alert);

  void dispose() => _controller.close();
}
