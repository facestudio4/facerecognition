import 'dart:math' as math;

import 'package:flutter/material.dart';

enum RapidActionType {
  pulse,
  checkpoint,
  sync,
  scan,
  secure,
  map,
  relay,
  optimize,
  verify,
  launch,
}

class RapidScenario {
  final int id;
  final String title;
  final String subtitle;
  final String actionLabel;
  final IconData icon;
  final Color color;
  final Color accent;
  final RapidActionType actionType;
  final double intensity;

  const RapidScenario({
    required this.id,
    required this.title,
    required this.subtitle,
    required this.actionLabel,
    required this.icon,
    required this.color,
    required this.accent,
    required this.actionType,
    required this.intensity,
  });
}

enum RapidActionMode {
  dialogMatrix,
  timelineSheet,
  consolePage,
  snackBurst,
  gateCheck,
  tunerSheet,
  toggleLab,
  progressRun,
  routePreview,
  pulseCode,
}

class RapidActionProgram {
  final RapidActionMode mode;
  final int lane;
  final int level;
  final int pulse;
  final String token;
  final String objective;

  const RapidActionProgram({
    required this.mode,
    required this.lane,
    required this.level,
    required this.pulse,
    required this.token,
    required this.objective,
  });
}

class _RapidThemeFamily {
  final Color shellA;
  final Color shellB;
  final Color edge;
  final Color glow;
  final Color chipA;
  final Color chipB;
  final Color actionA;

  const _RapidThemeFamily({
    required this.shellA,
    required this.shellB,
    required this.edge,
    required this.glow,
    required this.chipA,
    required this.chipB,
    required this.actionA,
  });
}

const List<_RapidThemeFamily> _rapidThemeFamilies = [
  _RapidThemeFamily(
    shellA: Color(0xFF163D5A),
    shellB: Color(0xFF0A1B2E),
    edge: Color(0xFF7DD9FF),
    glow: Color(0xFF5EC8FF),
    chipA: Color(0xFF103754),
    chipB: Color(0xFF8AD9FF),
    actionA: Color(0xFF163F63),
  ),
  _RapidThemeFamily(
    shellA: Color(0xFF4B2C12),
    shellB: Color(0xFF1E130A),
    edge: Color(0xFFFFBE6E),
    glow: Color(0xFFFFA646),
    chipA: Color(0xFF4A3118),
    chipB: Color(0xFFFFCC84),
    actionA: Color(0xFF5A3A18),
  ),
  _RapidThemeFamily(
    shellA: Color(0xFF103F33),
    shellB: Color(0xFF0A201A),
    edge: Color(0xFF7EF3B2),
    glow: Color(0xFF45D88F),
    chipA: Color(0xFF124236),
    chipB: Color(0xFF95FFC8),
    actionA: Color(0xFF195443),
  ),
  _RapidThemeFamily(
    shellA: Color(0xFF3A155C),
    shellB: Color(0xFF140A2A),
    edge: Color(0xFFC5A2FF),
    glow: Color(0xFFAF80FF),
    chipA: Color(0xFF341651),
    chipB: Color(0xFFD4B9FF),
    actionA: Color(0xFF442068),
  ),
];

_RapidThemeFamily _themeForScenarioId(int id) {
  final bucket = _themeBucketForScenarioId(id);
  return _rapidThemeFamilies[bucket];
}

String _themeTagForScenarioId(int id) {
  final bucket = _themeBucketForScenarioId(id);
  return const ['AURORA', 'SOLAR', 'EMERALD', 'NOVA'][bucket];
}

int _themeBucketForScenarioId(int id) {
  final raw = (id - 1) ~/ 100;
  if (raw < 0) {
    return 0;
  }
  if (raw > 3) {
    return 3;
  }
  return raw;
}

const List<String> _rapidAdjectives = [
  'Adaptive',
  'Neural',
  'Quantum',
  'Aero',
  'Dynamic',
  'Prism',
  'Kinetic',
  'Titan',
  'Vector',
  'Nova',
  'Signal',
  'Hyper',
  'Optic',
  'Fusion',
  'Sonic',
  'Polar',
  'Core',
  'Delta',
  'Vivid',
  'Pulse',
];

