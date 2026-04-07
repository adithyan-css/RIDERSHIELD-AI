import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';

import '../models/alert_model.dart';
import '../providers/app_state_provider.dart';
import '../providers/auth_provider.dart';

class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  GoogleMapController? _mapController;

  @override
  Widget build(BuildContext context) {
    final appState = ref.watch(appStateProvider);
    final rider = ref.watch(authProvider).rider;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Safety Map'),
        actions: [
          Container(
            margin: const EdgeInsets.only(right: 16),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            decoration: BoxDecoration(
              color: appState.isWebSocketConnected ? Colors.green : Colors.red,
              borderRadius: BorderRadius.circular(20),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  Icons.circle,
                  size: 8,
                  color: appState.isWebSocketConnected ? Colors.white : Colors.white,
                ),
                const SizedBox(width: 6),
                Text(
                  appState.isWebSocketConnected ? 'LIVE' : 'OFFLINE',
                  style: const TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
      body: Stack(
        children: [
          GoogleMap(
            initialCameraPosition: const CameraPosition(
              target: LatLng(37.7749, -122.4194),
              zoom: 14, // Default SF
            ),
            myLocationEnabled: true,
            myLocationButtonEnabled: true,
            mapType: MapType.normal,
            trafficEnabled: true,
            markers: _buildMarkers(appState),
            onMapCreated: (controller) {
              _mapController = controller;
              _animateToCurrentLocation(appState.currentLocation);
            },
          ),
          if (appState.alerts.isNotEmpty)
          // Alerts Overlay
            Positioned(
              top: 16,
              left: 16,
              right: 16,
              child: _buildAlertCard(appState.alerts.first),
            ),
          Positioned(
            bottom: 100,
            right: 16,
            child: Card(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    _legendItem('🕳️', 'Pothole'),
                    _legendItem('💥', 'Accident'),
                    _legendItem('🚧', 'Construction'),
                    _legendItem('🚦', 'Traffic'),
                    _legendItem('🌧️', 'Weather'),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Set<Marker> _buildMarkers(AppState state) {
    return state.hazards.map((hazard) {
      return Marker(
        markerId: MarkerId(hazard.id),
        position: LatLng(hazard.lat, hazard.lng),
        icon: BitmapDescriptor.defaultMarkerWithHue(
          hazard.severity == 'high'
              ? BitmapDescriptor.hueRed
              : BitmapDescriptor.hueOrange,
        ),
        infoWindow: InfoWindow(
          title: '${hazard.iconAsset} ${hazard.type}',
          snippet: 'Severity: ${hazard.severity}',
        ),
      );
    }).toSet();
  }

  Widget _buildAlertCard(Alert alert) {
    return Card(
      color: Colors.red.shade900,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              children: [
                const Icon(Icons.warning_amber_rounded, color: Colors.white),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'HAZARD ALERT',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          color: Colors.white,
                          fontWeight: FontWeight.bold,
                        ),
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.close, color: Colors.white70),
                  onPressed: () {
                    ref.read(appStateProvider.notifier).markAlertAsRead(alert.id);
                  },
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              alert.message,
              style: const TextStyle(color: Colors.white),
            ),
            const SizedBox(height: 4),
            Text(
              '${alert.hazardType} at ${alert.lat.toStringAsFixed(4)}, ${alert.lng.toStringAsFixed(4)}',
              style: TextStyle(
                color: Colors.white.withOpacity(0.7),
                fontSize: 12,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _legendItem(String emoji, String label) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(emoji, style: const TextStyle(fontSize: 16)),
          const SizedBox(width: 8),
          Text(label, style: const TextStyle(fontSize: 12)),
        ],
      ),
    );
  }

  void _animateToCurrentLocation(dynamic location) {
    if (location != null && _mapController != null) {
      _mapController!.animateCamera(
        CameraUpdate.newLatLng(
          LatLng(location.latitude, location.longitude),
        ),
      );
    }
  }
}
