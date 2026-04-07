import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'providers/auth_provider.dart';
import 'screens/login_screen.dart';
import 'screens/main_navigation_screen.dart';

const String _apiBaseUrl = String.fromEnvironment('API_BASE_URL');
const String _wsBaseUrl = String.fromEnvironment('WS_BASE_URL');
const String _mqttBroker = String.fromEnvironment('MQTT_BROKER', defaultValue: '');
const String _appEnv = String.fromEnvironment('APP_ENV', defaultValue: 'demo');

void _validateAndLogStartupConfig() {
  final missing = <String>[];
  if (_apiBaseUrl.isEmpty) {
    missing.add('API_BASE_URL');
  }
  if (_wsBaseUrl.isEmpty) {
    missing.add('WS_BASE_URL');
  }

  if (missing.isNotEmpty) {
    throw StateError('Missing required dart-define values: ${missing.join(', ')}');
  }

  debugPrint(
    'RiderShield startup env=$_appEnv api=$_apiBaseUrl ws=$_wsBaseUrl mqtt=${_mqttBroker.isEmpty ? 'not_set' : _mqttBroker}',
  );
}

void main() {
  _validateAndLogStartupConfig();
  runApp(
    const ProviderScope(
      child: RiderShieldApp(),
    ),
  );
}

class RiderShieldApp extends ConsumerWidget {
  const RiderShieldApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authProvider);

    return MaterialApp(
      title: 'RiderShield AI',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF2563EB),
          brightness: Brightness.dark,
        ),
        useMaterial3: true,
        // CardThemeData is required on current Flutter SDKs.
        cardTheme: CardThemeData(
          elevation: 8,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
          ),
        ),
      ),
      home: authState.isAuthenticated
          ? const MainNavigationScreen()
          : const LoginScreen(),
    );
  }
}
