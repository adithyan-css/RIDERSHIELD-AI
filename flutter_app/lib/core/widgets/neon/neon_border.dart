import 'package:flutter/material.dart';

import '../../constants/colors.dart';

class NeonBorder extends StatefulWidget {
  final Widget child;
  final Color color;
  final bool pulse;
  final double borderRadius;

  const NeonBorder({
    super.key,
    required this.child,
    this.color = AppColors.neonCyan,
    this.pulse = true,
    this.borderRadius = 16,
  });

  @override
  State<NeonBorder> createState() => _NeonBorderState();
}

class _NeonBorderState extends State<NeonBorder>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _animation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1400),
    );
    _animation = Tween<double>(begin: 0.35, end: 1.0).animate(_controller);
    if (widget.pulse) {
      _controller.repeat(reverse: true);
    } else {
      _controller.value = 1;
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _animation,
      builder: (context, child) {
        final alpha = _animation.value;
        return Container(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(widget.borderRadius),
            border: Border.all(
              color: widget.color.withOpacity(alpha),
              width: 1.2,
            ),
            boxShadow: [
              BoxShadow(
                color: widget.color.withOpacity(alpha * 0.35),
                blurRadius: 14,
                spreadRadius: 1,
              ),
            ],
          ),
          child: widget.child,
        );
      },
    );
  }
}
