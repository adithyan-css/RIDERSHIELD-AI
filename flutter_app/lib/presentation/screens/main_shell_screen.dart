import 'package:flutter/material.dart';

import '../../core/constants/colors.dart';
import '../components/nav_dock.dart';
import 'delivery_queue_screen.dart';
import 'helmet_control_screen.dart';
import 'live_map_screen.dart';
import 'rider_dashboard_screen.dart';

class MainShellScreen extends StatefulWidget {
  const MainShellScreen({super.key});

  @override
  State<MainShellScreen> createState() => _MainShellScreenState();
}

class _MainShellScreenState extends State<MainShellScreen> {
  int _index = 0;

  final _pages = const [
    RiderDashboardScreen(),
    LiveMapScreen(),
    DeliveryQueueScreen(),
    HelmetControlScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.deepBlack,
      body: Stack(
        children: [
          Positioned.fill(child: _pages[_index]),
          Positioned(
            left: 12,
            right: 12,
            bottom: 14,
            child: NavDock(
              index: _index,
              onChanged: (value) => setState(() => _index = value),
            ),
          ),
        ],
      ),
    );
  }
}
