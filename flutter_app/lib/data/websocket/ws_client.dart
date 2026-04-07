import 'dart:async';
import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import '../models/hazard.dart';

final websocketProvider =
    StateNotifierProvider<WSClient, WebSocketState>((ref) {
  return WSClient(ref);
});

class WebSocketState {
  final bool isConnected;
  final int activeHazards;
  final List<Alert> pendingAlerts;

  const WebSocketState({
    this.isConnected = false,
    this.activeHazards = 0,
    this.pendingAlerts = const [],
  });

  WebSocketState copyWith({
    bool? isConnected,
    int? activeHazards,
    List<Alert>? pendingAlerts,
  }) {
    return WebSocketState(
      isConnected: isConnected ?? this.isConnected,
      activeHazards: activeHazards ?? this.activeHazards,
      pendingAlerts: pendingAlerts ?? this.pendingAlerts,
    );
  }
}

class WSClient extends StateNotifier<WebSocketState> {
  static const String _wsBaseUrl = String.fromEnvironment('WS_BASE_URL');

  final Ref ref;
  WebSocketChannel? _channel;
  Timer? _reconnectTimer;

  WSClient(this.ref) : super(const WebSocketState()) {
    connect();
  }

  List<Alert> get pendingAlerts => state.pendingAlerts;

  void connect() {
    try {
      if (_wsBaseUrl.isEmpty) {
        throw StateError('Missing WS_BASE_URL dart-define');
      }
      final base = _wsBaseUrl.endsWith('/') ? _wsBaseUrl.substring(0, _wsBaseUrl.length - 1) : _wsBaseUrl;
      _channel = WebSocketChannel.connect(
        Uri.parse('$base/ws/rider/${getRiderId()}'),
      );

      _channel!.stream.listen(
        _onMessage,
        onError: _onError,
        onDone: _onDisconnect,
      );

      state = state.copyWith(isConnected: true);
    } catch (_) {
      _scheduleReconnect();
    }
  }

  String getRiderId() => 'demo_rider';

  void _onMessage(dynamic message) {
    final data = jsonDecode(message.toString()) as Map<String, dynamic>;
    final event = data['event'] ?? data['type'];

    switch (event) {
      case 'peer_alert':
        _handlePeerAlert(data);
        break;
      case 'AI_EVENT':
        _handlePeerAlert(_mapAiEventToAlert(data));
        break;
      case 'gp_surface_update':
      case 'reroute_suggestion':
      default:
        break;
    }
  }

  Map<String, dynamic> _mapAiEventToAlert(Map<String, dynamic> data) {
    final payload = (data['payload'] as Map<String, dynamic>?) ?? const <String, dynamic>{};
    final location = (payload['location'] as Map<String, dynamic>?) ?? const <String, dynamic>{};
    final metadata = (payload['metadata'] as Map<String, dynamic>?) ?? const <String, dynamic>{};
    final eventType = (payload['event_type'] ?? 'hazard').toString();

    return {
      'title': 'AI Event',
      'hazard_type': (metadata['hazard_type'] ?? eventType).toString(),
      'severity': (metadata['severity'] ?? 'medium').toString(),
      'direction': (metadata['direction'] ?? 'ahead').toString(),
      'distance': (metadata['distance'] as num?)?.toDouble() ?? 0,
      'description': (metadata['message'] ?? 'AI event detected').toString(),
      'has_voice': true,
      'voice_progress': 0,
      'suggests_reroute': (eventType == 'collision_risk'),
      'lat': (location['lat'] as num?)?.toDouble() ?? 0,
      'lng': (location['lng'] as num?)?.toDouble() ?? 0,
      'confidence': (payload['confidence'] as num?)?.toDouble() ?? 0.5,
    };
  }

  void _handlePeerAlert(Map<String, dynamic> data) {
    final alert = Alert.fromJson(data);
    final nextAlerts = [alert, ...state.pendingAlerts];
    state = state.copyWith(
      activeHazards: state.activeHazards + 1,
      pendingAlerts: nextAlerts,
    );
  }

  void _onError(Object _) => _scheduleReconnect();

  void _onDisconnect() => _scheduleReconnect();

  void _scheduleReconnect() {
    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(const Duration(seconds: 5), connect);
    state = state.copyWith(isConnected: false);
  }

  void disconnect() {
    _channel?.sink.close();
    _reconnectTimer?.cancel();
  }

  @override
  void dispose() {
    disconnect();
    super.dispose();
  }
}
