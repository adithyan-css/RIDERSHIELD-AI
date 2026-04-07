import 'package:flutter_tts/flutter_tts.dart';

class TtsService {
  final FlutterTts _flutterTts = FlutterTts();
  bool _isInitialized = false;

  Future<void> init() async {
    if (_isInitialized) return;

    await _flutterTts.setLanguage('en-US');
    await _flutterTts.setSpeechRate(0.5);
    await _flutterTts.setVolume(1.0);
    await _flutterTts.setPitch(1.0);
    _isInitialized = true;
  }

  Future<void> speak(String text) async {
    if (!_isInitialized) await init();
    await _flutterTts.stop();
    await _flutterTts.speak(text);
  }

  Future<void> alertHazard(String hazardType, String direction) async {
    final message =
        'Warning! $hazardType detected $direction meters ahead. Slow down!';
    await speak(message);
  }

  Future<void> stop() async {
    await _flutterTts.stop();
  }
}
