import 'dart:convert';
import 'dart:async';
import 'dart:io';

import 'package:camera/camera.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';
import 'package:geolocator/geolocator.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:webview_flutter/webview_flutter.dart';

const Color _kBg = Color(0xFF1A1A2E);
const Color _kPanel = Color(0xFF11182A);
const Color _kAccent = Color(0xFFE94560);
const Color _kTextMuted = Color(0xFFAAB2D6);
const Duration _kNetworkTimeout = Duration(seconds: 12);
const Duration _kAuthTimeout = Duration(seconds: 24);

int _parseVersionNumber(String value) {
  final match =
      RegExp(r'^(\d+)\.(\d+)\.(\d+)(?:\+(\d+))?$').firstMatch(value.trim());
  if (match == null) {
    return 0;
  }
  final major = int.tryParse(match.group(1) ?? '0') ?? 0;
  final minor = int.tryParse(match.group(2) ?? '0') ?? 0;
  final patch = int.tryParse(match.group(3) ?? '0') ?? 0;
  final build = int.tryParse(match.group(4) ?? '0') ?? 0;
  return (major * 1000000000) + (minor * 1000000) + (patch * 1000) + build;
}

void main() {
  runApp(const FaceStudioMobileClientApp());
}

class FaceStudioMobileClientApp extends StatelessWidget {
  const FaceStudioMobileClientApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'Face Studio Mobile Client',
      theme: ThemeData(
        useMaterial3: true,
        brightness: Brightness.dark,
        visualDensity: VisualDensity.adaptivePlatformDensity,
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF0EA5A4),
          brightness: Brightness.dark,
        ).copyWith(
          primary: _kAccent,
          onPrimary: const Color(0xFF07121F),
          secondary: const Color(0xFFFF8E3C),
          onSecondary: const Color(0xFF1F1300),
          tertiary: const Color(0xFFB7F171),
          surface: const Color(0xFF131B2D),
          onSurface: Colors.white,
          error: const Color(0xFFFF6B6B),
        ),
        fontFamily: 'Trebuchet MS',
        scaffoldBackgroundColor: _kBg,
        textTheme: ThemeData.dark().textTheme.apply(
              bodyColor: Colors.white,
              displayColor: Colors.white,
            ),
        primaryTextTheme: ThemeData.dark().primaryTextTheme.apply(
              bodyColor: Colors.white,
              displayColor: Colors.white,
            ),
        iconTheme: const IconThemeData(color: Colors.white),
        listTileTheme: const ListTileThemeData(
          textColor: Colors.white,
          iconColor: Colors.white,
        ),
        appBarTheme: const AppBarTheme(
          backgroundColor: _kPanel,
          foregroundColor: Colors.white,
          centerTitle: true,
          elevation: 0,
          titleTextStyle: TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.w800,
            letterSpacing: 0.2,
            color: Colors.white,
          ),
        ),
        cardTheme: CardThemeData(
          color: const Color(0xFF1B2740),
          elevation: 3,
          margin: const EdgeInsets.symmetric(vertical: 5),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
            side: const BorderSide(color: Color(0xFF30466F), width: 1),
          ),
        ),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: const Color(0xFF192740),
          contentPadding:
              const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(14),
            borderSide: const BorderSide(color: Color(0xFF3F5A84), width: 1),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(14),
            borderSide: const BorderSide(color: Color(0xFF22D3EE), width: 1.6),
          ),
          errorBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(14),
            borderSide: const BorderSide(color: Color(0xFFFF6B6B), width: 1.2),
          ),
          labelStyle: const TextStyle(color: _kTextMuted),
          hintStyle: const TextStyle(color: Color(0xFFB6C4E3)),
          prefixIconColor: const Color(0xFFD8E5FF),
          suffixIconColor: const Color(0xFFD8E5FF),
        ),
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            foregroundColor: Colors.white,
            backgroundColor: const Color(0xFF0EA5A4),
            minimumSize: const Size(0, 44),
            textStyle: const TextStyle(fontWeight: FontWeight.w700),
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
            ),
          ),
        ),
        filledButtonTheme: FilledButtonThemeData(
          style: FilledButton.styleFrom(
            backgroundColor: _kAccent,
            foregroundColor: const Color(0xFF07121F),
            minimumSize: const Size(0, 44),
            textStyle: const TextStyle(fontWeight: FontWeight.w800),
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            shape:
                RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          ),
        ),
        outlinedButtonTheme: OutlinedButtonThemeData(
          style: OutlinedButton.styleFrom(
            foregroundColor: const Color(0xFFCBE9FF),
            minimumSize: const Size(0, 42),
            side: const BorderSide(color: Color(0xFF4C6FA0), width: 1.2),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
            ),
          ),
        ),
        textButtonTheme: TextButtonThemeData(
          style: TextButton.styleFrom(
            foregroundColor: const Color(0xFF9DE7F7),
            textStyle: const TextStyle(fontWeight: FontWeight.w700),
          ),
        ),
        iconButtonTheme: IconButtonThemeData(
          style: IconButton.styleFrom(
            foregroundColor: const Color(0xFFE8F4FF),
            backgroundColor: const Color(0x1F4B6CA1),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(10),
            ),
          ),
        ),
        chipTheme: ChipThemeData(
          backgroundColor: const Color(0xFF1A2942),
          disabledColor: const Color(0xFF1A2942),
          selectedColor: const Color(0xFF22D3EE),
          secondarySelectedColor: const Color(0xFF22D3EE),
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
          labelStyle: const TextStyle(color: Colors.white),
          secondaryLabelStyle: const TextStyle(color: Color(0xFF07121F)),
          brightness: Brightness.dark,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(10),
            side: const BorderSide(color: Color(0xFF365782)),
          ),
        ),
        snackBarTheme: SnackBarThemeData(
          backgroundColor: const Color(0xFF203154),
          contentTextStyle: const TextStyle(color: Colors.white),
          behavior: SnackBarBehavior.floating,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
        dialogTheme: const DialogThemeData(
          backgroundColor: Color(0xFF17253D),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.all(Radius.circular(16)),
          ),
          titleTextStyle: TextStyle(
            color: Colors.white,
            fontWeight: FontWeight.w800,
            fontSize: 18,
          ),
          contentTextStyle: TextStyle(color: Color(0xFFD9E7FF)),
        ),
        bottomSheetTheme: const BottomSheetThemeData(
          backgroundColor: Color(0xFF17253D),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.vertical(top: Radius.circular(18)),
          ),
        ),
        progressIndicatorTheme: const ProgressIndicatorThemeData(
          color: Color(0xFF22D3EE),
          linearTrackColor: Color(0xFF2E4365),
          circularTrackColor: Color(0xFF2E4365),
        ),
        switchTheme: SwitchThemeData(
          thumbColor: WidgetStateProperty.resolveWith((states) {
            if (states.contains(WidgetState.selected)) {
              return const Color(0xFF22D3EE);
            }
            return const Color(0xFF8CA8D0);
          }),
          trackColor: WidgetStateProperty.resolveWith((states) {
            if (states.contains(WidgetState.selected)) {
              return const Color(0xFF2C7E9F);
            }
            return const Color(0xFF3B5074);
          }),
        ),
        checkboxTheme: CheckboxThemeData(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(5)),
          fillColor: WidgetStateProperty.resolveWith((states) {
            if (states.contains(WidgetState.selected)) {
              return const Color(0xFF22D3EE);
            }
            return const Color(0xFF3D5278);
          }),
          checkColor: WidgetStateProperty.all(const Color(0xFF04111B)),
        ),
        navigationBarTheme: NavigationBarThemeData(
          backgroundColor: const Color(0xFF111A2D),
          indicatorColor: const Color(0xFF265D89),
          labelTextStyle: WidgetStateProperty.all(
            const TextStyle(fontSize: 12, fontWeight: FontWeight.w700),
          ),
        ),
        floatingActionButtonTheme: const FloatingActionButtonThemeData(
          backgroundColor: Color(0xFF22D3EE),
          foregroundColor: Color(0xFF07121F),
        ),
      ),
      home: const AuthGate(),
    );
  }
}

class _AnimatedFadeSlide extends StatefulWidget {
  final Widget child;
  final int delayMs;
  final Offset beginOffset;

  const _AnimatedFadeSlide({
    required this.child,
    this.delayMs = 0,
    this.beginOffset = const Offset(0, 0.05),
  });

  @override
  State<_AnimatedFadeSlide> createState() => _AnimatedFadeSlideState();
}

class _AnimatedFadeSlideState extends State<_AnimatedFadeSlide> {
  bool _visible = false;

  @override
  void initState() {
    super.initState();
    Future.delayed(Duration(milliseconds: widget.delayMs), () {
      if (mounted) {
        setState(() => _visible = true);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedOpacity(
      opacity: _visible ? 1 : 0,
      duration: const Duration(milliseconds: 420),
      curve: Curves.easeOutCubic,
      child: AnimatedSlide(
        offset: _visible ? Offset.zero : widget.beginOffset,
        duration: const Duration(milliseconds: 420),
        curve: Curves.easeOutCubic,
        child: widget.child,
      ),
    );
  }
}

class _SectionBadge extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color tint;

  const _SectionBadge({
    required this.icon,
    required this.label,
    required this.tint,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: tint.withValues(alpha: 0.18),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: tint.withValues(alpha: 0.45)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: tint),
          const SizedBox(width: 6),
          Text(
            label,
            style: TextStyle(color: tint, fontWeight: FontWeight.w700),
          ),
        ],
      ),
    );
  }
}

class _KpiTile extends StatelessWidget {
  final String title;
  final String value;
  final Color tint;
  final IconData icon;

  const _KpiTile({
    required this.title,
    required this.value,
    required this.tint,
    required this.icon,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 160,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(14),
        color: const Color(0xFF16233A),
        border: Border.all(color: tint.withValues(alpha: 0.5)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 14, color: tint),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  title,
                  style: const TextStyle(
                    color: Color(0xFFAEC4E6),
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            value,
            style: const TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.w900,
              fontSize: 20,
            ),
          ),
        ],
      ),
    );
  }
}

class _ProfileFieldTile extends StatelessWidget {
  final String label;
  final String value;
  final IconData icon;

  const _ProfileFieldTile({
    required this.label,
    required this.value,
    required this.icon,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: const Color(0xFF182742),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFF34517B)),
      ),
      child: Row(
        children: [
          Icon(icon, size: 18, color: const Color(0xFF9DCCFF)),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  style:
                      const TextStyle(color: Color(0xFF9FB5D8), fontSize: 12),
                ),
                const SizedBox(height: 2),
                Text(
                  value,
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _TimelineActivityTile extends StatelessWidget {
  final String title;
  final String subtitle;
  final String trailing;

  const _TimelineActivityTile({
    required this.title,
    required this.subtitle,
    required this.trailing,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: const Color(0xFF14233A),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFF304D73)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 10,
            height: 10,
            margin: const EdgeInsets.only(top: 6),
            decoration: const BoxDecoration(
              shape: BoxShape.circle,
              color: Color(0xFF70D6FF),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                      color: Colors.white, fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 3),
                Text(
                  subtitle,
                  style:
                      const TextStyle(color: Color(0xFFC7D9F5), fontSize: 12),
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          Text(
            trailing,
            style: const TextStyle(color: Color(0xFF9BB2D6), fontSize: 11),
          ),
        ],
      ),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  final String title;

  const _SectionTitle(this.title);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 6, bottom: 6),
      child: Text(
        title,
        style: const TextStyle(
          color: Color(0xFFDDE6FF),
          fontWeight: FontWeight.w700,
          fontSize: 14,
        ),
      ),
    );
  }
}

class _MenuItem {
  final String title;
  final String subtitle;
  final int colorValue;
  final IconData icon;
  final Widget page;

  const _MenuItem({
    required this.title,
    required this.subtitle,
    required this.colorValue,
    required this.icon,
    required this.page,
  });
}

class _KnownMapLocation {
  final String name;
  final double latitude;
  final double longitude;

  const _KnownMapLocation({
    required this.name,
    required this.latitude,
    required this.longitude,
  });
}

class BackendApi {
  String _baseUrl;
  final String apiKey;
  String _token = '';
  String _username = '';
  String _role = 'user';

  BackendApi({required String baseUrl, required this.apiKey})
      : _baseUrl = baseUrl;

  String get _base => _baseUrl.trim().replaceAll(RegExp(r'/$'), '');
  String get baseUrl => _base;
  String get token => _token;
  String get username => _username;
  String get role => _role;

  void setBaseUrl(String url) {
    final raw = url.trim();
    if (raw.isEmpty) return;
    final normalized = raw.startsWith('http://') || raw.startsWith('https://')
        ? raw
        : 'http://$raw';
    _baseUrl = normalized;
  }

  List<String> _candidateBases() {
    final active = _base;
    final isPublicHttps = active.startsWith('https://') &&
        !active.contains('localhost') &&
        !active.contains('127.0.0.1') &&
        !active.contains('10.0.2.2') &&
        !active.contains('10.0.3.2');
    if (isPublicHttps) {
      final cloudFirst = <String>[
        active,
        'https://facerecognition-4.onrender.com',
        'https://face-studio-api.onrender.com',
      ];
      final seen = <String>{};
      return cloudFirst.where((u) => u.isNotEmpty && seen.add(u)).toList();
    }

    final ordered = <String>[
      active,
      const String.fromEnvironment(
        'FACE_STUDIO_BASE_URL',
        defaultValue: 'https://facerecognition-4.onrender.com',
      ).trim().replaceAll(RegExp(r'/$'), ''),
      'https://facerecognition-4.onrender.com',
      'https://face-studio-api.onrender.com',
      'http://10.0.2.2:8787',
      'http://10.0.3.2:8787',
      'http://127.0.0.1:8787',
      'http://localhost:8787',
    ];
    if (!kIsWeb && !Platform.isAndroid) {
      ordered.add('http://127.0.0.1:8787');
    }
    final seen = <String>{};
    return ordered.where((u) => u.isNotEmpty && seen.add(u)).toList();
  }

  void setSession(
      {required String token, required String username, required String role}) {
    _token = token;
    _username = username;
    _role = role;
  }

  void clearSession() {
    _token = '';
    _username = '';
    _role = 'user';
  }

  Future<Map<String, dynamic>> login({
    required String identifier,
    required String password,
  }) async {
    String lastReason = 'backend_unreachable';
    for (final base in _candidateBases()) {
      try {
        final health = await http
            .get(Uri.parse('$base/api/health'))
            .timeout(_kAuthTimeout);
        if (health.statusCode != 200) {
          lastReason = 'backend_http_${health.statusCode}';
          continue;
        }

        Future<http.Response> sendLogin() {
          return http
              .post(
                Uri.parse('$base/api/auth/login'),
                headers: {'Content-Type': 'application/json'},
                body: jsonEncode({
                  'identifier': identifier,
                  'password': password,
                  'ttl': 180
                }),
              )
              .timeout(_kAuthTimeout);
        }

        http.Response res;
        try {
          res = await sendLogin();
        } on TimeoutException {
          res = await sendLogin();
        }

        if (res.statusCode == 401 || res.statusCode == 403) {
          return {'ok': false, 'reason': 'invalid_credentials'};
        }
        if (res.statusCode != 200) {
          lastReason = 'backend_http_${res.statusCode}';
          continue;
        }
        final body = jsonDecode(res.body) as Map<String, dynamic>;
        final data = (body['data'] as Map<String, dynamic>?) ?? {};
        final user = (data['user'] as Map<String, dynamic>?) ?? {};
        final token = (data['token'] ?? '').toString();
        final username = (user['username'] ?? '').toString();
        final role = (user['role'] ?? 'user').toString().toLowerCase();
        if (token.isEmpty || username.isEmpty) {
          lastReason = 'invalid_payload';
          continue;
        }
        _baseUrl = base;
        setSession(token: token, username: username, role: role);
        return {'ok': true, 'user': user};
      } on TimeoutException {
        lastReason = 'timeout';
        continue;
      } catch (_) {
        lastReason = 'network_error';
        continue;
      }
    }
    return {'ok': false, 'reason': lastReason};
  }

