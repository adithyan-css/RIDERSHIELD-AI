import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import '../services/api_service.dart';

class DeliveryScreen extends StatefulWidget {
  const DeliveryScreen({super.key});

  @override
  State<DeliveryScreen> createState() => _DeliveryScreenState();
}

class _DeliveryScreenState extends State<DeliveryScreen> {
  final _digipinCtrl = TextEditingController();
  final _orderCtrl = TextEditingController();
  Map<String, dynamic>? _resolved;
  Map<String, dynamic>? _activeDelivery;
  bool _loading = false;
  String? _error;

  Future<void> _resolve() async {
    final code = _digipinCtrl.text.trim();
    if (code.isEmpty) return;
    setState(() { _loading = true; _error = null; });
    try {
      final res = await ApiService.resolveDigipin(code);
      setState(() => _resolved = res);
    } catch (e) {
      setState(() => _error = 'Could not resolve DIGIPIN');
    } finally {
      setState(() => _loading = false);
    }
  }

  Future<void> _startDelivery() async {
    if (_resolved == null || _orderCtrl.text.isEmpty) return;
    setState(() => _loading = true);
    try {
      final res = await ApiService.startDelivery(
        _orderCtrl.text.trim(),
        _digipinCtrl.text.trim(),
        'PICKUP-${_digipinCtrl.text.trim()}',
      );
      setState(() => _activeDelivery = res);
    } catch (e) {
      setState(() => _error = 'Failed to start delivery');
    } finally {
      setState(() => _loading = false);
    }
  }

  Future<void> _verifyDelivery() async {
    if (_activeDelivery == null) return;
    setState(() => _loading = true);
    try {
      await ApiService.verifyDelivery(_activeDelivery!['delivery_id'], true, null);
      setState(() { _activeDelivery = null; _resolved = null; _digipinCtrl.clear(); _orderCtrl.clear(); });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('✅ Delivery verified!'), backgroundColor: Color(0xFF00C8A0)));
      }
    } finally {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    const teal = Color(0xFF00C8A0);
    return Scaffold(
      backgroundColor: const Color(0xFF0A0F1E),
      appBar: AppBar(
        backgroundColor: const Color(0xFF0D1526),
        title: const Text('Delivery', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w600)),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(children: [
          // DIGIPIN resolver
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: const Color(0xFF0D1526),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: Colors.white10),
            ),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Text('DIGIPIN Resolver',
                  style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w600)),
              const SizedBox(height: 4),
              const Text('Enter 10-digit DIGIPIN code for delivery location',
                  style: TextStyle(color: Colors.white38, fontSize: 12)),
              const SizedBox(height: 14),
              TextField(
                controller: _digipinCtrl,
                style: const TextStyle(color: Colors.white),
                decoration: InputDecoration(
                  hintText: 'e.g. 5F3-KJ2-9P4Q',
                  hintStyle: const TextStyle(color: Colors.white24),
                  filled: true,
                  fillColor: const Color(0xFF131C33),
                  border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(10), borderSide: BorderSide.none),
                  suffixIcon: IconButton(
                    icon: _loading
                        ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Color(0xFF00C8A0)))
                        : const Icon(Icons.search, color: Color(0xFF00C8A0)),
                    onPressed: _resolve,
                  ),
                ),
                onSubmitted: (_) => _resolve(),
              ),
              if (_error != null) ...[
                const SizedBox(height: 8),
                Text(_error!, style: const TextStyle(color: Colors.redAccent, fontSize: 12)),
              ],
            ]),
          ),

          // Resolved result
          if (_resolved != null) ...[
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: teal.withOpacity(0.08),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: teal.withOpacity(0.3)),
              ),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  const Icon(Icons.location_on, color: Color(0xFF00C8A0), size: 18),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      _resolved!['address'] ?? '',
                      style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w500),
                    ),
                  ),
                ]),
                const SizedBox(height: 8),
                Text(
                  'Lat: ${_resolved!['lat']?.toStringAsFixed(6)}  Lng: ${_resolved!['lng']?.toStringAsFixed(6)}',
                  style: const TextStyle(color: Colors.white54, fontSize: 12),
                ),
                Text(
                  'Cell size: ${_resolved!['cell_size_m']}m',
                  style: const TextStyle(color: Colors.white38, fontSize: 11),
                ),
                const SizedBox(height: 12),
                // Mini map
                ClipRRect(
                  borderRadius: BorderRadius.circular(10),
                  child: SizedBox(
                    height: 160,
                    child: FlutterMap(
                      options: MapOptions(
                        initialCenter: LatLng(
                          (_resolved!['lat'] as num).toDouble(),
                          (_resolved!['lng'] as num).toDouble(),
                        ),
                        initialZoom: 17,
                      ),
                      children: [
                        TileLayer(
                          urlTemplate:
                              'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
                          subdomains: const ['a', 'b', 'c', 'd'],
                        ),
                        MarkerLayer(markers: [
                          Marker(
                            point: LatLng(
                              (_resolved!['lat'] as num).toDouble(),
                              (_resolved!['lng'] as num).toDouble(),
                            ),
                            child: const Icon(Icons.location_pin, color: Color(0xFF00C8A0), size: 32),
                          ),
                        ]),
                      ],
                    ),
                  ),
                ),
              ]),
            ),
            const SizedBox(height: 12),
            // Start delivery
            if (_activeDelivery == null) ...[
              TextField(
                controller: _orderCtrl,
                style: const TextStyle(color: Colors.white),
                decoration: InputDecoration(
                  hintText: 'Order ID',
                  hintStyle: const TextStyle(color: Colors.white24),
                  prefixIcon: const Icon(Icons.receipt_long_outlined, color: Colors.white38),
                  filled: true,
                  fillColor: const Color(0xFF131C33),
                  border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(10), borderSide: BorderSide.none),
                ),
              ),
              const SizedBox(height: 10),
              SizedBox(
                width: double.infinity,
                height: 46,
                child: ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(
                      backgroundColor: teal, foregroundColor: Colors.black,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
                  onPressed: _loading ? null : _startDelivery,
                  icon: const Icon(Icons.local_shipping),
                  label: const Text('Start Delivery', style: TextStyle(fontWeight: FontWeight.w700)),
                ),
              ),
            ] else ...[
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: const Color(0xFF0D1526),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: Colors.orangeAccent.withOpacity(0.4)),
                ),
                child: Column(children: [
                  const Row(children: [
                    Icon(Icons.local_shipping, color: Colors.orangeAccent, size: 18),
                    SizedBox(width: 8),
                    Text('Delivery In Progress', style: TextStyle(color: Colors.orangeAccent, fontWeight: FontWeight.w600)),
                  ]),
                  const SizedBox(height: 12),
                  SizedBox(
                    width: double.infinity,
                    height: 46,
                    child: ElevatedButton.icon(
                      style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.greenAccent, foregroundColor: Colors.black,
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
                      onPressed: _loading ? null : _verifyDelivery,
                      icon: const Icon(Icons.check_circle),
                      label: const Text('Mark Delivered', style: TextStyle(fontWeight: FontWeight.w700)),
                    ),
                  ),
                ]),
              ),
            ],
          ],
        ]),
      ),
    );
  }
}
