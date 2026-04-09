class AuthTokens {
  final String accessToken;
  final String refreshToken;
  final int expiresIn;

  const AuthTokens({
    required this.accessToken,
    required this.refreshToken,
    required this.expiresIn,
  });

  factory AuthTokens.fromJson(Map<String, dynamic> json) {
    return AuthTokens(
      accessToken: json['access_token']?.toString() ?? '',
      refreshToken: json['refresh_token']?.toString() ?? '',
      expiresIn: int.tryParse(json['expires_in']?.toString() ?? '') ?? 0,
    );
  }
}

class AuthUser {
  final String id;
  final String fullName;
  final String? email;
  final String? phone;
  final String? status;
  final List<String> roles;

  const AuthUser({
    required this.id,
    required this.fullName,
    required this.email,
    required this.phone,
    required this.status,
    required this.roles,
  });

  factory AuthUser.fromJson(Map<String, dynamic> json) {
    final rawRoles = (json['roles'] as List<dynamic>? ?? <dynamic>[])
        .map((role) => role.toString().toLowerCase())
        .toList(growable: false);

    return AuthUser(
      id: json['id']?.toString() ?? '',
      fullName: json['full_name']?.toString() ?? '',
      email: json['email']?.toString(),
      phone: json['phone']?.toString(),
      status: json['status']?.toString(),
      roles: rawRoles,
    );
  }
}

class LoginResponseData {
  final AuthTokens tokens;
  final AuthUser user;

  const LoginResponseData({required this.tokens, required this.user});

  factory LoginResponseData.fromJson(Map<String, dynamic> json) {
    final tokensJson =
        json['tokens'] as Map<String, dynamic>? ?? <String, dynamic>{};
    final userJson =
        json['user'] as Map<String, dynamic>? ?? <String, dynamic>{};

    return LoginResponseData(
      tokens: AuthTokens.fromJson(tokensJson),
      user: AuthUser.fromJson(userJson),
    );
  }
}

class RegistrationResponseData {
  final String requestId;
  final String userId;
  final String status;
  final String message;

  const RegistrationResponseData({
    required this.requestId,
    required this.userId,
    required this.status,
    required this.message,
  });

  factory RegistrationResponseData.fromJson(Map<String, dynamic> json) {
    return RegistrationResponseData(
      requestId: json['request_id']?.toString() ?? '',
      userId: json['user_id']?.toString() ?? '',
      status: json['status']?.toString() ?? '',
      message: json['message']?.toString() ?? '',
    );
  }
}
