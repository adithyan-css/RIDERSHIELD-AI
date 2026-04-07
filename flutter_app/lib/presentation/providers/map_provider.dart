import 'package:flutter_riverpod/flutter_riverpod.dart';

class MapViewport {
  final double lat;
  final double lng;
  final double zoom;
  final String? focusedHazardId;

  const MapViewport({
    required this.lat,
    required this.lng,
    required this.zoom,
    this.focusedHazardId,
  });

  MapViewport copyWith({
    double? lat,
    double? lng,
    double? zoom,
    String? focusedHazardId,
  }) {
    return MapViewport(
      lat: lat ?? this.lat,
      lng: lng ?? this.lng,
      zoom: zoom ?? this.zoom,
      focusedHazardId: focusedHazardId ?? this.focusedHazardId,
    );
  }
}

final mapProvider = StateNotifierProvider<MapNotifier, MapViewport>((ref) {
  return MapNotifier();
});

class MapNotifier extends StateNotifier<MapViewport> {
  MapNotifier() : super(const MapViewport(lat: 12.9716, lng: 77.5946, zoom: 14));

  void updateViewport({required double lat, required double lng, required double zoom}) {
    state = state.copyWith(lat: lat, lng: lng, zoom: zoom);
  }

  void focusHazard(String hazardId) {
    state = state.copyWith(focusedHazardId: hazardId);
  }
}
