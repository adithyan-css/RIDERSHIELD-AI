import 'dart:async';

class LocationPoint {
  final double lat;
  final double lng;

  const LocationPoint({required this.lat, required this.lng});
}

class LocationStream {
  final StreamController<LocationPoint> _controller = StreamController.broadcast();

  Stream<LocationPoint> get stream => _controller.stream;

  void add(LocationPoint point) => _controller.add(point);

  void dispose() => _controller.close();
}
