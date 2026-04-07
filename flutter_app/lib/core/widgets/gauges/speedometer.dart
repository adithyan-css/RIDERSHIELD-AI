import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../constants/colors.dart';
import '../../constants/typography.dart';

class Speedometer extends StatelessWidget {
  final double speed;
  final double maxSpeed;
  final double size;

  const Speedometer({
    super.key,
    required this.speed,
    this.maxSpeed = 120,
    this.size = 240,
  });

  @override
  Widget build(BuildContext context) {
    final clamped = speed.clamp(0, maxSpeed);
    final progress = maxSpeed == 0 ? 0.0 : (clamped / maxSpeed);

    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        alignment: Alignment.center,
        children: [
          CustomPaint(
            size: Size.square(size),
            painter: _SpeedometerPainter(progress),
          ),
          Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                clamped.toStringAsFixed(0),
                style: AppTypography.speedometer.copyWith(fontSize: 56),
              ),
              Text('KM/H', style: AppTypography.label),
            ],
          ),
        ],
      ),
    );
  }
}

class _SpeedometerPainter extends CustomPainter {
  final double progress;

  _SpeedometerPainter(this.progress);

  @override
  void paint(Canvas canvas, Size size) {
    final center = size.center(Offset.zero);
    final radius = (size.shortestSide / 2) - 12;

    const start = math.pi * 0.75;
    const sweepMax = math.pi * 1.5;
    final sweep = sweepMax * progress;

    final basePaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 14
      ..color = AppColors.surfaceElevated;

    final activePaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..strokeWidth = 14
      ..shader = const LinearGradient(
        colors: [AppColors.neonCyan, AppColors.neonBlue],
      ).createShader(Rect.fromCircle(center: center, radius: radius));

    canvas.drawArc(Rect.fromCircle(center: center, radius: radius), start, sweepMax,
        false, basePaint);
    canvas.drawArc(Rect.fromCircle(center: center, radius: radius), start, sweep,
        false, activePaint);
  }

  @override
  bool shouldRepaint(covariant _SpeedometerPainter oldDelegate) {
    return oldDelegate.progress != progress;
  }
}
