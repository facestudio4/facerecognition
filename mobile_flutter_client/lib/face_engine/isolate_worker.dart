// Worker isolate entry and message handlers.
// Runs inside a spawned isolate: loads models, receives frames, runs detection/embedding and sends results back.
// ignore_for_file: unused_import, unused_local_variable, unused_element

import 'dart:async';
import 'dart:typed_data';
import 'package:flutter/foundation.dart';
import 'dart:isolate';

import 'model_provider.dart';
import 'recognition_result.dart';

late SendPort _mainSendPort;
late ModelProvider _models;

void isolateEntry(SendPort mainSendPort) {
  _mainSendPort = mainSendPort;
  final port = ReceivePort();

  // Reply with the worker's SendPort so main can send messages
  _mainSendPort.send(port.sendPort);

  port.listen((message) async {
    try {
      if (message is Map) {
        final type = message['type'];
        switch (type) {
          case 'init':
            final useGpu = message['useGpu'] as bool? ?? true;
            _models = ModelProvider();
            await _models.loadModels(useGpu: useGpu);
            _mainSendPort.send({'type': 'log', 'msg': 'models_loaded'});
            break;
          case 'frame':
            await _handleFrame(message);
            break;
          case 'enroll':
            await _handleEnroll(message);
            break;
          case 'removeUser':
            // TODO: instruct FaceDB to remove user
            break;
        }
      }
    } catch (e, st) {
      _mainSendPort.send(
          {'type': 'error', 'error': e.toString(), 'stack': st.toString()});
    }
  });
}

Future<void> _handleFrame(Map msg) async {
  final frameId = msg['frameId'] as int?;
  final ttd = msg['data'] as TransferableTypedData?;
  final meta = Map<String, dynamic>.from(msg['meta'] ?? {});
  if (ttd == null) return;

  // Convert to usable bytes (ownership transferred)
  final bytes = ttd.materialize().asUint8List();

  // 1) Run BlazeFace detection (placeholder)
  final detections = await _models.runFaceDetect(
      bytes, meta['width'] as int, meta['height'] as int);

  // 2) For each detection do alignment + embedding
  for (final det in detections) {
    final crop = await _models.extractAlignedCrop(
        bytes, meta['width'] as int, meta['height'] as int, det);
    final embedding = await _models.runEmbedding(crop);

    // 3) Search local DB (placeholder - actual FaceDB to be implemented)
    final match = await _models.searchEmbedding(embedding);

    // 4) Compose recognition result and send to main isolate
    final result = RecognitionResult(
      userId: match?['userId'] as String?,
      score: match?['score'] as double? ?? 0.0,
      livenessScore: 0.0,
      timestamp: DateTime.now(),
      bbox: det['bbox'] as Map<String, dynamic>?,
      debug: {'det_conf': det['confidence'], 'emb_len': embedding.length},
    );

    _mainSendPort.send({'type': 'result', 'data': result.toMap()});
  }

  // Acknowledge frame processed
  if (frameId != null) {
    _mainSendPort.send({'type': 'ack', 'frameId': frameId});
  }
}

Future<void> _handleEnroll(Map msg) async {
  final userId = msg['userId'] as String?;
  final ttd = msg['data'] as TransferableTypedData?;
  final meta = Map<String, dynamic>.from(msg['meta'] ?? {});
  if (userId == null || ttd == null) return;
  final bytes = ttd.materialize().asUint8List();

  // Enrollment flow: detect, align, embed, store
  final detections = await _models.runFaceDetect(
      bytes, meta['width'] as int, meta['height'] as int);
  if (detections.isEmpty) return;
  final det = detections.first;
  final crop = await _models.extractAlignedCrop(
      bytes, meta['width'] as int, meta['height'] as int, det);
  final embedding = await _models.runEmbedding(crop);
  await _models.storeEmbedding(userId, embedding);
  _mainSendPort.send({'type': 'log', 'msg': 'enrolled', 'userId': userId});
}
