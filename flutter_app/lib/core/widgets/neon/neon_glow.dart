import 'package:flutter/material.dart';

import '../../constants/colors.dart';

class NeonGlow extends StatefulWidget {
  final Widget child;
  final Color glowColor;
  final double intensity;
  final bool animate;
  final Duration duration;

  const NeonGlow({
    super.key,
    required this.child,
    this.glowColor = AppColors.neonCyan,
    this.intensity = 20,
    this.animate = false,
    this.duration = const Duration(milliseconds: 1500),
  });

  @override
  State<NeonGlow> createState() => _NeonGlowState();
}

class _NeonGlowState extends State<NeonGlow>
    with SingleTickerProviderStateMixin {
  AnimationController? _controller;
  Animation<double>? _animation;

  @override
  void initState() {
    super.initState();
    if (widget.animate) {
      _controller = AnimationController(
        vsync: this,
        duration: widget.duration,
      )..repeat(reverse: true);
      _animation = Tween<double>(begin: 0.5, end: 1.0).animate(_controller!);
    }
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (!widget.animate || _animation == null) {
      return _buildGlow(widget.intensity);
    }

    return AnimatedBuilder(
      animation: _animation!,
      builder: (context, child) {
        return _buildGlow(widget.intensity * _animation!.value);
      },
    );
  }

  Widget _buildGlow(double blur) {
    return Container(
      decoration: BoxDecoration(
        boxShadow: [
          BoxShadow(
            color: widget.glowColor.withOpacity(0.6),
            blurRadius: blur,
            spreadRadius: blur * 0.2,
          ),
          BoxShadow(
            color: widget.glowColor.withOpacity(0.3),
            blurRadius: blur * 2,
            spreadRadius: blur * 0.5,
          ),
        ],
      ),
      child: widget.child,
    );
  }
}
