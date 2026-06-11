import 'dart:math' as math;
import 'dart:typed_data';

import 'package:tflite_flutter/tflite_flutter.dart';

import '../storage/face_db.dart';
import 'model_assets.dart';
import 'preprocessing.dart';

class ModelProvider {
  ModelProvider({
    FaceDB? faceDb,
    this.detectorAssetPath = FaceModelAssets.detector,
    this.embedderAssetPath = FaceModelAssets.embedder,
    Preprocessing? preprocessing,
  })  : _faceDb = faceDb ?? FaceDB(),
        _preprocessing = preprocessing ?? Preprocessing();

  final String detectorAssetPath;
  final String embedderAssetPath;
  final FaceDB _faceDb;
  final Preprocessing _preprocessing;

  Interpreter? _detectorInterpreter;
  Interpreter? _embedderInterpreter;
  bool _loaded = false;

  bool get isLoaded => _loaded;

  Future<void> loadModels({bool useGpu = true}) async {
    if (_loaded) {
      return;
    }

    await _faceDb.open();
    _detectorInterpreter =
        await _tryLoadInterpreter(detectorAssetPath, useGpu: useGpu);
    _embedderInterpreter =
        await _tryLoadInterpreter(embedderAssetPath, useGpu: useGpu);
    _loaded = true;
  }

  Future<List<Map<String, dynamic>>> runFaceDetect(
      Uint8List rgbBytes, int width, int height) async {
    if (!_loaded || _detectorInterpreter == null) {
      return _fallbackDetections(width, height);
    }

    final resized = _preprocessing.resizeRgb(rgbBytes, width, height, 128, 128);
    final input = _preprocessing.normalize(resized);
    final outputTensors = <int, Object>{
      0: _allocateOutputBuffer(_detectorInterpreter!.getOutputTensor(0)),
    };

    _detectorInterpreter!.runForMultipleInputs([input], outputTensors);
    return _parseDetections(outputTensors, width, height);
  }

  Future<Uint8List> extractAlignedCrop(
      Uint8List rgbBytes, int width, int height, Map det) async {
    final bbox = det['bbox'];
    if (bbox is Map) {
      final x = (bbox['x'] as num?)?.toInt() ?? 0;
      final y = (bbox['y'] as num?)?.toInt() ?? 0;
      final w = (bbox['w'] as num?)?.toInt() ?? width;
      final h = (bbox['h'] as num?)?.toInt() ?? height;
      return _preprocessing.cropAndResizeRgb(
          rgbBytes, width, height, x, y, w, h, 112, 112);
    }

    return _preprocessing.resizeRgb(rgbBytes, width, height, 112, 112);
  }

  Future<Float32List> runEmbedding(Uint8List alignedCrop) async {
    if (!_loaded || _embedderInterpreter == null) {
      return _fallbackEmbedding(alignedCrop);
    }

    final input = _preprocessing.normalize(alignedCrop);
    final output =
        _allocateOutputBuffer(_embedderInterpreter!.getOutputTensor(0));
    _embedderInterpreter!.run(input, output);

    if (output is Float32List) {
      return _normalizeEmbedding(output);
    }
    if (output is List) {
      return _normalizeEmbedding(Float32List.fromList(
          output.cast<num>().map((value) => value.toDouble()).toList()));
    }

    return _fallbackEmbedding(alignedCrop);
  }

  Future<Map<String, dynamic>?> searchEmbedding(Float32List embedding) async {
    return _faceDb.findNearest(embedding);
  }

  Future<void> storeEmbedding(String userId, Float32List embedding) async {
    await _faceDb.putEmbedding(userId, embedding);
  }

  Future<void> dispose() async {
    _detectorInterpreter?.close();
    _embedderInterpreter?.close();
    await _faceDb.close();
    _detectorInterpreter = null;
    _embedderInterpreter = null;
    _loaded = false;
  }

  Future<Interpreter?> _tryLoadInterpreter(String assetPath,
      {required bool useGpu}) async {
    try {
      final options = InterpreterOptions()..threads = 2;
      if (useGpu) {
        try {
          options.addDelegate(GpuDelegateV2());
        } catch (_) {
          // Fall back to CPU if a GPU delegate is unavailable on this device.
        }
      }

      return await Interpreter.fromAsset(assetPath, options: options);
    } catch (_) {
      return null;
    }
  }

  List<Map<String, dynamic>> _fallbackDetections(int width, int height) {
    if (width <= 0 || height <= 0) {
      return <Map<String, dynamic>>[];
    }

    final boxWidth = math.max(1, (width * 0.7).round());
    final boxHeight = math.max(1, (height * 0.7).round());
    final left = ((width - boxWidth) / 2).round().clamp(0, width - 1);
    final top = ((height - boxHeight) / 2).round().clamp(0, height - 1);
    return <Map<String, dynamic>>[
      <String, dynamic>{
        'bbox': <String, dynamic>{
          'x': left,
          'y': top,
          'w': boxWidth,
          'h': boxHeight
        },
        'confidence': 0.5,
        'keypoints': const <Map<String, dynamic>>[],
      },
    ];
  }

  List<Map<String, dynamic>> _parseDetections(
      Map<int, Object> outputs, int width, int height) {
    final scoreBuffer = outputs.values
        .whereType<Float32List>()
        .where((buffer) => buffer.isNotEmpty)
        .toList(growable: false);
    if (scoreBuffer.isEmpty) {
      return _fallbackDetections(width, height);
    }

    final scores = scoreBuffer.first;
    final detections = <Map<String, dynamic>>[];
    for (var i = 0; i < scores.length; i++) {
      final score = scores[i];
      if (score < 0.6) {
        continue;
      }
      detections.add(<String, dynamic>{
        'bbox': <String, dynamic>{
          'x': (width * 0.2).round(),
          'y': (height * 0.2).round(),
          'w': (width * 0.6).round(),
          'h': (height * 0.6).round(),
        },
        'confidence': score,
        'keypoints': const <Map<String, dynamic>>[],
      });
      if (detections.length >= 3) {
        break;
      }
    }

    return detections.isEmpty ? _fallbackDetections(width, height) : detections;
  }

  Object _allocateOutputBuffer(Tensor tensor) {
    final shape = tensor.shape;
    final elementCount = shape.fold<int>(
        1, (previousValue, element) => previousValue * element.toInt());
    return Float32List(elementCount);
  }

  List<double> _normalizeVector(Float32List values) {
    final sumSquares =
        values.fold<double>(0.0, (sum, value) => sum + value * value);
    if (sumSquares == 0.0) {
      return values.map((value) => value.toDouble()).toList(growable: false);
    }

    final norm = math.sqrt(sumSquares);
    return values
        .map((value) => (value / norm).toDouble())
        .toList(growable: false);
  }

  Float32List _normalizeEmbedding(Float32List values) {
    final normalized = _normalizeVector(values);
    return Float32List.fromList(normalized);
  }

  Float32List _fallbackEmbedding(Uint8List alignedCrop) {
    const size = 128;
    final embedding = Float32List(size);
    if (alignedCrop.isEmpty) {
      return embedding;
    }

    for (var index = 0; index < alignedCrop.length; index++) {
      embedding[index % size] += alignedCrop[index] / 255.0;
    }

    return _normalizeEmbedding(embedding);
  }
}
