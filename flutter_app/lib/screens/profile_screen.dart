import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/rider_provider.dart';
import '../services/api_service.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  Map<String, dynamic>? _history;
  bool _loading = false;

  @override
  void initState() {
    super.initState();
    _loadHistory();
  }

  Future<void> _loadHistory() async {
    setState(() => _loading = true);
    try {
      final h = await ApiService.getRiderHistory();
      setState(() => _history = h);
    } catch (_) {}
    setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    const teal = Color(0xFF00C8A0);
    final rider = context.watch<RiderProvider>();
    final hazards = (_history?['hazards'] as List?) ?? [];
    final deliveries = (_history?['deliveries'] as List?) ?? [];

    return Scaffold(
      backgroundColor: const Color(0xFF0A0F1E),
      appBar: AppBar(
        backgroundColor: const Color(0xFF0D1526),
        title: const Text('Profile', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w600)),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout, color: Colors.redAccent),
            onPressed: () => rider.logout(),
          )
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(children: [
          // Profile card
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: const Color(0xFF0D1526),
              borderRadius: BorderRadius.circular(20),
            ),
            child: Row(children: [
              CircleAvatar(
                radius: 30,
                backgroundColor: teal.withOpacity(0.2),
                child: const Icon(Icons.person, color: Color(0xFF00C8A0), size: 32),
              ),
              const SizedBox(width: 16),
              Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(rider.name ?? 'Rider',
                    style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w600)),
                Text('ID: ${rider.riderId?.substring(0, 8)}...',
                    style: const TextStyle(color: Colors.white38, fontSize: 12)),
              ]),
            ]),
          ),
          const SizedBox(height: 16),
          // Stats row
          Row(children: [
            _StatCard(label: 'Hazards Reported', value: hazards.length.toString(), color: const Color(0xFF3B8BD4)),
            const SizedBox(width: 12),
            _StatCard(label: 'Deliveries', value: deliveries.length.toString(), color: teal),
          ]),
          const SizedBox(height: 16),
          // Hazard history
          const Align(
            alignment: Alignment.centerLeft,
            child: Text('Recent Hazards', style: TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.w600)),
          ),
          const SizedBox(height: 8),
          if (_loading)
            const Center(child: CircularProgressIndicator(color: Color(0xFF00C8A0)))
          else if (hazards.isEmpty)
            const Text('No hazards reported yet', style: TextStyle(color: Colors.white38, fontSize: 13))
          else
            ...hazards.take(5).map((h) => Container(
                  margin: const EdgeInsets.only(bottom: 8),
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: const Color(0xFF0D1526),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: Colors.white10),
                  ),
                  child: Row(children: [
                    const Icon(Icons.warning_amber, color: Colors.orangeAccent, size: 18),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text(h['hazard_class'] ?? 'unknown',
                            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w500, fontSize: 13)),
                        Text('Confidence: ${((h['confidence'] ?? 0) * 100).toStringAsFixed(0)}%',
                            style: const TextStyle(color: Colors.white38, fontSize: 11)),
                      ]),
                    ),
                    Text(h['verified'] == true ? '✓ Verified' : 'Pending',
                        style: TextStyle(
                            color: h['verified'] == true ? teal : Colors.white38,
                            fontSize: 11,
                            fontWeight: FontWeight.w600)),
                  ]),
                )),
        ]),
      ),
    );
  }
}

class _StatCard extends StatelessWidget {
  final String label;
  final String value;
  final Color color;
  const _StatCard({required this.label, required this.value, required this.color});

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: const Color(0xFF0D1526),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: color.withOpacity(0.3)),
        ),
        child: Column(children: [
          Text(value, style: TextStyle(color: color, fontSize: 28, fontWeight: FontWeight.w700)),
          const SizedBox(height: 4),
          Text(label, style: const TextStyle(color: Colors.white54, fontSize: 12), textAlign: TextAlign.center),
        ]),
      ),
    );
  }
}
