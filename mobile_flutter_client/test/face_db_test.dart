import 'dart:io';
import 'dart:typed_data';

import 'package:face_studio_mobile_client/storage/face_db.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('FaceDB stores, searches, and removes embeddings', () async {
    final tempDir = await Directory.systemTemp.createTemp('face_db_test_');
    final faceDb =
        FaceDB(baseDirectoryPath: tempDir.path, boxName: 'face_db_test_box');

    try {
      await faceDb.open();
      await faceDb.putEmbedding(
          'alice', Float32List.fromList(<double>[1.0, 0.0, 0.0]));
      await faceDb.putEmbedding(
          'bob', Float32List.fromList(<double>[0.0, 1.0, 0.0]));

      final nearest = await faceDb
          .findNearest(Float32List.fromList(<double>[0.98, 0.02, 0.0]));
      expect(nearest, isNotNull);
      expect(nearest!['userId'], 'alice');
      expect((nearest['score'] as num).toDouble(), greaterThan(0.9));

      await faceDb.removeUser('alice');
      final afterRemoval = await faceDb
          .findNearest(Float32List.fromList(<double>[1.0, 0.0, 0.0]));
      expect(afterRemoval, isNotNull);
      expect(afterRemoval!['userId'], 'bob');
    } finally {
      await faceDb.close();
      if (await tempDir.exists()) {
        await tempDir.delete(recursive: true);
      }
    }
  });
}
