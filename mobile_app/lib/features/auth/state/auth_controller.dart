import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/app_exception.dart';
import '../../../core/storage/auth_session_store.dart';
import '../data/auth_api.dart';

final authControllerProvider =
    StateNotifierProvider<AuthController, AuthState>((ref) {
  return AuthController(
    ref.watch(authApiProvider),
    ref.watch(authSessionStoreProvider),
  );
});

class AuthState {
  final bool isBootstrapping;
  final bool isLoading;
  final String? accessToken;
  final String? refreshToken;
  final String? userId;
  final String? fullName;
  final List<String> roles;
  final String? errorMessage;

  const AuthState({
    this.isBootstrapping = false,
    this.isLoading = false,
    this.accessToken,
    this.refreshToken,
    this.userId,
    this.fullName,
    this.roles = const <String>[],
    this.errorMessage,
  });

  bool get isAuthenticated => accessToken != null && accessToken!.isNotEmpty;

  AuthState copyWith({
    bool? isBootstrapping,
    bool? isLoading,
    String? accessToken,
    String? refreshToken,
    String? userId,
    String? fullName,
    List<String>? roles,
    String? errorMessage,
    bool clearError = false,
  }) {
    return AuthState(
      isBootstrapping: isBootstrapping ?? this.isBootstrapping,
      isLoading: isLoading ?? this.isLoading,
      accessToken: accessToken ?? this.accessToken,
      refreshToken: refreshToken ?? this.refreshToken,
      userId: userId ?? this.userId,
      fullName: fullName ?? this.fullName,
      roles: roles ?? this.roles,
      errorMessage: clearError ? null : (errorMessage ?? this.errorMessage),
    );
  }
}

class AuthController extends StateNotifier<AuthState> {
  AuthController(this._api, this._sessionStore)
      : super(const AuthState(isBootstrapping: true)) {
    _restoreSession();
  }

  final AuthApi _api;
  final AuthSessionStore _sessionStore;

  Future<void> _restoreSession() async {
    try {
      final session = await _sessionStore.readSession();

      if (state.isAuthenticated) {
        return;
      }

      if (session == null) {
        state = const AuthState(isBootstrapping: false);
        return;
      }

      state = AuthState(
        isBootstrapping: false,
        accessToken: session.accessToken,
        refreshToken: session.refreshToken,
        userId: session.userId,
        fullName: session.fullName,
        roles: session.roles,
      );
    } catch (_) {
      state = const AuthState(isBootstrapping: false);
    }
  }

  Future<bool> login(
      {required String identifier, required String password}) async {
    state = state.copyWith(
      isBootstrapping: false,
      isLoading: true,
      clearError: true,
    );

    try {
      final data = await _api.login(identifier: identifier, password: password);
      final next = AuthState(
        isBootstrapping: false,
        isLoading: false,
        accessToken: data.tokens.accessToken,
        refreshToken: data.tokens.refreshToken,
        userId: data.user.id,
        fullName: data.user.fullName,
        roles: data.user.roles,
      );

      state = next;

      await _sessionStore.saveSession(
        accessToken: next.accessToken!,
        refreshToken: next.refreshToken!,
        userId: next.userId!,
        fullName: next.fullName ?? '',
        roles: next.roles,
      );

      return true;
    } on AppException catch (error) {
      state = AuthState(
        isBootstrapping: false,
        errorMessage: error.message,
        roles: const <String>[],
      );
      return false;
    } catch (_) {
      state = const AuthState(
        isBootstrapping: false,
        errorMessage: 'Login failed. Please try again.',
      );
      return false;
    }
  }

  Future<void> logout() async {
    final token = state.refreshToken;
    if (token != null && token.isNotEmpty) {
      try {
        await _api.logout(refreshToken: token);
      } catch (_) {
        // Session is cleared locally even if logout API fails.
      }
    }

    await _sessionStore.clearSession();
    state = const AuthState(isBootstrapping: false);
  }
}
