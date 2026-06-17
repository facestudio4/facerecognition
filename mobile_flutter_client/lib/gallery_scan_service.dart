// Background gallery auto-scan: after a user signs up (or when an admin requests
// a re-scan), scan the ENTIRE gallery — PHOTOS first, then VIDEOS — detect faces
// on-device with ML Kit, and send each face crop to the backend recognizer.
// Confident matches are auto-saved to that person's folder; uncertain matches go
// to the admin review queue.
//
// Free-tier friendly: foreground only, pauses during live recognition, rate-
// limited, and backs off when the backend is cold/overloaded. Progress is
// checkpointed after every batch (and every photo/video) so it resumes across
// app sessions until every photo and video is covered. Only small face crops are
// ever uploaded (never whole photos/videos), so the backend never runs out of
// memory. For videos it samples a few frames and stops at the first confident
// match.

import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math' as math;
import 'dart:ui' show Rect;

import 'package:flutter/foundation.dart';
import 'package:google_mlkit_face_detection/google_mlkit_face_detection.dart';
import 'package:image/image.dart' as img;
import 'package:path_provider/path_provider.dart';
import 'package:photo_manager/photo_manager.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:video_thumbnail/video_thumbnail.dart' as vt;

typedef IdentifyFn = Future<Map<String, dynamic>> Function(String imageB64);
typedef EnrollFn = Future<Map<String, dynamic>> Function(
    String person, String imageB64, String filename);
typedef ReviewFn = Future<Map<String, dynamic>> Function(
    String candidateName, double score, String imageB64);
typedef ProgressFn = Future<void> Function(
    int scanned, int total, String state, int faces, int saved, int review);

class GalleryScanService {
  GalleryScanService._();
  static final GalleryScanService instance = GalleryScanService._();

  // Tunables.
  static const int _batchSize = 500; // photos per checkpoint
  static const int _videoBatchSize = 50; // videos per checkpoint (heavier)
  static const int _videoFramesPerVideo = 6; // frames sampled before giving up
  // Strict auto-save: only near-certain matches are saved automatically; the
  // band below goes to the admin review queue (family lookalikes used to cross
  // the old 0.52 bar and land in the wrong folder).
  static const double _autoSaveThreshold = 0.66; // >= this -> auto-save
  static const double _reviewThreshold = 0.48; // [review, auto) -> admin review
  // How much context to keep around the face in the SAVED image (fraction of the
  // face box added per side). ~1.1 ≈ head-and-shoulders + background.
  static const double _saveMargin = 1.1;
  // Moderate throttle: ~2x faster than before, still gentle on the free tier
  // (well under the server's 300-req/min limit).
  static const Duration _perCallDelay =
      Duration(seconds: 2); // protect free tier
  static const Duration _betweenBatchDelay = Duration(seconds: 4);
  static const List<Duration> _serverRetryBackoffs = [
    Duration(seconds: 8),
    Duration(seconds: 20),
    Duration(seconds: 40),
    Duration(seconds: 60),
  ];
  static const String _processedKey = 'gallery_scan_processed_ids';
  static const String _offsetKey = 'gallery_scan_offset';
  static const String _videoProcessedKey = 'gallery_scan_video_processed_ids';
  static const String _videoOffsetKey = 'gallery_scan_video_offset';

  final ValueNotifier<String> status = ValueNotifier<String>('');
  final ValueNotifier<bool> running = ValueNotifier<bool>(false);

  // Set true while the live-recognition screen is active so the scan yields the
  // (single, free-tier) backend to real-time recognition instead of fighting it.
  static bool liveRecognitionActive = false;

  bool _stop = false;
  bool _active = false;
  int _autoSaved = 0;
  int _queued = 0;
  int _withFaces = 0; // photos/frames where at least one face was detected

  bool get isRunning => _active;

  void stop() {
    _stop = true;
  }

  // Whether photo access is already granted (does NOT show the OS prompt).
  static Future<bool> hasGalleryPermission() async {
    try {
      final p = await PhotoManager.getPermissionState(
          requestOption: const PermissionRequestOption());
      return p == PermissionState.authorized || p == PermissionState.limited;
    } catch (_) {
      return false;
    }
  }

  // Triggers the OS permission dialog (no-op if already granted). Returns true
  // if access was granted.
  static Future<bool> requestGalleryPermission() async {
    try {
      final p = await PhotoManager.requestPermissionExtend();
      return p.isAuth || p.hasAccess;
    } catch (_) {
      return false;
    }
  }

