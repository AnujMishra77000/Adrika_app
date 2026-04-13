import 'package:flutter/foundation.dart';

class AppEnv {
  const AppEnv._();

  static String get apiBaseUrl {
    const configured = String.fromEnvironment('API_BASE_URL');
    if (configured.isNotEmpty) {
      return configured;
    }

    if (kIsWeb) {
      return 'http://localhost:8000/api/v1';
    }

    if (defaultTargetPlatform == TargetPlatform.android) {
      return 'http://10.0.2.2:8000/api/v1';
    }

    return 'http://localhost:8000/api/v1';
  }

  static String get apiOrigin {
    final parsed = Uri.tryParse(apiBaseUrl);
    if (parsed == null || parsed.host.isEmpty) {
      return apiBaseUrl;
    }

    final originUri = Uri(
      scheme: parsed.scheme,
      host: parsed.host,
      port: parsed.hasPort ? parsed.port : null,
    );
    return originUri.toString().replaceAll(RegExp(r'/+$'), '');
  }

  static String? resolveServerUrl(String? raw) {
    final value = raw?.trim();
    if (value == null || value.isEmpty) {
      return null;
    }

    final parsed = Uri.tryParse(value);
    if (parsed != null && parsed.hasScheme) {
      return value;
    }

    if (value.startsWith('/')) {
      return '$apiOrigin$value';
    }

    return '$apiOrigin/$value';
  }
}
