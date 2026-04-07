import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/rider_model.dart';
import '../services/api_service.dart';

final apiServiceProvider = Provider((ref) => ApiService());

final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  return AuthNotifier(ref.read(apiServiceProvider));
});

class AuthState {
  final Rider? rider;
  final bool isLoading;
  final String? error;

  AuthState({
    this.rider,
    this.isLoading = false,
    this.error,
  });

  bool get isAuthenticated => rider != null;

  AuthState copyWith({
    Rider? rider,
    bool? isLoading,
    String? error,
  }) {
    return AuthState(
      rider: rider ?? this.rider,
      isLoading: isLoading ?? this.isLoading,
      error: error,
    );
  }
}

class AuthNotifier extends StateNotifier<AuthState> {
  final ApiService _apiService;

  AuthNotifier(this._apiService) : super(AuthState());

  Future<void> login(String phone, String password) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final rider = await _apiService.login(phone, password);
      _apiService.setToken(rider.token);
      state = state.copyWith(rider: rider, isLoading: false);
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  void logout() {
    _apiService.clearToken();
    state = AuthState();
  }
}
