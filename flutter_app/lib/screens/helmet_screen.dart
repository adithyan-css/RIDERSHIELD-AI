import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class HelmetScreen extends ConsumerWidget {
  const HelmetScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Mock data - in real app, connect to Bluetooth
    final isConnected = true;
    final batteryLevel = 78;
    final isWorn = true;
    final temperature = 24.5;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Smart Helmet'),
        actions: [
          IconButton(
            icon: const Icon(Icons.bluetooth_connected),
            onPressed: () {
              // Open Bluetooth settings
            },
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            // Helmet Status Card
            Card(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  children: [
                    Stack(
                      alignment: Alignment.center,
                      children: [
                        SizedBox(
                          width: 150,
                          height: 150,
                          child: CircularProgressIndicator(
                            value: batteryLevel / 100,
                            strokeWidth: 12,
                            backgroundColor: Colors.grey.shade800,
                            valueColor: AlwaysStoppedAnimation<Color>(
                              batteryLevel > 20 ? Colors.green : Colors.red,
                            ),
                          ),
                        ),
                        Column(
                          children: [
                            Icon(
                              Icons.headset_mic,
                              size: 60,
                              color: isConnected ? Colors.green : Colors.grey,
                            ),
                            const SizedBox(height: 8),
                            Text(
                              '$batteryLevel%',
                              style: Theme.of(context).textTheme.headlineMedium,
                            ),
                          ],
                        ),
                      ],
                    ),
                    const SizedBox(height: 24),
                    Text(
                      isConnected ? 'Connected' : 'Disconnected',
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                            color: isConnected ? Colors.green : Colors.red,
                          ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),

            // Status Grid
            GridView.count(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              crossAxisCount: 2,
              crossAxisSpacing: 16,
              mainAxisSpacing: 16,
              children: [
                _statusCard(
                  context,
                  'Wearing Status',
                  isWorn ? 'WORN' : 'NOT WORN',
                  isWorn ? Icons.check_circle : Icons.error,
                  isWorn ? Colors.green : Colors.orange,
                ),
                _statusCard(
                  context,
                  'Temperature',
                  '${temperature.toStringAsFixed(1)}°C',
                  Icons.thermostat,
                  Colors.blue,
                ),
                _statusCard(
                  context,
                  'Microphone',
                  'ON',
                  Icons.mic,
                  Colors.purple,
                ),
                _statusCard(
                  context,
                  'Speakers',
                  'ON',
                  Icons.speaker,
                  Colors.teal,
                ),
              ],
            ),
            const SizedBox(height: 16),

            // Safety Features
            Card(
              child: Column(
                children: [
                  ListTile(
                    leading: const Icon(Icons.emergency, color: Colors.red),
                    title: const Text('Emergency SOS'),
                    subtitle:
                        const Text('Auto-detect crashes and alert emergency contacts'),
                    trailing: Switch(
                      value: true,
                      onChanged: (v) {},
                    ),
                  ),
                  const Divider(height: 1),
                  ListTile(
                    leading:
                        const Icon(Icons.record_voice_over, color: Colors.orange),
                    title: const Text('Voice Alerts'),
                    subtitle: const Text('Read hazard warnings aloud'),
                    trailing: Switch(
                      value: true,
                      onChanged: (v) {},
                    ),
                  ),
                  const Divider(height: 1),
                  ListTile(
                    leading: const Icon(Icons.navigation, color: Colors.blue),
                    title: const Text('Turn-by-Turn Navigation'),
                    subtitle: const Text('Audio navigation instructions'),
                    trailing: Switch(
                      value: true,
                      onChanged: (v) {},
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _statusCard(
    BuildContext context,
    String title,
    String value,
    IconData icon,
    Color color,
  ) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 32, color: color),
            const SizedBox(height: 8),
            Text(
              value,
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: color,
                  ),
            ),
            Text(
              title,
              style: Theme.of(context).textTheme.bodySmall,
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}