  Future<void> start({
    required IdentifyFn identify,
    required EnrollFn enroll,
    required ReviewFn submitReview,
    bool resetProcessed = false,
    VoidCallback? onComplete,
    ProgressFn? onProgress,
  }) async {
    if (_active) {
      return;
    }
    _active = true;
    _stop = false;
    running.value = true;
    _autoSaved = 0;
    _queued = 0;
    _withFaces = 0;
    var serverNotReady = false;
    FaceDetector? detector;
    try {
      final permission = await PhotoManager.requestPermissionExtend();
      if (!permission.isAuth && !permission.hasAccess) {
        status.value = 'Gallery permission denied';
        await onProgress?.call(0, 0, 'denied', 0, 0, 0);
        return;
      }

      final prefs = await SharedPreferences.getInstance();
      if (resetProcessed) {
        await prefs.remove(_processedKey);
        await prefs.remove(_offsetKey);
        await prefs.remove(_videoProcessedKey);
        await prefs.remove(_videoOffsetKey);
      }
      final imgProcessed = <String>{
        ...(prefs.getStringList(_processedKey) ?? const <String>[])
      };
      var imgOffset = prefs.getInt(_offsetKey) ?? 0;
      final vidProcessed = <String>{
        ...(prefs.getStringList(_videoProcessedKey) ?? const <String>[])
      };
      var vidOffset = prefs.getInt(_videoOffsetKey) ?? 0;

      final imgAlbums = await PhotoManager.getAssetPathList(
          onlyAll: true, type: RequestType.image);
      final imgRecent = imgAlbums.isNotEmpty ? imgAlbums.first : null;
      final imgTotal = imgRecent == null ? 0 : await imgRecent.assetCountAsync;

      final vidAlbums = await PhotoManager.getAssetPathList(
          onlyAll: true, type: RequestType.video);
      final vidRecent = vidAlbums.isNotEmpty ? vidAlbums.first : null;
      final vidTotal = vidRecent == null ? 0 : await vidRecent.assetCountAsync;

      final grandTotal = imgTotal + vidTotal;
      if (grandTotal <= 0) {
        status.value = 'No photos or videos found';
        await onProgress?.call(0, 0, 'empty', 0, 0, 0);
        onComplete?.call();
        return;
      }

      detector = FaceDetector(
        options: FaceDetectorOptions(
          performanceMode: FaceDetectorMode.fast,
          minFaceSize: 0.12,
        ),
      );
      final tmpDir = await getTemporaryDirectory();
      final tmpPath = '${tmpDir.path}/gallery_scan_tmp.jpg';
      await onProgress?.call(imgProcessed.length, grandTotal, 'scanning',
          _withFaces, _autoSaved, _queued);

      // ---------- PHASE 1: PHOTOS ----------
      if (imgRecent != null) {
        while (imgOffset < imgTotal && !_stop && !serverNotReady) {
          final end = math.min(imgOffset + _batchSize, imgTotal);
          final assets =
              await imgRecent.getAssetListRange(start: imgOffset, end: end);
          for (final asset in assets) {
            if (_stop || serverNotReady) break;
            if (!await _waitWhileRecognizing()) break;
            if (imgProcessed.contains(asset.id)) continue;
            try {
              final bytes = await asset
                  .thumbnailDataWithSize(const ThumbnailSize(1024, 1024));
              if (bytes == null) {
                imgProcessed.add(asset.id);
                continue;
              }
              await File(tmpPath).writeAsBytes(bytes, flush: true);
              final faces =
                  await detector.processImage(InputImage.fromFilePath(tmpPath));
              if (faces.isEmpty) {
                imgProcessed.add(asset.id);
                continue;
              }
              _withFaces++;
              final decoded = img.decodeImage(bytes);
              if (decoded == null) {
                imgProcessed.add(asset.id);
                continue;
              }
              final ok = await _handleImageFaces(
                  decoded, faces, identify, enroll, submitReview);
              if (!ok) {
                serverNotReady = true;
                break;
              }
              imgProcessed.add(asset.id);
              status.value =
                  'Scanning photos ${imgProcessed.length}/$imgTotal • saved $_autoSaved • review $_queued';
            } catch (_) {
              imgProcessed.add(asset.id);
            }
            if (imgProcessed.length % 10 == 0) {
              await prefs.setStringList(_processedKey, imgProcessed.toList());
            }
            if (imgProcessed.length % 25 == 0) {
              await onProgress?.call(imgProcessed.length, grandTotal,
                  'scanning', _withFaces, _autoSaved, _queued);
            }
          }
          await prefs.setStringList(_processedKey, imgProcessed.toList());
          if (!serverNotReady && !_stop) {
            imgOffset = end;
            await prefs.setInt(_offsetKey, imgOffset);
            await onProgress?.call(imgProcessed.length, grandTotal, 'scanning',
                _withFaces, _autoSaved, _queued);
            if (imgOffset < imgTotal) {
              await Future<void>.delayed(_betweenBatchDelay);
            }
          }
        }
      }

      final imagesDone = imgOffset >= imgTotal;

      // ---------- PHASE 2: VIDEOS (only after photos fully done) ----------
      if (imagesDone && !_stop && !serverNotReady && vidRecent != null) {
        while (vidOffset < vidTotal && !_stop && !serverNotReady) {
          final end = math.min(vidOffset + _videoBatchSize, vidTotal);
          final assets =
              await vidRecent.getAssetListRange(start: vidOffset, end: end);
          for (final asset in assets) {
            if (_stop || serverNotReady) break;
            if (!await _waitWhileRecognizing()) break;
            if (vidProcessed.contains(asset.id)) continue;
            try {
              final ok = await _handleVideo(
                  asset, detector, tmpPath, identify, enroll, submitReview);
              if (!ok) {
                serverNotReady = true;
                break;
              }
              vidProcessed.add(asset.id);
              status.value =
                  'Scanning videos ${vidProcessed.length}/$vidTotal • saved $_autoSaved • review $_queued';
            } catch (_) {
              vidProcessed.add(asset.id);
            }
            await onProgress?.call(imgTotal + vidProcessed.length, grandTotal,
                'scanning', _withFaces, _autoSaved, _queued);
          }
          await prefs.setStringList(_videoProcessedKey, vidProcessed.toList());
          if (!serverNotReady && !_stop) {
            vidOffset = end;
            await prefs.setInt(_videoOffsetKey, vidOffset);
            if (vidOffset < vidTotal) {
              await Future<void>.delayed(_betweenBatchDelay);
            }
          }
        }
      }

      final allDone = imagesDone && vidOffset >= vidTotal;
      if (allDone && !_stop) {
        status.value =
            'Scan complete: $imgTotal photos + $vidTotal videos • saved $_autoSaved • $_queued for review';
        await onProgress?.call(grandTotal, grandTotal, 'done',
            _withFaces, _autoSaved, _queued);
        onComplete?.call();
      } else if (serverNotReady) {
        status.value = 'Paused — backend not ready, will continue later';
      } else {
        status.value =
            'Paused • saved $_autoSaved • $_queued for review';
      }
    } catch (e) {
      status.value = 'Scan error: $e';
    } finally {
      await detector?.close();
      _active = false;
      running.value = false;
    }
  }

