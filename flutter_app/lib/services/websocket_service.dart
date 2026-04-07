import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math';

import 'package:flutter/foundation.dart';

import '../models/alert_model.dart';

class WebSocketService extends ChangeNotifier {
  static const String _wsBaseUrl = String.fromEnvironment('WS_BASE_URL');
  static const Duration _staleThreshold = Duration(seconds: 3);
  static const Duration _heartbeatInterval = Duration(seconds: 10);

  WebSocket? _socket;
  final StreamController<Alert> _alertController = StreamController<Alert>.broadcast();
  bool _isConnected = false;
  bool _manualDisconnect = false;
  bool _isDisposed = false;
  int _reconnectAttempts = 0;
  String? _riderId;
  Timer? _reconnectTimer;
  Timer? _heartbeatTimer;
  DateTime? _lastMessageAt;

  Stream<Alert> get alertStream => _alertController.stream;
  bool get isConnected => _isConnected;
  DateTime? get lastMessageAt => _lastMessageAt;
  bool get isStale {
    final lastMessage = _lastMessageAt;
    if (!_isConnected || lastMessage == null) {
      return true;
    }
    return DateTime.now().difference(lastMessage) > _staleThreshold;
  }

  Future<void> connect(String riderId) async {
    if (_isDisposed) return;
    _manualDisconnect = false;
    _riderId = riderId;
    if (_isConnected && _socket != null) {
      return;
    }

    await _openConnection();
  }

  Future<void> _openConnection() async {
    final riderId = _riderId;
    if (riderId == null || _isDisposed) return;

    await _closeSocket();

    try {
      if (_wsBaseUrl.isEmpty) {
        throw StateError('Missing WS_BASE_URL dart-define');
      }
      final base = _wsBaseUrl.endsWith('/') ? _wsBaseUrl.substring(0, _wsBaseUrl.length - 1) : _wsBaseUrl;
      final wsUrl = '$base/ws/rider/$riderId';
      _socket = await WebSocket.connect(wsUrl);
      _setConnected(true);
      _reconnectAttempts = 0;
      _lastMessageAt = DateTime.now();
      _startHeartbeat();

      _socket!.listen(
        (dynamic message) {
          _handleMessage(message);
        },
        onError: (Object error, StackTrace stackTrace) {
          debugPrint('WebSocket error: $error');
          _reconnect();
        },
        onDone: () {
          _setConnected(false);
          _reconnect();
        },
        cancelOnError: true,
      );
    } catch (e) {
      debugPrint('WebSocket connection failed: $e');
      _reconnect();
    }
  }

  void _startHeartbeat() {
    _heartbeatTimer?.cancel();
    _heartbeatTimer = Timer.periodic(_heartbeatInterval, (_) {
      final socket = _socket;
      if (socket == null || !_isConnected) {
        return;
      }
      try {
        socket.add(jsonEncode({'type': 'ping'}));
      } catch (e) {
        debugPrint('Heartbeat failed: $e');
        _reconnect(forceDelay: const Duration(seconds: 1));
      }
    });
  }

  void _handleMessage(dynamic message) {
    try {
      final data = jsonDecode(_asText(message));
      if (data is! Map<String, dynamic>) {
        return;
      }

      _lastMessageAt = DateTime.now();
      if (data['type'] == 'pong') {
        return;
      }

      if (data['type'] == 'peer_alert') {
        final alert = Alert.fromJson(data);
        _alertController.add(alert);
      }

      if (data['type'] == 'AI_EVENT' && data['payload'] is Map<String, dynamic>) {
        final alertJson = _toAlertJson(data['payload'] as Map<String, dynamic>);
        final alert = Alert.fromJson(alertJson);
        _alertController.add(alert);
      }
    } catch (e) {
      debugPrint('Error parsing message: $e');
    }
  }

  String _asText(dynamic message) {
    if (message is String) {
      return message;
    }
    if (message is List<int>) {
      return utf8.decode(message);
    }
    return message.toString();
  }

  Map<String, dynamic> _toAlertJson(Map<String, dynamic> payload) {
    final location = (payload['location'] as Map<String, dynamic>?) ?? const <String, dynamic>{};
    final metadata = (payload['metadata'] as Map<String, dynamic>?) ?? const <String, dynamic>{};
    final eventType = (payload['event_type'] ?? 'hazard').toString();

    return {
      'id': (metadata['event_id'] ?? DateTime.now().millisecondsSinceEpoch.toString()).toString(),
      'type': eventType,
      'hazard_type': (metadata['hazard_type'] ?? eventType).toString(),
      'lat': (location['lat'] as num?)?.toDouble() ?? 0.0,
      'lng': (location['lng'] as num?)?.toDouble() ?? 0.0,
      'message': (metadata['message'] ?? 'AI event detected').toString(),
    };
  }

  void _setConnected(bool value) {
    if (_isConnected == value) {
      return;
    }
    _isConnected = value;
    notifyListeners();
  }

  void _reconnect({Duration? forceDelay}) {
    if (_manualDisconnect || _isDisposed || _riderId == null) {
      return;
    }

    _setConnected(false);
    _heartbeatTimer?.cancel();

    if (_reconnectTimer?.isActive ?? false) {
      return;
    }

    final exponent = _reconnectAttempts > 5 ? 5 : _reconnectAttempts;
    final backoffSeconds = min(30, 1 << exponent);
    final delay = forceDelay ?? Duration(seconds: backoffSeconds);
    _reconnectAttempts = min(_reconnectAttempts + 1, 8);

    _reconnectTimer = Timer(delay, () {
      _reconnectTimer = null;
      final riderId = _riderId;
      if (riderId == null || _manualDisconnect || _isDisposed) {
        return;
      }
      connect(riderId);
    });
  }

  Future<void> disconnect() async {
    _manualDisconnect = true;
    _reconnectTimer?.cancel();
    _reconnectTimer = null;
    _heartbeatTimer?.cancel();
    _heartbeatTimer = null;
    _setConnected(false);
    await _closeSocket();
  }

  Future<void> _closeSocket() async {
    final socket = _socket;
    _socket = null;
    if (socket == null) {
      return;
    }
    try {
      await socket.close();
    } catch (_) {
      // Ignore socket close race during reconnects.
    }
  }

  @override
  void dispose() {
    _isDisposed = true;
    unawaited(disconnect());
    unawaited(_alertController.close());
    super.dispose();
  }
}
