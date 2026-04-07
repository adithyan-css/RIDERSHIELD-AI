import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/rider_provider.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _phoneCtrl = TextEditingController();
  final _otpCtrl = TextEditingController();
  final _nameCtrl = TextEditingController();
  final _companyCtrl = TextEditingController(text: 'demo_company');
  bool _isRegister = false;
  bool _loading = false;
  String? _error;

  @override
  Widget build(BuildContext context) {
    final teal = const Color(0xFF00C8A0);
    return Scaffold(
      backgroundColor: const Color(0xFF0A0F1E),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(28),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 48),
              Row(children: [
                Container(
                  width: 44, height: 44,
                  decoration: BoxDecoration(
                    color: teal.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(Icons.shield, color: teal, size: 26),
                ),
                const SizedBox(width: 12),
                Text('RiderShield',
                    style: TextStyle(
                        color: teal,
                        fontSize: 26,
                        fontWeight: FontWeight.w700,
                        letterSpacing: -0.5)),
              ]),
              const SizedBox(height: 8),
              Text(
                _isRegister ? 'Create your rider account' : 'Welcome back, rider',
                style: const TextStyle(color: Colors.white70, fontSize: 15),
              ),
              const SizedBox(height: 40),
              if (_isRegister) ...[
                _field(_nameCtrl, 'Full Name', Icons.person_outline),
                const SizedBox(height: 16),
                _field(_companyCtrl, 'Company ID', Icons.business_outlined),
                const SizedBox(height: 16),
              ],
              _field(_phoneCtrl, 'Phone Number', Icons.phone_outlined,
                  type: TextInputType.phone),
              const SizedBox(height: 16),
              _field(_otpCtrl, _isRegister ? 'Create PIN' : 'OTP / PIN',
                  Icons.lock_outline,
                  obscure: true),
              if (_error != null) ...[
                const SizedBox(height: 12),
                Text(_error!, style: const TextStyle(color: Colors.redAccent, fontSize: 13)),
              ],
              const SizedBox(height: 28),
              SizedBox(
                width: double.infinity,
                height: 52,
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: teal,
                    foregroundColor: Colors.black,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                  ),
                  onPressed: _loading ? null : _submit,
                  child: _loading
                      ? const SizedBox(
                          width: 22, height: 22,
                          child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black))
                      : Text(_isRegister ? 'Register' : 'Login',
                          style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
                ),
              ),
              const SizedBox(height: 20),
              GestureDetector(
                onTap: () => setState(() {
                  _isRegister = !_isRegister;
                  _error = null;
                }),
                child: Center(
                  child: Text(
                    _isRegister
                        ? 'Already have an account? Login'
                        : "Don't have an account? Register",
                    style: TextStyle(color: teal, fontSize: 13),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _field(TextEditingController ctrl, String hint, IconData icon,
      {bool obscure = false, TextInputType type = TextInputType.text}) {
    return TextField(
      controller: ctrl,
      obscureText: obscure,
      keyboardType: type,
      style: const TextStyle(color: Colors.white),
      decoration: InputDecoration(
        hintText: hint,
        hintStyle: const TextStyle(color: Colors.white38),
        prefixIcon: Icon(icon, color: Colors.white38, size: 20),
        filled: true,
        fillColor: const Color(0xFF131C33),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide.none,
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: Color(0xFF00C8A0), width: 1.5),
        ),
      ),
    );
  }

  Future<void> _submit() async {
    setState(() { _loading = true; _error = null; });
    try {
      final rider = context.read<RiderProvider>();
      if (_isRegister) {
        await rider.register(_nameCtrl.text.trim(), _phoneCtrl.text.trim(), _companyCtrl.text.trim());
      } else {
        await rider.login(_phoneCtrl.text.trim(), _otpCtrl.text.trim());
      }
    } catch (e) {
      setState(() => _error = 'Login failed. Check credentials or server.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }
}