  Future<Map<String, dynamic>> requestSignupVerification({
    required String username,
    required String email,
    required String phone,
    required String password,
  }) async {
    final res = await http
        .post(
          Uri.parse('$_base/api/auth/signup/request'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({
            'username': username,
            'email': email,
            'phone': phone,
            'password': password,
          }),
        )
        .timeout(_kNetworkTimeout);
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>?> verifySignupCode({
    required String email,
    required String code,
  }) async {
    final res = await http
        .post(
          Uri.parse('$_base/api/auth/signup/verify'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({'email': email, 'code': code, 'ttl': 180}),
        )
        .timeout(_kNetworkTimeout);
    if (res.statusCode != 200) {
      return null;
    }
    final body = jsonDecode(res.body) as Map<String, dynamic>;
    final data = (body['data'] as Map<String, dynamic>?) ?? {};
    final user = (data['user'] as Map<String, dynamic>?) ?? {};
    final token = (data['token'] ?? '').toString();
    final uname = (user['username'] ?? '').toString();
    final role = (user['role'] ?? 'user').toString().toLowerCase();
    if (token.isEmpty || uname.isEmpty) {
      return null;
    }
    setSession(token: token, username: uname, role: role);
    return user;
  }

  Future<Map<String, dynamic>> requestPasswordReset(
      {required String identifier}) async {
    final res = await http
        .post(
          Uri.parse('$_base/api/auth/password/request'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({'identifier': identifier}),
        )
        .timeout(_kNetworkTimeout);
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> resetPassword({
    required String username,
    required String code,
    required String newPassword,
  }) async {
    final res = await http
        .post(
          Uri.parse('$_base/api/auth/password/reset'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({
            'username': username,
            'code': code,
            'new_password': newPassword,
          }),
        )
        .timeout(_kNetworkTimeout);
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  Future<bool> ensureToken() async {
    if (_token.isNotEmpty) return true;
    if (apiKey.isEmpty) return false;
    for (final base in _candidateBases()) {
      try {
        final res = await http.get(
          Uri.parse('$base/api/auth/token?subject=android_mobile&ttl=120'),
          headers: {'X-API-Key': apiKey},
        ).timeout(_kNetworkTimeout);
        if (res.statusCode != 200) {
          continue;
        }
        final body = jsonDecode(res.body) as Map<String, dynamic>;
        final token = (body['data']?['token'] ?? '').toString();
        if (token.isEmpty) {
          continue;
        }
        _baseUrl = base;
        _token = token;
        return true;
      } catch (_) {
        continue;
      }
    }
    return false;
  }

  Future<Map<String, dynamic>> getCurrentUser() async {
    try {
      final ok = await ensureToken();
      if (!ok) return {'ok': false, 'error': 'Token issue failed'};
      final res = await http.get(
        Uri.parse('$_base/api/users/me'),
        headers: {'Authorization': 'Bearer $_token'},
      ).timeout(_kNetworkTimeout);
      return jsonDecode(res.body) as Map<String, dynamic>;
    } catch (e) {
      return {'ok': false, 'error': 'Backend unavailable: $e'};
    }
  }

  Future<Map<String, dynamic>> getHealth() async {
    for (final base in _candidateBases()) {
      try {
        final ready = await http
            .get(Uri.parse('$base/api/health'))
            .timeout(_kNetworkTimeout);
        if (ready.statusCode != 200) {
          continue;
        }
        _baseUrl = base;
        return jsonDecode(ready.body) as Map<String, dynamic>;
      } catch (_) {
        continue;
      }
    }
    return {'ok': false, 'error': 'Backend unavailable'};
  }

  Future<Map<String, dynamic>> getStats() async {
    final ok = await ensureToken();
    if (!ok) {
      return {
        'ok': false,
        'error': 'Server is not available try after some time'
      };
    }
    final res = await http.get(
      Uri.parse('$_base/api/stats'),
      headers: {'Authorization': 'Bearer $_token'},
    );
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getUsers({int limit = 200}) async {
    final ok = await ensureToken();
    if (!ok) {
      return {
        'ok': false,
        'error': 'Server is not available try after some time'
      };
    }
    final res = await http.get(
      Uri.parse('$_base/api/users?limit=$limit'),
      headers: {'Authorization': 'Bearer $_token'},
    );
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getActivity({int limit = 200}) async {
    final ok = await ensureToken();
    if (!ok) {
      return {
        'ok': false,
        'error': 'Server is not available try after some time'
      };
    }
    final res = await http.get(
      Uri.parse('$_base/api/activity?limit=$limit'),
      headers: {'Authorization': 'Bearer $_token'},
    );
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getDocs() async {
    final res = await http.get(Uri.parse('$_base/api/docs'));
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getDbOverview() async {
    final ok = await ensureToken();
    if (!ok) return {'ok': false, 'error': 'Token issue failed'};
    final res = await http.get(
      Uri.parse('$_base/api/db/overview'),
      headers: {'Authorization': 'Bearer $_token'},
    );
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getAdminModule(String modulePath) async {
    final ok = await ensureToken();
    if (!ok) return {'ok': false, 'error': 'Token issue failed'};
    final res = await http.get(
      Uri.parse('$_base/api/admin/$modulePath'),
      headers: {'Authorization': 'Bearer $_token'},
    );
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> postAdminAction(String actionPath,
      {Map<String, dynamic>? payload}) async {
    final ok = await ensureToken();
    if (!ok) return {'ok': false, 'error': 'Token issue failed'};
    final res = await http.post(
      Uri.parse('$_base$actionPath'),
      headers: {
        'Authorization': 'Bearer $_token',
        'Content-Type': 'application/json',
      },
      body: jsonEncode(payload ?? const {}),
    );
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> saveRecognitionLocation({
    required String recognizedName,
    required String locationName,
    double? latitude,
    double? longitude,
    double? confidence,
    String source = 'mobile_manual',
  }) async {
    final ok = await ensureToken();
    if (!ok) {
      return {
        'ok': false,
        'error': 'Server is not available try after some time'
      };
    }
    final res = await http.post(
      Uri.parse('$_base/api/mobile/recognition-location/save'),
      headers: {
        'Authorization': 'Bearer $_token',
        'Content-Type': 'application/json',
      },
      body: jsonEncode({
        'recognized_name': recognizedName,
        'location_name': locationName,
        'latitude': latitude,
        'longitude': longitude,
        'confidence': confidence,
        'source': source,
        'requested_by': _username.isEmpty ? 'mobile' : _username,
      }),
    );
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> searchRecognitionLocations({
    required String name,
    int limit = 100,
  }) async {
    final ok = await ensureToken();
    if (!ok) {
      return {
        'ok': false,
        'error': 'Server is not available try after some time'
      };
    }
    final person = Uri.encodeQueryComponent(name.trim());
    final res = await http.get(
      Uri.parse(
          '$_base/api/mobile/recognition-location/search?name=$person&limit=$limit'),
      headers: {'Authorization': 'Bearer $_token'},
    );
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getMobileAppUpdateInfo() async {
    for (final base in _candidateBases()) {
      try {
        final res = await http
            .get(Uri.parse('$base/api/mobile/app-update'))
            .timeout(_kNetworkTimeout);
        if (res.statusCode != 200) {
          continue;
        }
        _baseUrl = base;
        final body = jsonDecode(res.body) as Map<String, dynamic>;
        final data =
            (body['data'] as Map<String, dynamic>?) ?? <String, dynamic>{};
        return {'ok': true, 'data': data};
      } catch (_) {
        continue;
      }
    }
    return {'ok': false};
  }
}

BackendApi _createBackendApi() {
  const baseUrl = String.fromEnvironment(
    'FACE_STUDIO_BASE_URL',
    defaultValue: 'https://facerecognition-4.onrender.com',
  );
  const apiKey =
      String.fromEnvironment('FACE_STUDIO_API_KEY', defaultValue: '');
  return BackendApi(baseUrl: baseUrl, apiKey: apiKey);
}

final BackendApi _backendApi = _createBackendApi();

BackendApi buildBackendApi() {
  return _backendApi;
}

class AuthGate extends StatefulWidget {
  const AuthGate({super.key});

  @override
  State<AuthGate> createState() => _AuthGateState();
}

class _AuthGateState extends State<AuthGate> {
  bool _ready = false;
  String _username = '';
  bool _isAdmin = false;
  bool _updateDialogShown = false;

  @override
  void initState() {
    super.initState();
    _checkForAppUpdate();
    _loadSession();
  }

  Future<void> _checkForAppUpdate() async {
    final api = buildBackendApi();
    final info = await api.getMobileAppUpdateInfo();
    if (info['ok'] != true || !mounted || _updateDialogShown) {
      return;
    }

    final data = (info['data'] as Map<String, dynamic>?) ?? <String, dynamic>{};
    final latestVersion = (data['latest_version'] ?? '').toString().trim();
    final minimumVersion = (data['minimum_version'] ?? '').toString().trim();
    final updateUrl = (data['apk_url'] ?? '').toString().trim();
    final notes = (data['notes'] ?? '').toString().trim();
    final forceUpdate = data['force_update'] == true;
    if (latestVersion.isEmpty || updateUrl.isEmpty) {
      return;
    }

    final pkg = await PackageInfo.fromPlatform();
    final currentVersion = '${pkg.version}+${pkg.buildNumber}';
    final currentN = _parseVersionNumber(currentVersion);
    final latestN = _parseVersionNumber(latestVersion);
    final minimumN = _parseVersionNumber(minimumVersion);
    final isOutdated = latestN > 0 && latestN > currentN;
    final mustUpdate = minimumN > 0 && currentN < minimumN;
    if (!isOutdated && !mustUpdate) {
      return;
    }

    _updateDialogShown = true;
    final canSkip = !(forceUpdate || mustUpdate);
    final result = await showDialog<bool>(
      context: context,
      barrierDismissible: canSkip,
      builder: (ctx) {
        return AlertDialog(
          title: const Text('Update Available'),
          content: Text(
            notes.isEmpty
                ? 'A new app version is available. Please update to continue with latest improvements.'
                : notes,
          ),
          actions: [
            if (canSkip)
              TextButton(
                onPressed: () => Navigator.of(ctx).pop(false),
                child: const Text('Later'),
              ),
            ElevatedButton(
              onPressed: () => Navigator.of(ctx).pop(true),
              child: const Text('Update Now'),
            ),
          ],
        );
      },
    );

    if (result == true) {
      final uri = Uri.tryParse(updateUrl);
      if (uri != null) {
        await launchUrl(uri, mode: LaunchMode.externalApplication);
      }
    }
  }

  Future<void> _loadSession() async {
    try {
      final api = buildBackendApi();
      final prefs = await SharedPreferences.getInstance();
      final token = prefs.getString('fs_token') ?? '';
      final username = prefs.getString('fs_username') ?? '';
      final role = (prefs.getString('fs_role') ?? 'user').toLowerCase();

      if (token.isNotEmpty && username.isNotEmpty) {
        api.setSession(token: token, username: username, role: role);
        final me = await api.getCurrentUser().timeout(
              const Duration(seconds: 10),
              onTimeout: () => {'ok': false, 'error': 'session_check_timeout'},
            );
        if (me['ok'] == true) {
          final data = (me['data'] as Map<String, dynamic>?) ?? {};
          _username = (data['username'] ?? username).toString();
          _isAdmin =
              ((data['role'] ?? role).toString().toLowerCase() == 'admin');
          api.setSession(
            token: token,
            username: _username,
            role: _isAdmin ? 'admin' : 'user',
          );
        } else {
          final errorText = (me['error'] ?? '').toString().toLowerCase();
          final connectivityIssue = errorText.contains('unavailable') ||
              errorText.contains('failed to connect') ||
              errorText.contains('socket') ||
              errorText.contains('timeout');
          if (connectivityIssue) {
            _username = username;
            _isAdmin = role == 'admin';
          } else {
            await prefs.remove('fs_token');
            await prefs.remove('fs_username');
            await prefs.remove('fs_role');
            api.clearSession();
          }
        }
      }
    } catch (_) {
    } finally {
      if (!mounted) return;
      setState(() {
        _ready = true;
      });
    }
  }

  Future<void> _onLoggedIn(Map<String, dynamic> user) async {
    final api = buildBackendApi();
    final prefs = await SharedPreferences.getInstance();
    final username = (user['username'] ?? '').toString();
    final role = (user['role'] ?? 'user').toString().toLowerCase();
    await prefs.setString('fs_token', api.token);
    await prefs.setString('fs_username', username);
    await prefs.setString('fs_role', role);
    if (!mounted) return;
    setState(() {
      _username = username;
      _isAdmin = role == 'admin';
    });
  }

  Future<void> _onLogout() async {
    final api = buildBackendApi();
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('fs_token');
    await prefs.remove('fs_username');
    await prefs.remove('fs_role');
    api.clearSession();
    if (!mounted) return;
    setState(() {
      _username = '';
      _isAdmin = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    if (!_ready) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }
    if (_username.isEmpty) {
      return LoginPage(onLoggedIn: _onLoggedIn);
    }
    return MobileHomePage(
      username: _username,
      isAdmin: _isAdmin,
      onLogout: _onLogout,
    );
  }
}

class LoginPage extends StatefulWidget {
  final Future<void> Function(Map<String, dynamic>) onLoggedIn;

  const LoginPage({super.key, required this.onLoggedIn});

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  int _mode = 0;
  final _idController = TextEditingController();
  final _pwController = TextEditingController();
  final _signupUserController = TextEditingController();
  final _signupEmailController = TextEditingController();
  final _signupPhoneController = TextEditingController();
  final _signupPwController = TextEditingController();
  final _signupCodeController = TextEditingController();
  final _forgotIdController = TextEditingController();
  final _forgotUserController = TextEditingController();
  final _forgotCodeController = TextEditingController();
  final _forgotNewPwController = TextEditingController();
  bool _signupCodeSent = false;
  String _error = '';
  String _info = '';
  bool _busy = false;

  @override
  void initState() {
    super.initState();
  }

  @override
  void dispose() {
    _idController.dispose();
    _pwController.dispose();
    _signupUserController.dispose();
    _signupEmailController.dispose();
    _signupPhoneController.dispose();
    _signupPwController.dispose();
    _signupCodeController.dispose();
    _forgotIdController.dispose();
    _forgotUserController.dispose();
    _forgotCodeController.dispose();
    _forgotNewPwController.dispose();
    super.dispose();
  }

  Future<void> _login() async {
    final id = _idController.text.trim();
    final pw = _pwController.text;
    if (id.isEmpty || pw.isEmpty) {
      setState(() => _error = 'Please enter username/email and password');
      return;
    }
    setState(() {
      _busy = true;
      _error = '';
      _info = '';
    });
    final api = buildBackendApi();
    try {
      final result = await api.login(identifier: id, password: pw);
      if (!mounted) return;
      if (result['ok'] != true) {
        final reason = (result['reason'] ?? '').toString();
        setState(() {
          if (reason == 'invalid_credentials') {
            _error =
                'Invalid credentials. Please check username/email and password.';
            _info = '';
          } else if (reason == 'timeout') {
            _error = 'Backend is waking up. Please retry in 10-20 seconds.';
            _info = 'Server: ${api.baseUrl}';
          } else if (reason.startsWith('backend_http_')) {
            _error =
                'Backend returned an error (${reason.replaceFirst('backend_http_', '')}).';
            _info = 'Server: ${api.baseUrl}';
          } else {
            _error = 'Cannot reach backend right now.';
            _info = 'Check internet, then retry. Active server: ${api.baseUrl}';
          }
        });
        return;
      }
      final user =
          Map<String, dynamic>.from((result['user'] as Map?) ?? const {});
      if (user.isEmpty) {
        setState(() {
          _error = 'Login response was empty. Please try again.';
          _info = '';
        });
        return;
      }
      await widget.onLoggedIn(user);
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = 'Login failed: $e';
        _info = 'Server: ${api.baseUrl}';
      });
    } finally {
      if (mounted) {
        setState(() => _busy = false);
      }
    }
  }

  Future<void> _signup() async {
    final username = _signupUserController.text.trim();
    final email = _signupEmailController.text.trim();
    final phone = _signupPhoneController.text.trim();
    final password = _signupPwController.text;
    final code = _signupCodeController.text.trim();

    if (!_signupCodeSent) {
      if (email.isEmpty || !email.contains('@')) {
        setState(
            () => _error = 'Enter a valid email to receive verification code');
        return;
      }
      if (password.length < 4 || (username.isEmpty && email.isEmpty)) {
        setState(
            () => _error = 'Enter username/email and password (min 4 chars)');
        return;
      }
      setState(() {
        _busy = true;
        _error = '';
        _info = '';
      });
      final api = buildBackendApi();
      Map<String, dynamic> res;
      try {
        res = await api.requestSignupVerification(
          username: username,
          email: email,
          phone: phone,
          password: password,
        );
      } catch (e) {
        if (!mounted) return;
        setState(() {
          _busy = false;
          _error = 'Could not send verification code: $e';
        });
        return;
      }
      if (!mounted) return;
      if (res['ok'] != true) {
        setState(() {
          _busy = false;
          _error =
              (res['error'] ?? 'Could not send verification code').toString();
        });
        return;
      }
      final data = (res['data'] as Map<String, dynamic>?) ?? const {};
      final mailSent = data['mail_sent'] != false;
      final fallbackCode = (data['verification_code'] ?? '').toString().trim();
      final smtpError = (data['smtp_error'] ?? '').toString().trim();
      setState(() {
        _busy = false;
        _signupCodeSent = true;
        if (mailSent) {
          _info = 'Verification code sent to $email';
        } else if (fallbackCode.isNotEmpty) {
          if (smtpError.isNotEmpty) {
            _info = 'SMTP error: $smtpError. Backup code: $fallbackCode';
          } else {
            _info = 'SMTP unavailable. Use this code: $fallbackCode';
          }
        } else {
          _info = 'Verification code is ready. Please continue.';
        }
      });
      return;
    }

    if (code.isEmpty) {
      setState(() => _error = 'Enter the verification code from your email');
      return;
    }

    setState(() {
      _busy = true;
      _error = '';
      _info = '';
    });
    final api = buildBackendApi();
    try {
      final user = await api.verifySignupCode(email: email, code: code);
      if (!mounted) return;
      if (user == null) {
        setState(() {
          _error = 'Signup verification failed. Check code and try again.';
        });
        return;
      }
      await widget.onLoggedIn(user);
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = 'Signup failed: $e';
      });
    } finally {
      if (mounted) {
        setState(() => _busy = false);
      }
    }
  }

  Future<void> _requestResetCode() async {
    final identifier = _forgotIdController.text.trim();
    if (identifier.isEmpty) {
      setState(() => _error = 'Enter username or email first');
      return;
    }
    setState(() {
      _busy = true;
      _error = '';
      _info = '';
    });
    final api = buildBackendApi();
    try {
      final res = await api.requestPasswordReset(identifier: identifier);
      if (!mounted) return;
      if (res['ok'] != true) {
        setState(() {
          _error = (res['error'] ?? 'Reset request failed').toString();
        });
        return;
      }
      final data = (res['data'] as Map<String, dynamic>?) ?? {};
      final username = (data['username'] ?? '').toString();
      final code = (data['code'] ?? '').toString();
      final mailSent = data['mail_sent'] == true;
      final smtpError = (data['smtp_error'] ?? '').toString().trim();
      setState(() {
        _forgotUserController.text = username;
        if (mailSent) {
          _info = 'Reset code sent to your email.';
        } else if (code.isNotEmpty) {
          _info = smtpError.isNotEmpty
              ? 'SMTP error: $smtpError. Backup reset code: $code'
              : 'Reset code: $code';
        } else {
          _info = 'Reset request accepted. Check your email.';
        }
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = 'Reset request failed: $e';
      });
    } finally {
      if (mounted) {
        setState(() => _busy = false);
      }
    }
  }

  Future<void> _resetPassword() async {
    final username = _forgotUserController.text.trim();
    final code = _forgotCodeController.text.trim();
    final newPassword = _forgotNewPwController.text;
    if (username.isEmpty || code.isEmpty || newPassword.length < 4) {
      setState(() => _error = 'Enter username, reset code, and new password');
      return;
    }
    setState(() {
      _busy = true;
      _error = '';
      _info = '';
    });
    final api = buildBackendApi();
    try {
      final res = await api.resetPassword(
          username: username, code: code, newPassword: newPassword);
      if (!mounted) return;
      if (res['ok'] != true) {
        setState(() {
          _error = (res['error'] ?? 'Reset failed').toString();
        });
        return;
      }
      setState(() {
        _mode = 0;
        _info = 'Password reset successful. Please login.';
        _forgotCodeController.clear();
        _forgotNewPwController.clear();
        _pwController.clear();
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = 'Reset failed: $e';
      });
    } finally {
      if (mounted) {
        setState(() => _busy = false);
      }
    }
  }

  Widget _modeSelector() {
    return SegmentedButton<int>(
      segments: const [
        ButtonSegment<int>(value: 0, label: Text('Login')),
        ButtonSegment<int>(value: 1, label: Text('Sign Up')),
        ButtonSegment<int>(value: 2, label: Text('Forgot')),
      ],
      selected: {_mode},
      onSelectionChanged: (set) {
        setState(() {
          _mode = set.first;
          _error = '';
          _info = '';
          if (_mode != 1) {
            _signupCodeSent = false;
            _signupCodeController.clear();
          }
        });
      },
    );
  }

  Widget _loginForm() {
    return Column(
      children: [
        TextField(
          controller: _idController,
          decoration: const InputDecoration(
            labelText: 'Username or Email',
            prefixIcon: Icon(Icons.person),
          ),
        ),
        const SizedBox(height: 10),
        TextField(
          controller: _pwController,
          obscureText: true,
          decoration: const InputDecoration(
            labelText: 'Password',
            prefixIcon: Icon(Icons.lock),
          ),
          onSubmitted: (_) => _login(),
        ),
        const SizedBox(height: 14),
        FilledButton.icon(
          onPressed: _busy ? null : _login,
          icon: _busy
              ? const SizedBox(
                  height: 16,
                  width: 16,
                  child: CircularProgressIndicator(strokeWidth: 2))
              : const Icon(Icons.login),
          label: Text(_busy ? 'Loading...' : 'Login'),
        ),
      ],
    );
  }

  Widget _signupForm() {
    return Column(
      children: [
        TextField(
          controller: _signupUserController,
          decoration: const InputDecoration(
              labelText: 'Username', prefixIcon: Icon(Icons.account_circle)),
        ),
        const SizedBox(height: 10),
        TextField(
          controller: _signupEmailController,
          decoration: const InputDecoration(
              labelText: 'Email', prefixIcon: Icon(Icons.email)),
        ),
        const SizedBox(height: 10),
        TextField(
          controller: _signupPhoneController,
          decoration: const InputDecoration(
              labelText: 'Phone', prefixIcon: Icon(Icons.phone)),
        ),
        const SizedBox(height: 10),
        TextField(
          controller: _signupPwController,
          obscureText: true,
          decoration: const InputDecoration(
              labelText: 'Password', prefixIcon: Icon(Icons.lock_outline)),
        ),
        if (_signupCodeSent) ...[
          const SizedBox(height: 10),
          TextField(
            controller: _signupCodeController,
            decoration: const InputDecoration(
              labelText: 'Verification Code',
              prefixIcon: Icon(Icons.verified_user),
            ),
          ),
        ],
        const SizedBox(height: 14),
        FilledButton.icon(
          onPressed: _busy ? null : _signup,
          icon: _busy
              ? const SizedBox(
                  height: 16,
                  width: 16,
                  child: CircularProgressIndicator(strokeWidth: 2))
              : Icon(_signupCodeSent ? Icons.verified : Icons.mark_email_read),
          label: Text(_busy
              ? (_signupCodeSent ? 'Verifying...' : 'Sending Code...')
              : (_signupCodeSent
                  ? 'Verify & Create Account'
                  : 'Send Verification Code')),
        ),
        if (_signupCodeSent) ...[
          const SizedBox(height: 8),
          TextButton.icon(
            onPressed: _busy
                ? null
                : () {
                    setState(() {
                      _signupCodeSent = false;
                      _signupCodeController.clear();
                      _error = '';
                      _info = 'You can request a new verification code.';
                    });
                  },
            icon: const Icon(Icons.refresh),
            label: const Text('Resend Code'),
          ),
        ],
        const SizedBox(height: 8),
        const Text(
          'Use an email you can access. Signup completes only after email verification.',
          textAlign: TextAlign.center,
          style: TextStyle(color: Color(0xFFB8C1D4), fontSize: 12),
        ),
      ],
    );
  }

  Widget _forgotForm() {
    return Column(
      children: [
        TextField(
          controller: _forgotIdController,
          decoration: const InputDecoration(
            labelText: 'Username or Email',
            prefixIcon: Icon(Icons.person_search),
          ),
        ),
        const SizedBox(height: 10),
        OutlinedButton.icon(
          onPressed: _busy ? null : _requestResetCode,
          icon: const Icon(Icons.mark_email_read),
          label: const Text('Request Reset Code'),
        ),
        const SizedBox(height: 10),
        TextField(
          controller: _forgotUserController,
          decoration: const InputDecoration(
              labelText: 'Username', prefixIcon: Icon(Icons.account_circle)),
        ),
        const SizedBox(height: 10),
        TextField(
          controller: _forgotCodeController,
          decoration: const InputDecoration(
              labelText: 'Reset Code', prefixIcon: Icon(Icons.pin)),
        ),
        const SizedBox(height: 10),
        TextField(
          controller: _forgotNewPwController,
          obscureText: true,
          decoration: const InputDecoration(
              labelText: 'New Password', prefixIcon: Icon(Icons.lock_reset)),
        ),
        const SizedBox(height: 14),
        FilledButton.icon(
          onPressed: _busy ? null : _resetPassword,
          icon: _busy
              ? const SizedBox(
                  height: 16,
                  width: 16,
                  child: CircularProgressIndicator(strokeWidth: 2))
              : const Icon(Icons.check_circle),
          label: Text(_busy ? 'Updating...' : 'Reset Password'),
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Face Studio Login')),
      body: Stack(
        children: [
          Container(
            decoration: const BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [
                  Color(0xFF0A1322),
                  Color(0xFF111C30),
                  Color(0xFF0D1627)
                ],
              ),
            ),
          ),
          Positioned(
            top: -80,
            right: -70,
            child: TweenAnimationBuilder<double>(
              tween: Tween(begin: 0.84, end: 1),
              duration: const Duration(milliseconds: 900),
              curve: Curves.easeOutBack,
              builder: (context, scale, child) {
                return Transform.scale(scale: scale, child: child);
              },
              child: Container(
                width: 220,
                height: 220,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: const Color(0xFF22D3EE).withValues(alpha: 0.11),
                ),
              ),
            ),
          ),
          Positioned(
            left: -90,
            bottom: 60,
            child: TweenAnimationBuilder<double>(
              tween: Tween(begin: 1.18, end: 1),
              duration: const Duration(milliseconds: 980),
              curve: Curves.easeOutCubic,
              builder: (context, scale, child) {
                return Transform.scale(scale: scale, child: child);
              },
              child: Container(
                width: 240,
                height: 240,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: const Color(0xFFFF8E3C).withValues(alpha: 0.09),
                ),
              ),
            ),
          ),
          Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 500),
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  _AnimatedFadeSlide(
                    delayMs: 30,
                    beginOffset: const Offset(0, 0.07),
                    child: Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(18),
                        gradient: const LinearGradient(
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                          colors: [Color(0xFF21496F), Color(0xFF12253E)],
                        ),
                        border: Border.all(color: const Color(0xFF4A709D)),
                        boxShadow: const [
                          BoxShadow(
                            color: Color(0x5510243A),
                            blurRadius: 20,
                            offset: Offset(0, 8),
                          ),
                        ],
                      ),
                      child: const Row(
                        children: [
                          CircleAvatar(
                            radius: 24,
                            backgroundColor: Color(0x2232A8FF),
                            child: Icon(Icons.shield_rounded,
                                color: Color(0xFFD7E9FF), size: 28),
                          ),
                          SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'Welcome to Face Studio',
                                  style: TextStyle(
                                    fontSize: 22,
                                    fontWeight: FontWeight.w800,
                                    color: Colors.white,
                                  ),
                                ),
                                SizedBox(height: 4),
                                Text(
                                  'Secure login, signup verification, and live map tools',
                                  style: TextStyle(
                                      color: Color(0xFFD3E4FF), fontSize: 13),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 10),
                  const _AnimatedFadeSlide(
                    delayMs: 120,
                    beginOffset: Offset(0, 0.05),
                    child: Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        Chip(
                          avatar: Icon(Icons.lock, size: 16),
                          label: Text('Encrypted Auth'),
                        ),
                        Chip(
                          avatar: Icon(Icons.mark_email_read, size: 16),
                          label: Text('Email Verification'),
                        ),
                        Chip(
                          avatar: Icon(Icons.public, size: 16),
                          label: Text('Geo Tracking'),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 12),
                  const _AnimatedFadeSlide(
                    delayMs: 160,
                    beginOffset: Offset(0, 0.05),
                    child: SizedBox.shrink(),
                  ),
                  _modeSelector(),
                  const SizedBox(height: 12),
                  _AnimatedFadeSlide(
                    delayMs: 200,
                    beginOffset: const Offset(0, 0.06),
                    child: Container(
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(16),
                        color: const Color(0xCC121C30),
                        border: Border.all(color: const Color(0xFF334A73)),
                      ),
                      child: AnimatedSwitcher(
                        duration: const Duration(milliseconds: 280),
                        switchInCurve: Curves.easeOut,
                        switchOutCurve: Curves.easeIn,
                        transitionBuilder: (child, animation) {
                          return FadeTransition(
                            opacity: animation,
                            child: SlideTransition(
                              position: Tween<Offset>(
                                begin: const Offset(0.08, 0),
                                end: Offset.zero,
                              ).animate(animation),
                              child: child,
                            ),
                          );
                        },
                        child: KeyedSubtree(
                          key: ValueKey<int>(_mode),
                          child: _mode == 0
                              ? _loginForm()
                              : _mode == 1
                                  ? _signupForm()
                                  : _forgotForm(),
                        ),
                      ),
                    ),
                  ),
                  if (_error.isNotEmpty) ...[
                    const SizedBox(height: 10),
                    Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: const Color(0x33FF3D3D),
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(color: const Color(0x66FF8080)),
                      ),
                      child: Text(_error,
                          style: const TextStyle(color: Colors.white)),
                    ),
                  ],
                  if (_info.isNotEmpty) ...[
                    const SizedBox(height: 10),
                    Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: const Color(0x3326C281),
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(color: const Color(0x6696FFD1)),
                      ),
                      child: Text(_info,
                          style: const TextStyle(color: Color(0xFFE8FFF5))),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

const List<String> _desktopFilterStyles = [
  'Sketch',
  'Cartoon',
  'Oil Painting',
  'HDR',
  'Ghibli Art',
  'Anime',
  'Ghost',
  'Emboss',
  'Watercolor',
  'Pop Art',
  'Neon Glow',
  'Vintage',
  'Pixel Art',
  'Thermal',
  'Glitch',
  'Pencil Color',
];

const List<_KnownMapLocation> _worldMapLocations = [
  _KnownMapLocation(
      name: 'Mumbai, India', latitude: 19.0760, longitude: 72.8777),
  _KnownMapLocation(
      name: 'Delhi, India', latitude: 28.6139, longitude: 77.2090),
  _KnownMapLocation(
      name: 'Bengaluru, India', latitude: 12.9716, longitude: 77.5946),
  _KnownMapLocation(name: 'London, UK', latitude: 51.5074, longitude: -0.1278),
  _KnownMapLocation(
      name: 'New York, USA', latitude: 40.7128, longitude: -74.0060),
  _KnownMapLocation(
      name: 'Tokyo, Japan', latitude: 35.6762, longitude: 139.6503),
  _KnownMapLocation(
      name: 'Sydney, Australia', latitude: -33.8688, longitude: 151.2093),
  _KnownMapLocation(name: 'Dubai, UAE', latitude: 25.2048, longitude: 55.2708),
];

class MobileHomePage extends StatefulWidget {
  final String username;
  final bool isAdmin;
  final Future<void> Function() onLogout;

  const MobileHomePage({
    super.key,
    required this.username,
    required this.isAdmin,
    required this.onLogout,
  });

  @override
  State<MobileHomePage> createState() => _MobileHomePageState();
}

class _MobileHomePageState extends State<MobileHomePage> {
  late bool _isAdmin;
  late String _username;

  @override
  void initState() {
    super.initState();
    _isAdmin = widget.isAdmin;
    _username = widget.username;
  }

  List<_MenuItem> get _commonItems => [
        const _MenuItem(
          title: 'Face Recognition',
          subtitle: 'Identify people in real-time via camera or image',
          colorValue: 0xFF184E77,
          icon: Icons.face_retouching_natural,
          page:
              LiveRecognitionPage(pageTitle: 'Face Recognition - Live Webcam'),
        ),
        const _MenuItem(
          title: 'Face Generation',
          subtitle: 'Generate Anime, Sketch, Cartoon and style filters',
          colorValue: 0xFF5E548E,
          icon: Icons.auto_awesome,
          page: ApiToolsPage(
            initialTab: 1,
            moduleTitle: 'Face Generation',
            defaultTool: 'generate',
          ),
        ),
        const _MenuItem(
          title: 'Face Comparison',
          subtitle: 'Compare two faces and inspect similarity',
          colorValue: 0xFF1F7A8C,
          icon: Icons.compare,
          page: ApiToolsPage(
            initialTab: 0,
            moduleTitle: 'Face Comparison',
            defaultTool: 'compare',
          ),
        ),
        const _MenuItem(
          title: 'Recognition Map',
          subtitle: 'Search where each person was recognized',
          colorValue: 0xFF365486,
          icon: Icons.public,
          page: RecognitionLocationPage(),
        ),
      ];

  List<_MenuItem> get _adminItems => [
        const _MenuItem(
          title: 'Attendance',
          subtitle: 'Mark attendance via recognition',
          colorValue: 0xFF2A9D8F,
          icon: Icons.how_to_reg,
          page: LiveRecognitionPage(
              pageTitle: 'Attendance - Live Recognition', counterMode: true),
        ),
        const _MenuItem(
          title: 'Face Database',
          subtitle: 'Browse and manage registered faces',
          colorValue: 0xFF6D597A,
          icon: Icons.storage,
          page: UsersPage(pageTitle: 'Face Database', showRoles: false),
        ),
        const _MenuItem(
          title: 'Analytics Dashboard',
          subtitle: 'Charts, logs and insights',
          colorValue: 0xFFC44536,
          icon: Icons.analytics,
          page: AnalyticsPage(),
        ),
        const _MenuItem(
          title: 'Services Hub',
          subtitle: 'API, stream and backup controls',
          colorValue: 0xFF3A86FF,
          icon: Icons.hub,
          page: ServicesHubPage(),
        ),
        const _MenuItem(
          title: 'User Registry',
          subtitle: 'Manage users and access history',
          colorValue: 0xFF3A86FF,
          icon: Icons.group,
          page: UsersPage(pageTitle: 'User Registry', showRoles: true),
        ),
        const _MenuItem(
          title: 'Advanced Project Lab',
          subtitle: 'Integrity checks, backups, and deep diagnostics',
          colorValue: 0xFF5B8E7D,
          icon: Icons.science,
          page: AdminModulePage(
            title: 'Advanced Project Lab',
            modulePath: 'advanced-lab',
          ),
        ),
        const _MenuItem(
          title: 'Enterprise Control Center',
          subtitle: 'Roles, approvals, and governance overview',
          colorValue: 0xFF6C5B7B,
          icon: Icons.admin_panel_settings,
          page: AdminModulePage(
            title: 'Enterprise Control Center',
            modulePath: 'enterprise-control',
          ),
        ),
        const _MenuItem(
          title: 'Evaluator Bundle',
          subtitle: 'Generate and review demo artifact bundle',
          colorValue: 0xFF355C7D,
          icon: Icons.inventory_2,
          page: AdminModulePage(
            title: 'Evaluator Bundle',
            modulePath: 'evaluator-bundle',
            supportsExport: true,
          ),
        ),
        const _MenuItem(
          title: 'Judge Mode',
          subtitle: 'Latest status snapshot for quick evaluation',
          colorValue: 0xFFC06C84,
          icon: Icons.gavel,
          page: AdminModulePage(
            title: 'Judge Mode',
            modulePath: 'judge-mode',
          ),
        ),
        const _MenuItem(
          title: 'Demo Launcher',
          subtitle: 'One-screen readiness check for live demo',
          colorValue: 0xFF4D8076,
          icon: Icons.rocket_launch,
          page: AdminModulePage(
            title: 'Demo Launcher',
            modulePath: 'demo-launcher',
          ),
        ),
        const _MenuItem(
          title: 'Presentation Startup',
          subtitle: 'Presentation flow readiness and docs',
          colorValue: 0xFF9B5DE5,
          icon: Icons.present_to_all,
          page: AdminModulePage(
            title: 'Presentation Startup',
            modulePath: 'presentation-startup',
          ),
        ),
        const _MenuItem(
          title: 'Database Bridge',
          subtitle: 'Live DB tables linked with API and frontend',
          colorValue: 0xFF2A6F97,
          icon: Icons.storage_rounded,
          page: DatabaseBridgePage(),
        ),
      ];

  List<_MenuItem> get _userItems => [
        const _MenuItem(
          title: 'My Profile',
          subtitle: 'View account details and password options',
          colorValue: 0xFF2A9D8F,
          icon: Icons.person,
          page: ProfilePage(),
        ),
        const _MenuItem(
          title: 'Face Search',
          subtitle: 'Find faces quickly by person name',
          colorValue: 0xFF6D597A,
          icon: Icons.search,
          page: FaceSearchPage(),
        ),
        const _MenuItem(
          title: 'Face Stats',
          subtitle: 'Recognition summaries and trends',
          colorValue: 0xFFE76F51,
          icon: Icons.stacked_line_chart,
          page: FaceStatsPage(),
        ),
        const _MenuItem(
          title: 'Live Face Counter',
          subtitle: 'Count visible faces from camera stream',
          colorValue: 0xFF277DA1,
          icon: Icons.countertops,
          page: LiveRecognitionPage(
              pageTitle: 'Live Face Counter', counterMode: true),
        ),
        const _MenuItem(
          title: 'System Info',
          subtitle: 'Model files and runtime health',
          colorValue: 0xFF9C6644,
          icon: Icons.info,
          page: SystemInfoPage(),
        ),
        const _MenuItem(
          title: 'Help & About',
          subtitle: 'Shortcuts and feature guide',
          colorValue: 0xFF355070,
          icon: Icons.help,
          page: HelpAboutPage(),
        ),
      ];

  List<_MenuItem> get _visibleItems => [
        ..._commonItems,
        ...(_isAdmin ? _adminItems : _userItems),
      ];

  void _openPage(Widget page) {
    Navigator.of(context).push(MaterialPageRoute(builder: (_) => page));
  }

  @override
  Widget build(BuildContext context) {
    final roleText = _isAdmin ? 'Admin Mode' : 'User Mode';
    final roleColor = _isAdmin ? const Color(0xFFFF8E8E) : _kAccent;

    return Scaffold(
      appBar: AppBar(title: const Text('Face Studio')),
      body: _AnimatedFadeSlide(
        delayMs: 20,
        beginOffset: const Offset(0, 0.035),
        child: ListView(
          padding: const EdgeInsets.all(14),
          children: [
            _AnimatedFadeSlide(
              delayMs: 40,
              child: Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(18),
                  gradient: const LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [Color(0xFF1D3D5F), Color(0xFF16263E)],
                  ),
                  border: Border.all(color: const Color(0xFF3E638E)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Face Studio',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 30,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 0.3,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      'Welcome, $_username',
                      style: const TextStyle(
                          color: Color(0xFFDCEAFF), fontSize: 15),
                    ),
                    const SizedBox(height: 10),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        Chip(
                          avatar: Icon(
                            _isAdmin
                                ? Icons.admin_panel_settings
                                : Icons.person,
                            size: 16,
                            color: roleColor,
                          ),
                          label: Text(roleText),
                        ),
                        Chip(
                          avatar: const Icon(Icons.grid_view, size: 16),
                          label: Text('${_visibleItems.length} modules'),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 12),
            const _AnimatedFadeSlide(
              delayMs: 90,
              child: Text(
                'Choose a mode to get started',
                style: TextStyle(
                    color: Color(0xFFAEC2E0), fontWeight: FontWeight.w600),
              ),
            ),
            const SizedBox(height: 8),
            ..._visibleItems.asMap().entries.map(
                  (entry) => _AnimatedMenuCard(
                    delay: Duration(milliseconds: 80 * entry.key),
                    item: entry.value,
                    onTap: () => _openPage(entry.value.page),
                  ),
                ),
            const SizedBox(height: 14),
            _AnimatedFadeSlide(
              delayMs: 180,
              child: FilledButton.icon(
                onPressed: () async {
                  await widget.onLogout();
                },
                icon: const Icon(Icons.logout),
                label: const Text('Logout'),
              ),
            ),
            const _AnimatedFadeSlide(
              delayMs: 210,
              child: Text(
                'Press back on any page to return here',
                textAlign: TextAlign.center,
                style: TextStyle(color: Color(0xFF8FA4C9), fontSize: 12),
              ),
            ),
            const SizedBox(height: 12),
          ],
        ),
      ),
    );
  }
}

class _AnimatedMenuCard extends StatefulWidget {
  final _MenuItem item;
  final VoidCallback onTap;
  final Duration delay;

  const _AnimatedMenuCard({
    required this.item,
    required this.onTap,
    required this.delay,
  });

  @override
  State<_AnimatedMenuCard> createState() => _AnimatedMenuCardState();
}

class _AnimatedMenuCardState extends State<_AnimatedMenuCard> {
  bool _visible = false;

  @override
  void initState() {
    super.initState();
    Future.delayed(widget.delay, () {
      if (mounted) {
        setState(() => _visible = true);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final color = Color(widget.item.colorValue);
    return AnimatedOpacity(
      duration: const Duration(milliseconds: 350),
      opacity: _visible ? 1 : 0,
      child: AnimatedSlide(
        duration: const Duration(milliseconds: 350),
        offset: _visible ? Offset.zero : const Offset(0, 0.08),
        child: Card(
          color: color,
          margin: const EdgeInsets.symmetric(vertical: 6),
          child: InkWell(
            onTap: widget.onTap,
            borderRadius: BorderRadius.circular(12),
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Row(
                children: [
                  Icon(widget.item.icon, color: Colors.white),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          widget.item.title,
                          style: const TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.bold,
                            fontSize: 16,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          widget.item.subtitle,
                          style: const TextStyle(color: Color(0xFFD6DEEF)),
                        ),
                      ],
                    ),
                  ),
                  const Icon(Icons.arrow_forward_ios,
                      color: Colors.white70, size: 16),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class LiveRecognitionPage extends StatefulWidget {
  final String pageTitle;
  final bool counterMode;

  const LiveRecognitionPage({
    super.key,
    this.pageTitle = 'Face Recognition - Live Webcam',
    this.counterMode = false,
  });

  @override
  State<LiveRecognitionPage> createState() => _LiveRecognitionPageState();
}

class _LiveRecognitionPageState extends State<LiveRecognitionPage> {
  String get _baseUrl => buildBackendApi().baseUrl;
  final String _apiKey =
      const String.fromEnvironment('FACE_STUDIO_API_KEY', defaultValue: '');

  CameraController? _controller;
  Timer? _loopTimer;
  bool _busy = false;
  String _token = '';
  String _status = 'Starting camera...';
  String _topName = 'Unknown';
  double _topScore = 0.0;
  List<Map<String, dynamic>> _liveFaces = const [];
  int _imgW = 0;
  int _imgH = 0;
  bool _locationPermissionGranted = false;
  double? _currentLat;
  double? _currentLng;
  String _currentLocationLabel = 'Detecting location...';
  DateTime? _lastLocationFetchAt;
  String _lastSavedInfo = 'No recognition location saved yet';

  @override
  void initState() {
    super.initState();
    _setup();
  }

  @override
  void dispose() {
    _loopTimer?.cancel();
    _controller?.dispose();
    super.dispose();
  }

  Future<void> _setup() async {
    try {
      await _ensureLocationAccess();
      await _updateCurrentLocation(force: true);

      final cams = await availableCameras();
      if (cams.isEmpty) {
        setState(() => _status = 'No camera found on device');
        return;
      }

      final front = cams
          .where((c) => c.lensDirection == CameraLensDirection.front)
          .toList();
      final selected = front.isNotEmpty ? front.first : cams.first;

      final controller = CameraController(
        selected,
        ResolutionPreset.medium,
        enableAudio: false,
      );
      await controller.initialize();
      _controller = controller;

      final ok = await _ensureToken();
      if (!ok) {
        setState(() => _status = 'Auth failed. Check backend/API key.');
      } else {
        setState(() => _status = 'Live recognition running');
      }

      _loopTimer = Timer.periodic(const Duration(seconds: 2), (_) {
        _captureAndRecognize();
      });
      await _captureAndRecognize();
      if (mounted) {
        setState(() {});
      }
    } catch (e) {
      if (mounted) {
        setState(() => _status = 'Camera setup error: $e');
      }
    }
  }

  Future<void> _ensureLocationAccess() async {
    try {
      final serviceEnabled = await Geolocator.isLocationServiceEnabled();
      if (!serviceEnabled) {
        if (mounted) {
          setState(() {
            _locationPermissionGranted = false;
            _currentLocationLabel = 'Location service is off';
          });
        }
        return;
      }

      var permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }

      final granted = permission == LocationPermission.whileInUse ||
          permission == LocationPermission.always;
      if (mounted) {
        setState(() {
          _locationPermissionGranted = granted;
          if (!granted) {
            _currentLocationLabel = 'Location permission denied';
          }
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _locationPermissionGranted = false;
          _currentLocationLabel = 'Location error: $e';
        });
      }
    }
  }

  Future<void> _updateCurrentLocation({bool force = false}) async {
    if (!_locationPermissionGranted) {
      return;
    }
    final now = DateTime.now();
    if (!force &&
        _lastLocationFetchAt != null &&
        now.difference(_lastLocationFetchAt!).inSeconds < 12) {
      return;
    }

    try {
      final pos = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.medium,
          distanceFilter: 0,
        ),
      );
      _lastLocationFetchAt = now;
      if (mounted) {
        setState(() {
          _currentLat = pos.latitude;
          _currentLng = pos.longitude;
          _currentLocationLabel =
              'Lat ${pos.latitude.toStringAsFixed(5)}, Lng ${pos.longitude.toStringAsFixed(5)}';
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _currentLocationLabel = 'Location fetch failed';
        });
      }
    }
  }

  Future<bool> _ensureToken() async {
    final sessionApi = buildBackendApi();
    if (sessionApi.token.isNotEmpty) {
      _token = sessionApi.token;
      return true;
    }
    final sessionOk = await sessionApi.ensureToken();
    if (sessionOk) {
      _token = sessionApi.token;
      return _token.isNotEmpty;
    }
    if (_token.isNotEmpty) {
      return true;
    }
    if (_apiKey.isEmpty) {
      return false;
    }
    final uri = Uri.parse(
        '${_baseUrl.trim().replaceAll(RegExp(r'/$'), '')}/api/auth/token?subject=android_live&ttl=720');
    final res = await http.get(uri, headers: {'X-API-Key': _apiKey});
    if (res.statusCode != 200) {
      return false;
    }
    final data = jsonDecode(res.body) as Map<String, dynamic>;
    _token = (data['data']?['token'] ?? '').toString();
    return _token.isNotEmpty;
  }

  Future<void> _saveUnknownFaceWithName({
    required String imageB64,
    required String personName,
  }) async {
    if (!await _ensureToken()) {
      if (mounted) {
        setState(() => _status = 'Token unavailable for save');
      }
      return;
    }
    final cleanName = personName.trim();
    if (cleanName.isEmpty) {
      return;
    }
    final endpoint = Uri.parse(
        '${_baseUrl.trim().replaceAll(RegExp(r'/$'), '')}/api/admin/faces/sync');
    final now = DateTime.now().millisecondsSinceEpoch;
    final filename = 'mobile_$now.jpg';
    final res = await http.post(
      endpoint,
      headers: {
        'Authorization': 'Bearer $_token',
        'Content-Type': 'application/json',
      },
      body: jsonEncode({
        'entries': [
          {
            'person': cleanName,
            'filename': filename,
            'image_b64': imageB64,
          }
        ],
        'clear_existing': false,
        'refresh_after': true,
      }),
    );
    if (!mounted) {
      return;
    }
    if (res.statusCode != 200) {
      setState(() {
        _status = 'Save unknown failed: ${res.statusCode}';
      });
      return;
    }
    setState(() {
      _status = 'Saved unknown as $cleanName';
      _lastSavedInfo = 'Saved: $cleanName at $_currentLocationLabel';
    });
  }

  Future<void> _promptAndSaveUnknownFace(String imageB64) async {
    final nameController = TextEditingController();
    final entered = await showDialog<String>(
      context: context,
      builder: (ctx) {
        return AlertDialog(
          title: const Text('Unknown Face Detected'),
          content: TextField(
            controller: nameController,
            autofocus: true,
            decoration: const InputDecoration(
              labelText: 'Enter person name',
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(''),
              child: const Text('Skip'),
            ),
            ElevatedButton(
              onPressed: () => Navigator.of(ctx).pop(nameController.text),
              child: const Text('Save'),
            ),
          ],
        );
      },
    );
    final name = (entered ?? '').trim();
    if (name.isEmpty) {
      return;
    }
    await _saveUnknownFaceWithName(imageB64: imageB64, personName: name);
  }

  Future<void> _captureAndRecognize({bool interactive = false}) async {
    final ctrl = _controller;
    if (!mounted || ctrl == null || !ctrl.value.isInitialized || _busy) {
      return;
    }
    _busy = true;
    try {
      if (!await _ensureToken()) {
        if (mounted) {
          setState(() => _status = 'Token unavailable');
        }
        return;
      }

      unawaited(_updateCurrentLocation());

      final shot = await ctrl.takePicture();
      final file = File(shot.path);
      final bytes = await file.readAsBytes();
      final imageB64 = base64Encode(bytes);

      final uri = Uri.parse(
          '${_baseUrl.trim().replaceAll(RegExp(r'/$'), '')}/api/mobile/identify');
      final sessionUser = buildBackendApi().username;
      Future<http.Response> sendIdentify() {
        return http
            .post(
              uri,
              headers: {
                'Authorization': 'Bearer $_token',
                'Content-Type': 'application/json',
              },
              body: jsonEncode({
                'image_b64': imageB64,
                'top_k': 1,
                'tracking': {
                  'location_name': _currentLocationLabel,
                  'latitude': _currentLat,
                  'longitude': _currentLng,
                  'requested_by': sessionUser.isEmpty ? 'mobile' : sessionUser,
                  'force_update': false,
                },
              }),
            )
            .timeout(const Duration(seconds: 8));
      }

      var res = await sendIdentify();
      if (res.statusCode == 401 || res.statusCode == 403) {
        _token = '';
        final refreshed = await _ensureToken();
        if (refreshed) {
          res = await sendIdentify();
        }
      }

      if (res.statusCode != 200) {
        if (mounted) {
          setState(() => _status = 'Identify error: ${res.statusCode}');
        }
        return;
      }

      final body = jsonDecode(res.body) as Map<String, dynamic>;
      final data = body['data'] as Map<String, dynamic>?;
      final faces = ((data?['faces'] as List?) ?? const [])
          .whereType<Map>()
          .map((e) => Map<String, dynamic>.from(e))
          .toList();
      final best =
          Map<String, dynamic>.from((data?['best'] as Map?) ?? const {});
      final name = (best['name'] ?? 'Unknown').toString();
      final score = double.tryParse((best['score'] ?? 0).toString()) ?? 0.0;
      final iw = int.tryParse((data?['image_width'] ?? 0).toString()) ?? 0;
      final ih = int.tryParse((data?['image_height'] ?? 0).toString()) ?? 0;
      final tracking = Map<String, dynamic>.from(
          (data?['location_tracking'] as Map?) ?? const {});
      final detected = data?['detected'] == true;
      final faceCount =
          int.tryParse((data?['face_count'] ?? faces.length).toString()) ??
              faces.length;
      final saved = tracking['saved'] == true;
      final deduped =
          (tracking['reason'] ?? '').toString() == 'deduped_recent_event';
      final saveInfo = name.toLowerCase() == 'unknown'
          ? 'No save: unknown face'
          : saved
              ? 'Saved: $name at $_currentLocationLabel'
              : (deduped
                  ? 'Already saved recently for $name at $_currentLocationLabel'
                  : 'Save pending for $name');

      if (mounted) {
        setState(() {
          _topName = name;
          _topScore = score;
          _liveFaces = faces;
          _imgW = iw;
          _imgH = ih;
          _lastSavedInfo = saveInfo;
          final backendMsg = (data?['message'] ?? '').toString().trim();
          _status = faces.isEmpty
              ? (backendMsg.isNotEmpty
                  ? backendMsg
                  : 'No face detected in current frame')
              : 'Live recognition running';
        });
      }

      if (interactive &&
          detected &&
          faceCount > 0 &&
          name.toLowerCase() == 'unknown') {
        await _promptAndSaveUnknownFace(imageB64);
      }
    } catch (e) {
      if (mounted) {
        setState(() => _status = 'Live loop error: $e');
      }
    } finally {
      _busy = false;
    }
  }

  @override
  Widget build(BuildContext context) {
    final ctrl = _controller;
    final paused = _loopTimer == null;
    return Scaffold(
      appBar: AppBar(title: Text(widget.pageTitle)),
      body: Column(
        children: [
          Expanded(
            child: Container(
              color: const Color(0xFF080D17),
              child: ctrl == null || !ctrl.value.isInitialized
                  ? const Center(
                      child: CircularProgressIndicator(),
                    )
                  : Stack(
                      fit: StackFit.expand,
                      children: [
                        CameraPreview(ctrl),
                        Positioned.fill(
                          child: IgnorePointer(
                            child: CustomPaint(
                              painter: _LiveFaceOverlayPainter(
                                faces: _liveFaces,
                                imageWidth: _imgW,
                                imageHeight: _imgH,
                              ),
                            ),
                          ),
                        ),
                        Positioned(
                          left: 12,
                          right: 12,
                          top: 12,
                          child: AnimatedSwitcher(
                            duration: const Duration(milliseconds: 260),
                            child: Card(
                              key: ValueKey<String>(
                                  '${_topName}_${paused}_${_liveFaces.length}'),
                              color: const Color(0xCC0B1322),
                              child: Padding(
                                padding: const EdgeInsets.all(10),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      widget.counterMode
                                          ? 'Visible Faces: ${_liveFaces.length}'
                                          : 'Recognized: $_topName',
                                      style: const TextStyle(
                                        color: Colors.white,
                                        fontWeight: FontWeight.bold,
                                        fontSize: 16,
                                      ),
                                    ),
                                    const SizedBox(height: 2),
                                    if (!widget.counterMode)
                                      Text(
                                        'Confidence: ${(_topScore * 100).toStringAsFixed(1)}%',
                                        style: const TextStyle(
                                            color: Colors.white70),
                                      ),
                                    const SizedBox(height: 6),
                                    Wrap(
                                      spacing: 6,
                                      runSpacing: 6,
                                      children: [
                                        Chip(
                                          avatar: Icon(
                                            paused
                                                ? Icons.pause_circle
                                                : Icons.play_circle,
                                            size: 16,
                                          ),
                                          label: Text(paused
                                              ? 'Live Paused'
                                              : 'Live Active'),
                                        ),
                                        Chip(
                                          avatar:
                                              const Icon(Icons.face, size: 16),
                                          label: Text(
                                              '${_liveFaces.length} faces'),
                                        ),
                                      ],
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
            ),
          ),
          Container(
            width: double.infinity,
            color: const Color(0xFF111A2D),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                AnimatedContainer(
                  duration: const Duration(milliseconds: 280),
                  width: double.infinity,
                  padding:
                      const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                  decoration: BoxDecoration(
                    color: const Color(0xFF16243C),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0xFF38567E)),
                  ),
                  child: AnimatedSwitcher(
                    duration: const Duration(milliseconds: 220),
                    child: Text(
                      'Status: $_status',
                      key: ValueKey<String>(_status),
                      style: const TextStyle(color: Colors.white),
                    ),
                  ),
                ),
                const SizedBox(height: 8),
                AnimatedContainer(
                  duration: const Duration(milliseconds: 280),
                  width: double.infinity,
                  padding:
                      const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                  decoration: BoxDecoration(
                    color: const Color(0xFF0E1422),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0xFF355070)),
                  ),
                  child: AnimatedSwitcher(
                    duration: const Duration(milliseconds: 220),
                    child: Text(
                      _locationPermissionGranted
                          ? 'Current Location: $_currentLocationLabel'
                          : 'Location permission required for auto map updates',
                      key: ValueKey<String>(
                        _locationPermissionGranted
                            ? _currentLocationLabel
                            : 'perm_missing',
                      ),
                      style: const TextStyle(color: Color(0xFFBBD0F8)),
                    ),
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  _lastSavedInfo,
                  style: const TextStyle(
                      color: Color(0xFF9BE7A8),
                      fontSize: 12,
                      fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    FilledButton.icon(
                      onPressed: () => _captureAndRecognize(interactive: true),
                      icon: const Icon(Icons.radar),
                      label: const Text('Recognize Now'),
                    ),
                    OutlinedButton.icon(
                      onPressed: () async {
                        await _ensureLocationAccess();
                        await _updateCurrentLocation(force: true);
                      },
                      icon: const Icon(Icons.my_location),
                      label: const Text('Refresh Location'),
                    ),
                    ElevatedButton.icon(
                      onPressed: () {
                        if (_loopTimer == null) {
                          _loopTimer =
                              Timer.periodic(const Duration(seconds: 2), (_) {
                            _captureAndRecognize();
                          });
                          setState(() => _status = 'Live recognition resumed');
                        }
                      },
                      icon: const Icon(Icons.play_arrow),
                      label: const Text('Resume Live'),
                    ),
                    ElevatedButton.icon(
                      onPressed: () {
                        _loopTimer?.cancel();
                        _loopTimer = null;
                        setState(() => _status = 'Live recognition paused');
                      },
                      icon: const Icon(Icons.pause),
                      label: const Text('Pause Live'),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _LiveFaceOverlayPainter extends CustomPainter {
  final List<Map<String, dynamic>> faces;
  final int imageWidth;
  final int imageHeight;

  _LiveFaceOverlayPainter({
    required this.faces,
    required this.imageWidth,
    required this.imageHeight,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (imageWidth <= 0 || imageHeight <= 0 || faces.isEmpty) {
      return;
    }

    final sx = size.width / imageWidth;
    final sy = size.height / imageHeight;

    final boxPaint = Paint()
      ..color = const Color(0xFF65B5FF)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2;

    for (final face in faces) {
      final bbox =
          Map<String, dynamic>.from((face['bbox'] as Map?) ?? const {});
      final best =
          Map<String, dynamic>.from((face['best'] as Map?) ?? const {});

      final x = (num.tryParse((bbox['x'] ?? 0).toString()) ?? 0).toDouble();
      final y = (num.tryParse((bbox['y'] ?? 0).toString()) ?? 0).toDouble();
      final w = (num.tryParse((bbox['w'] ?? 0).toString()) ?? 0).toDouble();
      final h = (num.tryParse((bbox['h'] ?? 0).toString()) ?? 0).toDouble();

      final name = (best['name'] ?? 'Unknown').toString();
      final score =
          (num.tryParse((best['score'] ?? 0).toString()) ?? 0).toDouble();

      final rect = Rect.fromLTWH(x * sx, y * sy, w * sx, h * sy);
      canvas.drawRect(rect, boxPaint);

      final label = '$name ${(score * 100).toStringAsFixed(1)}%';
      final span = TextSpan(
        text: label,
        style: const TextStyle(
          color: Colors.white,
          fontSize: 12,
          fontWeight: FontWeight.bold,
        ),
      );
      final tp = TextPainter(text: span, textDirection: TextDirection.ltr)
        ..layout();

      const labelPad = 4.0;
      final bg = RRect.fromRectAndRadius(
        Rect.fromLTWH(
          rect.left,
          (rect.top - tp.height - (labelPad * 2)).clamp(0, size.height),
          tp.width + (labelPad * 2),
          tp.height + (labelPad * 2),
        ),
        const Radius.circular(6),
      );
      canvas.drawRRect(
          bg, Paint()..color = Colors.black.withValues(alpha: 0.72));
      tp.paint(canvas, Offset(bg.left + labelPad, bg.top + labelPad));
    }
  }

  @override
  bool shouldRepaint(covariant _LiveFaceOverlayPainter oldDelegate) {
    return oldDelegate.faces != faces ||
        oldDelegate.imageWidth != imageWidth ||
        oldDelegate.imageHeight != imageHeight;
  }
}

class ProfilePage extends StatefulWidget {
  const ProfilePage({super.key});

  @override
  State<ProfilePage> createState() => _ProfilePageState();
}

class _ProfilePageState extends State<ProfilePage> {
  bool _loading = true;
  String _error = '';
  Map<String, dynamic> _profile = const {};
  List<Map<String, dynamic>> _recentActivity = const [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final api = buildBackendApi();
      final me = await api.getCurrentUser();
      final activity = await api.getActivity(limit: 20);
      final p = (me['data'] as Map<String, dynamic>?) ?? const {};
      final a = ((activity['data'] as List?) ?? const [])
          .whereType<Map>()
          .map((e) => Map<String, dynamic>.from(e))
          .toList();
      setState(() {
        _profile = p;
        _recentActivity = a;
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _error = 'Profile load error: $e';
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    final username = (_profile['username'] ?? 'User').toString();
    final email = (_profile['email'] ?? '-').toString();
    final phone = (_profile['phone'] ?? '-').toString();
    final role = (_profile['role'] ?? '-').toString();
    final created = (_profile['created'] ?? '-').toString();
    final recentCount = _recentActivity.length;
    final securityState =
        role.toLowerCase() == 'admin' ? 'Elevated' : 'Standard';
    return Scaffold(
      appBar: AppBar(title: const Text('My Profile')),
      body: ListView(
        padding: const EdgeInsets.all(12),
        children: [
          if (_error.isNotEmpty)
            Card(
              color: const Color(0xFF5C1A1A),
              child: Padding(
                padding: const EdgeInsets.all(12),
                child:
                    Text(_error, style: const TextStyle(color: Colors.white)),
              ),
            ),
          _AnimatedFadeSlide(
            delayMs: 120,
            child: Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(18),
                gradient: const LinearGradient(
                  colors: [Color(0xFF273F63), Color(0xFF192944)],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                border: Border.all(color: const Color(0xFF49658F), width: 1),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      CircleAvatar(
                        radius: 24,
                        backgroundColor: const Color(0xFF6AB8FF),
                        child: Text(
                          username.isNotEmpty ? username[0].toUpperCase() : 'U',
                          style: const TextStyle(
                            color: Color(0xFF08233E),
                            fontSize: 20,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              username,
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 20,
                                fontWeight: FontWeight.w900,
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              email,
                              style: const TextStyle(color: Color(0xFFC7DCF6)),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 14),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      _SectionBadge(
                        icon: Icons.verified_user,
                        label: role,
                        tint: const Color(0xFF7AE7FF),
                      ),
                      _SectionBadge(
                        icon: Icons.shield,
                        label: securityState,
                        tint: const Color(0xFF9AB1FF),
                      ),
                      _SectionBadge(
                        icon: Icons.history,
                        label: '$recentCount activities',
                        tint: const Color(0xFFFFCF92),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 10),
          _AnimatedFadeSlide(
            delayMs: 200,
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  _KpiTile(
                    title: 'Role Level',
                    value: role.toUpperCase(),
                    tint: const Color(0xFF78D5FF),
                    icon: Icons.admin_panel_settings,
                  ),
                  const SizedBox(width: 8),
                  _KpiTile(
                    title: 'Recent Activity',
                    value: '$recentCount',
                    tint: const Color(0xFFFFCB88),
                    icon: Icons.query_stats,
                  ),
                  const SizedBox(width: 8),
                  _KpiTile(
                    title: 'Member Since',
                    value: created.length > 10
                        ? created.substring(0, 10)
                        : created,
                    tint: const Color(0xFFA7BDFF),
                    icon: Icons.calendar_month,
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          const Text('Profile Details',
              style: TextStyle(fontWeight: FontWeight.bold)),
          const SizedBox(height: 6),
          _AnimatedFadeSlide(
            delayMs: 260,
            child: Column(
              children: [
                _ProfileFieldTile(
                    label: 'Username', value: username, icon: Icons.person),
                _ProfileFieldTile(
                    label: 'Email', value: email, icon: Icons.alternate_email),
                _ProfileFieldTile(
                    label: 'Phone', value: phone, icon: Icons.phone_iphone),
                _ProfileFieldTile(
                    label: 'Role', value: role, icon: Icons.badge),
                _ProfileFieldTile(
                    label: 'Created', value: created, icon: Icons.event),
              ],
            ),
          ),
          const SizedBox(height: 8),
          const Text('Recent Activity',
              style: TextStyle(fontWeight: FontWeight.bold)),
          const SizedBox(height: 6),
          ..._recentActivity.take(12).toList().asMap().entries.map((entry) {
            final index = entry.key;
            final a = entry.value;
            return _AnimatedFadeSlide(
              delayMs: 320 + (index * 40),
              child: _TimelineActivityTile(
                title: (a['action'] ?? 'Activity').toString(),
                subtitle: (a['detail'] ?? '').toString(),
                trailing: (a['event_time'] ?? '').toString(),
              ),
            );
          }),
        ],
      ),
    );
  }
}

class UsersPage extends StatefulWidget {
  final String pageTitle;
  final bool showRoles;

  const UsersPage({
    super.key,
    required this.pageTitle,
    this.showRoles = true,
  });

  @override
  State<UsersPage> createState() => _UsersPageState();
}

class _UsersPageState extends State<UsersPage> {
  bool _loading = true;
  String _error = '';
  List<Map<String, dynamic>> _users = const [];
  final TextEditingController _searchController = TextEditingController();
  final TextEditingController _roleController = TextEditingController();
  final TextEditingController _emailDomainController = TextEditingController();
  String _sortBy = 'Name (A-Z)';
  bool _adminsOnly = false;
  bool _recentOnly = false;
  bool _denseMode = false;
  bool _gridMode = false;
  Map<String, dynamic>? _selectedUser;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _searchController.dispose();
    _roleController.dispose();
    _emailDomainController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final api = buildBackendApi();
      final users = await api.getUsers(limit: 200);
      final rows = ((users['data'] as List?) ?? const [])
          .whereType<Map>()
          .map((e) => Map<String, dynamic>.from(e))
          .toList();
      setState(() {
        _users = rows;
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _error = 'Users load error: $e';
        _loading = false;
      });
    }
  }

  String _safeLower(dynamic value) => (value ?? '').toString().toLowerCase();

  int _loginCount(Map<String, dynamic> row) {
    final logs = (row['logins'] as List?) ?? const [];
    return logs.length;
  }

  int _createdStamp(Map<String, dynamic> row) {
    final text = (row['created'] ?? '').toString();
    final parsed = DateTime.tryParse(text.replaceFirst(' ', 'T'));
    return parsed?.millisecondsSinceEpoch ?? 0;
  }

  bool _matchesFilters(Map<String, dynamic> u) {
    final query = _searchController.text.trim().toLowerCase();
    final roleFilter = _roleController.text.trim().toLowerCase();
    final domainFilter = _emailDomainController.text.trim().toLowerCase();
    final username = _safeLower(u['username']);
    final email = _safeLower(u['email']);
    final phone = _safeLower(u['phone']);
    final role = _safeLower(u['role']);

    final matchesQuery = query.isEmpty ||
        username.contains(query) ||
        email.contains(query) ||
        phone.contains(query) ||
        role.contains(query);
    final matchesRole = roleFilter.isEmpty || role.contains(roleFilter);
    final matchesDomain = domainFilter.isEmpty || email.contains(domainFilter);
    final matchesAdmin = !_adminsOnly || role == 'admin';
    final matchesRecent = !_recentOnly || _createdStamp(u) > 0;
    return matchesQuery &&
        matchesRole &&
        matchesDomain &&
        matchesAdmin &&
        matchesRecent;
  }

  List<Map<String, dynamic>> _applySearchAndSort() {
    final filtered = _users.where(_matchesFilters).toList();
    filtered.sort((a, b) {
      switch (_sortBy) {
        case 'Name (Z-A)':
          return _safeLower(b['username']).compareTo(_safeLower(a['username']));
        case 'Created (Newest)':
          return _createdStamp(b).compareTo(_createdStamp(a));
        case 'Created (Oldest)':
          return _createdStamp(a).compareTo(_createdStamp(b));
        case 'Role (A-Z)':
          final roleCompare =
              _safeLower(a['role']).compareTo(_safeLower(b['role']));
          if (roleCompare != 0) {
            return roleCompare;
          }
          return _safeLower(a['username']).compareTo(_safeLower(b['username']));
        case 'Login Count (High-Low)':
          return _loginCount(b).compareTo(_loginCount(a));
        case 'Login Count (Low-High)':
          return _loginCount(a).compareTo(_loginCount(b));
        default:
          return _safeLower(a['username']).compareTo(_safeLower(b['username']));
      }
    });
    return filtered;
  }

  Map<String, int> _roleSummary(List<Map<String, dynamic>> rows) {
    final out = <String, int>{};
    for (final row in rows) {
      final role = (row['role'] ?? 'user').toString().toLowerCase();
      out[role] = (out[role] ?? 0) + 1;
    }
    return out;
  }

  Future<void> _copyUserSummary(List<Map<String, dynamic>> rows) async {
    final roleMap = _roleSummary(rows);
    final lines = <String>[
      'Face Studio User Snapshot',
      'Total Loaded: ${_users.length}',
      'Visible: ${rows.length}',
      'Admins: ${roleMap['admin'] ?? 0}',
      'Users: ${roleMap['user'] ?? 0}',
      'Filters: query="${_searchController.text.trim()}", role="${_roleController.text.trim()}", domain="${_emailDomainController.text.trim()}"',
      'Sort: $_sortBy',
    ];
    await Clipboard.setData(ClipboardData(text: lines.join('\n')));
    if (!mounted) {
      return;
    }
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('User summary copied to clipboard')),
    );
  }

  void _openUserSheet(Map<String, dynamic> user) {
    setState(() => _selectedUser = user);
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: const Color(0xFF121C2F),
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(18)),
      ),
      builder: (context) {
        final username = (user['username'] ?? '-').toString();
        final email = (user['email'] ?? '-').toString();
        final phone = (user['phone'] ?? '-').toString();
        final role = (user['role'] ?? 'user').toString();
        final created = (user['created'] ?? '-').toString();
        final logins = _loginCount(user);
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
            child: ListView(
              shrinkWrap: true,
              children: [
                Center(
                  child: Container(
                    width: 46,
                    height: 4,
                    decoration: BoxDecoration(
                      color: const Color(0xFF425B82),
                      borderRadius: BorderRadius.circular(999),
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  username,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 22,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    _SectionBadge(
                      icon: Icons.badge,
                      label: role,
                      tint: role.toLowerCase() == 'admin'
                          ? const Color(0xFFFFB0B0)
                          : const Color(0xFF9FD7FF),
                    ),
                    _SectionBadge(
                      icon: Icons.login,
                      label: '$logins logins',
                      tint: const Color(0xFFFFCF8E),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                _ProfileFieldTile(
                    label: 'Email', value: email, icon: Icons.alternate_email),
                _ProfileFieldTile(
                    label: 'Phone', value: phone, icon: Icons.phone),
                _ProfileFieldTile(
                    label: 'Created',
                    value: created,
                    icon: Icons.calendar_today),
                const SizedBox(height: 6),
                FilledButton.icon(
                  onPressed: () async {
                    await Clipboard.setData(
                      ClipboardData(
                          text:
                              'username=$username\nemail=$email\nphone=$phone\nrole=$role\ncreated=$created'),
                    );
                    if (!context.mounted) {
                      return;
                    }
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('User details copied')),
                    );
                  },
                  icon: const Icon(Icons.copy),
                  label: const Text('Copy User Details'),
                ),
              ],
            ),
          ),
        );
      },
    ).whenComplete(() {
      if (mounted) {
        setState(() => _selectedUser = null);
      }
    });
  }

  Widget _buildUserCard(Map<String, dynamic> u, {required int index}) {
    final role = (u['role'] ?? 'user').toString();
    final username = (u['username'] ?? '-').toString();
    final email = (u['email'] ?? '-').toString();
    final phone = (u['phone'] ?? '-').toString();
    final created = (u['created'] ?? '').toString();
    final loginCount = _loginCount(u);
    final selected = identical(_selectedUser, u);
    final roleAdmin = role.toLowerCase() == 'admin';
    final delay = 260 + (index * 20);
    final tileChild = InkWell(
      borderRadius: BorderRadius.circular(14),
      onTap: () => _openUserSheet(u),
      child: Container(
        padding: EdgeInsets.all(_denseMode ? 10 : 12),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(14),
          color: selected ? const Color(0xFF1C3153) : const Color(0xFF17253E),
          border: Border.all(
            color:
                roleAdmin ? const Color(0xFF8D4A61) : const Color(0xFF3E5A86),
            width: selected ? 1.6 : 1,
          ),
        ),
        child: Row(
          children: [
            CircleAvatar(
              radius: _denseMode ? 16 : 18,
              backgroundColor:
                  roleAdmin ? const Color(0xFF91445D) : const Color(0xFF2E4D7A),
              child: Text(
                username.isNotEmpty ? username[0].toUpperCase() : 'U',
                style: const TextStyle(
                    color: Colors.white, fontWeight: FontWeight.bold),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    username,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.w800,
                      fontSize: 15,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    email,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style:
                        const TextStyle(fontSize: 12, color: Color(0xFFC2D7F7)),
                  ),
                  if (!_denseMode) ...[
                    const SizedBox(height: 2),
                    Text(
                      'Phone: $phone',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                          fontSize: 12, color: Color(0xFFA9C1E7)),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(width: 8),
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: roleAdmin
                        ? const Color(0xFF6A2E43)
                        : const Color(0xFF29456E),
                    borderRadius: BorderRadius.circular(999),
                  ),
                  child: Text(
                    role,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  '$loginCount logs',
                  style:
                      const TextStyle(fontSize: 11, color: Color(0xFFB9CFEE)),
                ),
                const SizedBox(height: 2),
                Text(
                  created,
                  style:
                      const TextStyle(fontSize: 10, color: Color(0xFF97AED1)),
                ),
              ],
            ),
          ],
        ),
      ),
    );
    return _AnimatedFadeSlide(
      delayMs: delay,
      child: _gridMode
          ? tileChild
          : Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: tileChild,
            ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return Scaffold(
        appBar: AppBar(title: Text(widget.pageTitle)),
        body: const Center(child: CircularProgressIndicator()),
      );
    }
    final filtered = _applySearchAndSort();
    final roleMap = _roleSummary(filtered);
    final adminCount = roleMap['admin'] ?? 0;
    final userCount = roleMap['user'] ?? 0;
    final latestCreated = filtered.isEmpty
        ? 0
        : (filtered
            .map((e) => _createdStamp(e))
            .where((e) => e > 0)
            .fold<int>(0, (p, c) => c > p ? c : p));
    final latestText = latestCreated == 0
        ? '-'
        : DateTime.fromMillisecondsSinceEpoch(latestCreated)
            .toIso8601String()
            .split('T')
            .first;
    return Scaffold(
      appBar: AppBar(title: Text(widget.pageTitle)),
      body: ListView(
        padding: const EdgeInsets.all(12),
        children: [
          if (_error.isNotEmpty)
            Card(
              color: const Color(0xFF5C1A1A),
              child: Padding(
                padding: const EdgeInsets.all(12),
                child:
                    Text(_error, style: const TextStyle(color: Colors.white)),
              ),
            ),
          _AnimatedFadeSlide(
            delayMs: 110,
            child: Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(14),
                gradient: const LinearGradient(
                  colors: [Color(0xFF26456E), Color(0xFF17253D)],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                border: Border.all(color: const Color(0xFF496286), width: 1),
              ),
              child: Row(
                children: [
                  const Icon(Icons.groups_2, color: Color(0xFFBFE1FF)),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'User Registry  |  ${filtered.length} visible of ${_users.length}',
                      style: const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.bold,
                        fontSize: 16,
                      ),
                    ),
                  ),
                  IconButton(
                    onPressed: () => _copyUserSummary(filtered),
                    icon: const Icon(Icons.copy_all),
                    tooltip: 'Copy summary',
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 8),
          _AnimatedFadeSlide(
            delayMs: 170,
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  _KpiTile(
                    title: 'Visible Users',
                    value: '${filtered.length}',
                    tint: const Color(0xFF78D5FF),
                    icon: Icons.person_search,
                  ),
                  const SizedBox(width: 8),
                  _KpiTile(
                    title: 'Admins',
                    value: '$adminCount',
                    tint: const Color(0xFFFFB0BD),
                    icon: Icons.admin_panel_settings,
                  ),
                  const SizedBox(width: 8),
                  _KpiTile(
                    title: 'Users',
                    value: '$userCount',
                    tint: const Color(0xFF9DCAFF),
                    icon: Icons.people,
                  ),
                  const SizedBox(width: 8),
                  _KpiTile(
                    title: 'Latest Join',
                    value: latestText,
                    tint: const Color(0xFFFFD28E),
                    icon: Icons.schedule,
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 8),
          _AnimatedFadeSlide(
            delayMs: 210,
            child: TextField(
              controller: _searchController,
              onChanged: (_) => setState(() {}),
              decoration: InputDecoration(
                labelText: 'Search username / email / phone / role',
                prefixIcon: const Icon(Icons.search),
                suffixIcon: _searchController.text.isEmpty
                    ? null
                    : IconButton(
                        onPressed: () {
                          _searchController.clear();
                          setState(() {});
                        },
                        icon: const Icon(Icons.clear),
                      ),
              ),
            ),
          ),
          const SizedBox(height: 8),
          _AnimatedFadeSlide(
            delayMs: 240,
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _roleController,
                    onChanged: (_) => setState(() {}),
                    decoration: const InputDecoration(
                      labelText: 'Role filter',
                      prefixIcon: Icon(Icons.badge),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: TextField(
                    controller: _emailDomainController,
                    onChanged: (_) => setState(() {}),
                    decoration: const InputDecoration(
                      labelText: 'Email domain filter',
                      prefixIcon: Icon(Icons.alternate_email),
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 8),
          _AnimatedFadeSlide(
            delayMs: 260,
            child: DropdownButtonFormField<String>(
              initialValue: _sortBy,
              decoration: const InputDecoration(
                labelText: 'Sort By',
                prefixIcon: Icon(Icons.sort),
              ),
              items: const [
                DropdownMenuItem(
                    value: 'Name (A-Z)', child: Text('Name (A-Z)')),
                DropdownMenuItem(
                    value: 'Name (Z-A)', child: Text('Name (Z-A)')),
                DropdownMenuItem(
                    value: 'Created (Newest)', child: Text('Created (Newest)')),
                DropdownMenuItem(
                    value: 'Created (Oldest)', child: Text('Created (Oldest)')),
                DropdownMenuItem(
                    value: 'Role (A-Z)', child: Text('Role (A-Z)')),
                DropdownMenuItem(
                    value: 'Login Count (High-Low)',
                    child: Text('Login Count (High-Low)')),
                DropdownMenuItem(
                    value: 'Login Count (Low-High)',
                    child: Text('Login Count (Low-High)')),
              ],
              onChanged: (v) {
                if (v == null) {
                  return;
                }
                setState(() {
                  _sortBy = v;
                });
              },
            ),
          ),
          const SizedBox(height: 8),
          _AnimatedFadeSlide(
            delayMs: 300,
            child: Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                FilterChip(
                  selected: _adminsOnly,
                  label: const Text('Admins only'),
                  onSelected: (v) => setState(() => _adminsOnly = v),
                ),
                FilterChip(
                  selected: _recentOnly,
                  label: const Text('Created timestamp available'),
                  onSelected: (v) => setState(() => _recentOnly = v),
                ),
                FilterChip(
                  selected: _denseMode,
                  label: const Text('Dense mode'),
                  onSelected: (v) => setState(() => _denseMode = v),
                ),
                FilterChip(
                  selected: _gridMode,
                  label: const Text('Grid mode'),
                  onSelected: (v) => setState(() => _gridMode = v),
                ),
              ],
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Showing ${filtered.length} of ${_users.length} users',
            style: const TextStyle(
                color: Color(0xFFAFC4E9), fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 8),
          if (filtered.isEmpty)
            const Card(
              child: Padding(
                padding: EdgeInsets.all(16),
                child: Text('No users found with current filters.'),
              ),
            )
          else if (_gridMode)
            GridView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: filtered.length,
              gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: 2,
                mainAxisSpacing: 8,
                crossAxisSpacing: 8,
                childAspectRatio: 1.45,
              ),
              itemBuilder: (context, index) =>
                  _buildUserCard(filtered[index], index: index),
            )
          else
            ...filtered.asMap().entries.map(
                  (entry) => _buildUserCard(entry.value, index: entry.key),
                ),
          const SizedBox(height: 8),
          FilledButton.icon(
            onPressed: () {
              setState(() {
                _loading = true;
                _error = '';
              });
              _load();
            },
            icon: const Icon(Icons.refresh),
            label: const Text('Reload Users'),
          ),
        ],
      ),
    );
  }
}

class FaceSearchPage extends StatefulWidget {
  const FaceSearchPage({super.key});

  @override
  State<FaceSearchPage> createState() => _FaceSearchPageState();
}

class _FaceSearchPageState extends State<FaceSearchPage> {
  final _q = TextEditingController();
  List<String> _names = [];
  List<String> _filtered = [];
  String _status = 'Loading...';

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _q.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final api = buildBackendApi();
      final users = await api.getUsers(limit: 500);
      final data = (users['data'] as List?) ?? const [];
      final names = data
          .map((e) => (e as Map<String, dynamic>)['username']?.toString() ?? '')
          .where((e) => e.isNotEmpty)
          .toSet()
          .toList()
        ..sort();
      setState(() {
        _names = names;
        _filtered = names;
        _status = 'Loaded ${names.length} names';
      });
    } catch (e) {
      setState(() => _status = 'Search load error: $e');
    }
  }

  void _apply() {
    final q = _q.text.trim().toLowerCase();
    setState(() {
      _filtered = q.isEmpty
          ? _names
          : _names.where((n) => n.toLowerCase().contains(q)).toList();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Face Search')),
      body: ListView(
        padding: const EdgeInsets.all(12),
        children: [
          TextField(
            controller: _q,
            onChanged: (_) => _apply(),
            decoration: const InputDecoration(labelText: 'Search by name'),
          ),
          const SizedBox(height: 8),
          Text('Status: $_status'),
          const SizedBox(height: 8),
          ..._filtered.map((n) => Card(child: ListTile(title: Text(n)))),
        ],
      ),
    );
  }
}

class FaceStatsPage extends StatefulWidget {
  const FaceStatsPage({super.key});

  @override
  State<FaceStatsPage> createState() => _FaceStatsPageState();
}

class RecognitionLocationPage extends StatefulWidget {
  const RecognitionLocationPage({super.key});

  @override
  State<RecognitionLocationPage> createState() =>
      _RecognitionLocationPageState();
}

class _RecognitionLocationPageState extends State<RecognitionLocationPage> {
  final TextEditingController _nameController = TextEditingController();
  late final WebViewController _mapController;
  late final List<String> _mapCandidates;
  final Set<Factory<OneSequenceGestureRecognizer>> _mapGestures = {
    Factory<OneSequenceGestureRecognizer>(() => EagerGestureRecognizer()),
  };
  int _mapIndex = 0;
  bool _loading = false;
  bool _mapLoading = true;
  String _mapError = '';
  String _status = 'Search a recognized name to view recognition places';
  List<Map<String, dynamic>> _rows = const [];

  String _osmExactLocationUrl(double lat, double lng) {
    final latText = lat.toStringAsFixed(6);
    final lngText = lng.toStringAsFixed(6);
    return 'https://www.openstreetmap.org/?mlat=$latText&mlon=$lngText#map=18/$latText/$lngText';
  }

  @override
  void initState() {
    super.initState();
    final base = buildBackendApi().baseUrl;
    _mapCandidates = [
      '$base/api/map/view',
      'https://www.openstreetmap.org/#map=2/20.0/0.0',
    ];
    _mapController = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setBackgroundColor(const Color(0x00000000))
      ..setNavigationDelegate(
        NavigationDelegate(
          onPageStarted: (_) {
            if (!mounted) {
              return;
            }
            setState(() {
              _mapLoading = true;
              _mapError = '';
            });
          },
          onPageFinished: (_) {
            if (!mounted) {
              return;
            }
            setState(() {
              _mapLoading = false;
            });
          },
          onWebResourceError: (error) {
            if (!mounted) {
              return;
            }
            if (_mapIndex + 1 < _mapCandidates.length) {
              _mapIndex += 1;
              _mapController.loadRequest(Uri.parse(_mapCandidates[_mapIndex]));
              return;
            }
            setState(() {
              _mapLoading = false;
              _mapError = error.description;
            });
          },
        ),
      )
      ..loadRequest(Uri.parse(_mapCandidates[_mapIndex]));
  }

  @override
  void dispose() {
    _nameController.dispose();
    super.dispose();
  }

  Future<void> _search() async {
    final query = _nameController.text.trim();
    if (query.isEmpty) {
      setState(() => _status = 'Enter a name first');
      return;
    }
    setState(() {
      _loading = true;
      _status = 'Searching recognition places...';
      _rows = const [];
    });
    try {
      final api = buildBackendApi();
      final res = await api.searchRecognitionLocations(
        name: query,
        limit: 200,
      );
      if (!mounted) {
        return;
      }
      if (res['ok'] != true) {
        setState(() {
          _loading = false;
          _status = (res['error'] ?? 'Search failed').toString();
        });
        return;
      }
      final data = ((res['data'] as List?) ?? const [])
          .whereType<Map>()
          .map((e) => Map<String, dynamic>.from(e))
          .toList();
      setState(() {
        _loading = false;
        _rows = data;
        _status = data.isEmpty
            ? 'No recognition location found for "$query"'
            : 'Showing latest saved location for "$query"';
      });
    } catch (e) {
      if (!mounted) {
        return;
      }
      setState(() {
        _loading = false;
        _status = 'Search error: $e';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final viewportH = MediaQuery.of(context).size.height;
    final mapHeight = (viewportH * 0.52).clamp(320.0, 640.0).toDouble();

    return Scaffold(
      appBar: AppBar(title: const Text('Recognition Map')),
      body: ListView(
        padding: const EdgeInsets.all(12),
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(14),
              gradient: const LinearGradient(
                colors: [Color(0xFF2C5B83), Color(0xFF1B2740)],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              border: Border.all(color: const Color(0xFF4F6994), width: 1),
            ),
            child: Row(
              children: [
                const Icon(Icons.public, color: Color(0xFFBDE0FE)),
                const SizedBox(width: 8),
                const Expanded(
                  child: Text(
                    'Interactive World Map',
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 19,
                      color: Colors.white,
                    ),
                  ),
                ),
                OutlinedButton.icon(
                  onPressed: () {
                    _mapIndex = 0;
                    _mapController
                        .loadRequest(Uri.parse(_mapCandidates[_mapIndex]));
                  },
                  style: OutlinedButton.styleFrom(
                    foregroundColor: Colors.white,
                    side: const BorderSide(color: Color(0xFF95B7E2)),
                  ),
                  icon: const Icon(Icons.refresh, size: 16),
                  label: const Text('Reload'),
                ),
                const SizedBox(width: 8),
                OutlinedButton.icon(
                  onPressed: () {
                    Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (_) => FullScreenMapPage(
                          mapCandidates: _mapCandidates,
                          initialIndex: _mapIndex,
                        ),
                      ),
                    );
                  },
                  style: OutlinedButton.styleFrom(
                    foregroundColor: Colors.white,
                    side: const BorderSide(color: Color(0xFF95B7E2)),
                  ),
                  icon: const Icon(Icons.fullscreen, size: 16),
                  label: const Text('Full'),
                ),
              ],
            ),
          ),
          const SizedBox(height: 8),
          Container(
            height: mapHeight,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: const Color(0xFF4B5E8A), width: 1.2),
              color: const Color(0xFF0F1728),
              boxShadow: const [
                BoxShadow(
                  color: Color(0x66000000),
                  blurRadius: 16,
                  offset: Offset(0, 8),
                ),
              ],
            ),
            clipBehavior: Clip.antiAlias,
            child: Stack(
              children: [
                Positioned.fill(
                  child: WebViewWidget(
                    controller: _mapController,
                    gestureRecognizers: _mapGestures,
                  ),
                ),
                Positioned(
                  left: 10,
                  top: 10,
                  child: Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    decoration: BoxDecoration(
                      color: const Color(0xCC0D1526),
                      borderRadius: BorderRadius.circular(999),
                      border: Border.all(color: const Color(0xFF4F6994)),
                    ),
                    child: const Text(
                      'Map from map.py',
                      style: TextStyle(
                        color: Color(0xFFD7E7FF),
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ),
                if (_mapLoading)
                  const Positioned.fill(
                    child: Center(child: CircularProgressIndicator()),
                  ),
                if (_mapError.isNotEmpty)
                  Positioned.fill(
                    child: Container(
                      color: const Color(0xCC11182A),
                      alignment: Alignment.center,
                      padding: const EdgeInsets.all(12),
                      child: Text(
                        'Map load error: $_mapError',
                        textAlign: TextAlign.center,
                        style: const TextStyle(color: Colors.white),
                      ),
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(height: 8),
          const Text(
            'Use two fingers to zoom and pan around the world map, like Google Maps on Android.',
            style: TextStyle(color: Color(0xFFCCE3FF)),
          ),
          const SizedBox(height: 10),
          Container(
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0xFF254D70), Color(0xFF131F3A)],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: const Color(0xFF4B5E8A)),
            ),
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'World Recognition Locator',
                  style: TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 18,
                      color: Colors.white),
                ),
                const SizedBox(height: 6),
                const Text(
                  'Search any recognized user and view where their face was detected.',
                  style: TextStyle(color: Color(0xFFDAE6FF)),
                ),
                const SizedBox(height: 10),
                TextField(
                  controller: _nameController,
                  textInputAction: TextInputAction.search,
                  onSubmitted: (_) => _search(),
                  decoration: InputDecoration(
                    labelText: 'Recognized Name',
                    prefixIcon: const Icon(Icons.search),
                    suffixIcon: IconButton(
                      onPressed: _loading ? null : _search,
                      icon: const Icon(Icons.travel_explore),
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Container(
                width: 10,
                height: 10,
                decoration: const BoxDecoration(
                    color: Color(0xFF4ADE80), shape: BoxShape.circle),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  _status,
                  style: const TextStyle(
                    color: Color(0xFFCCE3FF),
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          if (_loading) const Center(child: CircularProgressIndicator()),
          ..._rows.map((row) {
            final location = (row['location_name'] ?? '-').toString();
            final when = (row['event_time'] ?? '-').toString();
            final lat = row['latitude'];
            final lng = row['longitude'];
            final conf =
                double.tryParse((row['confidence'] ?? 0).toString()) ?? 0.0;
            return Card(
              margin: const EdgeInsets.only(bottom: 8),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(14),
                side: const BorderSide(color: Color(0xFF3E527D)),
              ),
              child: InkWell(
                borderRadius: BorderRadius.circular(14),
                onTap: () {
                  final latNum = double.tryParse((lat ?? '').toString());
                  final lngNum = double.tryParse((lng ?? '').toString());
                  if (latNum == null || lngNum == null) {
                    setState(() {
                      _status = 'Selected location has no valid coordinates';
                    });
                    return;
                  }
                  final exactUrl = _osmExactLocationUrl(latNum, lngNum);
                  Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) => FullScreenMapPage(
                        mapCandidates: [exactUrl, ..._mapCandidates],
                        initialIndex: 0,
                      ),
                    ),
                  );
                },
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          const Icon(Icons.location_on,
                              color: Color(0xFFFF7D7D)),
                          const SizedBox(width: 6),
                          Expanded(
                            child: Text(
                              location,
                              style: const TextStyle(
                                  fontWeight: FontWeight.bold,
                                  color: Colors.white),
                            ),
                          ),
                          Text(
                            '${(conf * 100).toStringAsFixed(1)}%',
                            style: const TextStyle(
                                color: Color(0xFFA8D5FF),
                                fontWeight: FontWeight.w700),
                          ),
                        ],
                      ),
                      const SizedBox(height: 6),
                      Row(
                        children: [
                          const Icon(Icons.schedule,
                              size: 15, color: Color(0xFFB8CAE8)),
                          const SizedBox(width: 6),
                          Expanded(
                            child: Text('Time: $when',
                                style:
                                    const TextStyle(color: Color(0xFFD3DDF2))),
                          ),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Text('Coordinates: ${lat ?? '-'}, ${lng ?? '-'}',
                          style: const TextStyle(color: Color(0xFFAABCE2))),
                    ],
                  ),
                ),
              ),
            );
          }),
        ],
      ),
    );
  }
}

class _FaceStatsPageState extends State<FaceStatsPage> {
  bool _loading = true;
  String _error = '';
  Map<String, dynamic> _stats = const {};

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final api = buildBackendApi();
      final stats = await api.getStats();
      setState(() {
        _stats = (stats['data'] as Map<String, dynamic>?) ?? const {};
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _error = 'Stats load error: $e';
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    return Scaffold(
      appBar: AppBar(title: const Text('Face Stats')),
      body: ListView(
        padding: const EdgeInsets.all(12),
        children: [
          if (_error.isNotEmpty)
            Card(
              color: const Color(0xFF5C1A1A),
              child: Padding(
                padding: const EdgeInsets.all(12),
                child:
                    Text(_error, style: const TextStyle(color: Colors.white)),
              ),
            ),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _metricCard('Users', '${_stats['users'] ?? 0}'),
              _metricCard('Face Events', '${_stats['face_events'] ?? 0}'),
              _metricCard('Attendance', '${_stats['attendance_entries'] ?? 0}'),
              _metricCard('Activity', '${_stats['activity_events'] ?? 0}'),
            ],
          ),
        ],
      ),
    );
  }

  Widget _metricCard(String title, String value) {
    return SizedBox(
      width: 165,
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title,
                  style: const TextStyle(fontSize: 12, color: Colors.grey)),
              const SizedBox(height: 6),
              Text(value,
                  style: const TextStyle(
                      fontSize: 22, fontWeight: FontWeight.bold)),
            ],
          ),
        ),
      ),
    );
  }
}

class AnalyticsPage extends StatefulWidget {
  const AnalyticsPage({super.key});

  @override
  State<AnalyticsPage> createState() => _AnalyticsPageState();
}

class _AnalyticsPageState extends State<AnalyticsPage> {
  bool _loading = true;
  String _error = '';
  Map<String, dynamic> _stats = const {};
  List<Map<String, dynamic>> _activity = const [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final api = buildBackendApi();
      final stats = await api.getStats();
      final activity = await api.getActivity(limit: 100);
      setState(() {
        _stats = (stats['data'] as Map<String, dynamic>?) ?? const {};
        _activity = ((activity['data'] as List?) ?? const [])
            .whereType<Map>()
            .map((e) => Map<String, dynamic>.from(e))
            .toList();
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _error = 'Analytics load error: $e';
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    final users = (_stats['users'] ?? 0).toString();
    final events = (_stats['face_events'] ?? 0).toString();
    final pending = (_stats['pending_approvals'] ?? 0).toString();
    final db = '${_stats['db_size_mb'] ?? 0} MB';
    return Scaffold(
      appBar: AppBar(title: const Text('Analytics Dashboard')),
      body: ListView(
        padding: const EdgeInsets.all(12),
        children: [
          if (_error.isNotEmpty)
            Card(
              color: const Color(0xFF5C1A1A),
              child: Padding(
                padding: const EdgeInsets.all(12),
                child:
                    Text(_error, style: const TextStyle(color: Colors.white)),
              ),
            ),
          _AnimatedFadeSlide(
            delayMs: 120,
            child: Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(16),
                gradient: const LinearGradient(
                  colors: [Color(0xFF214A72), Color(0xFF1A2A46)],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                border: Border.all(color: const Color(0xFF47678F)),
              ),
              child: const Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Analytics Snapshot',
                    style: TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.w900,
                      fontSize: 19,
                    ),
                  ),
                  SizedBox(height: 6),
                  Text(
                    'System performance, user volume and recognition momentum.',
                    style: TextStyle(color: Color(0xFFC8DCF5)),
                  ),
                  SizedBox(height: 10),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      _SectionBadge(
                        icon: Icons.bolt,
                        label: 'Live telemetry',
                        tint: Color(0xFF7EE3FF),
                      ),
                      _SectionBadge(
                        icon: Icons.auto_graph,
                        label: 'Auto-updated',
                        tint: Color(0xFFFFC67F),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 10),
          _AnimatedFadeSlide(
            delayMs: 200,
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  _KpiTile(
                    title: 'Registered Users',
                    value: users,
                    tint: const Color(0xFF76DAFF),
                    icon: Icons.people_alt,
                  ),
                  const SizedBox(width: 8),
                  _KpiTile(
                    title: 'Face Events',
                    value: events,
                    tint: const Color(0xFFFFCD8B),
                    icon: Icons.face_retouching_natural,
                  ),
                  const SizedBox(width: 8),
                  _KpiTile(
                    title: 'Pending Approvals',
                    value: pending,
                    tint: const Color(0xFFB9B9FF),
                    icon: Icons.pending_actions,
                  ),
                  const SizedBox(width: 8),
                  _KpiTile(
                    title: 'Database Size',
                    value: db,
                    tint: const Color(0xFF96FFBC),
                    icon: Icons.storage,
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 8),
          const Text('Activity Timeline',
              style: TextStyle(fontWeight: FontWeight.bold)),
          const SizedBox(height: 6),
          ..._activity.take(40).toList().asMap().entries.map((entry) {
            final i = entry.key;
            final a = entry.value;
            return _AnimatedFadeSlide(
              delayMs: 300 + (i * 30),
              child: _TimelineActivityTile(
                title: (a['action'] ?? '-').toString(),
                subtitle:
                    '${a['username'] ?? '-'} (${a['role'] ?? '-'}) - ${a['detail'] ?? ''}',
                trailing: (a['event_time'] ?? '').toString(),
              ),
            );
          }),
        ],
      ),
    );
  }
}

class ServicesHubPage extends StatefulWidget {
  const ServicesHubPage({super.key});

  @override
  State<ServicesHubPage> createState() => _ServicesHubPageState();
}

class _ServicesHubPageState extends State<ServicesHubPage> {
  bool _loading = true;
  String _error = '';
  Map<String, dynamic> _health = const {};
  Map<String, dynamic> _docs = const {};
  final TextEditingController _endpointSearch = TextEditingController();
  bool _showPublic = true;
  bool _showSecure = true;
  bool _showMethods = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _endpointSearch.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final api = buildBackendApi();
      final health = await api.getHealth();
      final docs = await api.getDocs();
      setState(() {
        _health = health;
        _docs = docs;
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _error = 'Services load error: $e';
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    final docData = (_docs['data'] as Map<String, dynamic>?) ?? const {};
    final publicEndpoints = ((docData['public_endpoints'] as List?) ?? const [])
        .whereType<Map>()
        .map((e) => Map<String, dynamic>.from(e))
        .toList();
    final secureEndpoints = ((docData['secure_endpoints'] as List?) ?? const [])
        .whereType<Map>()
        .map((e) => Map<String, dynamic>.from(e))
        .toList();
    final query = _endpointSearch.text.trim().toLowerCase();
    final filteredPublic = publicEndpoints.where((e) {
      final path = (e['path'] ?? '').toString().toLowerCase();
      final method = (e['method'] ?? '').toString().toLowerCase();
      return query.isEmpty || path.contains(query) || method.contains(query);
    }).toList();
    final filteredSecure = secureEndpoints.where((e) {
      final path = (e['path'] ?? '').toString().toLowerCase();
      final method = (e['method'] ?? '').toString().toLowerCase();
      return query.isEmpty || path.contains(query) || method.contains(query);
    }).toList();
    final totalVisible = (_showPublic ? filteredPublic.length : 0) +
        (_showSecure ? filteredSecure.length : 0);

    Future<void> copyCatalog() async {
      final lines = <String>[
        'Face Studio Services Catalog',
        'Public endpoints: ${publicEndpoints.length}',
        'Secure endpoints: ${secureEndpoints.length}',
        'Visible endpoints: $totalVisible',
      ];
      for (final item in filteredPublic) {
        lines.add('PUBLIC ${item['method'] ?? 'GET'} ${item['path'] ?? ''}');
      }
      for (final item in filteredSecure) {
        lines.add('SECURE ${item['method'] ?? 'GET'} ${item['path'] ?? ''}');
      }
      await Clipboard.setData(ClipboardData(text: lines.join('\n')));
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Endpoint catalog copied')),
      );
    }

    return Scaffold(
      appBar: AppBar(title: const Text('Services Hub')),
      body: ListView(
        padding: const EdgeInsets.all(12),
        children: [
          if (_error.isNotEmpty)
            Card(
              color: const Color(0xFF5C1A1A),
              child: Padding(
                padding: const EdgeInsets.all(12),
                child:
                    Text(_error, style: const TextStyle(color: Colors.white)),
              ),
            ),
          _AnimatedFadeSlide(
            delayMs: 120,
            child: Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(14),
                gradient: const LinearGradient(
                  colors: [Color(0xFF27466D), Color(0xFF192740)],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                border: Border.all(color: const Color(0xFF4A668B)),
              ),
              child: Row(
                children: [
                  Icon(
                    _health['ok'] == true ? Icons.check_circle : Icons.error,
                    color: _health['ok'] == true
                        ? Colors.greenAccent
                        : Colors.redAccent,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      _health['ok'] == true ? 'API Healthy' : 'API Unhealthy',
                      style: const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w900,
                        fontSize: 18,
                      ),
                    ),
                  ),
                  IconButton(
                    onPressed: copyCatalog,
                    icon: const Icon(Icons.copy_all),
                    tooltip: 'Copy endpoint catalog',
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 8),
          _AnimatedFadeSlide(
            delayMs: 170,
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  _KpiTile(
                    title: 'Public',
                    value: '${publicEndpoints.length}',
                    tint: const Color(0xFF84D4FF),
                    icon: Icons.public,
                  ),
                  const SizedBox(width: 8),
                  _KpiTile(
                    title: 'Secure',
                    value: '${secureEndpoints.length}',
                    tint: const Color(0xFFFFCF90),
                    icon: Icons.lock,
                  ),
                  const SizedBox(width: 8),
                  _KpiTile(
                    title: 'Visible',
                    value: '$totalVisible',
                    tint: const Color(0xFFAFC2FF),
                    icon: Icons.visibility,
                  ),
                  const SizedBox(width: 8),
                  _KpiTile(
                    title: 'Server Time',
                    value: (_health['time'] ?? '-').toString(),
                    tint: const Color(0xFF97F3C0),
                    icon: Icons.schedule,
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 8),
          _AnimatedFadeSlide(
            delayMs: 210,
            child: TextField(
              controller: _endpointSearch,
              onChanged: (_) => setState(() {}),
              decoration: InputDecoration(
                labelText: 'Search endpoint path or method',
                prefixIcon: const Icon(Icons.search),
                suffixIcon: _endpointSearch.text.isEmpty
                    ? null
                    : IconButton(
                        onPressed: () {
                          _endpointSearch.clear();
                          setState(() {});
                        },
                        icon: const Icon(Icons.clear),
                      ),
              ),
            ),
          ),
          const SizedBox(height: 8),
          _AnimatedFadeSlide(
            delayMs: 240,
            child: Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                FilterChip(
                  selected: _showPublic,
                  label: const Text('Show Public'),
                  onSelected: (v) => setState(() => _showPublic = v),
                ),
                FilterChip(
                  selected: _showSecure,
                  label: const Text('Show Secure'),
                  onSelected: (v) => setState(() => _showSecure = v),
                ),
                FilterChip(
                  selected: _showMethods,
                  label: const Text('Show HTTP Method'),
                  onSelected: (v) => setState(() => _showMethods = v),
                ),
              ],
            ),
          ),
          if (_showPublic) ...[
            const SizedBox(height: 8),
            const _SectionTitle('Public Endpoints'),
            ...filteredPublic.asMap().entries.map((entry) {
              final i = entry.key;
              final e = entry.value;
              return _AnimatedFadeSlide(
                delayMs: 280 + (i * 18),
                child: Card(
                  child: ListTile(
                    leading: _showMethods
                        ? _MethodBadge((e['method'] ?? 'GET').toString())
                        : const Icon(Icons.link),
                    title: Text((e['path'] ?? '').toString()),
                    trailing: IconButton(
                      icon: const Icon(Icons.copy),
                      onPressed: () async {
                        await Clipboard.setData(
                          ClipboardData(text: (e['path'] ?? '').toString()),
                        );
                        if (!mounted) {
                          return;
                        }
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text('Path copied')),
                        );
                      },
                    ),
                  ),
                ),
              );
            }),
          ],
          if (_showSecure) ...[
            const SizedBox(height: 8),
            const _SectionTitle('Secure Endpoints'),
            ...filteredSecure.asMap().entries.map((entry) {
              final i = entry.key;
              final e = entry.value;
              return _AnimatedFadeSlide(
                delayMs: 310 + (i * 18),
                child: Card(
                  child: ListTile(
                    leading: _showMethods
                        ? _MethodBadge((e['method'] ?? 'GET').toString())
                        : const Icon(Icons.lock_outline),
                    title: Text((e['path'] ?? '').toString()),
                    trailing: IconButton(
                      icon: const Icon(Icons.copy),
                      onPressed: () async {
                        await Clipboard.setData(
                          ClipboardData(text: (e['path'] ?? '').toString()),
                        );
                        if (!mounted) {
                          return;
                        }
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text('Path copied')),
                        );
                      },
                    ),
                  ),
                ),
              );
            }),
          ],
          const SizedBox(height: 10),
          FilledButton.icon(
            onPressed: () {
              setState(() {
                _loading = true;
                _error = '';
              });
              _load();
            },
            icon: const Icon(Icons.refresh),
            label: const Text('Refresh Service Catalog'),
          ),
        ],
      ),
    );
  }
}

class _MethodBadge extends StatelessWidget {
  final String method;

  const _MethodBadge(this.method);

  @override
  Widget build(BuildContext context) {
    final upper = method.toUpperCase();
    final bg = switch (upper) {
      'POST' => const Color(0xFF7A3A2F),
      'PUT' => const Color(0xFF5F4C20),
      'PATCH' => const Color(0xFF61503A),
      'DELETE' => const Color(0xFF6A2933),
      _ => const Color(0xFF2B4A7C),
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Text(upper,
          style: const TextStyle(
              fontSize: 11, color: Colors.white, fontWeight: FontWeight.bold)),
    );
  }
}

class DatabaseBridgePage extends StatefulWidget {
  const DatabaseBridgePage({super.key});

  @override
  State<DatabaseBridgePage> createState() => _DatabaseBridgePageState();
}

class _DatabaseBridgePageState extends State<DatabaseBridgePage> {
  bool _loading = true;
  String _error = '';
  Map<String, dynamic> _db = const {};
  final TextEditingController _searchController = TextEditingController();
  String _sortBy = 'Rows (High-Low)';
  bool _onlyNonZero = false;
  bool _compactMode = false;
  Map<String, dynamic>? _selectedTable;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final api = buildBackendApi();
      final res = await api.getDbOverview();
      if (!mounted) return;
      if (res['ok'] != true) {
        setState(() {
          _error = (res['error'] ?? 'Unable to load DB overview').toString();
          _loading = false;
        });
        return;
      }
      setState(() {
        _db = (res['data'] as Map<String, dynamic>?) ?? const {};
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = 'Database bridge error: $e';
        _loading = false;
      });
    }
  }

  int _rowsCount(Map<String, dynamic> table) => (table['rows'] ?? 0) as int;

  List<Map<String, dynamic>> _filteredTables() {
    final tables = ((_db['tables'] as List?) ?? const [])
        .whereType<Map>()
        .map((e) => Map<String, dynamic>.from(e))
        .toList();
    final q = _searchController.text.trim().toLowerCase();
    final filtered = tables.where((t) {
      final name = (t['name'] ?? '').toString().toLowerCase();
      final rows = _rowsCount(t);
      final queryOk = q.isEmpty || name.contains(q);
      final nonZeroOk = !_onlyNonZero || rows > 0;
      return queryOk && nonZeroOk;
    }).toList();
    filtered.sort((a, b) {
      switch (_sortBy) {
        case 'Rows (Low-High)':
          return _rowsCount(a).compareTo(_rowsCount(b));
        case 'Name (A-Z)':
          return (a['name'] ?? '')
              .toString()
              .compareTo((b['name'] ?? '').toString());
        case 'Name (Z-A)':
          return (b['name'] ?? '')
              .toString()
              .compareTo((a['name'] ?? '').toString());
        default:
          return _rowsCount(b).compareTo(_rowsCount(a));
      }
    });
    return filtered;
  }

  Future<void> _copySummary(List<Map<String, dynamic>> rows) async {
    final totalRows = rows.fold<int>(0, (p, c) => p + _rowsCount(c));
    final lines = <String>[
      'Face Studio DB Snapshot',
      'DB: ${_db['db_path'] ?? '-'}',
      'Tables visible: ${rows.length}',
      'Total rows (visible): $totalRows',
      'Sort: $_sortBy',
      'Only non-zero: $_onlyNonZero',
    ];
    for (final t in rows.take(40)) {
      lines.add('${t['name'] ?? '-'} => ${_rowsCount(t)}');
    }
    await Clipboard.setData(ClipboardData(text: lines.join('\n')));
    if (!mounted) {
      return;
    }
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Database summary copied')),
    );
  }

  void _openTableSheet(Map<String, dynamic> table) {
    setState(() => _selectedTable = table);
    showModalBottomSheet<void>(
      context: context,
      backgroundColor: const Color(0xFF121C2E),
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(18)),
      ),
      builder: (context) {
        final name = (table['name'] ?? '-').toString();
        final rows = _rowsCount(table);
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 20),
            child: ListView(
              shrinkWrap: true,
              children: [
                Center(
                  child: Container(
                    width: 44,
                    height: 4,
                    decoration: BoxDecoration(
                      color: const Color(0xFF475F85),
                      borderRadius: BorderRadius.circular(999),
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  name,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 21,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: 8),
                _ProfileFieldTile(
                    label: 'Rows', value: '$rows', icon: Icons.table_rows),
                _ProfileFieldTile(
                  label: 'Database File',
                  value: (_db['db_path'] ?? '-').toString(),
                  icon: Icons.storage,
                ),
                const SizedBox(height: 6),
                FilledButton.icon(
                  onPressed: () async {
                    await Clipboard.setData(ClipboardData(text: '$name:$rows'));
                    if (!context.mounted) {
                      return;
                    }
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Table row info copied')),
                    );
                  },
                  icon: const Icon(Icons.copy),
                  label: const Text('Copy Table Snapshot'),
                ),
              ],
            ),
          ),
        );
      },
    ).whenComplete(() {
      if (mounted) {
        setState(() => _selectedTable = null);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    final filtered = _filteredTables();
    final totalRowsVisible = filtered.fold<int>(0, (p, c) => p + _rowsCount(c));
    final maxTable = filtered.isEmpty
        ? null
        : filtered.reduce((a, b) => _rowsCount(a) >= _rowsCount(b) ? a : b);
    return Scaffold(
      appBar: AppBar(title: const Text('Database Bridge')),
      body: ListView(
        padding: const EdgeInsets.all(12),
        children: [
          if (_error.isNotEmpty)
            Card(
              color: const Color(0xFF5C1A1A),
              child: Padding(
                padding: const EdgeInsets.all(12),
                child:
                    Text(_error, style: const TextStyle(color: Colors.white)),
              ),
            ),
          _AnimatedFadeSlide(
            delayMs: 110,
            child: Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(14),
                gradient: const LinearGradient(
                  colors: [Color(0xFF2A466C), Color(0xFF1A273F)],
                ),
                border: Border.all(color: const Color(0xFF4C688D)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.storage_rounded, color: Color(0xFFBFE2FF)),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'DB File: ${_db['db_path'] ?? '-'}',
                      style: const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                  IconButton(
                    onPressed: () => _copySummary(filtered),
                    icon: const Icon(Icons.copy_all),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 8),
          _AnimatedFadeSlide(
            delayMs: 160,
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  _KpiTile(
                    title: 'Visible Tables',
                    value: '${filtered.length}',
                    tint: const Color(0xFF81D5FF),
                    icon: Icons.table_chart,
                  ),
                  const SizedBox(width: 8),
                  _KpiTile(
                    title: 'Total Rows',
                    value: '$totalRowsVisible',
                    tint: const Color(0xFFFFD08E),
                    icon: Icons.analytics,
                  ),
                  const SizedBox(width: 8),
                  _KpiTile(
                    title: 'Top Table',
                    value: maxTable == null
                        ? '-'
                        : (maxTable['name'] ?? '-').toString(),
                    tint: const Color(0xFFACC1FF),
                    icon: Icons.emoji_events,
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 8),
          _AnimatedFadeSlide(
            delayMs: 190,
            child: TextField(
              controller: _searchController,
              onChanged: (_) => setState(() {}),
              decoration: const InputDecoration(
                labelText: 'Search table',
                prefixIcon: Icon(Icons.search),
              ),
            ),
          ),
          const SizedBox(height: 8),
          _AnimatedFadeSlide(
            delayMs: 220,
            child: DropdownButtonFormField<String>(
              initialValue: _sortBy,
              decoration: const InputDecoration(
                labelText: 'Sort tables',
                prefixIcon: Icon(Icons.sort),
              ),
              items: const [
                DropdownMenuItem(
                    value: 'Rows (High-Low)', child: Text('Rows (High-Low)')),
                DropdownMenuItem(
                    value: 'Rows (Low-High)', child: Text('Rows (Low-High)')),
                DropdownMenuItem(
                    value: 'Name (A-Z)', child: Text('Name (A-Z)')),
                DropdownMenuItem(
                    value: 'Name (Z-A)', child: Text('Name (Z-A)')),
              ],
              onChanged: (v) {
                if (v == null) {
                  return;
                }
                setState(() {
                  _sortBy = v;
                });
              },
            ),
          ),
          const SizedBox(height: 8),
          _AnimatedFadeSlide(
            delayMs: 240,
            child: Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                FilterChip(
                  selected: _onlyNonZero,
                  label: const Text('Only non-zero tables'),
                  onSelected: (v) => setState(() => _onlyNonZero = v),
                ),
                FilterChip(
                  selected: _compactMode,
                  label: const Text('Compact mode'),
                  onSelected: (v) => setState(() => _compactMode = v),
                ),
              ],
            ),
          ),
          const SizedBox(height: 8),
          Text('Showing ${filtered.length} tables',
              style: const TextStyle(color: Color(0xFFAAB2D6))),
          const SizedBox(height: 6),
          ...filtered.asMap().entries.map((entry) {
            final i = entry.key;
            final t = entry.value;
            final name = (t['name'] ?? '-').toString();
            final rows = _rowsCount(t);
            final selected = identical(_selectedTable, t);
            return _AnimatedFadeSlide(
              delayMs: 270 + (i * 18),
              child: Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: InkWell(
                  borderRadius: BorderRadius.circular(12),
                  onTap: () => _openTableSheet(t),
                  child: Container(
                    padding: EdgeInsets.all(_compactMode ? 10 : 12),
                    decoration: BoxDecoration(
                      color: selected
                          ? const Color(0xFF1F3352)
                          : const Color(0xFF16253C),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                          color: const Color(0xFF395780),
                          width: selected ? 1.5 : 1),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.table_rows, color: Color(0xFFA4CBFF)),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            name,
                            style: const TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 10, vertical: 4),
                          decoration: BoxDecoration(
                            color: const Color(0xFF223753),
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: Text('Rows: $rows'),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            );
          }),
          const SizedBox(height: 10),
          FilledButton.icon(
            onPressed: () {
              setState(() {
                _loading = true;
                _error = '';
              });
              _load();
            },
            icon: const Icon(Icons.refresh),
            label: const Text('Refresh Database Snapshot'),
          ),
        ],
      ),
    );
  }
}

class AdminModulePage extends StatefulWidget {
  final String title;
  final String modulePath;
  final bool supportsExport;

  const AdminModulePage({
    super.key,
    required this.title,
    required this.modulePath,
    this.supportsExport = false,
  });

  @override
  State<AdminModulePage> createState() => _AdminModulePageState();
}

class _AdminModulePageState extends State<AdminModulePage> {
  bool _loading = true;
  String _error = '';
  Map<String, dynamic> _data = const {};
  String _actionResult = '';
  bool _showRaw = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final api = buildBackendApi();
      final res = await api.getAdminModule(widget.modulePath);
      if (!mounted) return;
      if (res['ok'] != true) {
        setState(() {
          _error = (res['error'] ?? 'Load failed').toString();
          _loading = false;
        });
        return;
      }
      setState(() {
        _data = (res['data'] as Map<String, dynamic>?) ?? const {};
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = '$e';
        _loading = false;
      });
    }
  }

  Future<void> _runAction(String actionPath, String successPrefix,
      {Map<String, dynamic>? payload}) async {
    final api = buildBackendApi();
    final res = await api.postAdminAction(actionPath, payload: payload);
    if (!mounted) return;
    if (res['ok'] == true) {
      setState(
          () => _actionResult = '$successPrefix: ${jsonEncode(res['data'])}');
      await _load();
    } else {
      setState(
          () => _actionResult = 'Action failed: ${res['error'] ?? 'Unknown'}');
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return Scaffold(
          appBar: AppBar(title: Text(widget.title)),
          body: const Center(child: CircularProgressIndicator()));
    }

    final stats = (_data['stats'] as Map<String, dynamic>?) ?? const {};
    final recent = ((_data['recent_activity'] as List?) ?? const [])
        .whereType<Map>()
        .map((e) => Map<String, dynamic>.from(e))
        .toList();
    final roleBreakdown =
        (_data['role_breakdown'] as Map<String, dynamic>?) ?? const {};
    final checks = (_data['checks'] as Map<String, dynamic>?) ?? const {};
    final services = (_data['services'] as Map<String, dynamic>?) ?? const {};
    final files = (_data['files'] as Map<String, dynamic>?) ?? const {};
    final db = (_data['db'] as Map<String, dynamic>?) ?? const {};
    final dbTables = ((db['tables'] as List?) ?? const [])
        .whereType<Map>()
        .map((e) => Map<String, dynamic>.from(e))
        .toList();
    final nextSteps = ((_data['next_steps'] as List?) ?? const [])
        .map((e) => e.toString())
        .toList();

    return Scaffold(
      appBar: AppBar(title: Text(widget.title)),
      body: ListView(
        padding: const EdgeInsets.all(12),
        children: [
          if (_error.isNotEmpty)
            Card(
              color: const Color(0xFF5C1A1A),
              child: Padding(
                padding: const EdgeInsets.all(12),
                child:
                    Text(_error, style: const TextStyle(color: Colors.white)),
              ),
            ),
          if (stats.isNotEmpty)
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                _metricCard('Users', '${stats['users'] ?? 0}'),
                _metricCard('Faces', '${stats['face_events'] ?? 0}'),
                _metricCard('Activity', '${stats['activity_events'] ?? 0}'),
                _metricCard('Pending', '${stats['pending_approvals'] ?? 0}'),
              ],
            ),
          if (roleBreakdown.isNotEmpty)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(10),
                child: Wrap(
                  spacing: 10,
                  runSpacing: 10,
                  children: roleBreakdown.entries
                      .map((e) => Chip(
                            backgroundColor: const Color(0xFF263655),
                            label: Text('${e.key}: ${e.value}',
                                style: const TextStyle(color: Colors.white)),
                          ))
                      .toList(),
                ),
              ),
            ),
          if (checks.isNotEmpty || services.isNotEmpty)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(10),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    if (checks.isNotEmpty) ...[
                      const _SectionTitle('Checks'),
                      const SizedBox(height: 6),
                      ...checks.entries
                          .map((e) => Text('${e.key}: ${e.value}')),
                    ],
                    if (services.isNotEmpty) ...[
                      const SizedBox(height: 10),
                      const _SectionTitle('Services'),
                      const SizedBox(height: 6),
                      ...services.entries
                          .map((e) => Text('${e.key}: ${e.value}')),
                    ],
                  ],
                ),
              ),
            ),
          if (files.isNotEmpty)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(10),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const _SectionTitle('Artifacts'),
                    const SizedBox(height: 6),
                    ...files.entries.map((e) {
                      final f = (e.value as Map?) ?? const {};
                      final exists = f['exists'] == true;
                      return ListTile(
                        dense: true,
                        contentPadding: EdgeInsets.zero,
                        leading: Icon(
                            exists ? Icons.check_circle : Icons.error_outline,
                            color: exists ? Colors.green : Colors.orange),
                        title: Text(e.key),
                        subtitle: Text((f['path'] ?? '-').toString()),
                      );
                    }),
                  ],
                ),
              ),
            ),
          if (nextSteps.isNotEmpty)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(10),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const _SectionTitle('Next Steps'),
                    const SizedBox(height: 6),
                    ...nextSteps.map((s) => ListTile(
                          dense: true,
                          contentPadding: EdgeInsets.zero,
                          leading: const Icon(Icons.arrow_right),
                          title: Text(s),
                        )),
                  ],
                ),
              ),
            ),
          if (db.isNotEmpty)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(10),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Database: ${db['db_path'] ?? '-'}'),
                    Text('Size: ${db['db_size_mb'] ?? 0} MB'),
                    if (dbTables.isNotEmpty) ...[
                      const SizedBox(height: 6),
                      Text('Tables tracked: ${dbTables.length}'),
                    ],
                  ],
                ),
              ),
            ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              FilledButton.icon(
                onPressed: () {
                  setState(() {
                    _loading = true;
                    _error = '';
                  });
                  _load();
                },
                icon: const Icon(Icons.refresh),
                label: const Text('Refresh'),
              ),
              FilledButton.icon(
                onPressed: () =>
                    _runAction('/api/admin/backup/now', 'Backup created'),
                icon: const Icon(Icons.backup),
                label: const Text('Backup Now'),
              ),
              FilledButton.icon(
                onPressed: () => _runAction(
                    '/api/admin/scheduler/start', 'Scheduler started',
                    payload: {'interval_minutes': 1440}),
                icon: const Icon(Icons.play_circle_fill),
                label: const Text('Start Scheduler'),
              ),
              FilledButton.icon(
                onPressed: () => _runAction(
                    '/api/admin/scheduler/stop', 'Scheduler stopped'),
                icon: const Icon(Icons.stop_circle),
                label: const Text('Stop Scheduler'),
              ),
              if (widget.supportsExport)
                FilledButton.icon(
                  onPressed: () => _runAction(
                      '/api/admin/evaluator-bundle/export', 'Bundle exported'),
                  icon: const Icon(Icons.folder_zip),
                  label: const Text('Export Bundle'),
                ),
            ],
          ),
          if (_actionResult.isNotEmpty) ...[
            const SizedBox(height: 8),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(10),
                child: SelectableText(_actionResult),
              ),
            ),
          ],
          const SizedBox(height: 8),
          _AdminRunbookPanel(data: _data),
          const SizedBox(height: 8),
          SwitchListTile(
            value: _showRaw,
            onChanged: (v) => setState(() => _showRaw = v),
            title: const Text('Show raw debug JSON'),
          ),
          if (_showRaw)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(10),
                child: SelectableText(
                    const JsonEncoder.withIndent('  ').convert(_data)),
              ),
            ),
          if (recent.isNotEmpty) ...[
            const SizedBox(height: 10),
            const _SectionTitle('Recent Activity'),
            const SizedBox(height: 6),
            ...recent.take(15).map(
                  (a) => Card(
                    child: ListTile(
                      title: Text((a['action'] ?? '-').toString()),
                      subtitle: Text((a['detail'] ?? '').toString()),
                      trailing: Text((a['event_time'] ?? '').toString(),
                          style: const TextStyle(fontSize: 11)),
                    ),
                  ),
                ),
          ],
        ],
      ),
    );
  }

  Widget _metricCard(String title, String value) {
    return SizedBox(
      width: 150,
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(10),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title,
                  style:
                      const TextStyle(color: Color(0xFFAAB2D6), fontSize: 12)),
              const SizedBox(height: 4),
              Text(value,
                  style: const TextStyle(
                      fontSize: 20, fontWeight: FontWeight.bold)),
            ],
          ),
        ),
      ),
    );
  }
}

