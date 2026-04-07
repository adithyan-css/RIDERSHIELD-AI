import 'package:flutter_tts/flutter_tts.dart';

class TtsService {
  final FlutterTts _flutterTts = FlutterTts();
  bool _isInitialized = false;
  DateTime? _lastSpokenAt;
  String? _lastSpokenText;

  Future<void> init() async {
    if (_isInitialized) return;

    await _flutterTts.setLanguage('en-US');
    await _flutterTts.setSpeechRate(0.5);
    await _flutterTts.setVolume(1.0);
    await _flutterTts.setPitch(1.0);
    _isInitialized = true;
  }

  Future<void> speak(String text) async {
    final now = DateTime.now();
    if (_lastSpokenText == text && _lastSpokenAt != null && now.difference(_lastSpokenAt!) < const Duration(seconds: 2)) {
      return;
    }

    if (!_isInitialized) await init();
    await _flutterTts.stop();
    await _flutterTts.speak(text);
    _lastSpokenText = text;
    _lastSpokenAt = now;
  }

  Future<void> alertHazard(String hazardType, {String? message}) async {
    final normalized = hazardType.toLowerCase();
    if (normalized.contains('collision')) {
      await speak('Warning: collision risk ahead. Reduce speed immediately.');
      return;
    }

    final readableType = hazardType.replaceAll('_', ' ').trim();
    final spokenMessage =
        (message != null && message.trim().isNotEmpty) ? message.trim() : '$readableType detected ahead. Please slow down.';
    await speak('Warning: $spokenMessage');
  }

  Future<void> stop() async {
    await _flutterTts.stop();
  }
}
