import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'providers/rider_provider.dart';
import 'providers/hazard_provider.dart';
import 'providers/ble_provider.dart';
import 'screens/main_shell.dart';
import 'screens/login_screen.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const RiderShieldApp());
}

class RiderShieldApp extends StatelessWidget {
  const RiderShieldApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => RiderProvider()),
        ChangeNotifierProvider(create: (_) => HazardProvider()),
        ChangeNotifierProvider(create: (_) => BleProvider()),
      ],
      child: MaterialApp(
        title: 'RiderShield',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          colorScheme: ColorScheme.fromSeed(
            seedColor: const Color(0xFF00C8A0),
            brightness: Brightness.dark,
          ),
          scaffoldBackgroundColor: const Color(0xFF0A0F1E),
          useMaterial3: true,
          fontFamily: 'Inter',
        ),
        home: const AuthGate(),
      ),
    );
  }
}

class AuthGate extends StatefulWidget {
  const AuthGate({super.key});

  @override
  State<AuthGate> createState() => _AuthGateState();
}

class _AuthGateState extends State<AuthGate> {
  @override
  void initState() {
    super.initState();
    _checkLogin();
  }

  Future<void> _checkLogin() async {
    final rider = context.read<RiderProvider>();
    await rider.loadFromStorage();
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<RiderProvider>(
      builder: (context, rider, _) {
        if (rider.isLoggedIn) return const MainShell();
        return const LoginScreen();
      },
    );
  }
}
