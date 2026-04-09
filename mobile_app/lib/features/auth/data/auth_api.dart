import 'package:dio/dio.dart';
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

  Future<RegistrationResponseData> registerStudent({
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
    final formMap = <String, dynamic>{
      'name': name,
      'class_name': className,
      'stream': stream,
      'contact_number': contactNumber,
      'password': password,
      'confirm_password': confirmPassword,
      'parent_contact_number': parentContactNumber,
      'address': address,
      'school_details': schoolDetails,
    };

    if (photoPath != null && photoPath.isNotEmpty) {
      formMap['photo'] = await MultipartFile.fromFile(photoPath);
    }

    final response = await _client.postFormMap(
      '/auth/register/student',
      formData: FormData.fromMap(formMap),
    );
    return RegistrationResponseData.fromJson(response);
  }

  Future<RegistrationResponseData> registerTeacher({
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
    final formMap = <String, dynamic>{
      'name': name,
      'age': age.toString(),
      'gender': gender,
      'qualification': qualification,
      'specialization': specialization,
      'school_college': schoolCollege,
      'contact_number': contactNumber,
      'password': password,
      'confirm_password': confirmPassword,
      'address': address,
    };

    if (photoPath != null && photoPath.isNotEmpty) {
      formMap['photo'] = await MultipartFile.fromFile(photoPath);
    }

    final response = await _client.postFormMap(
      '/auth/register/teacher',
      formData: FormData.fromMap(formMap),
    );
    return RegistrationResponseData.fromJson(response);
  }

  Future<void> logout({required String refreshToken}) async {
    await _client.postMap(
      '/auth/logout',
      body: {'refresh_token': refreshToken},
    );
  }
}
