class AttachmentOpener {
  AttachmentOpener._();

  static Future<void> openFromUrl({
    required String url,
    required String fileName,
    String? contentType,
    String? accessToken,
  }) async {
    throw UnsupportedError('Attachment opening is not supported on this platform.');
  }
}