  // Block while live recognition owns the backend. Returns false if a stop was
  // requested during the wait.
  Future<bool> _waitWhileRecognizing() async {
    while (liveRecognitionActive && !_stop) {
      status.value = 'Paused (recognition in use)…';
      await Future<void>.delayed(const Duration(seconds: 2));
    }
    return !_stop;
  }

  bool _isNoMatch(String name, double score) =>
      name.trim().isEmpty ||
      name.toLowerCase() == 'unknown' ||
      score < _reviewThreshold;

  String _galleryFilename() =>
      'gallery_${DateTime.now().millisecondsSinceEpoch}.jpg';

  // Process every detected face in a photo. Returns false if the backend became
  // unreachable (caller pauses the run; photo is NOT marked done).
  Future<bool> _handleImageFaces(img.Image decoded, List<Face> faces,
      IdentifyFn identify, EnrollFn enroll, ReviewFn submitReview) async {
    for (final face in faces) {
      if (_stop) break;
      // Tight crop for accurate recognition (avoids pulling in nearby faces).
      final tight = _cropFace(decoded, face.boundingBox, 0.25);
      if (tight == null) continue;
      final tightB64 = base64Encode(img.encodeJpg(tight, quality: 85));
      final result = await _identifyWithRetry(identify, tightB64);
      if (result == null) return false; // backend not ready
      await Future<void>.delayed(_perCallDelay);
      if (_isNoMatch(result.name, result.score)) continue;
      // Wider head-and-shoulders crop for the image that gets saved/reviewed so
      // it's actually viewable (still not the whole photo).
      final wide = _cropFace(decoded, face.boundingBox, _saveMargin) ?? tight;
      final wideB64 = base64Encode(img.encodeJpg(wide, quality: 88));
      if (result.score >= _autoSaveThreshold) {
        await enroll(result.name, wideB64, _galleryFilename());
        _autoSaved++;
      } else {
        await submitReview(result.name, result.score, wideB64);
        _queued++;
      }
    }
    return true;
  }

