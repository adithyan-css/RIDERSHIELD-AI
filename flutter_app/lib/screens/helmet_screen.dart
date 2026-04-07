import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/ble_provider.dart';
import '../services/tts_service.dart';

class HelmetScreen extends StatelessWidget {
  const HelmetScreen({super.key});

  @override
  Widget build(BuildContext context) {
    const teal = Color(0xFF00C8A0);
    final ble = context.watch<BleProvider>();

    return Scaffold(
      backgroundColor: const Color(0xFF0A0F1E),
      appBar: AppBar(
        backgroundColor: const Color(0xFF0D1526),
        title: const Text('Helmet', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w600)),
        actions: [
          IconButton(
            icon: const Icon(Icons.volume_up, color: Color(0xFF00C8A0)),
            onPressed: () {
              ttsService.speak('Helmet status checked. All systems active.');
            },
          )
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(children: [
          // Helmet status card
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: const Color(0xFF0D1526),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(
                color: ble.connectedHelmet != null ? teal : Colors.white12,
                width: ble.connectedHelmet != null ? 1.5 : 0.5,
              ),
            ),
            child: Row(children: [
              Container(
                width: 64,
                height: 64,
                decoration: BoxDecoration(
                  color: (ble.connectedHelmet != null ? teal : Colors.white24).withOpacity(0.15),
                  shape: BoxShape.circle,
                ),
                child: Icon(
                  Icons.sports_motorsports,
                  color: ble.connectedHelmet != null ? teal : Colors.white38,
                  size: 32,
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(
                    ble.connectedHelmet?.name ?? 'No helmet paired',
                    style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w600),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    ble.connectedHelmet != null ? '🟢 Connected' : '⚪ Disconnected',
                    style: TextStyle(
                      color: ble.connectedHelmet != null ? teal : Colors.white38,
                      fontSize: 13,
                    ),
                  ),
                  if (ble.connectedHelmet != null) ...[
                    const SizedBox(height: 4),
                    Text(
                      'Battery: ${ble.connectedHelmet!.batteryPct}%',
                      style: const TextStyle(color: Colors.white54, fontSize: 12),
                    ),
                  ],
                ]),
              ),
            ]),
          ),

          const SizedBox(height: 16),

          // Scan button
          SizedBox(
            width: double.infinity,
            height: 48,
            child: ElevatedButton.icon(
              style: ElevatedButton.styleFrom(
                backgroundColor: ble.connectedHelmet != null ? Colors.redAccent : teal,
                foregroundColor: ble.connectedHelmet != null ? Colors.white : Colors.black,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
              ),
              onPressed: ble.scanning
                  ? null
                  : () async {
                      if (ble.connectedHelmet != null) {
                        ble.disconnect();
                      } else {
                        await ble.startScan();
                      }
                    },
              icon: ble.scanning
                  ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black))
                  : Icon(ble.connectedHelmet != null ? Icons.bluetooth_disabled : Icons.bluetooth_searching),
              label: Text(
                ble.scanning
                    ? 'Scanning...'
                    : ble.connectedHelmet != null
                        ? 'Disconnect'
                        : 'Scan for Helmet',
                style: const TextStyle(fontWeight: FontWeight.w700),
              ),
            ),
          ),

          // Scan results
          if (ble.scannedDevices.isNotEmpty && ble.connectedHelmet == null) ...[
            const SizedBox(height: 16),
            const Align(
              alignment: Alignment.centerLeft,
              child: Text('Found Devices', style: TextStyle(color: Colors.white70, fontSize: 14, fontWeight: FontWeight.w600)),
            ),
            const SizedBox(height: 8),
            ...ble.scannedDevices.map((d) => GestureDetector(
              onTap: () => ble.connect(d),
              child: Container(
                margin: const EdgeInsets.only(bottom: 8),
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: const Color(0xFF0D1526),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: teal.withOpacity(0.3)),
                ),
                child: Row(children: [
                  const Icon(Icons.bluetooth, color: Color(0xFF00C8A0), size: 20),
                  const SizedBox(width: 12),
                  Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(d.name, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w500)),
                    Text(d.id, style: const TextStyle(color: Colors.white38, fontSize: 11)),
                  ]),
                  const Spacer(),
                  const Text('Connect', style: TextStyle(color: Color(0xFF00C8A0), fontSize: 13, fontWeight: FontWeight.w600)),
                ]),
              ),
            )),
          ],

          const SizedBox(height: 16),

          // Features grid
          if (ble.connectedHelmet != null) ...[
            GridView.count(
              crossAxisCount: 2,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              mainAxisSpacing: 12,
              crossAxisSpacing: 12,
              childAspectRatio: 1.6,
              children: [
                _FeatureCard(
                  icon: Icons.videocam,
                  label: 'Camera',
                  active: ble.connectedHelmet!.cameraActive,
                  onTap: () => ble.updateHelmetStatus(camera: !ble.connectedHelmet!.cameraActive),
                ),
                _FeatureCard(
                  icon: Icons.volume_up,
                  label: 'Voice Alerts',
                  active: ttsService.enabled,
                  onTap: () {
                    ttsService.toggle();
                    // ignore: invalid_use_of_protected_member
                    (context as Element).markNeedsBuild();
                  },
                ),
                _FeatureCard(icon: Icons.sensors, label: 'IMU Active', active: true, onTap: () {}),
                _FeatureCard(icon: Icons.fiber_manual_record, label: 'Recording', active: false, onTap: () {}),
              ],
            ),
          ],
        ]),
      ),
    );
  }
}

class _FeatureCard extends StatelessWidget {
  final IconData icon;
  final String label;
  final bool active;
  final VoidCallback onTap;
  const _FeatureCard({required this.icon, required this.label, required this.active, required this.onTap});

  @override
  Widget build(BuildContext context) {
    const teal = Color(0xFF00C8A0);
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: active ? teal.withOpacity(0.1) : const Color(0xFF0D1526),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: active ? teal.withOpacity(0.4) : Colors.white10),
        ),
        child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
          Icon(icon, color: active ? teal : Colors.white38, size: 24),
          const SizedBox(height: 6),
          Text(label, style: TextStyle(color: active ? Colors.white : Colors.white38, fontSize: 12)),
          Text(active ? 'ON' : 'OFF',
              style: TextStyle(
                  color: active ? teal : Colors.white24,
                  fontSize: 11,
                  fontWeight: FontWeight.w700)),
        ]),
      ),
    );
  }
}