const List<String> _rapidDomains = [
  'Vision',
  'Identity',
  'Security',
  'Tracking',
  'Cluster',
  'Motion',
  'Insight',
  'Profile',
  'Gateway',
  'Engine',
  'Telemetry',
  'Beacon',
  'Network',
  'Guardian',
  'Signal',
  'Analyzer',
  'Console',
  'Lattice',
  'Atlas',
  'Hub',
];

const List<String> _rapidModes = [
  'Sweep',
  'Matrix',
  'Cascade',
  'Frame',
  'Sync',
  'Bridge',
  'Node',
  'Pilot',
  'Gate',
  'Drive',
  'Pulse',
  'Map',
  'Route',
  'Shield',
  'Stream',
  'Stack',
  'Track',
  'Orbit',
  'Grid',
  'Flow',
];

const List<IconData> _rapidIcons = [
  Icons.auto_awesome,
  Icons.radar,
  Icons.verified_user,
  Icons.layers,
  Icons.graphic_eq,
  Icons.route,
  Icons.memory,
  Icons.center_focus_strong,
  Icons.shield,
  Icons.blur_circular,
  Icons.analytics,
  Icons.bolt,
  Icons.pattern,
  Icons.hub,
  Icons.compare_arrows,
  Icons.speed,
  Icons.visibility,
  Icons.map,
  Icons.rocket_launch,
  Icons.fingerprint,
];

const List<Color> _rapidColors = [
  Color(0xFF6FD3FF),
  Color(0xFF7CEAB0),
  Color(0xFFFFC16B),
  Color(0xFFFF8C8C),
  Color(0xFFA8B4FF),
  Color(0xFFFF8FDB),
  Color(0xFF9BE8FF),
  Color(0xFF8DFFA8),
  Color(0xFFFFD97A),
  Color(0xFFFF9FB6),
];

const List<Color> _rapidAccents = [
  Color(0xFF1A3552),
  Color(0xFF173D33),
  Color(0xFF4A3314),
  Color(0xFF4A1F2A),
  Color(0xFF252C5B),
  Color(0xFF4E1D4B),
  Color(0xFF143A4B),
  Color(0xFF1B4025),
  Color(0xFF4C3D17),
  Color(0xFF4B2436),
];

String _rapidActionLabel(int id) {
  final action = [
    'Pulse',
    'Checkpoint',
    'Sync',
    'Scan',
    'Secure',
    'Map',
    'Relay',
    'Optimize',
    'Verify',
    'Launch',
  ][(id - 1) % 10];
  return '$action Sequence ${id.toString().padLeft(3, '0')}';
}

RapidActionType _rapidActionType(int id) {
  return RapidActionType.values[(id - 1) % RapidActionType.values.length];
}

final List<RapidScenario> rapidScenarios = List.generate(400, (index) {
  final id = index + 1;
  final adjective = _rapidAdjectives[index % _rapidAdjectives.length];
  final domain = _rapidDomains[(index * 3) % _rapidDomains.length];
  final mode = _rapidModes[(index * 7) % _rapidModes.length];
  return RapidScenario(
    id: id,
    title: '$adjective $domain $mode',
    subtitle:
        'Signature ${id.toString().padLeft(3, '0')} • Lane ${(index % 8) + 1} • Tier ${((index * 5) % 9) + 1}',
    actionLabel: _rapidActionLabel(id),
    icon: _rapidIcons[index % _rapidIcons.length],
    color: _rapidColors[index % _rapidColors.length],
    accent: _rapidAccents[index % _rapidAccents.length],
    actionType: _rapidActionType(id),
    intensity: 0.7 + ((index % 11) * 0.1),
  );
});

class RapidScenarioTile extends StatefulWidget {
  final RapidScenario scenario;

  const RapidScenarioTile({super.key, required this.scenario});

