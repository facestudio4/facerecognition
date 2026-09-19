import 'dart:async';
import 'dart:isolate';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:face_studio_mobile_client/face_engine/isolate_worker.dart';

void main() {
  test('worker isolate responds and acks frame via TransferableTypedData',
      () async {
    final receive = ReceivePort();
    SendPort? workerSendPort;
    final sendPortCompleter = Completer<SendPort>();
    final modelsLoaded = Completer<void>();
    final ackCompleter = Completer<int>();

    receive.listen((message) {
      if (message is SendPort) {
        workerSendPort = message;
        sendPortCompleter.complete(message);
        return;
      }
      if (message is Map) {
        final type = message['type'];
        if (type == 'log' && message['msg'] == 'models_loaded') {
          modelsLoaded.complete();
        } else if (type == 'ack' && message['frameId'] != null) {
          ackCompleter.complete(message['frameId'] as int);
        }
      }
    });

    final isolate = await Isolate.spawn(isolateEntry, receive.sendPort);

    // Wait to receive the worker's SendPort
    workerSendPort =
        await sendPortCompleter.future.timeout(const Duration(seconds: 10));
    final sendPort = workerSendPort!;

    // Initialize models (worker will send a log 'models_loaded')
    sendPort.send({'type': 'init', 'useGpu': false});
    await modelsLoaded.future.timeout(const Duration(seconds: 10));

    // Send a tiny frame as TransferableTypedData
    final data = Uint8List.fromList(List<int>.filled(16, 128));
    final ttd = TransferableTypedData.fromList([data]);
    sendPort.send({
      'type': 'frame',
      'frameId': 42,
      'data': ttd,
      'meta': {'width': 1, 'height': 1}
    });

    final ackId = await ackCompleter.future.timeout(const Duration(seconds: 10));
    expect(ackId, 42);

    // Cleanup
    receive.close();
    isolate.kill(priority: Isolate.immediate);
  });
}
