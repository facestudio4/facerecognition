import 'dart:convert';
import 'dart:async';
import 'dart:io';

import 'package:camera/camera.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:webview_flutter/webview_flutter.dart';

const Color _kBg = Color(0xFF1A1A2E);
const Color _kPanel = Color(0xFF11182A);
const Color _kAccent = Color(0xFFE94560);
const Color _kTextMuted = Color(0xFFAAB2D6);
const Duration _kNetworkTimeout = Duration(seconds: 3);

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
        brightness: Brightness.dark,
        colorScheme: ColorScheme.fromSeed(
            seedColor: const Color(0xFF184E77), brightness: Brightness.dark),
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
          titleTextStyle: TextStyle(
              fontSize: 18, fontWeight: FontWeight.w700, color: Colors.white),
        ),
        cardTheme: CardThemeData(
          color: const Color(0xFF1F2A44),
          elevation: 2,
          margin: const EdgeInsets.symmetric(vertical: 5),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(14),
            side: const BorderSide(color: Color(0xFF2C3C60), width: 0.8),
          ),
        ),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: const Color(0xFF18223A),
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: const BorderSide(color: Color(0xFF3A4B70)),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: const BorderSide(color: _kAccent, width: 1.4),
          ),
          labelStyle: const TextStyle(color: _kTextMuted),
          hintStyle: const TextStyle(color: Color(0xFFB6C4E3)),
          prefixIconColor: const Color(0xFFD8E5FF),
          suffixIconColor: const Color(0xFFD8E5FF),
        ),
        filledButtonTheme: FilledButtonThemeData(
          style: FilledButton.styleFrom(
            backgroundColor: _kAccent,
            foregroundColor: Colors.white,
            shape:
                RoundedRectangleBorder(borderRadius: BorderRadius.circular(11)),
          ),
        ),
        useMaterial3: true,
      ),
      home: const AuthGate(),
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
    final ordered = <String>[
      _base,
      const String.fromEnvironment(
        'FACE_STUDIO_BASE_URL',
        defaultValue: 'http://10.0.2.2:8787',
      ).trim().replaceAll(RegExp(r'/$'), ''),
      'http://10.0.2.2:8787',
      'http://10.0.3.2:8787',
      'http://127.0.0.1:8787',
      'http://localhost:8787',
    ];
    if (!Platform.isAndroid) {
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

  Future<Map<String, dynamic>?> login({
    required String identifier,
    required String password,
  }) async {
    for (final base in _candidateBases()) {
      try {
        final res = await http
            .post(
              Uri.parse('$base/api/auth/login'),
              headers: {'Content-Type': 'application/json'},
              body: jsonEncode(
                  {'identifier': identifier, 'password': password, 'ttl': 180}),
            )
            .timeout(_kNetworkTimeout);
        if (res.statusCode != 200) {
          continue;
        }
        final body = jsonDecode(res.body) as Map<String, dynamic>;
        final data = (body['data'] as Map<String, dynamic>?) ?? {};
        final user = (data['user'] as Map<String, dynamic>?) ?? {};
        final token = (data['token'] ?? '').toString();
        final username = (user['username'] ?? '').toString();
        final role = (user['role'] ?? 'user').toString().toLowerCase();
        if (token.isEmpty || username.isEmpty) {
          continue;
        }
        _baseUrl = base;
        setSession(token: token, username: username, role: role);
        return user;
      } catch (_) {
        continue;
      }
    }
    return null;
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
    if (!ok) return {'ok': false, 'error': 'Token issue failed'};
    final res = await http.get(
      Uri.parse('$_base/api/stats'),
      headers: {'Authorization': 'Bearer $_token'},
    );
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getUsers({int limit = 200}) async {
    final ok = await ensureToken();
    if (!ok) return {'ok': false, 'error': 'Token issue failed'};
    final res = await http.get(
      Uri.parse('$_base/api/users?limit=$limit'),
      headers: {'Authorization': 'Bearer $_token'},
    );
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getActivity({int limit = 200}) async {
    final ok = await ensureToken();
    if (!ok) return {'ok': false, 'error': 'Token issue failed'};
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
    if (!ok) return {'ok': false, 'error': 'Token issue failed'};
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
    if (!ok) return {'ok': false, 'error': 'Token issue failed'};
    final person = Uri.encodeQueryComponent(name.trim());
    final res = await http.get(
      Uri.parse(
          '$_base/api/mobile/recognition-location/search?name=$person&limit=$limit'),
      headers: {'Authorization': 'Bearer $_token'},
    );
    return jsonDecode(res.body) as Map<String, dynamic>;
  }
}

BackendApi _createBackendApi() {
  const baseUrl = String.fromEnvironment(
    'FACE_STUDIO_BASE_URL',
    defaultValue: 'https://hexadic-nora-unlodged.ngrok-free.dev',
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

  @override
  void initState() {
    super.initState();
    _loadSession();
  }

  Future<void> _loadSession() async {
    final api = buildBackendApi();
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('fs_token') ?? '';
    final username = prefs.getString('fs_username') ?? '';
    final role = (prefs.getString('fs_role') ?? 'user').toLowerCase();

    if (token.isNotEmpty && username.isNotEmpty) {
      api.setSession(token: token, username: username, role: role);
      final me = await api.getCurrentUser();
      if (me['ok'] == true) {
        final data = (me['data'] as Map<String, dynamic>?) ?? {};
        _username = (data['username'] ?? username).toString();
        _isAdmin = ((data['role'] ?? role).toString().toLowerCase() == 'admin');
        api.setSession(
          token: token,
          username: _username,
          role: _isAdmin ? 'admin' : 'user',
        );
      } else {
        final errorText = (me['error'] ?? '').toString().toLowerCase();
        final connectivityIssue = errorText.contains('unavailable') ||
            errorText.contains('failed to connect') ||
            errorText.contains('socket');
        if (connectivityIssue) {
          // Keep cached session if backend is temporarily unreachable.
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

    if (!mounted) return;
    setState(() {
      _ready = true;
    });
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
    final user = await api.login(identifier: id, password: pw);
    if (!mounted) return;
    if (user == null) {
      setState(() {
        _busy = false;
        _error = 'Invalid credentials or backend unreachable at ${api.baseUrl}';
      });
      return;
    }
    await widget.onLoggedIn(user);
    if (!mounted) return;
    setState(() => _busy = false);
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
      final res = await api.requestSignupVerification(
        username: username,
        email: email,
        phone: phone,
        password: password,
      );
      if (!mounted) return;
      if (res['ok'] != true) {
        setState(() {
          _busy = false;
          _error =
              (res['error'] ?? 'Could not send verification code').toString();
        });
        return;
      }
      setState(() {
        _busy = false;
        _signupCodeSent = true;
        _info = 'Verification code sent to $email';
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
    final user = await api.verifySignupCode(email: email, code: code);
    if (!mounted) return;
    if (user == null) {
      setState(() {
        _busy = false;
        _error = 'Signup verification failed. Check code and try again.';
      });
      return;
    }
    await widget.onLoggedIn(user);
    if (!mounted) return;
    setState(() => _busy = false);
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
    final res = await api.requestPasswordReset(identifier: identifier);
    if (!mounted) return;
    if (res['ok'] != true) {
      setState(() {
        _busy = false;
        _error = (res['error'] ?? 'Reset request failed').toString();
      });
      return;
    }
    final data = (res['data'] as Map<String, dynamic>?) ?? {};
    final username = (data['username'] ?? '').toString();
    final code = (data['code'] ?? '').toString();
    setState(() {
      _busy = false;
      _forgotUserController.text = username;
      _info = 'Reset code: $code';
    });
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
    final res = await api.resetPassword(
        username: username, code: code, newPassword: newPassword);
    if (!mounted) return;
    if (res['ok'] != true) {
      setState(() {
        _busy = false;
        _error = (res['error'] ?? 'Reset failed').toString();
      });
      return;
    }
    setState(() {
      _busy = false;
      _mode = 0;
      _info = 'Password reset successful. Please login.';
      _forgotCodeController.clear();
      _forgotNewPwController.clear();
      _pwController.clear();
    });
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
          label: Text(_busy ? 'Signing in...' : 'Login'),
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
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [Color(0xFF0F1728), Color(0xFF1A1A2E), Color(0xFF0D1425)],
          ),
        ),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 460),
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(18),
                    gradient: const LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [Color(0xFF2B5A84), Color(0xFF19253E)],
                    ),
                    border:
                        Border.all(color: const Color(0xFF496998), width: 1),
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
                const SizedBox(height: 12),
                Text(
                  'Server: ${buildBackendApi().baseUrl}',
                  textAlign: TextAlign.center,
                  style:
                      const TextStyle(color: Color(0xFFBFD4F4), fontSize: 12),
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 12),
                _modeSelector(),
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(14),
                    color: const Color(0xFF121C30),
                    border: Border.all(color: const Color(0xFF334A73)),
                  ),
                  child: Column(
                    children: [
                      if (_mode == 0) _loginForm(),
                      if (_mode == 1) _signupForm(),
                      if (_mode == 2) _forgotForm(),
                    ],
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
    final roleColor =
        _isAdmin ? const Color(0xFFE94560) : const Color(0xFF0F3460);

    return Scaffold(
      appBar: AppBar(
        backgroundColor: const Color(0xFF1A1A2E),
        foregroundColor: Colors.white,
        title: const Text('Face Studio'),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 12),
            child: Center(
              child: Text(
                _isAdmin ? 'Admin' : 'User',
                style:
                    const TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
              ),
            ),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(14),
        children: [
          const SizedBox(height: 6),
          const Text(
            'Face Studio',
            style: TextStyle(
              color: Color(0xFFE94560),
              fontSize: 28,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            '$roleText  |  Welcome, $_username',
            style: TextStyle(color: roleColor, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          const Text(
            'Choose a mode to get started',
            style: TextStyle(color: Color(0xFFA0A0B8)),
          ),
          const SizedBox(height: 12),
          ..._visibleItems.asMap().entries.map(
                (entry) => _AnimatedMenuCard(
                  delay: Duration(milliseconds: 80 * entry.key),
                  item: entry.value,
                  onTap: () => _openPage(entry.value.page),
                ),
              ),
          const SizedBox(height: 14),
          TextButton.icon(
            onPressed: () async {
              await widget.onLogout();
            },
            icon: const Icon(Icons.logout),
            label: const Text('Logout'),
          ),
          const Text(
            'Press back on any page to return here',
            textAlign: TextAlign.center,
            style: TextStyle(color: Color(0xFF555570), fontSize: 12),
          ),
          const SizedBox(height: 12),
        ],
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
  _KnownMapLocation _selectedLocation = _worldMapLocations.first;
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

  Future<void> _captureAndRecognize() async {
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

      final shot = await ctrl.takePicture();
      final file = File(shot.path);
      final bytes = await file.readAsBytes();
      final imageB64 = base64Encode(bytes);

      final uri = Uri.parse(
          '${_baseUrl.trim().replaceAll(RegExp(r'/$'), '')}/api/mobile/identify');
      final sessionUser = buildBackendApi().username;
      final res = await http.post(
        uri,
        headers: {
          'Authorization': 'Bearer $_token',
          'Content-Type': 'application/json',
        },
        body: jsonEncode({
          'image_b64': imageB64,
          'top_k': 1,
          'tracking': {
            'location_name': _selectedLocation.name,
            'latitude': _selectedLocation.latitude,
            'longitude': _selectedLocation.longitude,
            'requested_by': sessionUser.isEmpty ? 'mobile' : sessionUser,
          },
        }),
      );

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
      final saved = tracking['saved'] == true;
      final deduped =
          (tracking['reason'] ?? '').toString() == 'deduped_recent_event';
      final saveInfo = name.toLowerCase() == 'unknown'
          ? 'No save: unknown face'
          : saved
              ? 'Saved: $name at ${_selectedLocation.name}'
              : (deduped
                  ? 'Already saved recently for $name at ${_selectedLocation.name}'
                  : 'Save pending for $name');

      if (mounted) {
        setState(() {
          _topName = name;
          _topScore = score;
          _liveFaces = faces;
          _imgW = iw;
          _imgH = ih;
          _lastSavedInfo = saveInfo;
          _status = faces.isEmpty
              ? 'No match in current frame'
              : 'Live recognition running';
        });
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
    return Scaffold(
      appBar: AppBar(title: Text(widget.pageTitle)),
      body: Column(
        children: [
          Expanded(
            child: Container(
              color: Colors.black,
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
                          child: Card(
                            color: Colors.black.withValues(alpha: 0.65),
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
                                ],
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
            color: const Color(0xFF10182B),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Status: $_status',
                    style: const TextStyle(color: Colors.white)),
                const SizedBox(height: 8),
                DropdownButtonFormField<_KnownMapLocation>(
                  initialValue: _selectedLocation,
                  dropdownColor: const Color(0xFF11182A),
                  style: const TextStyle(color: Colors.white),
                  decoration: const InputDecoration(
                    labelText: 'Recognition Location',
                    labelStyle: TextStyle(color: Color(0xFFBBD0F8)),
                    filled: true,
                    fillColor: Color(0xFF0E1422),
                  ),
                  items: _worldMapLocations
                      .map(
                        (loc) => DropdownMenuItem<_KnownMapLocation>(
                          value: loc,
                          child: Text(loc.name),
                        ),
                      )
                      .toList(),
                  onChanged: (value) {
                    if (value == null) {
                      return;
                    }
                    setState(() {
                      _selectedLocation = value;
                    });
                  },
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
                    ElevatedButton(
                      onPressed: _captureAndRecognize,
                      child: const Text('Recognize Now'),
                    ),
                    ElevatedButton(
                      onPressed: () {
                        if (_loopTimer == null) {
                          _loopTimer =
                              Timer.periodic(const Duration(seconds: 2), (_) {
                            _captureAndRecognize();
                          });
                          setState(() => _status = 'Live recognition resumed');
                        }
                      },
                      child: const Text('Resume Live'),
                    ),
                    ElevatedButton(
                      onPressed: () {
                        _loopTimer?.cancel();
                        _loopTimer = null;
                        setState(() => _status = 'Live recognition paused');
                      },
                      child: const Text('Pause Live'),
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
          Card(
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Username: ${_profile['username'] ?? '-'}'),
                  Text('Email: ${_profile['email'] ?? '-'}'),
                  Text('Phone: ${_profile['phone'] ?? '-'}'),
                  Text('Role: ${_profile['role'] ?? '-'}'),
                  Text('Created: ${_profile['created'] ?? '-'}'),
                ],
              ),
            ),
          ),
          const SizedBox(height: 8),
          const Text('Recent Activity',
              style: TextStyle(fontWeight: FontWeight.bold)),
          const SizedBox(height: 6),
          ..._recentActivity.take(10).map(
                (a) => Card(
                  child: ListTile(
                    title: Text((a['action'] ?? 'Activity').toString()),
                    subtitle: Text((a['detail'] ?? '').toString()),
                    trailing: Text((a['event_time'] ?? '').toString(),
                        style: const TextStyle(fontSize: 11)),
                  ),
                ),
              ),
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

  @override
  void initState() {
    super.initState();
    _load();
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

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return Scaffold(
        appBar: AppBar(title: Text(widget.pageTitle)),
        body: const Center(child: CircularProgressIndicator()),
      );
    }
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
          Text('Total users: ${_users.length}',
              style: const TextStyle(fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          ..._users.map(
            (u) => Card(
              child: ListTile(
                leading: const Icon(Icons.person),
                title: Text((u['username'] ?? '-').toString()),
                subtitle: Text(
                  widget.showRoles
                      ? 'Role: ${(u['role'] ?? 'user')}  |  Email: ${(u['email'] ?? '-')}'
                      : 'Email: ${(u['email'] ?? '-')}  |  Phone: ${(u['phone'] ?? '-')}',
                ),
                trailing: Text((u['created'] ?? '').toString(),
                    style: const TextStyle(fontSize: 11)),
              ),
            ),
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
      final res = await api.searchRecognitionLocations(name: query, limit: 200);
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
            : 'Found ${data.length} recognition location records';
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
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Icon(Icons.location_on, color: Color(0xFFFF7D7D)),
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
                              style: const TextStyle(color: Color(0xFFD3DDF2))),
                        ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Text('Coordinates: ${lat ?? '-'}, ${lng ?? '-'}',
                        style: const TextStyle(color: Color(0xFFAABCE2))),
                  ],
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
          Card(
            child: ListTile(
              leading: const Icon(Icons.insights),
              title: Text(
                  'Users: ${_stats['users'] ?? 0}  |  Face Events: ${_stats['face_events'] ?? 0}'),
              subtitle: Text(
                  'Pending approvals: ${_stats['pending_approvals'] ?? 0}  |  DB: ${_stats['db_size_mb'] ?? 0} MB'),
            ),
          ),
          const SizedBox(height: 8),
          const Text('Activity Timeline',
              style: TextStyle(fontWeight: FontWeight.bold)),
          const SizedBox(height: 6),
          ..._activity.take(40).map(
                (a) => Card(
                  child: ListTile(
                    title: Text((a['action'] ?? '-').toString()),
                    subtitle: Text(
                        '${a['username'] ?? '-'} (${a['role'] ?? '-'}) - ${a['detail'] ?? ''}'),
                    trailing: Text((a['event_time'] ?? '').toString(),
                        style: const TextStyle(fontSize: 11)),
                  ),
                ),
              ),
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

  @override
  void initState() {
    super.initState();
    _load();
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
          Card(
            child: ListTile(
              leading: Icon(
                  _health['ok'] == true ? Icons.check_circle : Icons.error,
                  color:
                      _health['ok'] == true ? Colors.green : Colors.redAccent),
              title:
                  Text(_health['ok'] == true ? 'API Healthy' : 'API Unhealthy'),
              subtitle: Text('Server time: ${_health['time'] ?? '-'}'),
            ),
          ),
          Card(
            child: ListTile(
              title: Text('Public Endpoints: ${publicEndpoints.length}'),
              subtitle: Text('Secure Endpoints: ${secureEndpoints.length}'),
            ),
          ),
          const _SectionTitle('Public Endpoints'),
          ...publicEndpoints.map(
            (e) => Card(
              child: ListTile(
                leading: _MethodBadge((e['method'] ?? 'GET').toString()),
                title: Text((e['path'] ?? '').toString()),
              ),
            ),
          ),
          const _SectionTitle('Secure Endpoints'),
          ...secureEndpoints.map(
            (e) => Card(
              child: ListTile(
                leading: _MethodBadge((e['method'] ?? 'GET').toString()),
                title: Text((e['path'] ?? '').toString()),
              ),
            ),
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
    final bg =
        upper == 'POST' ? const Color(0xFF7A3A2F) : const Color(0xFF2B4A7C);
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

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    final tables = ((_db['tables'] as List?) ?? const [])
        .whereType<Map>()
        .map((e) => Map<String, dynamic>.from(e))
        .toList()
      ..sort((a, b) =>
          ((b['rows'] ?? 0) as int).compareTo((a['rows'] ?? 0) as int));
    final q = _searchController.text.trim().toLowerCase();
    final filtered = q.isEmpty
        ? tables
        : tables
            .where(
                (t) => (t['name'] ?? '').toString().toLowerCase().contains(q))
            .toList();
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
          Card(
            child: ListTile(
              title: Text('DB File: ${_db['db_path'] ?? '-'}'),
              subtitle: Text(
                  'Exists: ${_db['db_exists'] ?? false}  |  Size: ${_db['db_size_mb'] ?? 0} MB'),
            ),
          ),
          const SizedBox(height: 8),
          TextField(
            controller: _searchController,
            onChanged: (_) => setState(() {}),
            decoration: const InputDecoration(
              labelText: 'Search table',
              prefixIcon: Icon(Icons.search),
            ),
          ),
          const SizedBox(height: 8),
          Text('Showing ${filtered.length} of ${tables.length} tables',
              style: const TextStyle(color: Color(0xFFAAB2D6))),
          const SizedBox(height: 8),
          const _SectionTitle('Tables'),
          const SizedBox(height: 6),
          ...filtered.map(
            (t) => Card(
              child: ListTile(
                leading: const Icon(Icons.table_rows),
                title: Text((t['name'] ?? '-').toString()),
                trailing: Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: const Color(0xFF22304B),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Text('Rows: ${(t['rows'] ?? 0)}'),
                ),
              ),
            ),
          ),
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
  final String _apiKey =
      const String.fromEnvironment('FACE_STUDIO_API_KEY', defaultValue: '');
  String _text = 'Loading...';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      if (_apiKey.isEmpty) {
        setState(() => _text = 'API key missing for system info');
        return;
      }
      final b = _baseUrl.trim().replaceAll(RegExp(r'/$'), '');
      final tokenRes = await http.get(
        Uri.parse('$b/api/auth/token?subject=android_sys&ttl=60'),
        headers: {'X-API-Key': _apiKey},
      );
      if (tokenRes.statusCode != 200) {
        setState(() => _text = 'Token request failed: ${tokenRes.statusCode}');
        return;
      }
      final token = ((jsonDecode(tokenRes.body) as Map<String, dynamic>)['data']
                  ?['token'] ??
              '')
          .toString();
      final hRes = await http.get(Uri.parse('$b/api/health'));
      final sRes = await http.get(Uri.parse('$b/api/stats'),
          headers: {'Authorization': 'Bearer $token'});
      final data = {
        'health': hRes.statusCode == 200
            ? jsonDecode(hRes.body)
            : {'error': hRes.statusCode},
        'stats': sRes.statusCode == 200
            ? jsonDecode(sRes.body)
            : {'error': sRes.statusCode},
      };
      setState(() => _text = const JsonEncoder.withIndent('  ').convert(data));
    } catch (e) {
      setState(() => _text = 'System info error: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('System Info')),
      body: ListView(
        padding: const EdgeInsets.all(12),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(8),
              child: SelectableText(_text),
            ),
          )
        ],
      ),
    );
  }
}

class HelpAboutPage extends StatelessWidget {
  const HelpAboutPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Help & About')),
      body: const Padding(
        padding: EdgeInsets.all(12),
        child: Text(
          'Face Studio\n\n'
          '- Face Recognition: live webcam recognition with label overlay.\n'
          '- Face Generation: all desktop filter styles.\n'
          '- Face Comparison: compare two images using backend identify results.\n\n'
          'Note: Some advanced desktop-only modules require additional backend mobile APIs.',
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
  final _picker = ImagePicker();

  String _token = '';
  File? _pickedImage;
  File? _compareImage;
  File? _generatedImage;
  String _status = 'Ready';
  String _identifyJson = '';
  String _activeTool = 'identify';
  bool _bootstrapping = false;

  bool get _isGenerationModule => widget.moduleTitle == 'Face Generation';
  bool get _isCompareModule => widget.moduleTitle == 'Face Comparison';
  bool get _isProfileModule => widget.moduleTitle == 'My Profile';

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
    super.dispose();
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
  }

  Future<void> _captureFromCamera() async {
    final x =
        await _picker.pickImage(source: ImageSource.camera, imageQuality: 85);
    if (x == null) return;
    setState(() {
      _pickedImage = File(x.path);
      _generatedImage = null;
      _identifyJson = '';
      _status = 'Camera image captured';
    });
    if (_activeTool == 'identify') {
      await _identify();
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
    setState(() => _status = 'Running identify...');

    final imageB64 = base64Encode(await _pickedImage!.readAsBytes());
    final uri = Uri.parse('$baseUrl/api/mobile/identify');
    final res = await http.post(
      uri,
      headers: {
        'Authorization': 'Bearer $_token',
        'Content-Type': 'application/json',
      },
      body: jsonEncode({'image_b64': imageB64, 'top_k': 3}),
    );

    if (res.statusCode != 200) {
      setState(() => _status = 'Identify failed: ${res.statusCode}');
      return;
    }

    final data = jsonDecode(res.body) as Map<String, dynamic>;
    setState(() {
      _identifyJson = const JsonEncoder.withIndent('  ').convert(data['data']);
      _status = 'Identify complete';
    });
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
    });
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
        break;
      default:
        setState(() => _status = 'Tool not available yet');
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

  @override
  Widget build(BuildContext context) {
    final showResultJson = _identifyJson.isNotEmpty &&
        (_activeTool == 'identify' ||
            _activeTool == 'search' ||
            _isCompareModule);

    return Scaffold(
      appBar: AppBar(
        title: Text(widget.moduleTitle),
      ),
      body: ListView(
        padding: const EdgeInsets.all(12),
        children: [
          Card(
            color: const Color(0xFF10182B),
            child: Padding(
              padding: const EdgeInsets.all(10),
              child: Text(
                'Connected Backend: $_baseUrl',
                style: const TextStyle(color: Color(0xFFB4C6EA)),
              ),
            ),
          ),
          const SizedBox(height: 8),
          if (_isProfileModule) ...[
            const Card(
              color: Color(0xFF10182B),
              child: Padding(
                padding: EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Account',
                        style: TextStyle(
                            color: Colors.white, fontWeight: FontWeight.bold)),
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
                    onPressed: _runActiveTool,
                    child: Text(_activeTool.toUpperCase())),
            ],
          ),
          const SizedBox(height: 10),
          Text('Status: $_status', style: const TextStyle(color: Colors.white)),
          const SizedBox(height: 10),
          if (!_isProfileModule) _imageCard('Picked Image', _pickedImage),
          if (_isCompareModule) _imageCard('Second Image', _compareImage),
          if (_isGenerationModule || _generatedImage != null)
            _imageCard('Generated Image', _generatedImage),
          if (showResultJson)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(8),
                child: SelectableText(_identifyJson),
              ),
            ),
        ],
      ),
    );
  }
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
