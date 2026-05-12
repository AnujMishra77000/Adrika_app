import "dart:async";
import "dart:convert";

import "package:firebase_core/firebase_core.dart";
import "package:firebase_messaging/firebase_messaging.dart";
import "package:flutter/foundation.dart";
import "package:flutter_local_notifications/flutter_local_notifications.dart";
import "package:flutter_secure_storage/flutter_secure_storage.dart";

import "../network/api_client.dart";

typedef NotificationSignalCallback = void Function();

@pragma("vm:entry-point")
Future<void> firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  try {
    await Firebase.initializeApp();
  } catch (_) {
    // Ignore in local/dev when Firebase config is absent.
  }
}

class PushNotificationService {
  PushNotificationService._();

  static final PushNotificationService instance = PushNotificationService._();

  static const String _androidChannelId = "adr_notifications_high";
  static const String _androidChannelName = "ADR Notifications";
  static const String _androidChannelDescription =
      "Important notifications for homework, tests and notices";
  static const String _deviceIdStorageKey = "push.device_id";
  static const String _appVersion = "0.1.0";

  static const FlutterSecureStorage _secureStorage = FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
  );

  final FlutterLocalNotificationsPlugin _localNotifications =
      FlutterLocalNotificationsPlugin();

  bool _initialized = false;
  bool _tokenRefreshBound = false;
  ApiClient? _apiClient;
  String? _activeAccessToken;
  String? _activeUserId;
  List<String> _activeRoles = const <String>[];
  String? _lastRegisteredPushToken;
  String? _lastRegisteredUserId;
  StreamSubscription<RemoteMessage>? _foregroundSub;
  StreamSubscription<RemoteMessage>? _openedAppSub;
  NotificationSignalCallback? _onSignal;

  bool get _isStudentSession =>
      _activeRoles.any((role) => role.toLowerCase() == "student");

  String get _platformLabel {
    if (kIsWeb) {
      return "web";
    }
    switch (defaultTargetPlatform) {
      case TargetPlatform.android:
        return "android";
      case TargetPlatform.iOS:
        return "ios";
      case TargetPlatform.macOS:
        return "macos";
      case TargetPlatform.windows:
        return "windows";
      case TargetPlatform.linux:
        return "linux";
      case TargetPlatform.fuchsia:
        return "fuchsia";
    }
  }

  Future<void> initialize({
    NotificationSignalCallback? onSignal,
  }) async {
    _onSignal = onSignal ?? _onSignal;

    if (_initialized) {
      return;
    }

    if (kIsWeb) {
      _initialized = true;
      return;
    }

    try {
      await Firebase.initializeApp();
    } catch (error) {
      debugPrint("push_init_skipped reason=$error");
      return;
    }

    FirebaseMessaging.onBackgroundMessage(firebaseMessagingBackgroundHandler);
    final messaging = FirebaseMessaging.instance;
    await messaging.requestPermission(
      alert: true,
      badge: true,
      sound: true,
      provisional: false,
    );

    await _localNotifications.initialize(
      const InitializationSettings(
        android: AndroidInitializationSettings("@mipmap/ic_launcher"),
        iOS: DarwinInitializationSettings(),
      ),
    );

    await _createAndroidChannel();
    await _requestLocalNotificationPermissions();

    _foregroundSub?.cancel();
    _foregroundSub = FirebaseMessaging.onMessage.listen(
      _handleForegroundMessage,
    );

    _openedAppSub?.cancel();
    _openedAppSub = FirebaseMessaging.onMessageOpenedApp.listen((_) {
      _emitSignal();
    });

    final initialMessage = await messaging.getInitialMessage();
    if (initialMessage != null) {
      _emitSignal();
    }

    if (!_tokenRefreshBound) {
      messaging.onTokenRefresh.listen((token) async {
        await _registerPushToken(token);
      });
      _tokenRefreshBound = true;
    }

    _initialized = true;
  }

  Future<void> syncAuthSession({
    required ApiClient apiClient,
    required String? accessToken,
    required String? userId,
    required List<String> roles,
  }) async {
    _apiClient = apiClient;
    _activeAccessToken = accessToken;
    _activeUserId = userId;
    _activeRoles = roles;

    await initialize();

    if (!_initialized || !_isStudentSession) {
      return;
    }
    if (accessToken == null ||
        accessToken.isEmpty ||
        userId == null ||
        userId.isEmpty) {
      return;
    }

    String? token;
    try {
      token = await FirebaseMessaging.instance.getToken();
    } catch (error) {
      debugPrint("push_token_fetch_failed reason=$error");
      return;
    }

    if (token == null || token.isEmpty) {
      return;
    }

    await _registerPushToken(token);
  }

  Future<void> _createAndroidChannel() async {
    final androidImplementation =
        _localNotifications.resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>();
    if (androidImplementation == null) {
      return;
    }

    const channel = AndroidNotificationChannel(
      _androidChannelId,
      _androidChannelName,
      description: _androidChannelDescription,
      importance: Importance.high,
      playSound: true,
    );
    await androidImplementation.createNotificationChannel(channel);
  }

  Future<void> _requestLocalNotificationPermissions() async {
    final androidImplementation =
        _localNotifications.resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>();
    await androidImplementation?.requestNotificationsPermission();

    final iosImplementation =
        _localNotifications.resolvePlatformSpecificImplementation<
            IOSFlutterLocalNotificationsPlugin>();
    await iosImplementation?.requestPermissions(
      alert: true,
      badge: true,
      sound: true,
    );
  }

  Future<void> _handleForegroundMessage(RemoteMessage message) async {
    _emitSignal();

    final title =
        message.notification?.title ?? message.data["title"]?.toString() ?? "";
    final body =
        message.notification?.body ?? message.data["body"]?.toString() ?? "";
    if (title.isEmpty && body.isEmpty) {
      return;
    }

    final payload = jsonEncode(<String, String>{
      "notification_id": message.data["notification_id"]?.toString() ?? "",
      "notification_type": message.data["notification_type"]?.toString() ?? "",
    });

    await _localNotifications.show(
      DateTime.now().millisecondsSinceEpoch ~/ 1000,
      title,
      body,
      const NotificationDetails(
        android: AndroidNotificationDetails(
          _androidChannelId,
          _androidChannelName,
          channelDescription: _androidChannelDescription,
          importance: Importance.high,
          priority: Priority.high,
          playSound: true,
          enableVibration: true,
          icon: "@mipmap/ic_launcher",
        ),
        iOS: DarwinNotificationDetails(
          presentAlert: true,
          presentBadge: true,
          presentSound: true,
          sound: "default",
        ),
      ),
      payload: payload,
    );
  }

  void _emitSignal() {
    final callback = _onSignal;
    if (callback != null) {
      callback();
    }
  }

  Future<String> _resolveDeviceId() async {
    final existing = await _secureStorage.read(key: _deviceIdStorageKey);
    if (existing != null && existing.isNotEmpty) {
      return existing;
    }

    final generated =
        "adr-$_platformLabel-${DateTime.now().microsecondsSinceEpoch.toString()}";
    await _secureStorage.write(key: _deviceIdStorageKey, value: generated);
    return generated;
  }

  Future<void> _registerPushToken(String pushToken) async {
    if (!_initialized || !_isStudentSession) {
      return;
    }
    final apiClient = _apiClient;
    final accessToken = _activeAccessToken;
    final userId = _activeUserId;
    if (apiClient == null ||
        accessToken == null ||
        accessToken.isEmpty ||
        userId == null ||
        userId.isEmpty) {
      return;
    }

    if (_lastRegisteredPushToken == pushToken &&
        _lastRegisteredUserId == userId) {
      return;
    }

    try {
      final deviceId = await _resolveDeviceId();
      await apiClient.postMap(
        "/devices/register",
        accessToken: accessToken,
        body: <String, dynamic>{
          "device_id": deviceId,
          "platform": _platformLabel,
          "push_token": pushToken,
          "app_version": _appVersion,
        },
      );
      _lastRegisteredPushToken = pushToken;
      _lastRegisteredUserId = userId;
    } catch (error) {
      debugPrint("push_device_register_failed reason=$error");
    }
  }
}
