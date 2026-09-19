import 'dart:typed_data';

import 'package:face_studio_mobile_client/face_engine/preprocessing.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('Preprocessing normalizes and crops RGB frames', () {
    final preprocessing = Preprocessing();

    final rgb = Uint8List.fromList(<int>[
      255,
      0,
      0,
      0,
      255,
      0,
      0,
      0,
      255,
      255,
      255,
      255,
    ]);

    final resized = preprocessing.resizeRgb(rgb, 2, 2, 4, 4);
    expect(resized.length, 4 * 4 * 3);
    expect(resized[0], 255);
    expect(resized[1], 0);
    expect(resized[2], 0);

    final cropped = preprocessing.cropAndResizeRgb(rgb, 2, 2, 0, 0, 2, 2, 2, 2);
    expect(cropped.length, rgb.length);
    expect(cropped[0], 255);
    expect(cropped[3], 0);

    final normalized =
        preprocessing.normalize(Uint8List.fromList(<int>[0, 128, 255]));
    expect(normalized.length, 3);
    expect(normalized[0], closeTo(0.0, 0.0001));
    expect(normalized[1], closeTo(128 / 255.0, 0.0001));
    expect(normalized[2], closeTo(1.0, 0.0001));
  });
}
