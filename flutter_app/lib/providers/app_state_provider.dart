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
  final bool isFallbackMode;
  final double? currentSpeed;
  final bool isTracking;

  AppState({
    this.currentLocation,
    this.hazards = const [],
    this.alerts = const [],
    this.isWebSocketConnected = false,
    this.isFallbackMode = false,
    this.currentSpeed,
    this.isTracking = false,
  });

  AppState copyWith({
    Position? currentLocation,
    List<Hazard>? hazards,
    List<Alert>? alerts,
    bool? isWebSocketConnected,
    bool? isFallbackMode,
    double? currentSpeed,
    bool? isTracking,
  }) {
    return AppState(
      currentLocation: currentLocation ?? this.currentLocation,
      hazards: hazards ?? this.hazards,
      alerts: alerts ?? this.alerts,
      isWebSocketConnected: isWebSocketConnected ?? this.isWebSocketConnected,
      isFallbackMode: isFallbackMode ?? this.isFallbackMode,
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
  Timer? _fallbackTimer;
  StreamSubscription<Position>? _locationSub;
  StreamSubscription<Alert>? _alertSub;
  bool _isFallbackFetchInFlight = false;

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
      _startFallbackPolling();
      _startLocationTracking();
      _loadHazards();
    }
  }

  Future<void> _connectWebSocket() async {
    final rider = _rider;
    if (rider == null) return;

    await _wsService.connect(rider.id);

    _wsService.addListener(() {
      state = state.copyWith(
        isWebSocketConnected: _wsService.isConnected,
        isFallbackMode: !_wsService.isConnected,
      );
    });

    _alertSub = _wsService.alertStream.listen(
      _handleAlert,
      onError: (Object error, StackTrace stackTrace) {
        debugPrint('Alert stream error: $error');
      },
    );
  }

  void _handleAlert(Alert alert) {
    _ingestAlert(alert);
  }

  void _ingestAlert(Alert alert) {
    if (state.alerts.any((a) => a.id == alert.id)) {
      return;
    }

    final nextAlerts = [alert, ...state.alerts];
    state = state.copyWith(
      alerts: nextAlerts.length > 80 ? nextAlerts.take(80).toList() : nextAlerts,
    );

    unawaited(_ttsService.alertHazard(alert.hazardType, message: alert.message));
  }

  void _startFallbackPolling() {
    _fallbackTimer?.cancel();
    _fallbackTimer = Timer.periodic(const Duration(seconds: 3), (_) {
      unawaited(_recoverFromRealtimeGap());
    });
  }

  Future<void> _recoverFromRealtimeGap() async {
    final rider = _rider;
    if (rider == null || _isFallbackFetchInFlight) {
      return;
    }

    final shouldUseFallback = !_wsService.isConnected || _wsService.isStale;
    if (!shouldUseFallback) {
      if (state.isFallbackMode) {
        state = state.copyWith(isFallbackMode: false);
      }
      return;
    }

    _isFallbackFetchInFlight = true;
    state = state.copyWith(isFallbackMode: true);
    try {
      final recentEvents = await _apiService.getRecentAiEvents(riderId: rider.id, limit: 30);
      for (final alert in recentEvents.reversed) {
        _ingestAlert(alert);
      }
    } catch (e) {
      debugPrint('Fallback recent-event fetch failed: $e');
    } finally {
      _isFallbackFetchInFlight = false;
    }
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
    _fallbackTimer?.cancel();
    _locationSub?.cancel();
    _alertSub?.cancel();
    _locationService.dispose();
    _wsService.dispose();
    super.dispose();
  }
}
