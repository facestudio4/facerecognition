import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter/services.dart';
import 'package:flutter/foundation.dart';

void main() {
  testWidgets('back button prevented by WillPopScope',
      (WidgetTester tester) async {
    await tester.pumpWidget(MaterialApp(
      home: Builder(builder: (context) {
        return Scaffold(
          body: ElevatedButton(
            onPressed: () {
              Navigator.of(context).push(MaterialPageRoute(builder: (_) {
                return WillPopScope(
                  onWillPop: () async => false,
                  child: const Scaffold(body: Center(child: Text('child'))),
                );
              }));
            },
            child: const Text('push'),
          ),
        );
      }),
    ));

    await tester.tap(find.text('push'));
    await tester.pumpAndSettle();
    expect(find.text('child'), findsOneWidget);

    // Simulate system back button; WillPopScope returns false so pop is prevented.
    final handled = await tester.binding.handlePopRoute();
    expect(handled, isTrue);
    expect(find.text('child'), findsOneWidget);
  });

  testWidgets('back button allowed when onWillPop returns true',
      (WidgetTester tester) async {
    await tester.pumpWidget(MaterialApp(
      home: Builder(builder: (context) {
        return Scaffold(
          body: ElevatedButton(
            onPressed: () {
              Navigator.of(context).push(MaterialPageRoute(builder: (_) {
                return WillPopScope(
                  onWillPop: () async => true,
                  child: const Scaffold(body: Center(child: Text('child'))),
                );
              }));
            },
            child: const Text('push'),
          ),
        );
      }),
    ));

    await tester.tap(find.text('push'));
    await tester.pumpAndSettle();
    expect(find.text('child'), findsOneWidget);

    // Simulate system back button; WillPopScope returns true so pop should occur.
    final handled = await tester.binding.handlePopRoute();
    expect(handled, isTrue);
    await tester.pumpAndSettle();
    expect(find.text('child'), findsNothing);
  });

  testWidgets('Android: prevented back does not call SystemNavigator.pop',
      (WidgetTester tester) async {
    // Override platform to Android for this test.
    final prev = debugDefaultTargetPlatformOverride;
    debugDefaultTargetPlatformOverride = TargetPlatform.android;

    final calls = <String>[];
    SystemChannels.platform.setMockMethodCallHandler((call) async {
      calls.add(call.method);
      return null;
    });

    try {
      await tester.pumpWidget(MaterialApp(
        home: Builder(builder: (context) {
          return Scaffold(
            body: ElevatedButton(
              onPressed: () {
                Navigator.of(context).push(MaterialPageRoute(builder: (_) {
                  return WillPopScope(
                    onWillPop: () async => false,
                    child: const Scaffold(body: Center(child: Text('child'))),
                  );
                }));
              },
              child: const Text('push'),
            ),
          );
        }),
      ));

      await tester.tap(find.text('push'));
      await tester.pumpAndSettle();
      expect(find.text('child'), findsOneWidget);

      // Simulate system back; WillPopScope prevents popping, framework should report handled
      final handled = await tester.binding.handlePopRoute();
      expect(handled, isTrue);
      // Allow incidental platform calls; ensure SystemNavigator.pop wasn't invoked.
      expect(calls.contains('SystemNavigator.pop'), isFalse,
          reason:
              'SystemNavigator.pop should not be invoked when pop was handled');
    } finally {
      SystemChannels.platform.setMockMethodCallHandler(null);
      debugDefaultTargetPlatformOverride = prev;
    }
  });

  testWidgets('Android: at root the pop route is unhandled',
      (WidgetTester tester) async {
    final prev = debugDefaultTargetPlatformOverride;
    debugDefaultTargetPlatformOverride = TargetPlatform.android;

    SystemChannels.platform.setMockMethodCallHandler((call) async {
      return null;
    });
    try {
      await tester.pumpWidget(
          const MaterialApp(home: Scaffold(body: Center(child: Text('root')))));
      await tester.pumpAndSettle();

      // No route to pop; framework should report unhandled so embedding may call SystemNavigator.pop.
      final handled = await tester.binding.handlePopRoute();
      expect(handled, isFalse);
    } finally {
      SystemChannels.platform.setMockMethodCallHandler(null);
      debugDefaultTargetPlatformOverride = prev;
    }
  });

  testWidgets(
      'Android: left-edge drag does not pop when WillPopScope prevents pop',
      (WidgetTester tester) async {
    final prev = debugDefaultTargetPlatformOverride;
    debugDefaultTargetPlatformOverride = TargetPlatform.android;
    try {
      await tester.pumpWidget(MaterialApp(
        home: Builder(builder: (context) {
          return Scaffold(
            body: ElevatedButton(
              onPressed: () {
                Navigator.of(context).push(MaterialPageRoute(builder: (_) {
                  return WillPopScope(
                    onWillPop: () async => false,
                    child: const Scaffold(body: Center(child: Text('child'))),
                  );
                }));
              },
              child: const Text('push'),
            ),
          );
        }),
      ));

      await tester.tap(find.text('push'));
      await tester.pumpAndSettle();
      expect(find.text('child'), findsOneWidget);

      // Attempt a left-edge drag (edge-swipe). On Android this shouldn't trigger a pop.
      final scaffoldFinder = find.byType(Scaffold).first;
      final size = tester.getSize(scaffoldFinder);
      final start = Offset(0.0, size.height / 2);
      await tester.dragFrom(start, const Offset(300, 0));
      await tester.pumpAndSettle();
      expect(find.text('child'), findsOneWidget);
    } finally {
      debugDefaultTargetPlatformOverride = prev;
    }
  });

  testWidgets(
      'Dialog: back closes dialog even if parent WillPopScope prevents pop',
      (WidgetTester tester) async {
    await tester.pumpWidget(MaterialApp(
      home: Builder(builder: (context) {
        return WillPopScope(
          onWillPop: () async => false,
          child: Scaffold(
            body: ElevatedButton(
              onPressed: () {
                showDialog<void>(
                  context: context,
                  builder: (context) => const AlertDialog(
                    content: Text('dialog content'),
                  ),
                );
              },
              child: const Text('open dialog'),
            ),
          ),
        );
      }),
    ));

    await tester.tap(find.text('open dialog'));
    await tester.pumpAndSettle();
    expect(find.text('dialog content'), findsOneWidget);

    // Simulate system back; should close the dialog (top route) even if parent prevents pop
    final handled = await tester.binding.handlePopRoute();
    expect(handled, isTrue);
    await tester.pumpAndSettle();
    expect(find.text('dialog content'), findsNothing);
  });

  testWidgets('Drawer: back closes drawer when open',
      (WidgetTester tester) async {
    await tester.pumpWidget(MaterialApp(
      home: Scaffold(
        appBar: AppBar(title: const Text('home')),
        drawer: const Drawer(child: Center(child: Text('drawer content'))),
        body: Builder(builder: (innerContext) {
          return ElevatedButton(
            onPressed: () => Scaffold.of(innerContext).openDrawer(),
            child: const Text('open drawer'),
          );
        }),
      ),
    ));

    await tester.tap(find.text('open drawer'));
    await tester.pumpAndSettle();
    expect(find.text('drawer content'), findsOneWidget);

    // Simulate system back; should close the drawer (pop the drawer route)
    final handled = await tester.binding.handlePopRoute();
    expect(handled, isTrue);
    await tester.pumpAndSettle();
    expect(find.text('drawer content'), findsNothing);
  });

  testWidgets(
      'Android: left-edge drag allowed when onWillPop returns true but route may not support gesture',
      (WidgetTester tester) async {
    final prev = debugDefaultTargetPlatformOverride;
    debugDefaultTargetPlatformOverride = TargetPlatform.android;
    try {
      await tester.pumpWidget(MaterialApp(
        home: Builder(builder: (context) {
          return Scaffold(
            body: ElevatedButton(
              onPressed: () {
                Navigator.of(context).push(MaterialPageRoute(builder: (_) {
                  return WillPopScope(
                    onWillPop: () async => true,
                    child: const Scaffold(body: Center(child: Text('child'))),
                  );
                }));
              },
              child: const Text('push'),
            ),
          );
        }),
      ));

      await tester.tap(find.text('push'));
      await tester.pumpAndSettle();
      expect(find.text('child'), findsOneWidget);

      // Attempt a left-edge drag; Android routes typically don't support back-swipe,
      // so we assert the child remains (gesture doesn't pop by default).
      final scaffoldFinder = find.byType(Scaffold).first;
      final size = tester.getSize(scaffoldFinder);
      final start = Offset(0.0, size.height / 2);
      await tester.dragFrom(start, const Offset(300, 0));
      await tester.pumpAndSettle();
      expect(find.text('child'), findsOneWidget);
    } finally {
      debugDefaultTargetPlatformOverride = prev;
    }
  });
}
