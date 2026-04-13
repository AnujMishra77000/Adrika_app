import 'dart:convert';

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
  final String? infoMessage;

  const AuthState({
    this.isBootstrapping = false,
    this.isLoading = false,
    this.accessToken,
    this.refreshToken,
    this.userId,
    this.fullName,
    this.roles = const <String>[],
    this.errorMessage,
    this.infoMessage,
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
    String? infoMessage,
    bool clearError = false,
    bool clearInfo = false,
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
      infoMessage: clearInfo ? null : (infoMessage ?? this.infoMessage),
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

  bool _looksExpiredJwt(String token) {
    try {
      final parts = token.split('.');
      if (parts.length != 3) {
        return false;
      }

      final payload =
          utf8.decode(base64Url.decode(base64Url.normalize(parts[1])));
      final decoded = jsonDecode(payload);
      if (decoded is! Map<String, dynamic>) {
        return false;
      }

      final expRaw = decoded['exp'];
      final expSeconds =
          expRaw is int ? expRaw : int.tryParse(expRaw?.toString() ?? '');

      if (expSeconds == null) {
        return false;
      }

      final expiresAt = DateTime.fromMillisecondsSinceEpoch(
        expSeconds * 1000,
        isUtc: true,
      );

      // 30s skew tolerance
      return DateTime.now()
          .toUtc()
          .isAfter(expiresAt.subtract(const Duration(seconds: 30)));
    } catch (_) {
      return false;
    }
  }

  Future<void> _restoreSession() async {
    try {
      final session = await _sessionStore.readSession();

      if (state.isAuthenticated) {
        state = state.copyWith(isBootstrapping: false);
        return;
      }

      if (session == null) {
        state = const AuthState(isBootstrapping: false);
        return;
      }

      if (_looksExpiredJwt(session.accessToken)) {
        await _sessionStore.clearSession();
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
      clearInfo: true,
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

  Future<bool> registerStudent({
    required String name,
    required String className,
    required String stream,
    required String contactNumber,
    required String password,
    required String confirmPassword,
    required String parentContactNumber,
    required String address,
    required String schoolDetails,
    String? photoPath,
  }) async {
    state = state.copyWith(
      isLoading: true,
      clearError: true,
      clearInfo: true,
    );

    try {
      final response = await _api.registerStudent(
        name: name,
        className: className,
        stream: stream,
        contactNumber: contactNumber,
        password: password,
        confirmPassword: confirmPassword,
        parentContactNumber: parentContactNumber,
        address: address,
        schoolDetails: schoolDetails,
        photoPath: photoPath,
      );

      state = state.copyWith(
        isLoading: false,
        infoMessage: response.message,
        clearError: true,
      );
      return true;
    } on AppException catch (error) {
      state = state.copyWith(
        isLoading: false,
        errorMessage: error.message,
        clearInfo: true,
      );
      return false;
    } catch (_) {
      state = state.copyWith(
        isLoading: false,
        errorMessage: 'Registration failed. Please try again.',
        clearInfo: true,
      );
      return false;
    }
  }

  Future<bool> registerTeacher({
    required String name,
    required int age,
    required String gender,
    required String qualification,
    required String specialization,
    String? schoolCollege,
    required String contactNumber,
    required String password,
    required String confirmPassword,
    required String address,
    String? photoPath,
  }) async {
    state = state.copyWith(
      isLoading: true,
      clearError: true,
      clearInfo: true,
    );

    try {
      final response = await _api.registerTeacher(
        name: name,
        age: age,
        gender: gender,
        qualification: qualification,
        specialization: specialization,
        schoolCollege: schoolCollege,
        contactNumber: contactNumber,
        password: password,
        confirmPassword: confirmPassword,
        address: address,
        photoPath: photoPath,
      );

      state = state.copyWith(
        isLoading: false,
        infoMessage: response.message,
        clearError: true,
      );
      return true;
    } on AppException catch (error) {
      state = state.copyWith(
        isLoading: false,
        errorMessage: error.message,
        clearInfo: true,
      );
      return false;
    } catch (_) {
      state = state.copyWith(
        isLoading: false,
        errorMessage: 'Registration failed. Please try again.',
        clearInfo: true,
      );
      return false;
    }
  }

  void clearMessages() {
    state = state.copyWith(clearError: true, clearInfo: true);
  }

  Future<void> clearSessionLocal() async {
    await _sessionStore.clearSession();
    state = const AuthState(isBootstrapping: false);
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
