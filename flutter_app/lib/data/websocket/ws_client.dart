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
  final Ref ref;
  WebSocketChannel? _channel;
  Timer? _reconnectTimer;

  WSClient(this.ref) : super(const WebSocketState()) {
    connect();
  }

  List<Alert> get pendingAlerts => state.pendingAlerts;

  void connect() {
    try {
      _channel = WebSocketChannel.connect(
        Uri.parse('ws://127.0.0.1:8000/ws/rider/${getRiderId()}'),
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
      case 'gp_surface_update':
      case 'reroute_suggestion':
      default:
        break;
    }
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
