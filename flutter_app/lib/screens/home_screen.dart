import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:provider/provider.dart';
import '../providers/rider_provider.dart';
import '../providers/hazard_provider.dart';
import '../services/location_service.dart';
import '../widgets/alert_sheet.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final MapController _mapCtrl = MapController();
  LatLng _center = const LatLng(11.0168, 76.9558); // Coimbatore default

  @override
  void initState() {
    super.initState();
    _init();
  }

  Future<void> _init() async {
    final pos = locationService.lastPosition;
    if (pos != null) {
      _center = LatLng(pos.latitude, pos.longitude);
    }
    if (mounted) {
      await context
          .read<HazardProvider>()
          .fetchNearby(_center.latitude, _center.longitude);
    }
  }

  @override
  Widget build(BuildContext context) {
    final hazards = context.watch<HazardProvider>();
    final rider = context.watch<RiderProvider>();
    const teal = Color(0xFF00C8A0);

    return Scaffold(
      backgroundColor: const Color(0xFF0A0F1E),
      body: Stack(
        children: [
          FlutterMap(
            mapController: _mapCtrl,
            options: MapOptions(
              initialCenter: _center,
              initialZoom: 15,
              backgroundColor: const Color(0xFF0D1526),
            ),
            children: [
              TileLayer(
                urlTemplate:
                    'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
                subdomains: const ['a', 'b', 'c', 'd'],
                userAgentPackageName: 'com.ridershield.app',
              ),
              // Hazard markers
              MarkerLayer(
                markers: hazards.verifiedHazards.map((h) {
                  final lat = (h['lat'] ?? 0).toDouble();
                  final lng = (h['lng'] ?? 0).toDouble();
                  final cls = h['hazard_class'] ?? 'flood';
                  return Marker(
                    point: LatLng(lat, lng),
                    width: 36,
                    height: 36,
                    child: _HazardPin(hazardClass: cls),
                  );
                }).toList(),
              ),
              // Rider position
              if (locationService.lastPosition != null)
                MarkerLayer(markers: [
                  Marker(
                    point: LatLng(
                      locationService.lastPosition!.latitude,
                      locationService.lastPosition!.longitude,
                    ),
                    width: 48,
                    height: 48,
                    child: const _RiderDot(),
                  ),
                ]),
            ],
          ),

          // Top bar
          Positioned(
            top: 0, left: 0, right: 0,
            child: SafeArea(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Row(children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                    decoration: BoxDecoration(
                      color: const Color(0xCC0D1526),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Row(children: [
                      const Icon(Icons.shield, color: teal, size: 18),
                      const SizedBox(width: 6),
                      Text('RiderShield',
                          style: const TextStyle(
                              color: teal, fontWeight: FontWeight.w700, fontSize: 15)),
                    ]),
                  ),
                  const Spacer(),
                  _StatusBadge(
                    label: 'WS',
                    active: true,
                    icon: Icons.wifi,
                  ),
                ]),
              ),
            ),
          ),

          // Alert sheet for incoming peer alerts
          if (rider.recentAlerts.isNotEmpty)
            Positioned(
              bottom: 16, left: 12, right: 12,
              child: AlertSheet(alert: rider.recentAlerts.first),
            ),

          // Refresh FAB
          Positioned(
            right: 16,
            bottom: rider.recentAlerts.isNotEmpty ? 130 : 80,
            child: FloatingActionButton.small(
              backgroundColor: teal,
              foregroundColor: Colors.black,
              onPressed: _init,
              child: const Icon(Icons.refresh),
            ),
          ),
        ],
      ),
    );
  }
}

class _HazardPin extends StatelessWidget {
  final String hazardClass;
  const _HazardPin({required this.hazardClass});

  Color get _color {
    switch (hazardClass) {
      case 'flood': return const Color(0xFF3B8BD4);
      case 'pothole': return const Color(0xFFFF6B35);
      case 'rough': return const Color(0xFFFFB347);
      default: return Colors.grey;
    }
  }

  IconData get _icon {
    switch (hazardClass) {
      case 'flood': return Icons.water;
      case 'pothole': return Icons.report_problem;
      case 'rough': return Icons.terrain;
      default: return Icons.warning;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: _color.withOpacity(0.9),
        shape: BoxShape.circle,
        boxShadow: [BoxShadow(color: _color.withOpacity(0.5), blurRadius: 8)],
      ),
      child: Icon(_icon, color: Colors.white, size: 20),
    );
  }
}

class _RiderDot extends StatelessWidget {
  const _RiderDot();

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF00C8A0),
        shape: BoxShape.circle,
        border: Border.all(color: Colors.white, width: 2),
        boxShadow: const [
          BoxShadow(color: Color(0x8000C8A0), blurRadius: 16, spreadRadius: 4)
        ],
      ),
      child: const Icon(Icons.navigation, color: Colors.white, size: 22),
    );
  }
}

class _StatusBadge extends StatelessWidget {
  final String label;
  final bool active;
  final IconData icon;
  const _StatusBadge({required this.label, required this.active, required this.icon});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: active
            ? const Color(0xFF00C8A0).withOpacity(0.15)
            : Colors.red.withOpacity(0.15),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: active ? const Color(0xFF00C8A0) : Colors.red,
          width: 0.8,
        ),
      ),
      child: Row(children: [
        Icon(icon, size: 13, color: active ? const Color(0xFF00C8A0) : Colors.red),
        const SizedBox(width: 4),
        Text(label,
            style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w600,
                color: active ? const Color(0xFF00C8A0) : Colors.red)),
      ]),
    );
  }
}