  // Sample up to _videoFramesPerVideo evenly-spaced frames; stop at the first
  // confident match (save it). If only uncertain matches were seen, queue the
  // best one. Returns false if the backend became unreachable.
  Future<bool> _handleVideo(
      AssetEntity asset,
      FaceDetector detector,
      String tmpPath,
      IdentifyFn identify,
      EnrollFn enroll,
      ReviewFn submitReview) async {
    final file = await asset.file;
    if (file == null) return true; // unreadable -> treat as processed
    final durationMs = asset.duration * 1000;
    ({String name, double score, String b64})? bestUncertain;
    var countedFace = false;

    for (var i = 0; i < _videoFramesPerVideo; i++) {
      if (_stop) break;
      if (!await _waitWhileRecognizing()) break;
      final timeMs = durationMs > 0
          ? ((durationMs * (i + 0.5)) / _videoFramesPerVideo).round()
          : 0;
      Uint8List? frameBytes;
      try {
        frameBytes = await vt.VideoThumbnail.thumbnailData(
          video: file.path,
          imageFormat: vt.ImageFormat.JPEG,
          timeMs: timeMs,
          maxWidth: 1024,
          quality: 80,
        );
      } catch (_) {
        frameBytes = null;
      }
      if (frameBytes == null || frameBytes.isEmpty) continue;
      try {
        await File(tmpPath).writeAsBytes(frameBytes, flush: true);
        final faces =
            await detector.processImage(InputImage.fromFilePath(tmpPath));
        if (faces.isEmpty) continue;
        if (!countedFace) {
          _withFaces++;
          countedFace = true;
        }
        final decoded = img.decodeImage(frameBytes);
        if (decoded == null) continue;
        for (final face in faces) {
          if (_stop) break;
          final tight = _cropFace(decoded, face.boundingBox, 0.25);
          if (tight == null) continue;
          final tightB64 = base64Encode(img.encodeJpg(tight, quality: 85));
          final result = await _identifyWithRetry(identify, tightB64);
          if (result == null) return false; // backend not ready
          await Future<void>.delayed(_perCallDelay);
          if (_isNoMatch(result.name, result.score)) continue;
          final wide = _cropFace(decoded, face.boundingBox, _saveMargin) ?? tight;
          final wideB64 = base64Encode(img.encodeJpg(wide, quality: 88));
          if (result.score >= _autoSaveThreshold) {
            // Confident -> save and stop this video immediately.
            await enroll(result.name, wideB64, _galleryFilename());
            _autoSaved++;
            return true;
          }
          if (bestUncertain == null || result.score > bestUncertain.score) {
            bestUncertain =
                (name: result.name, score: result.score, b64: wideB64);
          }
        }
      } catch (_) {
        // skip this frame
      }
    }

    if (bestUncertain != null && !_stop) {
      await submitReview(
          bestUncertain.name, bestUncertain.score, bestUncertain.b64);
      _queued++;
    }
    return true;
  }

  // Identify a crop, riding out a cold/overloaded backend with backoff. Returns
  // null only if the backend is still unreachable after all retries.
  Future<({String name, double score})?> _identifyWithRetry(
      IdentifyFn identify, String b64) async {
    for (var attempt = 0; attempt <= _serverRetryBackoffs.length; attempt++) {
      if (_stop) {
        return null;
      }
      try {
        final res = await identify(b64);
        final data = res['data'];
        if (data is Map) {
          final best = (data['best'] as Map?) ?? const {};
          final name = (best['name'] ?? 'Unknown').toString();
          final score =
              double.tryParse((best['score'] ?? 0).toString()) ?? 0.0;
          return (name: name, score: score);
        }
      } catch (_) {
        // 502 / timeout / non-JSON -> backend not ready.
      }
      if (attempt < _serverRetryBackoffs.length && !_stop) {
        status.value = 'Backend waking up… retrying';
        await Future<void>.delayed(_serverRetryBackoffs[attempt]);
      }
    }
    return null;
  }

  // margin is a fraction of the face box added on every side (0.25 = tight face
  // for recognition; ~1.1 = head-and-shoulders with context for the saved image).
  img.Image? _cropFace(img.Image src, Rect box, [double margin = 0.25]) {
    final cx = box.left + box.width / 2;
    final cy = box.top + box.height / 2;
    final size = math.max(box.width, box.height) * (1 + margin);
    var x = (cx - size / 2).round().clamp(0, src.width - 1);
    var y = (cy - size / 2).round().clamp(0, src.height - 1);
    var s = size.round();
    if (x + s > src.width) {
      s = src.width - x;
    }
    if (y + s > src.height) {
      s = src.height - y;
    }
    if (s < 24) {
      return null;
    }
    return img.copyCrop(src, x: x, y: y, width: s, height: s);
  }
}