class SystemInfoPage extends StatefulWidget {
  const SystemInfoPage({super.key});

  @override
  State<SystemInfoPage> createState() => _SystemInfoPageState();
}

class _SystemInfoPageState extends State<SystemInfoPage> {
  String get _baseUrl => buildBackendApi().baseUrl;
  List<Map<String, String>> _rows = [];
  String _error = '';
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final api = buildBackendApi();
      final ok = await api.ensureToken();
      if (!ok || api.token.isEmpty) {
        setState(() {
          _loading = false;
          _error = 'Login required for system info';
        });
        return;
      }
      final b = _baseUrl.trim().replaceAll(RegExp(r'/$'), '');
      final infoRes = await http.get(
        Uri.parse('$b/api/system-info'),
        headers: {'Authorization': 'Bearer ${api.token}'},
      );
      if (infoRes.statusCode != 200) {
        setState(() {
          _loading = false;
          _error = 'System info request failed: ${infoRes.statusCode}';
        });
        return;
      }
      final body = jsonDecode(infoRes.body) as Map<String, dynamic>;
      final data = (body['data'] as Map<String, dynamic>?) ?? const {};
      final rowsRaw = (data['rows'] as List?) ?? const [];
      final rows = rowsRaw
          .whereType<Map>()
          .map((e) => Map<String, String>.from({
                'label': (e['label'] ?? '').toString(),
                'value': (e['value'] ?? '').toString(),
              }))
          .toList();
      setState(() {
        _rows = rows;
        _error = '';
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _loading = false;
        _error = 'System info error: $e';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final uptimeRow = _rows.firstWhere(
      (row) => (row['label'] ?? '').toLowerCase().contains('uptime'),
      orElse: () => const {'label': 'Uptime', 'value': 'n/a'},
    );
    final envRow = _rows.firstWhere(
      (row) => (row['label'] ?? '').toLowerCase().contains('environment'),
      orElse: () => const {'label': 'Environment', 'value': 'production'},
    );
    return Scaffold(
      appBar: AppBar(title: const Text('System Info')),
      body: ListView(
        padding: const EdgeInsets.all(12),
        children: [
          if (_loading)
            const Center(child: CircularProgressIndicator())
          else if (_error.isNotEmpty)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(10),
                child: Text(_error),
              ),
            )
          else
            Card(
              child: Column(
                children: _rows
                    .map(
                      (row) => ListTile(
                        dense: true,
                        title: Text(
                          row['label'] ?? '',
                          style: const TextStyle(color: _kTextMuted),
                        ),
                        trailing: Text(
                          row['value'] ?? '',
                          style: const TextStyle(fontWeight: FontWeight.w700),
                        ),
                      ),
                    )
                    .toList(),
              ),
            ),
        ],
      ),
    );
  }
}

