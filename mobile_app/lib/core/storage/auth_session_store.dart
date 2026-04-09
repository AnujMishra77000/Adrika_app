import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

final authSessionStoreProvider = Provider<AuthSessionStore>((ref) {
  return const AuthSessionStore();
});

class PersistedAuthSession {
  final String accessToken;
  final String refreshToken;
  final String userId;
  final String fullName;
  final List<String> roles;

  const PersistedAuthSession({
    required this.accessToken,
    required this.refreshToken,
    required this.userId,
    required this.fullName,
    required this.roles,
  });
}

class AuthSessionStore {
  const AuthSessionStore();

  static const _storage = FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
  );

  static const _accessTokenKey = 'auth.access_token';
  static const _refreshTokenKey = 'auth.refresh_token';
  static const _userIdKey = 'auth.user_id';
  static const _fullNameKey = 'auth.full_name';
  static const _rolesKey = 'auth.roles';
  static const _schemaVersionKey = 'auth.schema_version';
  static const _currentSchemaVersion = '3';

  Future<void> saveSession({
    required String accessToken,
    required String refreshToken,
    required String userId,
    required String fullName,
    required List<String> roles,
  }) async {
    await _storage.write(key: _accessTokenKey, value: accessToken);
    await _storage.write(key: _refreshTokenKey, value: refreshToken);
    await _storage.write(key: _userIdKey, value: userId);
    await _storage.write(key: _fullNameKey, value: fullName);
    await _storage.write(key: _rolesKey, value: jsonEncode(roles));
    await _storage.write(key: _schemaVersionKey, value: _currentSchemaVersion);
  }

  Future<PersistedAuthSession?> readSession() async {
    final schemaVersion = await _storage.read(key: _schemaVersionKey);
    if (schemaVersion != _currentSchemaVersion) {
      await clearSession();
      return null;
    }

    final accessToken = await _storage.read(key: _accessTokenKey);
    final refreshToken = await _storage.read(key: _refreshTokenKey);
    final userId = await _storage.read(key: _userIdKey);
    final fullName = await _storage.read(key: _fullNameKey);
    final rolesRaw = await _storage.read(key: _rolesKey);

    if (accessToken == null ||
        refreshToken == null ||
        userId == null ||
        fullName == null ||
        rolesRaw == null) {
      return null;
    }

    try {
      final decoded = jsonDecode(rolesRaw);
      final roles = (decoded as List<dynamic>)
          .map((item) => item.toString())
          .toList(growable: false);

      return PersistedAuthSession(
        accessToken: accessToken,
        refreshToken: refreshToken,
        userId: userId,
        fullName: fullName,
        roles: roles,
      );
    } catch (_) {
      return null;
    }
  }

  Future<void> clearSession() async {
    await _storage.delete(key: _accessTokenKey);
    await _storage.delete(key: _refreshTokenKey);
    await _storage.delete(key: _userIdKey);
    await _storage.delete(key: _fullNameKey);
    await _storage.delete(key: _rolesKey);
    await _storage.delete(key: _schemaVersionKey);
  }
}
