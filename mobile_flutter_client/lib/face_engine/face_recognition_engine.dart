// FaceRecognitionEngine: orchestrates camera input, worker isolate, enrollments,
// and exposes a recognition result stream to the UI.
// ignore_for_file: unused_import, unused_local_variable, unused_element

import 'dart:async';
import 'dart:isolate';

import 'package:camera/camera.dart';
import 'package:flutter/foundation.dart';

import 'camera_frame_adapter.dart';
import 'isolate_worker.dart';
import 'recognition_result.dart';

class FaceRecognitionEngine {
  FaceRecognitionEngine({CameraFrameAdapter? frameAdapter})
      : _frameAdapter = frameAdapter ?? CameraFrameAdapter();

  final CameraFrameAdapter _frameAdapter;

  // Public stream of recognition results for the UI
  final StreamController<RecognitionResult> _resultsController =
      StreamController.broadcast();

  // Ports for isolate communication
  Isolate? _workerIsolate;
  SendPort? _workerSendPort;
  ReceivePort? _mainReceivePort;

  // In-flight frame tracking
  final Map<int, Completer<void>> _inFlight = {};
  int _frameCounter = 0;

  // Engine state
  bool _initialized = false;

  Stream<RecognitionResult> get recognitionStream => _resultsController.stream;

  /// Convert a [CameraImage] and send it to the worker isolate.
  void processCameraImage(CameraImage image) {
    final frame = _frameAdapter.fromCameraImage(image);
    processCameraFrame(
        _frameAdapter.toTransferable(frame), _frameAdapter.toMeta(frame));
  }

  /// Convert a [CameraImage] with an explicit rotation and send it to the worker isolate.
  void processCameraImageWithRotation(CameraImage image,
      {required int rotationDegrees}) {
    final frame = _frameAdapter.fromCameraImage(
      image,
      rotationDegrees: rotationDegrees,
    );
    processCameraFrame(
        _frameAdapter.toTransferable(frame), _frameAdapter.toMeta(frame));
  }

  Future<void> initialize({bool useGpu = true}) async {
    if (_initialized) return;
    _mainReceivePort = ReceivePort();
    final completer = Completer<SendPort>();

    _mainReceivePort!.listen((message) {
      if (message is SendPort) {
        _workerSendPort = message;
        completer.complete(message);
        return;
      }
      // worker -> main messages
      _handleWorkerMessage(message);
    });

    // Spawn isolate and pass the SendPort for main -> worker messaging
    _workerIsolate = await Isolate.spawn<SendPort>(
      isolateEntry,
      _mainReceivePort!.sendPort,
      paused: false,
      onError: _mainReceivePort!.sendPort,
      onExit: _mainReceivePort!.sendPort,
    );

    // Wait until worker supplies its SendPort
    await completer.future;

    // Now tell worker to initialize models
    _workerSendPort!.send({'type': 'init', 'useGpu': useGpu});

    _initialized = true;
  }

  /// Attach a camera RGB frame (packed bytes) to be processed.
  /// Use TransferableTypedData on the message when sending across isolates.
  void processCameraFrame(
      TransferableTypedData frameData, Map<String, dynamic> meta) {
    if (!_initialized || _workerSendPort == null) return;
    final id = ++_frameCounter;
    _workerSendPort!.send({
      'type': 'frame',
      'frameId': id,
      'data': frameData,
      'meta': meta,
    });

    // Optionally track in-flight
    _inFlight[id] = Completer<void>();
  }

  Future<void> enroll(
      String userId, TransferableTypedData frameData, Map meta) async {
    if (!_initialized || _workerSendPort == null) return;
    _workerSendPort!.send({
      'type': 'enroll',
      'userId': userId,
      'data': frameData,
      'meta': meta,
    });
  }

  Future<void> removeEnrollment(String userId) async {
    if (!_initialized || _workerSendPort == null) return;
    _workerSendPort!.send({'type': 'removeUser', 'userId': userId});
  }

  void _handleWorkerMessage(dynamic message) {
    if (message is Map) {
      final type = message['type'];
      switch (type) {
        case 'result':
          final result = RecognitionResult.fromMap(
              Map<String, dynamic>.from(message['data'] ?? {}));
          _resultsController.add(result);
          break;
        case 'ack':
          final frameId = message['frameId'] as int?;
          if (frameId != null) {
            final c = _inFlight.remove(frameId);
            c?.complete();
          }
          break;
        default:
          // TODO: handle logs/debug
          break;
      }
    }
  }

  Future<void> dispose() async {
    _resultsController.close();
    _mainReceivePort?.close();
    _workerIsolate?.kill(priority: Isolate.immediate);
    _workerIsolate = null;
    _workerSendPort = null;
    _initialized = false;
  }
}