class HelpAboutPage extends StatelessWidget {
  const HelpAboutPage({super.key});

  static const String _helpText = 'ðŸ§‘ FACE STUDIO â€” Help & Documentation\n'
      '========================================\n\n'
      'OVERVIEW\n'
      '--------\n'
      'Face Studio is a comprehensive face recognition and management application\n'
      'built with Python, OpenCV (YuNet + SFace), and Tkinter.\n\n'
      'FEATURES FOR ALL USERS:\n'
      'â€¢ Face Recognition â€” Real-time webcam face identification\n'
      'â€¢ Face Generation â€” Create stylized images (Sketch, Cartoon, Ghibli, etc.)\n'
      'â€¢ Face Comparison â€” Compare two images for similarity\n'
      'â€¢ Batch Processing â€” Process multiple images at once\n'
      'â€¢ Image Enhancement â€” Improve photo quality with various tools\n'
      'â€¢ Face Search â€” Find a person across all stored images\n'
      'â€¢ User Profile â€” View account info, change password\n\n'
      'KEYBOARD SHORTCUTS:\n'
      'â€¢ ESC â€” Return to home page (from webcam modes)\n'
      'â€¢ Q â€” Save and quit attendance mode\n'
      'â€¢ S â€” Take screenshot (during webcam recognition)\n\n'
      'RECOGNITION ENGINE:\n'
      'â€¢ Detection: OpenCV YuNet (ONNX) â€” ~33ms per frame\n'
      'â€¢ Encoding: OpenCV SFace (ONNX) â€” ~48ms per face\n'
      'â€¢ Matching: Cosine Similarity (threshold: 0.363)\n'
      'â€¢ Tracking: IoU-based FaceTracker with exponential smoothing\n\n'
      'ARTISTIC FILTERS (16):\n'
      'Sketch, Cartoon, Oil Painting, HDR, Ghibli Art, Anime, Ghost,\n'
      'Emboss, Watercolor, Pop Art, Neon Glow, Vintage, Pixel Art,\n'
      'Thermal, Glitch, Pencil Color\n\n'
      'REQUIREMENTS:\n'
      'pip install opencv-python opencv-contrib-python numpy pillow\n'
      's\n'
      'CREDITS:\n'
      'â€¢ OpenCV Team â€” YuNet & SFace models\n'
      'â€¢ Python / Tkinter â€” GUI framework\n'
      'â€¢ NumPy â€” Numerical computing\n\n'
      'For more information please contact facestudio4@gmail.com\n\n'
      'VERSION: 2.0 | Built with Python\n';

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Help & About')),
      body: const Padding(
        padding: EdgeInsets.all(12),
        child: SingleChildScrollView(
          child: SelectableText(_helpText),
        ),
      ),
    );
  }
}

