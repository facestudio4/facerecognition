// Preprocessing helpers: color conversion, resize, normalization, and alignment helpers.

import 'dart:math' as math;
import 'dart:typed_data';

class Preprocessing {
  Preprocessing();

  /// Convert YUV420 camera plane bytes to packed RGB bytes (u8 u8 u8)
  Uint8List yuv420ToRgb(
      Uint8List y, Uint8List u, Uint8List v, int width, int height) {
    if (width <= 0 || height <= 0) {
      return Uint8List(0);
    }

    final output = Uint8List(width * height * 3);
    for (var row = 0; row < height; row++) {
      for (var col = 0; col < width; col++) {
        final yIndex = row * width + col;
        final uvIndex = (row >> 1) * (width >> 1) + (col >> 1);
        final yValue = yIndex < y.length ? y[yIndex].toDouble() : 0.0;
        final uValue = uvIndex < u.length ? u[uvIndex].toDouble() : 128.0;
        final vValue = uvIndex < v.length ? v[uvIndex].toDouble() : 128.0;

        final r = (yValue + 1.402 * (vValue - 128.0)).round().clamp(0, 255);
        final g =
            (yValue - 0.344136 * (uValue - 128.0) - 0.714136 * (vValue - 128.0))
                .round()
                .clamp(0, 255);
        final b = (yValue + 1.772 * (uValue - 128.0)).round().clamp(0, 255);
        final target = yIndex * 3;
        output[target] = r;
        output[target + 1] = g;
        output[target + 2] = b;
      }
    }

    return output;
  }

  /// Resize an RGB buffer to target w x h
  Uint8List resizeRgb(Uint8List rgb, int srcW, int srcH, int dstW, int dstH) {
    if (srcW <= 0 || srcH <= 0 || dstW <= 0 || dstH <= 0) {
      return Uint8List(0);
    }

    final output = Uint8List(dstW * dstH * 3);
    for (var y = 0; y < dstH; y++) {
      final sourceY = ((y * srcH) / dstH).floor().clamp(0, srcH - 1);
      for (var x = 0; x < dstW; x++) {
        final sourceX = ((x * srcW) / dstW).floor().clamp(0, srcW - 1);
        final sourceIndex = (sourceY * srcW + sourceX) * 3;
        final targetIndex = (y * dstW + x) * 3;
        if (sourceIndex + 2 < rgb.length) {
          output[targetIndex] = rgb[sourceIndex];
          output[targetIndex + 1] = rgb[sourceIndex + 1];
          output[targetIndex + 2] = rgb[sourceIndex + 2];
        }
      }
    }

    return output;
  }

  /// Normalize packed u8 RGB to Float32List [-1..1] or [0..1] as model expects
  Float32List normalize(Uint8List rgb, {bool toMinusOneToOne = false}) {
    final output = Float32List(rgb.length);
    for (var index = 0; index < rgb.length; index++) {
      final value = rgb[index] / 255.0;
      output[index] = toMinusOneToOne ? (value * 2.0 - 1.0) : value;
    }
    return output;
  }

  /// Crop a detection box, clamp it to the source image bounds, and resize to target size.
  Uint8List cropAndResizeRgb(
    Uint8List rgb,
    int srcW,
    int srcH,
    int left,
    int top,
    int cropW,
    int cropH,
    int dstW,
    int dstH,
  ) {
    if (srcW <= 0 || srcH <= 0 || rgb.isEmpty) {
      return Uint8List(0);
    }

    final safeLeft = left.clamp(0, math.max(0, srcW - 1)).toInt();
    final safeTop = top.clamp(0, math.max(0, srcH - 1)).toInt();
    final safeWidth = cropW.clamp(1, srcW - safeLeft).toInt();
    final safeHeight = cropH.clamp(1, srcH - safeTop).toInt();

    final cropped = Uint8List(safeWidth * safeHeight * 3);
    for (var y = 0; y < safeHeight; y++) {
      for (var x = 0; x < safeWidth; x++) {
        final sourceIndex = ((safeTop + y) * srcW + (safeLeft + x)) * 3;
        final targetIndex = (y * safeWidth + x) * 3;
        if (sourceIndex + 2 < rgb.length) {
          cropped[targetIndex] = rgb[sourceIndex];
          cropped[targetIndex + 1] = rgb[sourceIndex + 1];
          cropped[targetIndex + 2] = rgb[sourceIndex + 2];
        }
      }
    }

    return resizeRgb(cropped, safeWidth, safeHeight, dstW, dstH);
  }
}
