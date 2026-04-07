import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';

import '../models/hazard_model.dart';
import '../models/alert_model.dart';
import '../models/rider_model.dart';
import '../services/api_service.dart';
import '../services/location_service.dart';
import '../services/tts_service.dart';
import '../services/websocket_service.dart';
import 'auth_provider.dart';

final webSocketServiceProvider = Provider((ref) => WebSocketService());
final locationServiceProvider = Provider((ref) => LocationService());
final ttsServiceProvider = Provider((ref) => TtsService());

final appStateProvider = StateNotifierProvider<AppStateNotifier, AppState>((ref) {
  return AppStateNotifier(
    ref.read(webSocketServiceProvider),
    ref.read(locationServiceProvider),
    ref.read(ttsServiceProvider),
    ref.read(apiServiceProvider),
    ref.read(authProvider).rider,
  );
});

class AppState {
  final Position? currentLocation;
  final List<Hazard> hazards;
  final List<Alert> alerts;
  final bool isWebSocketConnected;
  final double? currentSpeed;
  final bool isTracking;

  AppState({
    this.currentLocation,
    this.hazards = const [],
    this.alerts = const [],
    this.isWebSocketConnected = false,
    this.currentSpeed,
    this.isTracking = false,
  });

  AppState copyWith({
    Position? currentLocation,
    List<Hazard>? hazards,
    List<Alert>? alerts,
    bool? isWebSocketConnected,
    double? currentSpeed,
    bool? isTracking,
  }) {
    return AppState(
      currentLocation: currentLocation ?? this.currentLocation,
      hazards: hazards ?? this.hazards,
      alerts: alerts ?? this.alerts,
      isWebSocketConnected: isWebSocketConnected ?? this.isWebSocketConnected,
      currentSpeed: currentSpeed ?? this.currentSpeed,
      isTracking: isTracking ?? this.isTracking,
    );
  }
}

class AppStateNotifier extends StateNotifier<AppState> {
  final WebSocketService _wsService;
  final LocationService _locationService;
  final TtsService _ttsService;
  final ApiService _apiService;
  final Rider? _rider;
  Timer? _locationTimer;
  StreamSubscription<Position>? _locationSub;
  StreamSubscription<Alert>? _alertSub;

  AppStateNotifier(
    this._wsService,
    this._locationService,
    this._ttsService,
    this._apiService,
    this._rider,
  ) : super(AppState()) {
    _init();
  }

  void _init() {
    if (_rider != null) {
      _connectWebSocket();
      _startLocationTracking();
      _loadHazards();
    }
  }

  Future<void> _connectWebSocket() async {
    final rider = _rider;
    if (rider == null) return;

    await _wsService.connect(rider.id);

    _wsService.addListener(() {
      state = state.copyWith(isWebSocketConnected: _wsService.isConnected);
    });

    _alertSub = _wsService.alertStream.listen(_handleAlert);
  }

  void _handleAlert(Alert alert) {
    final newAlerts = [alert, ...state.alerts];
    state = state.copyWith(alerts: newAlerts);

    // Voice alert
    _ttsService.alertHazard(alert.hazardType, '50');

    // Show notification (in real app, use flutter_local_notifications)
  }

  Future<void> _startLocationTracking() async {
    final hasPermission = await _locationService.requestPermission();
    if (!hasPermission) return;

    state = state.copyWith(isTracking: true);
    _locationService.startTracking();

    _locationSub = _locationService.locationStream.listen((position) {
      state = state.copyWith(
        currentLocation: position,
        currentSpeed: position.speed * 3.6, // Convert to km/h
      );
    });

    // Send location every 5 seconds
    _locationTimer = Timer.periodic(const Duration(seconds: 5), (_) {
      _sendLocationUpdate();
    });
  }

  Future<void> _sendLocationUpdate() async {
    final rider = _rider;
    if (rider == null || state.currentLocation == null) return;

    try {
      await _apiService.updateLocation(
        rider.id,
        state.currentLocation!.latitude,
        state.currentLocation!.longitude,
        state.currentSpeed ?? 0,
      );
    } catch (e) {
      debugPrint('Failed to update location: $e');
    }
  }

  Future<void> _loadHazards() async {
    try {
      final hazards = await _apiService.getHazards();
      state = state.copyWith(hazards: hazards);
    } catch (e) {
      debugPrint('Failed to load hazards: $e');
    }
  }

  void markAlertAsRead(String alertId) {
    final updatedAlerts = state.alerts.map((a) {
      if (a.id == alertId) {
        return Alert(
          id: a.id,
          type: a.type,
          hazardType: a.hazardType,
          lat: a.lat,
          lng: a.lng,
          message: a.message,
          receivedAt: a.receivedAt,
          isRead: true,
        );
      }
      return a;
    }).toList();
    state = state.copyWith(alerts: updatedAlerts);
  }

  @override
  void dispose() {
    _locationTimer?.cancel();
    _locationSub?.cancel();
    _alertSub?.cancel();
    _locationService.dispose();
    _wsService.dispose();
    super.dispose();
  }
}
