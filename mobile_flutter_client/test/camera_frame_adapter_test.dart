import 'dart:typed_data';

import 'package:face_studio_mobile_client/face_engine/camera_frame_adapter.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('CameraFrameAdapter converts BGRA bytes into RGB transferable data', () {
    final adapter = CameraFrameAdapter();
    final frame = adapter.fromBgra8888Bytes(
      Uint8List.fromList(<int>[
        10,
        20,
        30,
        255,
        40,
        50,
        60,
        255,
      ]),
      width: 2,
      height: 1,
    );

    expect(frame.width, 2);
    expect(frame.height, 1);
    expect(
        frame.rgbBytes,
        Uint8List.fromList(<int>[
          30,
          20,
          10,
          60,
          50,
          40,
        ]));

    final ttd = adapter.toTransferable(frame);
    final materialized = ttd.materialize().asUint8List();
    expect(materialized, frame.rgbBytes);

    final meta = adapter.toMeta(frame);
    expect(meta['width'], 2);
    expect(meta['height'], 1);
    expect(meta['rotationDegrees'], 0);
  });
}
