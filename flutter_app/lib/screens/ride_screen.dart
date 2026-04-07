import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'dart:async';

import '../providers/app_state_provider.dart';
import '../providers/auth_provider.dart';
import '../widgets/fatigue_gauge.dart';

class RideScreen extends ConsumerStatefulWidget {
  const RideScreen({super.key});

  @override
  ConsumerState<RideScreen> createState() => _RideScreenState();
}

class _RideScreenState extends ConsumerState<RideScreen> {
  Timer? _pollTimer;
  int _fatiguePct = 0;
  bool _loadingFatigue = false;

  @override
  void initState() {
    super.initState();
    _refreshFatigue();
    _pollTimer = Timer.periodic(const Duration(seconds: 6), (_) => _refreshFatigue());
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }

  int get _fatigueLevel {
    if (_fatiguePct <= 25) return 1;
    if (_fatiguePct <= 50) return 2;
    if (_fatiguePct <= 75) return 3;
    return 4;
  }

  Color get _fatigueColor {
    if (_fatiguePct <= 25) return Colors.green;
    if (_fatiguePct <= 50) return Colors.orange;
    if (_fatiguePct <= 75) return Colors.deepOrange;
    return Colors.red;
  }

  Future<void> _refreshFatigue() async {
    final rider = ref.read(authProvider).rider;
    if (rider == null || _loadingFatigue) return;

    setState(() {
      _loadingFatigue = true;
    });
    try {
      final api = ref.read(apiServiceProvider);
      final state = await api.getRiderState(rider.id);
      final raw = (state['fatigue_level'] as num?)?.toDouble() ?? 0;
      final nextPct = raw.clamp(0, 100).round();
      if (!mounted) return;
      setState(() {
        _fatiguePct = nextPct;
      });
    } catch (_) {
      // Keep last known value during transient backend/network issues.
    } finally {
      if (mounted) {
        setState(() {
          _loadingFatigue = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final appState = ref.watch(appStateProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Active Ride'),
      ),
      body: Column(
        children: [
          // Speedometer Card
          Expanded(
            flex: 2,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Card(
                child: Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(
                        '${(appState.currentSpeed ?? 0).toStringAsFixed(0)}',
                        style: Theme.of(context).textTheme.displayLarge?.copyWith(
                              fontWeight: FontWeight.bold,
                              color: Theme.of(context).colorScheme.primary,
                            ),
                      ),
                      Text(
                        'KM/H',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 24),
                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 20),
                        child: Column(
                          children: [
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                const Text('AI Fatigue Monitor'),
                                Text(
                                  '$_fatiguePct%',
                                  style: TextStyle(
                                    color: _fatigueColor,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 8),
                            FatigueGauge(level: _fatigueLevel),
                            const SizedBox(height: 8),
                            ClipRRect(
                              borderRadius: BorderRadius.circular(8),
                              child: LinearProgressIndicator(
                                value: _fatiguePct / 100,
                                minHeight: 8,
                                color: _fatigueColor,
                                backgroundColor: Colors.white12,
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 16),
                      if (appState.currentSpeed != null && appState.currentSpeed! > 60)
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 16,
                            vertical: 8,
                          ),
                          decoration: BoxDecoration(
                            color: Colors.red,
                            borderRadius: BorderRadius.circular(20),
                          ),
                          child: const Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(Icons.speed, color: Colors.white),
                              SizedBox(width: 8),
                              Text(
                                'SPEED WARNING',
                                style: TextStyle(
                                  color: Colors.white,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ],
                          ),
                        ),
                    ],
                  ),
                ),
              ),
            ),
          ),

          // Stats Grid
          Expanded(
            flex: 3,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: GridView.count(
                crossAxisCount: 2,
                crossAxisSpacing: 16,
                mainAxisSpacing: 16,
                children: [
                  _statCard(
                    context,
                    'Fatigue Level',
                    '$_fatiguePct%',
                    Icons.psychology,
                    _fatigueColor,
                  ),
                  _statCard(
                    context,
                    'Distance',
                    '12.5 km',
                    Icons.route,
                    Colors.blue,
                  ),
                  _statCard(
                    context,
                    'Duration',
                    '45 min',
                    Icons.timer,
                    Colors.orange,
                  ),
                  _statCard(
                    context,
                    'Hazards',
                    '${appState.hazards.length}',
                    Icons.warning,
                    Colors.red,
                  ),
                ],
              ),
            ),
          ),

          // Safety Score
          Padding(
            padding: const EdgeInsets.all(16),
            child: Card(
              child: ListTile(
                leading: const Icon(Icons.shield, color: Colors.green, size: 40),
                title: const Text('Safety Score'),
                subtitle: const Text('Based on your riding behavior'),
                trailing: Text(
                  '94%',
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                        color: Colors.green,
                        fontWeight: FontWeight.bold,
                      ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _statCard(
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
            Icon(icon, size: 40, color: color),
            const SizedBox(height: 8),
            Text(
              value,
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.bold,
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
