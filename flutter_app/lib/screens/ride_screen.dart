import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/rider_provider.dart';
import '../services/location_service.dart';
import '../services/api_service.dart';
import '../services/tts_service.dart';
import '../services/ws_service.dart';
import '../widgets/fatigue_gauge.dart';

class RideScreen extends StatefulWidget {
  const RideScreen({super.key});

  @override
  State<RideScreen> createState() => _RideScreenState();
}

class _RideScreenState extends State<RideScreen> {
  bool _rideActive = false;
  Timer? _timer;
  Duration _elapsed = Duration.zero;
  double _speedKmh = 0;
  int _fatigueLevel = 1;
  double _depthCm = 0;
  int _rainRaw = 0;
  final List<String> _alertLog = [];

  @override
  void initState() {
    super.initState();
    wsService.addListener(_onAlert);
  }

  @override
  void dispose() {
    _timer?.cancel();
    wsService.removeListener(_onAlert);
    super.dispose();
  }

  void _onAlert(Map<String, dynamic> msg) {
    if (msg['type'] == 'peer_alert') {
      final cls = msg['hazard_class'] ?? 'hazard';
      final dist = msg['distance_m'] ?? 0;
      final alertText = '⚠️ $cls detected ${dist}m ahead';
      ttsService.speak('Warning! $cls detected $dist meters ahead');
      if (mounted) {
        setState(() => _alertLog.insert(0, alertText));
      }
    }
  }

  void _toggleRide() {
    setState(() => _rideActive = !_rideActive);
    if (_rideActive) {
      _elapsed = Duration.zero;
      _timer = Timer.periodic(const Duration(seconds: 1), (_) {
        setState(() {
          _elapsed += const Duration(seconds: 1);
          // Simulate telemetry updates
          final pos = locationService.lastPosition;
          if (pos != null) _speedKmh = pos.speed * 3.6;
          _fatigueLevel = _elapsed.inHours >= 4
              ? 4
              : _elapsed.inHours >= 2
                  ? 3
                  : _elapsed.inHours >= 1
                      ? 2
                      : 1;
        });
      });
      ttsService.speak('Ride started. RiderShield is active.');
    } else {
      _timer?.cancel();
      ttsService.speak('Ride ended. Stay safe.');
    }
  }

  String get _elapsedStr {
    final h = _elapsed.inHours.toString().padLeft(2, '0');
    final m = (_elapsed.inMinutes % 60).toString().padLeft(2, '0');
    final s = (_elapsed.inSeconds % 60).toString().padLeft(2, '0');
    return '$h:$m:$s';
  }

  @override
  Widget build(BuildContext context) {
    const teal = Color(0xFF00C8A0);
    return Scaffold(
      backgroundColor: const Color(0xFF0A0F1E),
      appBar: AppBar(
        backgroundColor: const Color(0xFF0D1526),
        title: const Text('Active Ride', style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w600)),
        actions: [
          IconButton(
            icon: Icon(
              ttsService.enabled ? Icons.volume_up : Icons.volume_off,
              color: teal,
            ),
            onPressed: () {
              ttsService.toggle();
              setState(() {});
            },
          )
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            // Timer + Start/Stop
            _RideTimerCard(
              elapsed: _elapsedStr,
              active: _rideActive,
              onToggle: _toggleRide,
            ),
            const SizedBox(height: 16),
            // Telemetry grid
            GridView.count(
              crossAxisCount: 2,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              mainAxisSpacing: 12,
              crossAxisSpacing: 12,
              childAspectRatio: 1.4,
              children: [
                _TelemetryCard(
                  label: 'Speed',
                  value: _speedKmh.toStringAsFixed(1),
                  unit: 'km/h',
                  icon: Icons.speed,
                  color: teal,
                ),
                _TelemetryCard(
                  label: 'Water Depth',
                  value: _depthCm.toStringAsFixed(1),
                  unit: 'cm',
                  icon: Icons.water_drop,
                  color: const Color(0xFF3B8BD4),
                ),
                _TelemetryCard(
                  label: 'Rain',
                  value: _rainRaw.toString(),
                  unit: 'raw',
                  icon: Icons.grain,
                  color: const Color(0xFF7F77DD),
                ),
                _TelemetryCard(
                  label: 'Duration',
                  value: '${_elapsed.inMinutes}',
                  unit: 'min',
                  icon: Icons.timer_outlined,
                  color: const Color(0xFFFFB347),
                ),
              ],
            ),
            const SizedBox(height: 16),
            // Fatigue gauge
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: const Color(0xFF0D1526),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: Colors.white10),
              ),
              child: Column(
                children: [
                  const Text('Fatigue Level',
                      style: TextStyle(color: Colors.white70, fontSize: 14)),
                  const SizedBox(height: 12),
                  FatigueGauge(level: _fatigueLevel),
                ],
              ),
            ),
            const SizedBox(height: 16),
            // Alert log
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: const Color(0xFF0D1526),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: Colors.white10),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Peer Alerts',
                      style: TextStyle(
                          color: Colors.white,
                          fontSize: 15,
                          fontWeight: FontWeight.w600)),
                  const SizedBox(height: 8),
                  if (_alertLog.isEmpty)
                    const Text('No alerts yet',
                        style: TextStyle(color: Colors.white38, fontSize: 13))
                  else
                    ..._alertLog.take(5).map((a) => Padding(
                          padding: const EdgeInsets.symmetric(vertical: 4),
                          child: Text(a,
                              style: const TextStyle(
                                  color: Colors.orangeAccent, fontSize: 13)),
                        )),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _RideTimerCard extends StatelessWidget {
  final String elapsed;
  final bool active;
  final VoidCallback onToggle;
  const _RideTimerCard({required this.elapsed, required this.active, required this.onToggle});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: const Color(0xFF0D1526),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: active ? const Color(0xFF00C8A0) : Colors.white12,
          width: active ? 1.5 : 0.5,
        ),
      ),
      child: Column(children: [
        Text(elapsed,
            style: const TextStyle(
                color: Colors.white, fontSize: 48, fontWeight: FontWeight.w200, letterSpacing: 4)),
        const SizedBox(height: 16),
        SizedBox(
          width: 180,
          height: 48,
          child: ElevatedButton.icon(
            style: ElevatedButton.styleFrom(
              backgroundColor: active ? Colors.redAccent : const Color(0xFF00C8A0),
              foregroundColor: active ? Colors.white : Colors.black,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
            ),
            onPressed: onToggle,
            icon: Icon(active ? Icons.stop : Icons.play_arrow),
            label: Text(active ? 'End Ride' : 'Start Ride',
                style: const TextStyle(fontWeight: FontWeight.w700)),
          ),
        ),
      ]),
    );
  }
}

class _TelemetryCard extends StatelessWidget {
  final String label;
  final String value;
  final String unit;
  final IconData icon;
  final Color color;
  const _TelemetryCard({required this.label, required this.value, required this.unit, required this.icon, required this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFF0D1526),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Icon(icon, color: color, size: 20),
        const Spacer(),
        RichText(
          text: TextSpan(
            children: [
              TextSpan(
                  text: value,
                  style: TextStyle(color: color, fontSize: 24, fontWeight: FontWeight.w700)),
              TextSpan(
                  text: ' $unit',
                  style: const TextStyle(color: Colors.white38, fontSize: 12)),
            ],
          ),
        ),
        const SizedBox(height: 2),
        Text(label, style: const TextStyle(color: Colors.white54, fontSize: 12)),
      ]),
    );
  }
}