class ApiToolsPage extends StatefulWidget {
  final int initialTab;
  final String moduleTitle;
  final String defaultTool;
  final bool openCameraOnStart;

  const ApiToolsPage({
    super.key,
    required this.initialTab,
    required this.moduleTitle,
    required this.defaultTool,
    this.openCameraOnStart = false,
  });

  @override
  State<ApiToolsPage> createState() => _ApiToolsPageState();
}

class _ApiToolsPageState extends State<ApiToolsPage> {
  String get _baseUrl => buildBackendApi().baseUrl;
  final _apiKeyController = TextEditingController();
  final String _autoApiKey =
      const String.fromEnvironment('FACE_STUDIO_API_KEY', defaultValue: '');
  final _styleController = TextEditingController(text: 'Anime');
  final _topKController = TextEditingController(text: '3');
  final _picker = ImagePicker();

  String _token = '';
  File? _pickedImage;
  File? _compareImage;
  File? _generatedImage;
  String _status = 'Ready';
  String _identifyJson = '';
  String _activeTool = 'identify';
  bool _bootstrapping = false;
  bool _busy = false;
  bool _showAdvanced = false;
  bool _showToolGuide = true;
  bool _autoRunOnPick = false;
  bool _showPayloadPreview = false;
  int _requestCount = 0;
  int _successCount = 0;
  DateTime? _lastRequestAt;
  final List<String> _logs = [];

