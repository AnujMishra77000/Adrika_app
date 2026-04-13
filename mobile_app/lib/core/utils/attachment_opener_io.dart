import 'dart:io';

import 'package:dio/dio.dart';
import 'package:open_filex/open_filex.dart';
import 'package:path_provider/path_provider.dart';

class AttachmentOpener {
  AttachmentOpener._();

  static final Dio _dio = Dio(
    BaseOptions(
      connectTimeout: const Duration(seconds: 20),
      receiveTimeout: const Duration(seconds: 30),
    ),
  );

  static Future<void> openFromUrl({
    required String url,
    required String fileName,
    String? contentType,
    String? accessToken,
  }) async {
    final resolvedUrl = url.trim();
    if (resolvedUrl.isEmpty) {
      throw const _AttachmentOpenException('Attachment URL is missing.');
    }

    final directory = await getTemporaryDirectory();
    final extension = _fileExtension(fileName, contentType);
    final safeName = _sanitizeFileName(fileName);
    final targetName = safeName.isEmpty ? 'attachment$extension' : safeName;
    final target = File(
      '${directory.path}/adr_notice_${DateTime.now().millisecondsSinceEpoch}_$targetName',
    );

    Response<List<int>> response;
    try {
      response = await _dio.get<List<int>>(
        resolvedUrl,
        options: Options(
          responseType: ResponseType.bytes,
          headers: {
            if (accessToken != null && accessToken.isNotEmpty)
              'Authorization': 'Bearer $accessToken',
          },
        ),
      );
    } on DioException {
      throw const _AttachmentOpenException(
        'Unable to download this attachment right now.',
      );
    }

    final bytes = response.data;
    if (bytes == null || bytes.isEmpty) {
      throw const _AttachmentOpenException('Attachment file is empty.');
    }

    await target.writeAsBytes(bytes, flush: true);

    final result = await OpenFilex.open(target.path, type: contentType);
    if (result.type != ResultType.done) {
      final message = result.message.trim();
      throw _AttachmentOpenException(
        message.isNotEmpty
            ? message
            : 'No compatible app found to open this file.',
      );
    }
  }

  static String _fileExtension(String fileName, String? contentType) {
    final normalized = fileName.trim();
    final lastDot = normalized.lastIndexOf('.');
    if (lastDot > -1 && lastDot < normalized.length - 1) {
      return normalized.substring(lastDot).toLowerCase();
    }

    switch (contentType?.toLowerCase()) {
      case 'application/pdf':
        return '.pdf';
      case 'image/png':
        return '.png';
      case 'image/jpeg':
      case 'image/jpg':
        return '.jpg';
      case 'image/webp':
        return '.webp';
      default:
        return '';
    }
  }

  static String _sanitizeFileName(String fileName) {
    final normalized = fileName.trim();
    if (normalized.isEmpty) {
      return '';
    }

    final safe = normalized.replaceAll(RegExp(r'[^A-Za-z0-9._-]'), '_');
    return safe.length > 120 ? safe.substring(0, 120) : safe;
  }
}

class _AttachmentOpenException implements Exception {
  const _AttachmentOpenException(this.message);

  final String message;

  @override
  String toString() => message;
}
