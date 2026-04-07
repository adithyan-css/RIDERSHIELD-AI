import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'dart:async';

import '../models/alert_model.dart';
import '../providers/app_state_provider.dart';

class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  GoogleMapController? _mapController;
  Timer? _blinkTimer;
  Timer? _popupTimer;
  bool _blinkOn = true;
  bool _showAlertPopup = false;
  late final ProviderSubscription<AppState> _appStateSub;

  @override
  void initState() {
    super.initState();
    _blinkTimer = Timer.periodic(const Duration(milliseconds: 650), (_) {
      if (!mounted) return;
      setState(() {
        _blinkOn = !_blinkOn;
      });
    });

    _appStateSub = ref.listenManual<AppState>(appStateProvider, (previous, next) {
      if (next.currentLocation != null) {
        _animateToCurrentLocation(next.currentLocation);
      }

      final before = previous?.alerts.length ?? 0;
      if (next.alerts.length > before) {
        if (!mounted) return;
        setState(() {
          _showAlertPopup = true;
        });
        _popupTimer?.cancel();
        _popupTimer = Timer(const Duration(seconds: 6), () {
          if (!mounted) return;
          setState(() {
            _showAlertPopup = false;
          });
        });
      }
    });
  }

  @override
  void dispose() {
    _blinkTimer?.cancel();
    _popupTimer?.cancel();
    _appStateSub.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final appState = ref.watch(appStateProvider);
    final liveColor = appState.isWebSocketConnected
        ? Colors.green
        : (appState.isFallbackMode ? Colors.orange : Colors.red);
    final liveLabel = appState.isWebSocketConnected
        ? 'LIVE WS'
        : (appState.isFallbackMode ? 'REST FALLBACK' : 'OFFLINE');

    return Scaffold(
      appBar: AppBar(
        title: const Text('Safety Map'),
        actions: [
          Container(
            margin: const EdgeInsets.only(right: 16),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            decoration: BoxDecoration(
              color: liveColor,
              borderRadius: BorderRadius.circular(20),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(
                  Icons.circle,
                  size: 8,
                  color: Colors.white,
                ),
                const SizedBox(width: 6),
                Text(
                  liveLabel,
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
            mapType: MapType.hybrid,
            trafficEnabled: true,
            markers: _buildMarkers(appState),
            circles: _buildHeatmap(appState),
            onMapCreated: (controller) {
              _mapController = controller;
              _animateToCurrentLocation(appState.currentLocation);
            },
          ),
          Positioned(
            top: 16,
            left: 16,
            child: Card(
              color: Colors.black.withValues(alpha: 0.70),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'LIVE SAFETY FEED',
                      style: TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.bold,
                        fontSize: 12,
                        letterSpacing: 0.6,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      'Hazards: ${appState.hazards.length}',
                      style: const TextStyle(color: Colors.white70, fontSize: 12),
                    ),
                    Text(
                      'AI Alerts: ${appState.alerts.length}',
                      style: const TextStyle(color: Colors.white70, fontSize: 12),
                    ),
                  ],
                ),
              ),
            ),
          ),
          if (_showAlertPopup && appState.alerts.isNotEmpty)
          // Alerts Overlay
            Positioned(
              top: 88,
              left: 16,
              right: 16,
              child: AnimatedSlide(
                duration: const Duration(milliseconds: 260),
                curve: Curves.easeOutCubic,
                offset: _showAlertPopup ? Offset.zero : const Offset(0, -0.4),
                child: AnimatedOpacity(
                  duration: const Duration(milliseconds: 260),
                  opacity: _showAlertPopup ? 1 : 0,
                  child: _buildAlertCard(appState.alerts.first),
                ),
              ),
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
    final markers = state.hazards.map((hazard) {
      final isHigh = hazard.severity.toLowerCase() == 'high';
      final hue = isHigh
          ? (_blinkOn ? BitmapDescriptor.hueRed : BitmapDescriptor.hueOrange)
          : BitmapDescriptor.hueOrange;
      return Marker(
        markerId: MarkerId(hazard.id),
        position: LatLng(hazard.lat, hazard.lng),
        icon: BitmapDescriptor.defaultMarkerWithHue(
          hue,
        ),
        infoWindow: InfoWindow(
          title: '${hazard.iconAsset} ${hazard.type}',
          snippet: 'Severity: ${hazard.severity}',
        ),
      );
    }).toSet();

    for (final alert in state.alerts.take(15)) {
      final isCollision = alert.hazardType.toLowerCase().contains('collision');
      final hue = isCollision
          ? (_blinkOn ? BitmapDescriptor.hueRed : BitmapDescriptor.hueRose)
          : (_blinkOn ? BitmapDescriptor.hueYellow : BitmapDescriptor.hueOrange);
      markers.add(
        Marker(
          markerId: MarkerId('alert_${alert.id}'),
          position: LatLng(alert.lat, alert.lng),
          icon: BitmapDescriptor.defaultMarkerWithHue(hue),
          infoWindow: InfoWindow(
            title: '⚠️ ${alert.hazardType}',
            snippet: alert.message,
          ),
        ),
      );
    }

    final location = state.currentLocation;
    if (location != null) {
      markers.add(
        Marker(
          markerId: const MarkerId('rider_live_location'),
          position: LatLng(location.latitude, location.longitude),
          icon: BitmapDescriptor.defaultMarkerWithHue(BitmapDescriptor.hueAzure),
          infoWindow: const InfoWindow(title: 'Your Live Location'),
        ),
      );
    }

    return markers;
  }

  Set<Circle> _buildHeatmap(AppState state) {
    final circles = state.hazards.map((hazard) {
      final severity = hazard.severity.toLowerCase();
      final radius = severity == 'high' ? (_blinkOn ? 120.0 : 80.0) : 70.0;
      final color = severity == 'high'
          ? Colors.red.withValues(alpha: _blinkOn ? 0.28 : 0.14)
          : Colors.orange.withValues(alpha: 0.18);

      return Circle(
        circleId: CircleId('heat_${hazard.id}'),
        center: LatLng(hazard.lat, hazard.lng),
        radius: radius,
        fillColor: color,
        strokeColor: Colors.transparent,
        strokeWidth: 0,
      );
    }).toSet();

    for (final alert in state.alerts.take(15)) {
      final isCollision = alert.hazardType.toLowerCase().contains('collision');
      circles.add(
        Circle(
          circleId: CircleId('alert_heat_${alert.id}'),
          center: LatLng(alert.lat, alert.lng),
          radius: isCollision ? (_blinkOn ? 130.0 : 95.0) : 80.0,
          fillColor: isCollision
              ? Colors.red.withValues(alpha: _blinkOn ? 0.24 : 0.12)
              : Colors.yellow.withValues(alpha: _blinkOn ? 0.18 : 0.08),
          strokeColor: Colors.transparent,
          strokeWidth: 0,
        ),
      );
    }

    return circles;
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
                    setState(() {
                      _showAlertPopup = false;
                    });
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
                color: Colors.white.withValues(alpha: 0.7),
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
