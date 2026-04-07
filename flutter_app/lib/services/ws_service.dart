import 'dart:async';
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';

typedef AlertCallback = void Function(Map<String, dynamic> msg);

class WsService {
  static const String wsBase = 'ws://10.0.2.2:8000';

  WebSocketChannel? _channel;
  Timer? _pingTimer;
  bool _connected = false;
  final List<AlertCallback> _listeners = [];

  bool get connected => _connected;

  void addListener(AlertCallback cb) => _listeners.add(cb);
  void removeListener(AlertCallback cb) => _listeners.remove(cb);

  Future<void> connect(String riderId) async {
    _channel = WebSocketChannel.connect(
      Uri.parse('$wsBase/ws/rider/$riderId'),
    );
    _connected = true;
    _channel!.stream.listen(
      (data) {
        try {
          final msg = jsonDecode(data as String) as Map<String, dynamic>;
          for (final cb in _listeners) {
            cb(msg);
          }
        } catch (_) {}
      },
      onDone: () {
        _connected = false;
        _scheduleReconnect(riderId);
      },
      onError: (_) {
        _connected = false;
        _scheduleReconnect(riderId);
      },
    );
  }

  void sendLocation(double lat, double lng) {
    if (!_connected) return;
    _channel?.sink.add(jsonEncode({
      'type': 'location',
      'lat': lat,
      'lng': lng,
      'ts': DateTime.now().toIso8601String(),
    }));
  }

  void _scheduleReconnect(String riderId) {
    Future.delayed(const Duration(seconds: 5), () => connect(riderId));
  }

  void disconnect() {
    _pingTimer?.cancel();
    _channel?.sink.close();
    _connected = false;
  }
}

final wsService = WsService();
