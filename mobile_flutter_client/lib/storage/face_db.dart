import 'dart:math' as math;
import 'dart:io';
import 'dart:typed_data';

import 'package:hive/hive.dart';
import 'package:path_provider/path_provider.dart';

class FaceDB {
  FaceDB({this.baseDirectoryPath, this.boxName = 'face_embeddings'});

  final String? baseDirectoryPath;
  final String boxName;

  Box<dynamic>? _box;

  bool get isOpen => _box?.isOpen ?? false;

  Future<void> open() async {
    if (isOpen) {
      return;
    }

    final basePath = baseDirectoryPath ?? await _resolveBasePath();
    Hive.init(basePath);
    _box = await Hive.openBox<dynamic>(boxName);
  }

  Future<void> close() async {
    await _box?.close();
    _box = null;
  }

  Future<void> putEmbedding(String userId, Float32List embedding) async {
    final box = _requireBox();
    final record = _normalizeRecord(box.get(userId));
    record['embeddings'].add(_toList(embedding));
    record['updatedAt'] = DateTime.now().toIso8601String();
    await box.put(userId, record);
  }

  Future<Map<String, dynamic>?> findNearest(Float32List embedding,
      {int topK = 1}) async {
    if (_box == null || _box!.isEmpty) {
      return null;
    }

    final query = _normalizeVector(embedding);
    String? bestUserId;
    double bestScore = double.negativeInfinity;

    for (final key in _box!.keys) {
      final userId = key.toString();
      final record = _normalizeRecord(_box!.get(key));
      final storedEmbeddings = record['embeddings'] as List<dynamic>;
      for (final stored in storedEmbeddings) {
        final score = _cosineSimilarity(query, _normalizeVector(stored));
        if (score > bestScore) {
          bestScore = score;
          bestUserId = userId;
        }
      }
    }

    if (bestUserId == null) {
      return null;
    }

    return <String, dynamic>{
      'userId': bestUserId,
      'score': bestScore,
      'topK': topK,
    };
  }

  Future<void> removeUser(String userId) async {
    final box = _box;
    if (box == null) {
      return;
    }
    await box.delete(userId);
  }

  Box<dynamic> _requireBox() {
    final box = _box;
    if (box == null) {
      throw StateError('FaceDB.open() must be called before use.');
    }
    return box;
  }

  Map<String, dynamic> _normalizeRecord(dynamic value) {
    if (value is Map) {
      final embeddings = value['embeddings'];
      return <String, dynamic>{
        'embeddings': embeddings is List
            ? List<dynamic>.from(embeddings)
            : <List<double>>[],
        'updatedAt': value['updatedAt'] ?? DateTime.now().toIso8601String(),
      };
    }

    return <String, dynamic>{
      'embeddings': <List<double>>[],
      'updatedAt': DateTime.now().toIso8601String(),
    };
  }

  List<double> _toList(Float32List embedding) =>
      embedding.map((value) => value.toDouble()).toList(growable: false);

  List<double> _normalizeVector(dynamic values) {
    if (values is Float32List) {
      return values.map((value) => value.toDouble()).toList(growable: false);
    }
    if (values is List) {
      return values
          .map((value) => (value as num).toDouble())
          .toList(growable: false);
    }
    throw ArgumentError.value(
        values, 'values', 'Expected a list or Float32List');
  }

  double _cosineSimilarity(List<double> a, List<double> b) {
    final length = math.min(a.length, b.length);
    if (length == 0) {
      return 0.0;
    }

    double dot = 0.0;
    double normA = 0.0;
    double normB = 0.0;
    for (var i = 0; i < length; i++) {
      final av = a[i];
      final bv = b[i];
      dot += av * bv;
      normA += av * av;
      normB += bv * bv;
    }

    if (normA == 0.0 || normB == 0.0) {
      return 0.0;
    }

    return dot / (math.sqrt(normA) * math.sqrt(normB));
  }

  Future<String> _resolveBasePath() async {
    try {
      return (await getApplicationDocumentsDirectory()).path;
    } catch (_) {
      return Directory.systemTemp.path;
    }
  }
}