  @override
  State<RapidScenarioTile> createState() => _RapidScenarioTileState();
}

class _RapidScenarioTileState extends State<RapidScenarioTile>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: Duration(milliseconds: 1600 + (widget.scenario.id % 7) * 180),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _runAction() async {
    final s = widget.scenario;
    final program = _programForScenario(s);
    switch (program.mode) {
      case RapidActionMode.dialogMatrix:
        await _showMatrixDialog(s, program);
        break;
      case RapidActionMode.timelineSheet:
        await _showTimelineSheet(s, program);
        break;
      case RapidActionMode.consolePage:
        await _openConsolePage(s, program);
        break;
      case RapidActionMode.snackBurst:
        _showSnackBurst(s, program);
        break;
      case RapidActionMode.gateCheck:
        await _showGateCheck(s, program);
        break;
      case RapidActionMode.tunerSheet:
        await _showTunerSheet(s, program);
        break;
      case RapidActionMode.toggleLab:
        await _showToggleLab(s, program);
        break;
      case RapidActionMode.progressRun:
        await _showProgressRun(s, program);
        break;
      case RapidActionMode.routePreview:
        await _showRoutePreview(s, program);
        break;
      case RapidActionMode.pulseCode:
        await _showPulseCode(s, program);
        break;
    }
  }

  RapidActionProgram _programForScenario(RapidScenario scenario) {
    final seed = scenario.id - 1;
    final tokenHex = (seed * 37 + 19).toRadixString(16).toUpperCase();
    final routeMark = String.fromCharCode(65 + (seed % 26));
    return RapidActionProgram(
      mode: RapidActionMode.values[seed % RapidActionMode.values.length],
      lane: (seed % 8) + 1,
      level: ((seed * 7) % 12) + 1,
      pulse: ((seed * 13) % 97) + 3,
      token:
          '${scenario.id.toString().padLeft(3, '0')}-$routeMark-${tokenHex.padLeft(4, '0')}',
      objective:
          'Lane ${(seed % 8) + 1} -> Cluster ${((seed * 5) % 9) + 1} -> Tier ${((seed * 3) % 6) + 1}',
    );
  }

  Future<void> _showDialogCard(String title, String body) async {
    if (!mounted) {
      return;
    }
    await showDialog<void>(
      context: context,
      builder: (ctx) {
        return AlertDialog(
          title: Text(title),
          content: Text(body),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: const Text('OK'),
            ),
          ],
        );
      },
    );
  }

  Future<void> _showMatrixDialog(
      RapidScenario s, RapidActionProgram program) async {
    if (!mounted) {
      return;
    }
    await showDialog<void>(
      context: context,
      builder: (ctx) {
        return AlertDialog(
          title: Text('Matrix ${s.id.toString().padLeft(3, '0')}'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(s.title),
              const SizedBox(height: 8),
              Text(program.objective),
              const SizedBox(height: 10),
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: List<Widget>.generate(6, (i) {
                  final v = (program.pulse + i * program.level) % 100;
                  return Chip(label: Text('M$i:$v'));
                }),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: const Text('Close'),
            ),
          ],
        );
      },
    );
  }

  Future<void> _showTimelineSheet(
      RapidScenario s, RapidActionProgram program) async {
    if (!mounted) {
      return;
    }
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (ctx) {
        return Padding(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 18),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Timeline ${program.token}',
                  style: const TextStyle(
                      fontWeight: FontWeight.w800,
                      fontSize: 16,
                      color: Color(0xFFEAF4FF))),
              const SizedBox(height: 8),
              ...List<Widget>.generate(4, (i) {
                final value = ((program.pulse + i * 11) % 100) / 100;
                return Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: TweenAnimationBuilder<double>(
                    tween: Tween<double>(begin: 0, end: value),
                    duration: Duration(milliseconds: 360 + i * 160),
                    curve: Curves.easeOutCubic,
                    builder: (context, v, child) {
                      return Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('Stage ${i + 1} • ${s.actionLabel}'),
                          const SizedBox(height: 4),
                          LinearProgressIndicator(value: v),
                        ],
                      );
                    },
                  ),
                );
              }),
            ],
          ),
        );
      },
    );
  }

  Future<void> _openConsolePage(
      RapidScenario s, RapidActionProgram program) async {
    if (!mounted) {
      return;
    }
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => RapidActionConsolePage(scenario: s, program: program),
      ),
    );
  }

  void _showSnackBurst(RapidScenario s, RapidActionProgram program) {
    _toast('Burst ${program.token}: ${s.actionLabel}');
    Future<void>.delayed(const Duration(milliseconds: 900), () {
      if (!mounted) {
        return;
      }
      _toast('Lane ${program.lane} verified • Pulse ${program.pulse}');
    });
  }

  Future<void> _showGateCheck(
      RapidScenario s, RapidActionProgram program) async {
    if (!mounted) {
      return;
    }
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) {
        return AlertDialog(
          title: Text('Gate Check ${s.id.toString().padLeft(3, '0')}'),
          content: Text('${program.objective}\nToken ${program.token}'),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(false),
              child: const Text('Hold'),
            ),
            FilledButton(
              onPressed: () => Navigator.of(ctx).pop(true),
              child: const Text('Pass'),
            ),
          ],
        );
      },
    );
    _toast(
        ok == true ? 'Gate passed for ${s.title}' : 'Gate held for ${s.title}');
  }

  Future<void> _showTunerSheet(
      RapidScenario s, RapidActionProgram program) async {
    if (!mounted) {
      return;
    }
    double tune = (program.level / 12).clamp(0.15, 0.95).toDouble();
    await showModalBottomSheet<void>(
      context: context,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (context, setSheetState) {
            return Padding(
              padding: const EdgeInsets.fromLTRB(16, 14, 16, 20),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Tuner ${program.token}',
                      style: const TextStyle(
                          fontWeight: FontWeight.w800,
                          color: Color(0xFFEAF4FF))),
                  const SizedBox(height: 8),
                  Slider(
                    value: tune,
                    onChanged: (v) => setSheetState(() => tune = v),
                  ),
                  Text('Output ${(tune * 100).round()}% for ${s.actionLabel}'),
                  const SizedBox(height: 6),
                  FilledButton.tonal(
                    onPressed: () => Navigator.of(ctx).pop(),
                    child: const Text('Apply Tuning'),
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  Future<void> _showToggleLab(
      RapidScenario s, RapidActionProgram program) async {
    if (!mounted) {
      return;
    }
    bool a = program.lane.isEven;
    bool b = program.level.isOdd;
    bool c = program.pulse % 3 == 0;
    await showModalBottomSheet<void>(
      context: context,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (context, setSheetState) {
            return Padding(
              padding: const EdgeInsets.fromLTRB(16, 14, 16, 20),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  SwitchListTile(
                    value: a,
                    onChanged: (v) => setSheetState(() => a = v),
                    title: Text('Vector lock for ${s.title}'),
                  ),
                  SwitchListTile(
                    value: b,
                    onChanged: (v) => setSheetState(() => b = v),
                    title: const Text('Adaptive channel'),
                  ),
                  SwitchListTile(
                    value: c,
                    onChanged: (v) => setSheetState(() => c = v),
                    title: const Text('Diagnostic mirror'),
                  ),
                  FilledButton(
                    onPressed: () {
                      Navigator.of(ctx).pop();
                      _toast('Lab set: ${a ? 1 : 0}${b ? 1 : 0}${c ? 1 : 0}');
                    },
                    child: Text('Commit ${program.token}'),
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  Future<void> _showProgressRun(
      RapidScenario s, RapidActionProgram program) async {
    if (!mounted) {
      return;
    }
    await showDialog<void>(
      context: context,
      builder: (ctx) {
        return AlertDialog(
          title: Text('Run ${program.token}'),
          content: TweenAnimationBuilder<double>(
            tween: Tween<double>(begin: 0.0, end: 1.0),
            duration: Duration(milliseconds: 700 + (program.pulse * 9)),
            builder: (context, value, child) {
              return Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  LinearProgressIndicator(value: value),
                  const SizedBox(height: 8),
                  Text(
                      'Runtime ${(value * 100).round()}% • Lane ${program.lane}'),
                ],
              );
            },
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: const Text('Done'),
            ),
          ],
        );
      },
    );
  }

  Future<void> _showRoutePreview(
      RapidScenario s, RapidActionProgram program) async {
    if (!mounted) {
      return;
    }
    await showDialog<void>(
      context: context,
      builder: (ctx) {
        return AlertDialog(
          title: Text('Route ${program.lane}-${program.level}'),
          content: SizedBox(
            width: 320,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  height: 90,
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(10),
                    gradient: LinearGradient(
                      colors: [
                        s.color.withValues(alpha: 0.45),
                        s.accent.withValues(alpha: 0.95),
                      ],
                    ),
                  ),
                  child: Center(
                    child: Text(
                      program.objective,
                      style: const TextStyle(
                          color: Color(0xFFEAF4FF),
                          fontWeight: FontWeight.w700),
                    ),
                  ),
                ),
                const SizedBox(height: 8),
                Text('Preview set for ${s.title} • ${program.token}'),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: const Text('Close'),
            ),
          ],
        );
      },
    );
  }

  Future<void> _showPulseCode(
      RapidScenario s, RapidActionProgram program) async {
    if (!mounted) {
      return;
    }
    await showModalBottomSheet<void>(
      context: context,
      builder: (ctx) {
        return Padding(
          padding: const EdgeInsets.fromLTRB(16, 14, 16, 20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Pulse Code',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
              const SizedBox(height: 8),
              SelectableText(
                '${program.token}-${program.pulse.toString().padLeft(2, '0')}-${s.actionType.name.toUpperCase()}',
                style: TextStyle(
                  color: s.color,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 8),
              Text('Use this key for ${s.actionLabel}.'),
            ],
          ),
        );
      },
    );
  }

  Future<void> _showBottomSheet(String title, String subtitle) async {
    if (!mounted) {
      return;
    }
    await showModalBottomSheet<void>(
      context: context,
      builder: (ctx) {
        return Padding(
          padding: const EdgeInsets.fromLTRB(16, 14, 16, 20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title,
                  style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w800,
                      color: Color(0xFFEAF4FF))),
              const SizedBox(height: 6),
              Text(subtitle,
                  style:
                      const TextStyle(color: Color(0xFFB8D5EE), height: 1.3)),
              const SizedBox(height: 10),
              LinearProgressIndicator(
                  value: 0.62 + (widget.scenario.id % 20) * 0.015),
            ],
          ),
        );
      },
    );
  }

  void _toast(String text) {
    if (!mounted) {
      return;
    }
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
          content: Text(text), duration: const Duration(milliseconds: 1200)),
    );
  }

  Widget _buildVariantContent(RapidScenario s, RapidActionProgram program) {
    final variant = (s.id - 1) % 8;
    final t = _themeForScenarioId(s.id);
    final chips = [
      'L${program.lane}',
      'T${program.level}',
      'P${program.pulse}',
    ];
    if (variant == 0) {
      return Row(
        children: [
          Container(
            width: 52,
            height: 52,
            decoration: BoxDecoration(
              color: Color.alphaBlend(s.color.withValues(alpha: 0.18), t.chipA),
              borderRadius: BorderRadius.circular(14),
            ),
            child: Icon(s.icon, color: t.edge),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Wrap(
              spacing: 6,
              runSpacing: 6,
              children: chips
                  .map((e) => Chip(
                        label: Text(e),
                        backgroundColor: Color.alphaBlend(
                            s.color.withValues(alpha: 0.14), t.chipA),
                        side: BorderSide(
                            color: t.edge.withValues(alpha: 0.38), width: 0.8),
                      ))
                  .toList(),
            ),
          ),
        ],
      );
    }
    if (variant == 1) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(program.objective,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(color: Color(0xFFCAE2F6), fontSize: 11)),
          const SizedBox(height: 6),
          LinearProgressIndicator(
            value: ((program.pulse % 90) + 10) / 100,
            minHeight: 6,
            borderRadius: BorderRadius.circular(999),
            color: t.edge,
            backgroundColor: t.shellA.withValues(alpha: 0.7),
          ),
        ],
      );
    }
    if (variant == 2) {
      return Row(
        children: List<Widget>.generate(3, (i) {
          final v = ((program.pulse + i * 9) % 100).toString().padLeft(2, '0');
          return Expanded(
            child: Container(
              margin: EdgeInsets.only(right: i == 2 ? 0 : 8),
              padding: const EdgeInsets.symmetric(vertical: 8),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(10),
                color: t.shellA.withValues(alpha: 0.72),
                border: Border.all(color: t.edge.withValues(alpha: 0.34)),
              ),
              child: Column(
                children: [
                  Text('N${i + 1}',
                      style: TextStyle(color: t.chipB, fontSize: 10)),
                  const SizedBox(height: 2),
                  Text(v,
                      style: const TextStyle(
                          color: Color(0xFFEAF4FF),
                          fontWeight: FontWeight.w700)),
                ],
              ),
            ),
          );
        }),
      );
    }
    if (variant == 3) {
      return Stack(
        children: [
          Positioned(
            right: 0,
            top: -10,
            child: Text(
              s.id.toString().padLeft(3, '0'),
              style: TextStyle(
                color: t.edge.withValues(alpha: 0.16),
                fontSize: 40,
                fontWeight: FontWeight.w900,
              ),
            ),
          ),
          Text(
            '${program.token} • ${program.objective}',
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(color: Color(0xFFD6ECFF), fontSize: 11),
          ),
        ],
      );
    }
    if (variant == 4) {
      return Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: List<Widget>.generate(8, (i) {
          final h = 8 + (((program.pulse + i * 7) % 18) * 2.0);
          return Expanded(
            child: Container(
              height: h,
              margin: EdgeInsets.only(right: i == 7 ? 0 : 3),
              decoration: BoxDecoration(
                color: t.edge.withValues(alpha: 0.2 + (i * 0.05)),
                borderRadius: BorderRadius.circular(3),
              ),
            ),
          );
        }),
      );
    }
    if (variant == 5) {
      return Wrap(
        spacing: 8,
        runSpacing: 8,
        children: List<Widget>.generate(4, (i) {
          final active = i <= (program.level % 4);
          return Container(
            width: 32,
            height: 32,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: active ? s.color.withValues(alpha: 0.26) : s.accent,
              border: Border.all(color: t.edge.withValues(alpha: 0.5)),
            ),
            child: Center(
              child: Text(
                '${i + 1}',
                style: TextStyle(
                  color: active ? t.chipB : const Color(0xFF8FA8C2),
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          );
        }),
      );
    }
    if (variant == 6) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: [
              _rapidDomains[(s.id * 3) % _rapidDomains.length],
              _rapidModes[(s.id * 7) % _rapidModes.length],
              'Tier-${program.level}',
            ]
                .map((e) => Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(999),
                        color: t.shellA.withValues(alpha: 0.62),
                      ),
                      child: Text(e,
                          style: TextStyle(
                            color: t.chipB.withValues(alpha: 0.96),
                            fontSize: 11,
                          )),
                    ))
                .toList(),
          ),
        ],
      );
    }
    return Row(
      children: [
        Expanded(
          child: Text(
            program.token,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              color: t.chipB.withValues(alpha: 0.95),
              fontWeight: FontWeight.w700,
              fontSize: 11,
            ),
          ),
        ),
        const SizedBox(width: 8),
        Icon(Icons.bolt, color: t.edge, size: 18),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    final s = widget.scenario;
    final program = _programForScenario(s);
    final variant = (s.id - 1) % 8;
    final t = _themeForScenarioId(s.id);
    final family = _themeBucketForScenarioId(s.id);
    final radius = 12.0 + (variant % 4) * 2.0 + family * 1.2;
    final borderRadius = [
      BorderRadius.circular(radius),
      BorderRadius.only(
        topLeft: Radius.circular(radius + 7),
        topRight: Radius.circular(radius - 2),
        bottomLeft: Radius.circular(radius - 4),
        bottomRight: Radius.circular(radius + 10),
      ),
      BorderRadius.horizontal(
        left: Radius.circular(radius + 12),
        right: Radius.circular(radius - 2),
      ),
      BorderRadius.only(
        topLeft: Radius.circular(radius + 2),
        topRight: Radius.circular(radius + 10),
        bottomLeft: Radius.circular(radius + 10),
        bottomRight: Radius.circular(radius + 2),
      ),
    ][family];
    final begin = [
      Alignment.topLeft,
      Alignment.topCenter,
      Alignment.centerLeft,
      Alignment.bottomLeft,
    ][variant % 4];
    final end = [
      Alignment.bottomRight,
      Alignment.bottomCenter,
      Alignment.centerRight,
      Alignment.topRight,
    ][variant % 4];
    return TweenAnimationBuilder<double>(
      tween: Tween<double>(begin: 0.86, end: 1),
      duration: Duration(milliseconds: 260 + (s.id % 10) * 16),
      curve: Curves.easeOutBack,
      builder: (context, value, child) {
        return Opacity(
          opacity: value.clamp(0, 1),
          child: Transform.scale(scale: value, child: child),
        );
      },
      child: AnimatedBuilder(
        animation: _controller,
        builder: (context, child) {
          final phase = (_controller.value * math.pi * 2) + (s.id * 0.27);
          var x = 0.0;
          var y = 0.0;
          var rotate = 0.0;
          var scale = 1.0;

          if (family == 0) {
            x = math.sin(phase * 0.7) * 2.2;
            y = math.cos(phase) * 2.6;
            rotate = math.sin(phase * 0.45) * 0.005;
          } else if (family == 1) {
            y = math.sin(phase * 1.15) * 1.6;
            rotate = math.sin(phase * 0.9) * 0.007;
            scale = 1.0 + (math.sin(phase * 1.9).abs() * 0.024);
          } else if (family == 2) {
            x = math.sin(phase * 1.1) * 1.4;
            y = math.sin(phase * 0.82) * 2.1;
            rotate = math.sin(phase * 1.35) * 0.016;
          } else {
            x = math.cos(phase * 1.2) * 3.0;
            y = math.sin(phase * 1.2) * 2.2;
            rotate = math.sin(phase * 1.2) * 0.012;
            scale = 1.0 + (math.sin(phase * 1.2) * 0.012);
          }

          final glowBeat =
              (math.sin(phase * (family == 1 ? 2.0 : 1.25)).abs() * 0.12);
          return Transform.translate(
            offset: Offset(x, y),
            child: Transform.rotate(
              angle: rotate,
              alignment: Alignment.center,
              child: Transform.scale(
                scale: scale,
                child: Material(
                  color: Colors.transparent,
                  child: InkWell(
                    borderRadius: borderRadius,
                    onTap: _runAction,
                    onLongPress: () {
                      _showPulseCode(s, program);
                    },
                    child: DecoratedBox(
                      decoration: BoxDecoration(
                        borderRadius: borderRadius,
                        gradient: LinearGradient(
                          begin: begin,
                          end: end,
                          colors: [
                            Color.alphaBlend(
                                s.color
                                    .withValues(alpha: 0.14 + (variant * 0.02)),
                                t.shellA),
                            Color.alphaBlend(t.shellB.withValues(alpha: 0.96),
                                const Color(0xFF0B1322)),
                          ],
                        ),
                        border: Border.all(
                            color: Color.alphaBlend(
                                s.color.withValues(alpha: 0.3),
                                t.edge.withValues(alpha: 0.6))),
                        boxShadow: [
                          BoxShadow(
                            color: t.glow.withValues(
                                alpha: 0.16 + glowBeat + (family * 0.015)),
                            blurRadius: 13.0 + (variant % 3) * 4.0 + family,
                            spreadRadius:
                                0.2 + (variant % 2) * 0.2 + family * 0.08,
                            offset:
                                Offset(0, 4 + (variant % 3) * 2 + family * 0.5),
                          ),
                        ],
                      ),
                      child: Padding(
                        padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Icon(s.icon, color: s.color),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: Text(
                                    s.title,
                                    style: const TextStyle(
                                      color: Color(0xFFEAF5FF),
                                      fontWeight: FontWeight.w800,
                                      fontSize: 14,
                                    ),
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                ),
                                Container(
                                  padding: const EdgeInsets.symmetric(
                                      horizontal: 8, vertical: 4),
                                  decoration: BoxDecoration(
                                    color: t.chipA.withValues(alpha: 0.8),
                                    borderRadius: BorderRadius.circular(999),
                                  ),
                                  child: Text(
                                    '${_themeTagForScenarioId(s.id)} ${s.id.toString().padLeft(3, '0')}',
                                    style: TextStyle(
                                      color: t.chipB,
                                      fontWeight: FontWeight.w700,
                                      fontSize: 11,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 8),
                            Text(
                              s.subtitle,
                              style: const TextStyle(
                                color: Color(0xFFB9D9EE),
                                fontSize: 12,
                              ),
                            ),
                            const SizedBox(height: 10),
                            _buildVariantContent(s, program),
                            const SizedBox(height: 10),
                            SizedBox(
                              height: 36,
                              child: FilledButton.tonal(
                                onPressed: _runAction,
                                style: FilledButton.styleFrom(
                                  backgroundColor: Color.alphaBlend(
                                      s.color.withValues(alpha: 0.08),
                                      t.actionA.withValues(alpha: 0.95)),
                                  foregroundColor: t.edge,
                                ),
                                child: Text(
                                  s.actionLabel,
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}

class RapidActionConsolePage extends StatelessWidget {
  final RapidScenario scenario;
  final RapidActionProgram program;

  const RapidActionConsolePage({
    super.key,
    required this.scenario,
    required this.program,
  });

  @override
  Widget build(BuildContext context) {
    final lines = List<String>.generate(6, (i) {
      final code = (program.pulse + (i + 1) * program.level) % 100;
      return 'Node ${i + 1}: lane ${program.lane} | level ${program.level} | code $code';
    });
    return Scaffold(
      appBar: AppBar(
          title: Text('Console ${scenario.id.toString().padLeft(3, '0')}')),
      body: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              scenario.title,
              style: const TextStyle(
                fontWeight: FontWeight.w800,
                fontSize: 18,
                color: Color(0xFFEAF5FF),
              ),
            ),
            const SizedBox(height: 8),
            Text(program.objective,
                style: const TextStyle(color: Color(0xFFBAD8EE))),
            const SizedBox(height: 10),
            Expanded(
              child: ListView.builder(
                itemCount: lines.length,
                itemBuilder: (context, index) {
                  return TweenAnimationBuilder<double>(
                    tween: Tween<double>(begin: 0, end: 1),
                    duration: Duration(milliseconds: 220 + index * 120),
                    curve: Curves.easeOutCubic,
                    builder: (context, value, child) {
                      return Opacity(
                        opacity: value,
                        child: Transform.translate(
                          offset: Offset((1 - value) * 22, 0),
                          child: Card(
                            color: const Color(0xFF12253D),
                            child: ListTile(
                              leading:
                                  Icon(scenario.icon, color: scenario.color),
                              title: Text(
                                lines[index],
                                style:
                                    const TextStyle(color: Color(0xFFEAF4FF)),
                              ),
                            ),
                          ),
                        ),
                      );
                    },
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}

final List<Widget Function()> rapidDeckBuilders =
    List<Widget Function()>.generate(
  rapidScenarios.length,
  (index) {
    final scenario = rapidScenarios[index];
    return () => RapidScenarioTile(scenario: scenario);
  },
);