  bool get _isGenerationModule => widget.moduleTitle == 'Face Generation';
  bool get _isCompareModule => widget.moduleTitle == 'Face Comparison';
  bool get _isProfileModule => widget.moduleTitle == 'My Profile';

  static const List<Map<String, String>> _operatorPlaybook = [
    {
      'title': '1) Connectivity Baseline',
      'body':
          'Confirm backend URL is reachable and token can be issued before image actions.'
    },
    {
      'title': '2) Capture Quality',
      'body':
          'Use front-lit image with face centered. Avoid strong side shadows and motion blur.'
    },
    {
      'title': '3) Identify Tuning',
      'body':
          'Use top_k=3 for quick checks and top_k=5 for broader candidate review.'
    },
    {
      'title': '4) Comparison Flow',
      'body':
          'When comparing, use similar angles and expressions for stable similarity scoring.'
    },
    {
      'title': '5) Generation Presets',
      'body':
          'Try Anime, Sketch, and Ghibli first; these are generally fastest and visually clear.'
    },
    {
      'title': '6) Retry Strategy',
      'body':
          'If request fails, refresh token, validate payload, then retry once with smaller payload size.'
    },
    {
      'title': '7) Operational Logging',
      'body':
          'Copy the session snapshot and include status text + JSON result when reporting issues.'
    },
    {
      'title': '8) Privacy Handling',
      'body':
          'Clear session images after testing in shared environments to avoid data retention.'
    },
    {
      'title': '9) Role-Gated Access',
      'body':
          'If endpoint authorization fails, confirm role mapping from login payload.'
    },
    {
      'title': '10) Mobile Throughput',
      'body':
          'Prefer compressed gallery images for rapid iteration; use camera only for final validation.'
    },
    {
      'title': '11) Fallback Behavior',
      'body':
          'If generate endpoint returns no image, verify selected style name and backend style map.'
    },
    {
      'title': '12) Incident Template',
      'body':
          'Capture timestamp, endpoint, status code, and first 20 lines of JSON for fast triage.'
    },
  ];

