import 'dart:isolate';
import 'dart:typed_data';

import 'package:camera/camera.dart';

import 'preprocessing.dart';

class CameraFrameAdapter {
  CameraFrameAdapter({Preprocessing? preprocessing})
      : _preprocessing = preprocessing ?? Preprocessing();

  final Preprocessing _preprocessing;

  /// Convert a [CameraImage] to packed RGB bytes with frame metadata.
  CameraFrameData fromCameraImage(CameraImage image,
      {int rotationDegrees = 0}) {
    final width = image.width;
    final height = image.height;

    if (image.format.group == ImageFormatGroup.yuv420) {
      final yPlane = image.planes[0].bytes;
      final uPlane =
          image.planes.length > 1 ? image.planes[1].bytes : Uint8List(0);
      final vPlane =
          image.planes.length > 2 ? image.planes[2].bytes : Uint8List(0);
      return fromYuv420Planes(
        yPlane: yPlane,
        uPlane: uPlane,
        vPlane: vPlane,
        width: width,
        height: height,
        rotationDegrees: rotationDegrees,
      );
    }

    if (image.format.group == ImageFormatGroup.bgra8888) {
      return fromBgra8888Bytes(
        image.planes.first.bytes,
        width: width,
        height: height,
        rotationDegrees: rotationDegrees,
      );
    }

    final fallbackRgb = Uint8List(width * height * 3);
    return CameraFrameData(
      rgbBytes: fallbackRgb,
      width: width,
      height: height,
      rotationDegrees: rotationDegrees,
      format: image.format.group.name,
    );
  }

  CameraFrameData fromYuv420Planes({
    required Uint8List yPlane,
    required Uint8List uPlane,
    required Uint8List vPlane,
    required int width,
    required int height,
    int rotationDegrees = 0,
  }) {
    final rgb =
        _preprocessing.yuv420ToRgb(yPlane, uPlane, vPlane, width, height);
    return CameraFrameData(
      rgbBytes: rgb,
      width: width,
      height: height,
      rotationDegrees: rotationDegrees,
      format: 'yuv420',
    );
  }

  CameraFrameData fromBgra8888Bytes(
    Uint8List bgra, {
    required int width,
    required int height,
    int rotationDegrees = 0,
  }) {
    final rgb = _bgraToRgb(bgra, width, height);
    return CameraFrameData(
      rgbBytes: rgb,
      width: width,
      height: height,
      rotationDegrees: rotationDegrees,
      format: 'bgra8888',
    );
  }

  TransferableTypedData toTransferable(CameraFrameData frame) {
    return TransferableTypedData.fromList(<Uint8List>[frame.rgbBytes]);
  }

  Map<String, dynamic> toMeta(CameraFrameData frame) {
    return <String, dynamic>{
      'width': frame.width,
      'height': frame.height,
      'rotationDegrees': frame.rotationDegrees,
      'format': frame.format,
    };
  }

  Uint8List _bgraToRgb(Uint8List bgra, int width, int height) {
    final rgb = Uint8List(width * height * 3);
    var sourceIndex = 0;
    var targetIndex = 0;
    while (sourceIndex + 3 < bgra.length && targetIndex + 2 < rgb.length) {
      rgb[targetIndex] = bgra[sourceIndex + 2];
      rgb[targetIndex + 1] = bgra[sourceIndex + 1];
      rgb[targetIndex + 2] = bgra[sourceIndex];
      sourceIndex += 4;
      targetIndex += 3;
    }
    return rgb;
  }
}

class CameraFrameData {
  const CameraFrameData({
    required this.rgbBytes,
    required this.width,
    required this.height,
    required this.rotationDegrees,
    required this.format,
  });

  final Uint8List rgbBytes;
  final int width;
  final int height;
  final int rotationDegrees;
  final String format;
}
