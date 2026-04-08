import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../models/auth_models.dart';

final authApiProvider = Provider<AuthApi>((ref) {
  return AuthApi(ref.watch(apiClientProvider));
});

class AuthApi {
  AuthApi(this._client);

  final ApiClient _client;

  Future<LoginResponseData> login({
    required String identifier,
    required String password,
  }) async {
    final response = await _client.postMap(
      '/auth/login',
      body: {
        'identifier': identifier,
        'password': password,
        'device': {
          'device_id': 'adr-mobile-device',
          'platform': 'android',
          'app_version': '0.1.0',
        },
      },
    );

    return LoginResponseData.fromJson(response);
  }

  Future<void> logout({required String refreshToken}) async {
    await _client.postMap(
      '/auth/logout',
      body: {'refresh_token': refreshToken},
    );
  }
}