  @override
  void initState() {
    super.initState();
    _activeTool = widget.defaultTool;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _bootstrapAccess();
      if (widget.openCameraOnStart) {
        _captureFromCamera();
      }
    });
  }

  @override
  void dispose() {
    _apiKeyController.dispose();
    _styleController.dispose();
    _topKController.dispose();
    super.dispose();
  }

  void _appendLog(String message) {
    final ts = DateTime.now().toIso8601String();
    _logs.insert(0, '[$ts] $message');
    if (_logs.length > 80) {
      _logs.removeRange(80, _logs.length);
    }
  }

  Map<String, dynamic> _resultMap() {
    if (_identifyJson.trim().isEmpty) {
      return const {};
    }
    try {
      final parsed = jsonDecode(_identifyJson);
      if (parsed is Map<String, dynamic>) {
        return parsed;
      }
      return {'value': parsed};
    } catch (_) {
      return {'raw': _identifyJson};
    }
  }

  Future<void> _pickImage() async {
    final x =
        await _picker.pickImage(source: ImageSource.gallery, imageQuality: 80);
    if (x == null) return;
    setState(() {
      _pickedImage = File(x.path);
      _generatedImage = null;
      _identifyJson = '';
      _status = 'Image selected';
    });
    _appendLog('Picked image: ${x.path}');
    if (_autoRunOnPick && !_isProfileModule) {
      await _runActiveTool();
    }
  }

  Future<void> _captureFromCamera() async {
    final x =
        await _picker.pickImage(source: ImageSource.camera, imageQuality: 80);
    if (x == null) return;
    setState(() {
      _pickedImage = File(x.path);
      _generatedImage = null;
      _identifyJson = '';
      _status = 'Camera image captured';
    });
    _appendLog('Captured image: ${x.path}');
    if (_activeTool == 'identify' || _activeTool == 'search') {
      if (_autoRunOnPick) {
        await _identify();
      }
    }
  }

  Future<void> _pickCompareImage() async {
    final x =
        await _picker.pickImage(source: ImageSource.gallery, imageQuality: 80);
    if (x == null) return;
    setState(() {
      _compareImage = File(x.path);
      _status = 'Second image selected';
    });
    _appendLog('Picked compare image: ${x.path}');
  }

  Future<bool> _issueToken({bool silent = false}) async {
    final baseUrl = _baseUrl.trim().replaceAll(RegExp(r'/$'), '');
    final apiKey = _apiKeyController.text.trim();
    if (apiKey.isEmpty) {
      if (!silent) {
        setState(() => _status = 'API key missing. Contact admin.');
      }
      return false;
    }

    if (!silent) {
      setState(() => _status = 'Issuing token...');
    }
    final uri = Uri.parse('$baseUrl/api/auth/token?subject=android&ttl=720');
    final res = await http.get(uri, headers: {'X-API-Key': apiKey});
    if (res.statusCode != 200) {
      if (!silent) {
        setState(() => _status = 'Token failed: ${res.statusCode}');
      }
      return false;
    }

    final data = jsonDecode(res.body) as Map<String, dynamic>;
    setState(() {
      _token = (data['data']?['token'] ?? '').toString();
      _status = _token.isEmpty
          ? 'Token missing in response'
          : (silent ? 'Connected' : 'Token issued');
    });
    _appendLog('Token issued (${_token.isNotEmpty ? 'ok' : 'missing'})');
    return _token.isNotEmpty;
  }

  Future<bool> _ensureToken() async {
    final sessionApi = buildBackendApi();
    if (sessionApi.token.isNotEmpty) {
      _token = sessionApi.token;
      return true;
    }
    if (_token.isNotEmpty) {
      return true;
    }
    return _issueToken(silent: true);
  }

  Future<void> _bootstrapAccess() async {
    if (_bootstrapping) {
      return;
    }
    _bootstrapping = true;
    if (_autoApiKey.isNotEmpty) {
      _apiKeyController.text = _autoApiKey;
      setState(() => _status = 'Connecting...');
      await _issueToken(silent: true);
    } else {
      setState(() => _status = 'Ready (API key required for cloud actions)');
    }
    _appendLog('Bootstrap completed');
    _bootstrapping = false;
  }

  Future<void> _identify() async {
    if (_pickedImage == null) {
      setState(() => _status = 'Pick image first');
      return;
    }
    if (!await _ensureToken()) {
      setState(() => _status = 'Unable to connect. Check backend/API key.');
      return;
    }

    final baseUrl = _baseUrl.trim().replaceAll(RegExp(r'/$'), '');
    final topK = int.tryParse(_topKController.text.trim()) ?? 3;
    setState(() => _status = 'Running identify...');

    final imageB64 = base64Encode(await _pickedImage!.readAsBytes());
    final uri = Uri.parse('$baseUrl/api/mobile/identify');
    final res = await http.post(
      uri,
      headers: {
        'Authorization': 'Bearer $_token',
        'Content-Type': 'application/json',
      },
      body: jsonEncode({'image_b64': imageB64, 'top_k': topK}),
    );

    if (res.statusCode != 200) {
      setState(() => _status = 'Identify failed: ${res.statusCode}');
      return;
    }

    final data = jsonDecode(res.body) as Map<String, dynamic>;
    setState(() {
      _identifyJson = const JsonEncoder.withIndent('  ').convert(data['data']);
      _status = 'Identify complete';
      _requestCount += 1;
      _successCount += 1;
      _lastRequestAt = DateTime.now();
    });
    _appendLog('Identify completed (top_k=$topK)');
  }

  Future<void> _generate() async {
    if (_pickedImage == null) {
      setState(() => _status = 'Pick image first');
      return;
    }
    if (!await _ensureToken()) {
      setState(() => _status = 'Unable to connect. Check backend/API key.');
      return;
    }

    final baseUrl = _baseUrl.trim().replaceAll(RegExp(r'/$'), '');
    final filterName = _styleController.text.trim();
    if (filterName.isEmpty) {
      setState(() => _status = 'Enter style name');
      return;
    }

    setState(() => _status = 'Generating $filterName...');

    final imageB64 = base64Encode(await _pickedImage!.readAsBytes());
    final uri = Uri.parse('$baseUrl/api/mobile/generate');
    final res = await http.post(
      uri,
      headers: {
        'Authorization': 'Bearer $_token',
        'Content-Type': 'application/json',
      },
      body: jsonEncode({'image_b64': imageB64, 'filter_name': filterName}),
    );

    if (res.statusCode != 200) {
      setState(() => _status = 'Generate failed: ${res.statusCode}');
      return;
    }

    final data = jsonDecode(res.body) as Map<String, dynamic>;
    final outB64 = (data['data']?['image_b64'] ?? '').toString();
    if (outB64.isEmpty) {
      setState(() => _status = 'No image returned');
      return;
    }

    final bytes = base64Decode(outB64);
    final outPath = '${_pickedImage!.parent.path}/generated_mobile.jpg';
    final outFile = File(outPath);
    await outFile.writeAsBytes(bytes, flush: true);

    setState(() {
      _generatedImage = outFile;
      _status = 'Generated image ready';
      _requestCount += 1;
      _successCount += 1;
      _lastRequestAt = DateTime.now();
    });
    _appendLog('Generated image: $outPath');
  }

  Future<void> _runActiveTool() async {
    switch (_activeTool) {
      case 'identify':
        await _identify();
        break;
      case 'generate':
        await _generate();
        break;
      case 'compare':
        await _compareFaces();
        break;
      case 'search':
        await _identify();
        break;
      case 'stats':
        setState(() => _status =
            'Stats: run Identify/Search to populate latest result panel.');
        break;
      case 'counter':
        setState(() => _status =
            'Live Counter: use camera capture repeatedly to count visible persons from results.');
        _appendLog('Counter helper invoked');
        break;
      default:
        setState(() => _status = 'Tool not available yet');
        _appendLog('Unknown tool requested: $_activeTool');
    }
  }

  Future<void> _compareFaces() async {
    if (_pickedImage == null || _compareImage == null) {
      setState(() => _status = 'Select both images for comparison');
      return;
    }
    if (!await _ensureToken()) {
      setState(() => _status = 'Unable to connect. Check backend/API key.');
      return;
    }
    setState(() => _status = 'Comparing faces...');

    final baseUrl = _baseUrl.trim().replaceAll(RegExp(r'/$'), '');
    final leftB64 = base64Encode(await _pickedImage!.readAsBytes());
    final rightB64 = base64Encode(await _compareImage!.readAsBytes());
    final uri = Uri.parse('$baseUrl/api/mobile/compare');
    final res = await http.post(
      uri,
      headers: {
        'Authorization': 'Bearer $_token',
        'Content-Type': 'application/json',
      },
      body: jsonEncode({
        'left_image_b64': leftB64,
        'right_image_b64': rightB64,
      }),
    );
    if (res.statusCode != 200) {
      setState(() => _status = 'Compare failed: ${res.statusCode}');
      return;
    }

    final body = jsonDecode(res.body) as Map<String, dynamic>;
    final data = (body['data'] as Map<String, dynamic>?) ?? const {};
    final likelySame = data['same_person'] == true;
    final result = {
      'compare': data,
      'likely_same_person': likelySame,
      'note': 'Mobile compare now uses dedicated backend similarity endpoint.',
    };
    setState(() {
      _identifyJson = const JsonEncoder.withIndent('  ').convert(result);
      _status = likelySame
          ? 'Comparison complete: likely SAME person'
          : 'Comparison complete: likely DIFFERENT person';
      _requestCount += 1;
      _successCount += 1;
      _lastRequestAt = DateTime.now();
    });
    _appendLog('Compare completed');
  }

  Future<void> _copyResultJson() async {
    if (_identifyJson.trim().isEmpty) {
      setState(() => _status = 'Nothing to copy yet');
      return;
    }
    await Clipboard.setData(ClipboardData(text: _identifyJson));
    if (!mounted) {
      return;
    }
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Result JSON copied')),
    );
  }

  Future<void> _copySessionSnapshot() async {
    final lines = <String>[
      'Face Studio Mobile Session',
      'Module: ${widget.moduleTitle}',
      'Tool: $_activeTool',
      'Status: $_status',
      'Requests: $_requestCount',
      'Success: $_successCount',
      'Last request: ${_lastRequestAt?.toIso8601String() ?? '-'}',
      'Backend: $_baseUrl',
      'Has token: ${_token.isNotEmpty}',
      'Picked image: ${_pickedImage?.path ?? '-'}',
      'Compare image: ${_compareImage?.path ?? '-'}',
      'Generated image: ${_generatedImage?.path ?? '-'}',
    ];
    await Clipboard.setData(ClipboardData(text: lines.join('\n')));
    if (!mounted) {
      return;
    }
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Session snapshot copied')),
    );
  }

  Future<void> _saveResultJsonToFile() async {
    if (_identifyJson.trim().isEmpty) {
      setState(() => _status = 'No result JSON to save');
      return;
    }
    final dir = _pickedImage?.parent.path ?? Directory.systemTemp.path;
    final stamp = DateTime.now().millisecondsSinceEpoch;
    final out = File('$dir/mobile_result_$stamp.json');
    await out.writeAsString(_identifyJson, flush: true);
    setState(() => _status = 'Saved result file: ${out.path}');
    _appendLog('Saved JSON file: ${out.path}');
  }

  void _clearSession() {
    setState(() {
      _pickedImage = null;
      _compareImage = null;
      _generatedImage = null;
      _identifyJson = '';
      _status = 'Session cleared';
      _logs.clear();
    });
  }

  InputDecoration _inputDecoration(String label) {
    return InputDecoration(
      labelText: label,
      labelStyle: const TextStyle(color: Color(0xFFB4C6EA)),
      filled: true,
      fillColor: const Color(0xFF10182B),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: Color(0xFF355070)),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: Color(0xFF65B5FF), width: 1.6),
      ),
    );
  }

  Widget _imageCard(String title, File? file) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(8),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: const TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            if (file == null)
              const Text('No image')
            else
              Image.file(file, height: 180, fit: BoxFit.contain),
          ],
        ),
      ),
    );
  }

  Widget _statusCard() {
    final ratio = _requestCount == 0 ? 0.0 : (_successCount / _requestCount);
    final ratioText =
        _requestCount == 0 ? 'n/a' : '${(ratio * 100).toStringAsFixed(0)}%';
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(14),
        gradient: const LinearGradient(
          colors: [Color(0xFF26476E), Color(0xFF17253E)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        border: Border.all(color: const Color(0xFF4D6890)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Session Diagnostics',
            style: TextStyle(
              color: Colors.white,
              fontSize: 17,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _SectionBadge(
                icon: Icons.bolt,
                label: 'Req $_requestCount',
                tint: const Color(0xFF89DFFF),
              ),
              _SectionBadge(
                icon: Icons.task_alt,
                label: 'Ok $_successCount',
                tint: const Color(0xFF96F5BD),
              ),
              _SectionBadge(
                icon: Icons.percent,
                label: 'Success $ratioText',
                tint: const Color(0xFFFFD08A),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            _status,
            style: const TextStyle(color: Color(0xFFD1E1F8)),
          ),
          if (_lastRequestAt != null) ...[
            const SizedBox(height: 4),
            Text(
              'Last request: ${_lastRequestAt!.toIso8601String()}',
              style: const TextStyle(color: Color(0xFFB3C8E7), fontSize: 12),
            ),
          ],
        ],
      ),
    );
  }

  Widget _toolGuidePanel() {
    return Card(
      child: ExpansionTile(
        initiallyExpanded: _showToolGuide,
        onExpansionChanged: (v) => setState(() => _showToolGuide = v),
        title: const Text('Operator Playbook'),
        children: _operatorPlaybook
            .map(
              (step) => ListTile(
                leading: const Icon(Icons.checklist, color: Color(0xFF92B8F5)),
                title: Text(step['title'] ?? ''),
                subtitle: Text(step['body'] ?? ''),
              ),
            )
            .toList(),
      ),
    );
  }

  Widget _resultInsightsPanel() {
    final map = _resultMap();
    final entries = map.entries.take(18).toList();
    if (entries.isEmpty) {
      return const SizedBox.shrink();
    }
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Result Insights',
              style:
                  TextStyle(fontWeight: FontWeight.w900, color: Colors.white),
            ),
            const SizedBox(height: 6),
            ...entries.map(
              (e) => Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    SizedBox(
                      width: 140,
                      child: Text(
                        e.key,
                        style: const TextStyle(
                          color: Color(0xFFA9C0E3),
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                    Expanded(
                      child: Text(
                        e.value.toString(),
                        style: const TextStyle(color: Color(0xFFD9E7FA)),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _activityLogPanel() {
    return Card(
      child: ExpansionTile(
        title: const Text('Activity Log'),
        children: [
          if (_logs.isEmpty)
            const ListTile(
              title: Text('No logs yet'),
            )
          else
            ..._logs.take(25).map(
                  (line) => ListTile(
                    dense: true,
                    title: Text(line, style: const TextStyle(fontSize: 12)),
                  ),
                ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final showResultJson = _identifyJson.isNotEmpty &&
        (_activeTool == 'identify' ||
            _activeTool == 'search' ||
            _isCompareModule);

    return Scaffold(
      appBar: AppBar(
        title: Text(widget.moduleTitle),
        actions: [
          IconButton(
            onPressed: _copySessionSnapshot,
            icon: const Icon(Icons.copy_all),
            tooltip: 'Copy session snapshot',
          ),
          IconButton(
            onPressed: _clearSession,
            icon: const Icon(Icons.delete_sweep),
            tooltip: 'Clear session',
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(12),
        children: [
          _AnimatedFadeSlide(
            delayMs: 120,
            child: Card(
              color: const Color(0xFF10182B),
              child: Padding(
                padding: const EdgeInsets.all(10),
                child: Text(
                  'Connected Backend: $_baseUrl',
                  style: const TextStyle(color: Color(0xFFB4C6EA)),
                ),
              ),
            ),
          ),
          const SizedBox(height: 8),
          _AnimatedFadeSlide(delayMs: 150, child: _statusCard()),
          const SizedBox(height: 8),
          _AnimatedFadeSlide(
            delayMs: 180,
            child: SwitchListTile(
              value: _showAdvanced,
              onChanged: (v) => setState(() => _showAdvanced = v),
              title: const Text('Advanced controls'),
            ),
          ),
          if (_showAdvanced)
            _AnimatedFadeSlide(
              delayMs: 200,
              child: Card(
                child: Padding(
                  padding: const EdgeInsets.all(10),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      TextField(
                        controller: _apiKeyController,
                        style: const TextStyle(color: Colors.white),
                        decoration: _inputDecoration('API key'),
                      ),
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          Expanded(
                            child: TextField(
                              controller: _topKController,
                              style: const TextStyle(color: Colors.white),
                              decoration: _inputDecoration('top_k (identify)'),
                              keyboardType: TextInputType.number,
                            ),
                          ),
                          const SizedBox(width: 8),
                          FilledButton.icon(
                            onPressed: () => _issueToken(),
                            icon: const Icon(Icons.key),
                            label: const Text('Issue Token'),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: [
                          FilterChip(
                            selected: _autoRunOnPick,
                            label: const Text('Auto run on image pick'),
                            onSelected: (v) =>
                                setState(() => _autoRunOnPick = v),
                          ),
                          FilterChip(
                            selected: _showPayloadPreview,
                            label: const Text('Show payload preview'),
                            onSelected: (v) =>
                                setState(() => _showPayloadPreview = v),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ),
          if (_showPayloadPreview && _pickedImage != null)
            _AnimatedFadeSlide(
              delayMs: 230,
              child: Card(
                child: Padding(
                  padding: const EdgeInsets.all(10),
                  child: Text(
                    'Payload preview: image=${_pickedImage!.path}, bytes=${_pickedImage!.lengthSync()}, tool=$_activeTool',
                    style: const TextStyle(color: Color(0xFFD8E7FA)),
                  ),
                ),
              ),
            ),
          const SizedBox(height: 8),
          _AnimatedFadeSlide(
            delayMs: 250,
            child: _toolGuidePanel(),
          ),
          const SizedBox(height: 8),
          if (_isProfileModule) ...[
            const _AnimatedFadeSlide(
              delayMs: 280,
              child: Card(
                color: Color(0xFF10182B),
                child: Padding(
                  padding: EdgeInsets.all(12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Account',
                          style: TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.bold)),
                      SizedBox(height: 6),
                      Text('User: Guest',
                          style: TextStyle(color: Color(0xFFB4C6EA))),
                      Text('Role: User',
                          style: TextStyle(color: Color(0xFFB4C6EA))),
                      SizedBox(height: 6),
                      Text(
                          'Profile actions are being wired to backend account APIs.',
                          style: TextStyle(color: Color(0xFF9CB3D9))),
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(height: 10),
          ],
          if (_isGenerationModule) ...[
            const Text(
              'Choose Style',
              style: TextStyle(
                  color: Color(0xFFB4C6EA), fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: _desktopFilterStyles
                  .map(
                    (style) => ChoiceChip(
                      label: Text(style),
                      selected: _styleController.text == style,
                      onSelected: (_) =>
                          setState(() => _styleController.text = style),
                    ),
                  )
                  .toList(),
            ),
            const SizedBox(height: 8),
          ],
          if (_isGenerationModule)
            TextField(
              controller: _styleController,
              style: const TextStyle(color: Colors.white),
              decoration: _inputDecoration('Style (e.g. Anime)'),
            ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              if (!_isProfileModule)
                ElevatedButton(
                    onPressed: _pickImage, child: const Text('Pick Image')),
              if (!_isProfileModule)
                ElevatedButton(
                    onPressed: _captureFromCamera,
                    child: const Text('Open Camera')),
              if (_isCompareModule)
                ElevatedButton(
                    onPressed: _pickCompareImage,
                    child: const Text('Pick 2nd Image')),
              if (_isProfileModule)
                ElevatedButton(
                    onPressed: () => setState(() =>
                        _status = 'Profile update action wiring in progress'),
                    child: const Text('Open Profile Actions')),
              if (!_isProfileModule)
                ElevatedButton(
                    onPressed: _busy
                        ? null
                        : () async {
                            setState(() => _busy = true);
                            try {
                              await _runActiveTool();
                            } finally {
                              if (mounted) {
                                setState(() => _busy = false);
                              }
                            }
                          },
                    child: Text(_activeTool.toUpperCase())),
              OutlinedButton.icon(
                onPressed: _copySessionSnapshot,
                icon: const Icon(Icons.copy),
                label: const Text('Copy Session'),
              ),
              OutlinedButton.icon(
                onPressed: _saveResultJsonToFile,
                icon: const Icon(Icons.save),
                label: const Text('Save Result JSON'),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text('Status: $_status', style: const TextStyle(color: Colors.white)),
          const SizedBox(height: 10),
          if (!_isProfileModule) _imageCard('Picked Image', _pickedImage),
          if (_isCompareModule) _imageCard('Second Image', _compareImage),
          if (_isGenerationModule || _generatedImage != null)
            _imageCard('Generated Image', _generatedImage),
          if (showResultJson) _resultInsightsPanel(),
          if (showResultJson)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(8),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Expanded(
                          child: Text(
                            'Raw Result JSON',
                            style: TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                        ),
                        IconButton(
                          onPressed: _copyResultJson,
                          icon: const Icon(Icons.copy_all),
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    SelectableText(_identifyJson),
                  ],
                ),
              ),
            ),
          _activityLogPanel(),
        ],
      ),
    );
  }
}

class _AdminRunbookPanel extends StatefulWidget {
  final Map<String, dynamic> data;

  const _AdminRunbookPanel({required this.data});

  @override
  State<_AdminRunbookPanel> createState() => _AdminRunbookPanelState();
}

class _AdminRunbookPanelState extends State<_AdminRunbookPanel> {
  final TextEditingController _query = TextEditingController();
  bool _showChecklist = true;
  bool _showFaq = false;
  bool _showSnapshot = false;

  static const List<Map<String, String>> _faq = [
    {
      'q': 'How often should backups run?',
      'a': 'Daily for baseline, hourly during high-change windows.'
    },
    {
      'q': 'What to do on auth failures?',
      'a':
          'Reissue token, verify role, then retry endpoint with minimal payload.'
    },
    {
      'q': 'How to triage slow responses?',
      'a':
          'Capture endpoint, request size, timestamp, and compare with health checks.'
    },
    {
      'q': 'What if export bundle fails?',
      'a':
          'Check write permission, disk free space, and artifact path existence.'
    },
    {
      'q': 'How to verify scheduler state?',
      'a':
          'Run start action, wait one cycle, confirm expected backup artifact timestamp.'
    },
    {
      'q': 'What data to include in incident reports?',
      'a':
          'Status code, request context, user role, and relevant recent activity rows.'
    },
    {
      'q': 'How to validate DB integrity quickly?',
      'a':
          'Inspect table counts, compare baseline deltas, and check non-zero critical tables.'
    },
    {
      'q': 'When to trigger immediate backup?',
      'a':
          'Before risky migrations, role policy changes, or bulk import operations.'
    },
    {
      'q': 'How to recover from config drift?',
      'a':
          'Use artifact checks, compare service values, then re-run controlled actions.'
    },
    {
      'q': 'What indicates healthy operations?',
      'a': 'Stable request success, valid artifacts, expected activity cadence.'
    },
  ];

  @override
  void dispose() {
    _query.dispose();
    super.dispose();
  }

  List<String> _filteredChecklist() {
    final q = _query.text.trim().toLowerCase();
    if (q.isEmpty) {
      return _AdminRunbookLibrary.checklist;
    }
    return _AdminRunbookLibrary.checklist
        .where((line) => line.toLowerCase().contains(q))
        .toList();
  }

  @override
  Widget build(BuildContext context) {
    final rows = _filteredChecklist();
    final stats = (widget.data['stats'] as Map<String, dynamic>?) ?? const {};
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Admin Runbook',
              style:
                  TextStyle(color: Colors.white, fontWeight: FontWeight.w900),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: _query,
              onChanged: (_) => setState(() {}),
              decoration: const InputDecoration(
                labelText: 'Search runbook steps',
                prefixIcon: Icon(Icons.search),
              ),
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                FilterChip(
                  selected: _showChecklist,
                  label: const Text('Checklist'),
                  onSelected: (v) => setState(() => _showChecklist = v),
                ),
                FilterChip(
                  selected: _showFaq,
                  label: const Text('FAQ'),
                  onSelected: (v) => setState(() => _showFaq = v),
                ),
                FilterChip(
                  selected: _showSnapshot,
                  label: const Text('Snapshot'),
                  onSelected: (v) => setState(() => _showSnapshot = v),
                ),
              ],
            ),
            const SizedBox(height: 8),
            if (_showSnapshot)
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  _SectionBadge(
                    icon: Icons.people,
                    label: 'Users ${stats['users'] ?? 0}',
                    tint: const Color(0xFF8FD6FF),
                  ),
                  _SectionBadge(
                    icon: Icons.face,
                    label: 'Faces ${stats['face_events'] ?? 0}',
                    tint: const Color(0xFFFFCD8B),
                  ),
                  _SectionBadge(
                    icon: Icons.pending_actions,
                    label: 'Pending ${stats['pending_approvals'] ?? 0}',
                    tint: const Color(0xFFAFC2FF),
                  ),
                ],
              ),
            if (_showChecklist) ...[
              const SizedBox(height: 6),
              Text(
                'Checklist entries: ${rows.length}',
                style: const TextStyle(color: Color(0xFFAFC4E7)),
              ),
              const SizedBox(height: 6),
              ...rows.take(120).map(
                    (line) => ListTile(
                      dense: true,
                      leading: const Icon(Icons.task_alt,
                          size: 18, color: Color(0xFF8BB8F7)),
                      title: Text(line),
                    ),
                  ),
            ],
            if (_showFaq) ...[
              const SizedBox(height: 8),
              ..._faq.map(
                (e) => ExpansionTile(
                  title: Text(e['q'] ?? ''),
                  childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 10),
                  children: [
                    Align(
                      alignment: Alignment.centerLeft,
                      child: Text(e['a'] ?? ''),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _AdminRunbookLibrary {
  static const List<String> checklist = [
    'Step 0001: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0002: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0003: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0004: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0005: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0006: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0007: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0008: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0009: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0010: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0011: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0012: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0013: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0014: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0015: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0016: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0017: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0018: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0019: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0020: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0021: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0022: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0023: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0024: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0025: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0026: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0027: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0028: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0029: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0030: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0031: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0032: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0033: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0034: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0035: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0036: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0037: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0038: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0039: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0040: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0041: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0042: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0043: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0044: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0045: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0046: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0047: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0048: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0049: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0050: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0051: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0052: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0053: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0054: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0055: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0056: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0057: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0058: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0059: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0060: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0061: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0062: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0063: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0064: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0065: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0066: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0067: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0068: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0069: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0070: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0071: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0072: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0073: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0074: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0075: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0076: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0077: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0078: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0079: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0080: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0081: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0082: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0083: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0084: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0085: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0086: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0087: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0088: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0089: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0090: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0091: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0092: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0093: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0094: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0095: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0096: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0097: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0098: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0099: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0100: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0101: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0102: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0103: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0104: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0105: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0106: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0107: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0108: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0109: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0110: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0111: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0112: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0113: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0114: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0115: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0116: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0117: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0118: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0119: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0120: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0121: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0122: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0123: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0124: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0125: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0126: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0127: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0128: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0129: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0130: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0131: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0132: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0133: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0134: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0135: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0136: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0137: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0138: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0139: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0140: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0141: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0142: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0143: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0144: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0145: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0146: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0147: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0148: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0149: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0150: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0151: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0152: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0153: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0154: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0155: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0156: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0157: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0158: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0159: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0160: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0161: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0162: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0163: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0164: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0165: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0166: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0167: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0168: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0169: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0170: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0171: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0172: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0173: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0174: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0175: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0176: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0177: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0178: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0179: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0180: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0181: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0182: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0183: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0184: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0185: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0186: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0187: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0188: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0189: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0190: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0191: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0192: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0193: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0194: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0195: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0196: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0197: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0198: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0199: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0200: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0201: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0202: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0203: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0204: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0205: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0206: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0207: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0208: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0209: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0210: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0211: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0212: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0213: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0214: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0215: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0216: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0217: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0218: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0219: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0220: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0221: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0222: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0223: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0224: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0225: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0226: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0227: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0228: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0229: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0230: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0231: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0232: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0233: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0234: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0235: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0236: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0237: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0238: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0239: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0240: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0241: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0242: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0243: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0244: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0245: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0246: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0247: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0248: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0249: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0250: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0251: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0252: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0253: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0254: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0255: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0256: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0257: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0258: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0259: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0260: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0261: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0262: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0263: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0264: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0265: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0266: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0267: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0268: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0269: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0270: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0271: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0272: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0273: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0274: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0275: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0276: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0277: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0278: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0279: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0280: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0281: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0282: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0283: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0284: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0285: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0286: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0287: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0288: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0289: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0290: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0291: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0292: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0293: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0294: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0295: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0296: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0297: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0298: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0299: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0300: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0301: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0302: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0303: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0304: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0305: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0306: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0307: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0308: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0309: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0310: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0311: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0312: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0313: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0314: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0315: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0316: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0317: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0318: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0319: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0320: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0321: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0322: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0323: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0324: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0325: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0326: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0327: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0328: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0329: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0330: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0331: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0332: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0333: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0334: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0335: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0336: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0337: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0338: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0339: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0340: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0341: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0342: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0343: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0344: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0345: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0346: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0347: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0348: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0349: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0350: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0351: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0352: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0353: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0354: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0355: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0356: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0357: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0358: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0359: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0360: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0361: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0362: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0363: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0364: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0365: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0366: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0367: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0368: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0369: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0370: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0371: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0372: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0373: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0374: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0375: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0376: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0377: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0378: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0379: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0380: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0381: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0382: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0383: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0384: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0385: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0386: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0387: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0388: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0389: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0390: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0391: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0392: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0393: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0394: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0395: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0396: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0397: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0398: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0399: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0400: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0401: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0402: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0403: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0404: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0405: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0406: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0407: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0408: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0409: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0410: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0411: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0412: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0413: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0414: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0415: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0416: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0417: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0418: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0419: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0420: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0421: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0422: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0423: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0424: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0425: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0426: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0427: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0428: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0429: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0430: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0431: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0432: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0433: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0434: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0435: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0436: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0437: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0438: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0439: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0440: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0441: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0442: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0443: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0444: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0445: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0446: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0447: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0448: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0449: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0450: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0451: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0452: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0453: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0454: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0455: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0456: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0457: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0458: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0459: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0460: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0461: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0462: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0463: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0464: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0465: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0466: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0467: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0468: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0469: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0470: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0471: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0472: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0473: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0474: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0475: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0476: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0477: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0478: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0479: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0480: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0481: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0482: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0483: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0484: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0485: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0486: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0487: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0488: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0489: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0490: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0491: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0492: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0493: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0494: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0495: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0496: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0497: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0498: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0499: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0500: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0501: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0502: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0503: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0504: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0505: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0506: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0507: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0508: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0509: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0510: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0511: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0512: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0513: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0514: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0515: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0516: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0517: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0518: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0519: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0520: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0521: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0522: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0523: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0524: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0525: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0526: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0527: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0528: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0529: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0530: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0531: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0532: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0533: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0534: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0535: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0536: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0537: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0538: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0539: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0540: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0541: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0542: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0543: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0544: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0545: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0546: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0547: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0548: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0549: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0550: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0551: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0552: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0553: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0554: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0555: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0556: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0557: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0558: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0559: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0560: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0561: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0562: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0563: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0564: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0565: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0566: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0567: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0568: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0569: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0570: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0571: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0572: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0573: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0574: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0575: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0576: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0577: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0578: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0579: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0580: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0581: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0582: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0583: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0584: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0585: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0586: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0587: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0588: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0589: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0590: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0591: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0592: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0593: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0594: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0595: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0596: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0597: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0598: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0599: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0600: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0601: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0602: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0603: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0604: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0605: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0606: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0607: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0608: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0609: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0610: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0611: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0612: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0613: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0614: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0615: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0616: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0617: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0618: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0619: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0620: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0621: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0622: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0623: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0624: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0625: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0626: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0627: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0628: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0629: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0630: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0631: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0632: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0633: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0634: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0635: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0636: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0637: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0638: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0639: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0640: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0641: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0642: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0643: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0644: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0645: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0646: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0647: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0648: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0649: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0650: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0651: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0652: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0653: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0654: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0655: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0656: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0657: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0658: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0659: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0660: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0661: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0662: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0663: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0664: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0665: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0666: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0667: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0668: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0669: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0670: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0671: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0672: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0673: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0674: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0675: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0676: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0677: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0678: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0679: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0680: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0681: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0682: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0683: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0684: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0685: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0686: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0687: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0688: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0689: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0690: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0691: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0692: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0693: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0694: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0695: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0696: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0697: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0698: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0699: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0700: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0701: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0702: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0703: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0704: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0705: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0706: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0707: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0708: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0709: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0710: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0711: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0712: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0713: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0714: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0715: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0716: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0717: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0718: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0719: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0720: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0721: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0722: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0723: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0724: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0725: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0726: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0727: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0728: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0729: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0730: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0731: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0732: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0733: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0734: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0735: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0736: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0737: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0738: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0739: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0740: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0741: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0742: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0743: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0744: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0745: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0746: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0747: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0748: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0749: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0750: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0751: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0752: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0753: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0754: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0755: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0756: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0757: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0758: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0759: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0760: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0761: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0762: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0763: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0764: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0765: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0766: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0767: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0768: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0769: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0770: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0771: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0772: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0773: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0774: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0775: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0776: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0777: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0778: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0779: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0780: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0781: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0782: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0783: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0784: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0785: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0786: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0787: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0788: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0789: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0790: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0791: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0792: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0793: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0794: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0795: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0796: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0797: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0798: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0799: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0800: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0801: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0802: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0803: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0804: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0805: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0806: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0807: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0808: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0809: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0810: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0811: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0812: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0813: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0814: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0815: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0816: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0817: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0818: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0819: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0820: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0821: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0822: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0823: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0824: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0825: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0826: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0827: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0828: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0829: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0830: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0831: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0832: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0833: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0834: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0835: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0836: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0837: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0838: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0839: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0840: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0841: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0842: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0843: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0844: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0845: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0846: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0847: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0848: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0849: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0850: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0851: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0852: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0853: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0854: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0855: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0856: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0857: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0858: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0859: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0860: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0861: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0862: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0863: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0864: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0865: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0866: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0867: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0868: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0869: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0870: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0871: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0872: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0873: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0874: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0875: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0876: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0877: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0878: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0879: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0880: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0881: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0882: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0883: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0884: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0885: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0886: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0887: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0888: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0889: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0890: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0891: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0892: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0893: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0894: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0895: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0896: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0897: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0898: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0899: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0900: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0901: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0902: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0903: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0904: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0905: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0906: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0907: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0908: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0909: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0910: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0911: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0912: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0913: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0914: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0915: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0916: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0917: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0918: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0919: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0920: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0921: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0922: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0923: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0924: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0925: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0926: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0927: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0928: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0929: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0930: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0931: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0932: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0933: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0934: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0935: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0936: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0937: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0938: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0939: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0940: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0941: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0942: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0943: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0944: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0945: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0946: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0947: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0948: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0949: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0950: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0951: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0952: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0953: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0954: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0955: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0956: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0957: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0958: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0959: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0960: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0961: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0962: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0963: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0964: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0965: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0966: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0967: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0968: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0969: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0970: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0971: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0972: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0973: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0974: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0975: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0976: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0977: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0978: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0979: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0980: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0981: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0982: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0983: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0984: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0985: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0986: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0987: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0988: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0989: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0990: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0991: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0992: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0993: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0994: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0995: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0996: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0997: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0998: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 0999: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1000: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1001: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1002: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1003: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1004: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1005: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1006: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1007: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1008: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1009: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1010: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1011: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1012: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1013: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1014: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1015: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1016: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1017: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1018: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1019: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1020: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1021: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1022: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1023: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1024: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1025: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1026: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1027: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1028: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1029: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1030: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1031: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1032: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1033: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1034: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1035: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1036: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1037: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1038: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1039: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1040: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1041: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1042: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1043: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1044: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1045: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1046: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1047: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1048: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1049: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1050: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1051: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1052: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1053: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1054: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1055: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1056: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1057: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1058: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1059: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1060: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1061: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1062: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1063: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1064: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1065: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1066: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1067: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1068: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1069: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1070: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1071: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1072: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1073: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1074: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1075: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1076: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1077: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1078: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1079: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1080: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1081: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1082: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1083: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1084: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1085: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1086: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1087: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1088: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1089: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1090: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1091: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1092: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1093: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1094: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1095: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1096: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1097: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1098: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1099: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
    'Step 1100: Validate admin telemetry, endpoint health, artifact state, and recovery readiness before next action.',
  ];
}

class PlaceholderPage extends StatelessWidget {
  final String title;

  const PlaceholderPage({super.key, required this.title});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(title)),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Text(
            '$title is ready in navigation.\nNext step is wiring this screen to backend APIs and camera flow.',
            textAlign: TextAlign.center,
          ),
        ),
      ),
    );
  }
}

class FullScreenMapPage extends StatefulWidget {
  final List<String> mapCandidates;
  final int initialIndex;

  const FullScreenMapPage({
    super.key,
    required this.mapCandidates,
    required this.initialIndex,
  });

  @override
  State<FullScreenMapPage> createState() => _FullScreenMapPageState();
}

class _FullScreenMapPageState extends State<FullScreenMapPage> {
  late final WebViewController _controller;
  final Set<Factory<OneSequenceGestureRecognizer>> _mapGestures = {
    Factory<OneSequenceGestureRecognizer>(() => EagerGestureRecognizer()),
  };
  late int _index;
  bool _loading = true;
  String _error = '';

  @override
  void initState() {
    super.initState();
    _index = widget.initialIndex.clamp(0, widget.mapCandidates.length - 1);
    _controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setBackgroundColor(const Color(0x00000000))
      ..setNavigationDelegate(
        NavigationDelegate(
          onPageStarted: (_) {
            if (!mounted) {
              return;
            }
            setState(() {
              _loading = true;
              _error = '';
            });
          },
          onPageFinished: (_) {
            if (!mounted) {
              return;
            }
            setState(() {
              _loading = false;
            });
          },
          onWebResourceError: (error) {
            if (!mounted) {
              return;
            }
            if (_index + 1 < widget.mapCandidates.length) {
              _index += 1;
              _controller.loadRequest(Uri.parse(widget.mapCandidates[_index]));
              return;
            }
            setState(() {
              _loading = false;
              _error = error.description;
            });
          },
        ),
      )
      ..loadRequest(Uri.parse(widget.mapCandidates[_index]));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Map Full Screen'),
        actions: [
          IconButton(
            onPressed: () {
              _index = 0;
              _controller.loadRequest(Uri.parse(widget.mapCandidates[_index]));
            },
            icon: const Icon(Icons.refresh),
            tooltip: 'Reload',
          ),
        ],
      ),
      body: Stack(
        children: [
          Positioned.fill(
            child: WebViewWidget(
              controller: _controller,
              gestureRecognizers: _mapGestures,
            ),
          ),
          if (_loading)
            const Positioned.fill(
              child: Center(child: CircularProgressIndicator()),
            ),
          if (_error.isNotEmpty)
            Positioned.fill(
              child: Container(
                color: const Color(0xCC11182A),
                alignment: Alignment.center,
                padding: const EdgeInsets.all(12),
                child: Text(
                  'Map load error: $_error',
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: Colors.white),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
