import 'package:flutter/material.dart';

import '../../core/constants/colors.dart';
import '../../core/widgets/glass/glass_container.dart';

class NavDock extends StatelessWidget {
  final int index;
  final ValueChanged<int> onChanged;

  const NavDock({
    super.key,
    required this.index,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return GlassContainer(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        children: [
          _item(icon: Icons.speed, tab: 0, label: 'Ride'),
          _item(icon: Icons.map, tab: 1, label: 'Map'),
          _item(icon: Icons.local_shipping, tab: 2, label: 'Delivery'),
          _item(icon: Icons.headset, tab: 3, label: 'Helmet'),
        ],
      ),
    );
  }

  Widget _item({
    required IconData icon,
    required int tab,
    required String label,
  }) {
    final selected = tab == index;
    return InkWell(
      onTap: () => onChanged(tab),
      borderRadius: BorderRadius.circular(12),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              color: selected ? AppColors.neonCyan : Colors.white70,
              size: 22,
            ),
            Text(
              label,
              style: TextStyle(
                color: selected ? AppColors.neonCyan : Colors.white70,
                fontSize: 11,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
