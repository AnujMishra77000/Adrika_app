import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../config/app_env.dart';
import 'app_exception.dart';

final apiClientProvider = Provider<ApiClient>(
  (ref) => ApiClient(baseUrl: AppEnv.apiBaseUrl),
);

class ApiClient {
  ApiClient({required String baseUrl})
      : _dio = Dio(
          BaseOptions(
            baseUrl: baseUrl,
            connectTimeout: const Duration(seconds: 15),
            receiveTimeout: const Duration(seconds: 20),
            headers: const {'Accept': 'application/json'},
          ),
        ) {
    if (!kReleaseMode) {
      debugPrint('api_base_url=${_dio.options.baseUrl}');
    }
  }

  final Dio _dio;

  Future<Map<String, dynamic>> getMap(
    String path, {
    String? accessToken,
    Map<String, dynamic>? queryParameters,
  }) async {
    try {
      final response = await _dio.get<dynamic>(
        path,
        queryParameters: queryParameters,
        options: _options(accessToken),
      );
      return _asMap(response.data);
    } on DioException catch (error) {
      throw _mapError(error);
    }
  }

  Future<Map<String, dynamic>> postMap(
    String path, {
    String? accessToken,
    Map<String, dynamic>? body,
  }) async {
    try {
      final response = await _dio.post<dynamic>(
        path,
        data: body,
        options: _options(accessToken),
      );
      return _asMap(response.data);
    } on DioException catch (error) {
      throw _mapError(error);
    }
  }

  Future<Map<String, dynamic>> postFormMap(
    String path, {
    String? accessToken,
    required FormData formData,
  }) async {
    try {
      final response = await _dio.post<dynamic>(
        path,
        data: formData,
        options: _options(accessToken),
      );
      return _asMap(response.data);
    } on DioException catch (error) {
      throw _mapError(error);
    }
  }

  Future<Map<String, dynamic>> putMap(
    String path, {
    String? accessToken,
    Map<String, dynamic>? body,
  }) async {
    try {
      final response = await _dio.put<dynamic>(
        path,
        data: body,
        options: _options(accessToken),
      );
      return _asMap(response.data);
    } on DioException catch (error) {
      throw _mapError(error);
    }
  }

  Future<Map<String, dynamic>> patchMap(
    String path, {
    String? accessToken,
    Map<String, dynamic>? body,
  }) async {
    try {
      final response = await _dio.patch<dynamic>(
        path,
        data: body,
        options: _options(accessToken),
      );
      return _asMap(response.data);
    } on DioException catch (error) {
      throw _mapError(error);
    }
  }

  Options _options(String? accessToken) {
    if (accessToken == null || accessToken.isEmpty) {
      return Options();
    }

    return Options(
      headers: {
        'Authorization': 'Bearer $accessToken',
      },
    );
  }

  Map<String, dynamic> _asMap(dynamic raw) {
    if (raw is Map<String, dynamic>) {
      return raw;
    }

    if (raw is Map) {
      return raw.map((key, value) => MapEntry(key.toString(), value));
    }

    return <String, dynamic>{};
  }

  AppException _mapError(DioException error) {
    final status = error.response?.statusCode;
    final payload = error.response?.data;

    if (error.type == DioExceptionType.connectionTimeout ||
        error.type == DioExceptionType.receiveTimeout ||
        error.type == DioExceptionType.connectionError) {
      return AppException(
        'Cannot reach server at ${_dio.options.baseUrl}. Check backend host/port and API_BASE_URL.',
        statusCode: status,
      );
    }

    final message = _extractServerMessage(payload);
    if (message != null && message.isNotEmpty) {
      return AppException(message, statusCode: status);
    }

    if (status == 401) {
      return AppException(
        'Session expired. Please login again.',
        statusCode: status,
      );
    }

    if (status == 403) {
      return AppException(
        'Permission denied for this action.',
        statusCode: status,
      );
    }

    if (status != null) {
      return AppException(
        'Request failed (HTTP $status). Please try again.',
        statusCode: status,
      );
    }

    return AppException(
      'Unable to complete request. Please try again.',
      statusCode: status,
    );
  }

  String? _extractServerMessage(dynamic payload) {
    if (payload is String) {
      final text = payload.trim();
      if (text.isNotEmpty) {
        return text;
      }
      return null;
    }

    if (payload is! Map) {
      return null;
    }

    final map = payload.map((key, value) => MapEntry(key.toString(), value));

    final detail = map['detail'];
    if (detail is String && detail.trim().isNotEmpty) {
      return detail.trim();
    }

    if (detail is List && detail.isNotEmpty) {
      final first = detail.first;
      if (first is Map) {
        final msg = first['msg'];
        if (msg is String && msg.trim().isNotEmpty) {
          return msg.trim();
        }
      }
      final listText = detail.join(', ').trim();
      if (listText.isNotEmpty) {
        return listText;
      }
    }

    final message = map['message'];
    if (message is String && message.trim().isNotEmpty) {
      return message.trim();
    }

    final title = map['title'];
    if (title is String && title.trim().isNotEmpty) {
      return title.trim();
    }

    return null;
  }
}
