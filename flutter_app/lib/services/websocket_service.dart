import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';

import '../models/alert_model.dart';

class WebSocketService extends ChangeNotifier {
  WebSocket? _socket;
  final StreamController<Alert> _alertController = StreamController<Alert>.broadcast();
  bool _isConnected = false;
  String? _riderId;

  Stream<Alert> get alertStream => _alertController.stream;
  bool get isConnected => _isConnected;

  Future<void> connect(String riderId) async {
    if (_isConnected && _riderId == riderId) return;

    _riderId = riderId;
    await disconnect();

    try {
      final wsUrl = 'ws://127.0.0.1:8000/ws/rider/$riderId';
      _socket = await WebSocket.connect(wsUrl);
      _isConnected = true;
      notifyListeners();

      _socket!.listen(
        (message) {
          _handleMessage(message);
        },
        onError: (error) {
          debugPrint('WebSocket error: $error');
          _reconnect();
        },
        onDone: () {
          _isConnected = false;
          notifyListeners();
          _reconnect();
        },
      );
    } catch (e) {
      debugPrint('WebSocket connection failed: $e');
      _reconnect();
    }
  }

  void _handleMessage(String message) {
    try {
      final data = jsonDecode(message);

      if (data['type'] == 'peer_alert') {
        final alert = Alert.fromJson(data);
        _alertController.add(alert);
      }
    } catch (e) {
      debugPrint('Error parsing message: $e');
    }
  }

  void _reconnect() {
    if (_riderId != null) {
      Future.delayed(const Duration(seconds: 5), () {
        connect(_riderId!);
      });
    }
  }

  Future<void> disconnect() async {
    _isConnected = false;
    notifyListeners();
    await _socket?.close();
    _socket = null;
  }

  @override
  void dispose() {
    disconnect();
    _alertController.close();
    super.dispose();
  }
}
