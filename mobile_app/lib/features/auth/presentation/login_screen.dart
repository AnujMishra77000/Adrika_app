import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';

import '../state/auth_controller.dart';

enum AuthEntryMode {
  menu,
  studentLogin,
  teacherLogin,
  studentRegister,
  teacherRegister,
}

enum _AuthFlow {
  none,
  studentLogin,
  teacherLogin,
  studentRegister,
  teacherRegister,
}

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key, this.mode = AuthEntryMode.menu});

  final AuthEntryMode mode;

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _picker = ImagePicker();

  final _phoneController = TextEditingController();
  final _passwordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();

  final _studentNameController = TextEditingController();
  final _studentClassController = TextEditingController();
  final _studentParentPhoneController = TextEditingController();
  final _studentAddressController = TextEditingController();
  final _studentSchoolController = TextEditingController();

  final _teacherNameController = TextEditingController();
  final _teacherAgeController = TextEditingController();
  final _teacherQualificationController = TextEditingController();
  final _teacherSpecializationController = TextEditingController();
  final _teacherSchoolCollegeController = TextEditingController();
  final _teacherAddressController = TextEditingController();

  _AuthFlow _flow = _AuthFlow.none;
  String _studentStream = 'science';
  String _teacherGender = 'male';
  XFile? _studentPhoto;
  XFile? _teacherPhoto;

  bool _obscurePassword = true;
  bool _obscureConfirm = true;

  @override
  void initState() {
    super.initState();
    _flow = _flowFromMode(widget.mode);
  }

  @override
  void didUpdateWidget(covariant LoginScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.mode != widget.mode) {
      setState(() {
        _flow = _flowFromMode(widget.mode);
      });
    }
  }

  _AuthFlow _flowFromMode(AuthEntryMode mode) {
    switch (mode) {
      case AuthEntryMode.studentLogin:
        return _AuthFlow.studentLogin;
      case AuthEntryMode.teacherLogin:
        return _AuthFlow.teacherLogin;
      case AuthEntryMode.studentRegister:
        return _AuthFlow.studentRegister;
      case AuthEntryMode.teacherRegister:
        return _AuthFlow.teacherRegister;
      case AuthEntryMode.menu:
        return _AuthFlow.none;
    }
  }

  @override
  void dispose() {
    _phoneController.dispose();
    _passwordController.dispose();
    _confirmPasswordController.dispose();

    _studentNameController.dispose();
    _studentClassController.dispose();
    _studentParentPhoneController.dispose();
    _studentAddressController.dispose();
    _studentSchoolController.dispose();

    _teacherNameController.dispose();
    _teacherAgeController.dispose();
    _teacherQualificationController.dispose();
    _teacherSpecializationController.dispose();
    _teacherSchoolCollegeController.dispose();
    _teacherAddressController.dispose();
    super.dispose();
  }

  Future<void> _pickPhoto({required bool student}) async {
    final file = await _picker.pickImage(
      source: ImageSource.gallery,
      maxWidth: 1024,
      imageQuality: 85,
    );

    if (file == null || !mounted) {
      return;
    }

    setState(() {
      if (student) {
        _studentPhoto = file;
      } else {
        _teacherPhoto = file;
      }
    });
  }

  void _goTo(String route, _AuthFlow fallbackFlow) {
    debugPrint('auth_nav_tap route=$route flow=${fallbackFlow.name}');
    _formKey.currentState?.reset();

    // Always switch local form state immediately so UI never appears stuck.
    setState(() {
      _flow = fallbackFlow;
      _obscurePassword = true;
      _obscureConfirm = true;
      _passwordController.clear();
      _confirmPasswordController.clear();
      _phoneController.clear();
    });

    final message = switch (fallbackFlow) {
      _AuthFlow.studentLogin => 'Opening Student Login',
      _AuthFlow.teacherLogin => 'Opening Teacher Login',
      _AuthFlow.studentRegister => 'Opening Student Registration',
      _AuthFlow.teacherRegister => 'Opening Teacher Registration',
      _AuthFlow.none => 'Opening menu',
    };

    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(
          content: Text(message),
          duration: const Duration(milliseconds: 700),
        ),
      );

    context.push(route);
  }

  void _backToMenu() {
    ref.read(authControllerProvider.notifier).clearMessages();
    _passwordController.clear();
    _confirmPasswordController.clear();
    _phoneController.clear();

    if (_flow != _AuthFlow.none) {
      setState(() {
        _flow = _AuthFlow.none;
      });
    }

    context.go('/login');
  }

  Future<void> _submit() async {
    FocusScope.of(context).unfocus();
    ref.read(authControllerProvider.notifier).clearMessages();

    final valid = _formKey.currentState?.validate() ?? false;
    if (!valid) {
      return;
    }

    if (_isLoginFlow) {
      final success = await ref.read(authControllerProvider.notifier).login(
            identifier: _phoneController.text.trim(),
            password: _passwordController.text,
          );

      if (!mounted || !success) {
        return;
      }

      final auth = ref.read(authControllerProvider);
      final roleNeeded =
          _activeFlow == _AuthFlow.studentLogin ? 'student' : 'teacher';

      if (!auth.roles.contains(roleNeeded)) {
        await ref.read(authControllerProvider.notifier).logout();
        if (!mounted) {
          return;
        }
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              roleNeeded == 'student'
                  ? 'This account is not a student account. Use Teacher Login.'
                  : 'This account is not a teacher account. Use Student Login.',
            ),
          ),
        );
        return;
      }

      context.go('/boot');
      return;
    }

    if (_passwordController.text != _confirmPasswordController.text) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Password and confirm password must match.')),
      );
      return;
    }

    bool success;
    if (_activeFlow == _AuthFlow.studentRegister) {
      success = await ref.read(authControllerProvider.notifier).registerStudent(
            name: _studentNameController.text.trim(),
            className: _studentClassController.text.trim(),
            stream: _studentStream,
            contactNumber: _phoneController.text.trim(),
            password: _passwordController.text,
            confirmPassword: _confirmPasswordController.text,
            parentContactNumber: _studentParentPhoneController.text.trim(),
            address: _studentAddressController.text.trim(),
            schoolDetails: _studentSchoolController.text.trim(),
            photoPath: _studentPhoto?.path,
          );
    } else {
      final age = int.tryParse(_teacherAgeController.text.trim());
      if (age == null) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Please enter a valid age.')),
        );
        return;
      }
      success = await ref.read(authControllerProvider.notifier).registerTeacher(
            name: _teacherNameController.text.trim(),
            age: age,
            gender: _teacherGender,
            qualification: _teacherQualificationController.text.trim(),
            specialization: _teacherSpecializationController.text.trim(),
            schoolCollege: _teacherSchoolCollegeController.text.trim().isEmpty
                ? null
                : _teacherSchoolCollegeController.text.trim(),
            contactNumber: _phoneController.text.trim(),
            password: _passwordController.text,
            confirmPassword: _confirmPasswordController.text,
            address: _teacherAddressController.text.trim(),
            photoPath: _teacherPhoto?.path,
          );
    }

    if (!mounted) {
      return;
    }

    final auth = ref.read(authControllerProvider);
    if (success) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            auth.infoMessage ??
                'Registration submitted. Admin approval is required before login.',
          ),
        ),
      );
      _backToMenu();
    }
  }

  _AuthFlow get _activeFlow {
    if (_flow != _AuthFlow.none) {
      return _flow;
    }
    return _flowFromMode(widget.mode);
  }

  bool get _isLoginFlow =>
      _activeFlow == _AuthFlow.studentLogin || _activeFlow == _AuthFlow.teacherLogin;

  bool get _isStudentFlow =>
      _activeFlow == _AuthFlow.studentLogin || _activeFlow == _AuthFlow.studentRegister;

  String get _screenTitle {
    switch (_activeFlow) {
      case _AuthFlow.studentLogin:
        return 'Student Login';
      case _AuthFlow.teacherLogin:
        return 'Teacher Login';
      case _AuthFlow.studentRegister:
        return 'Student Registration';
      case _AuthFlow.teacherRegister:
        return 'Teacher Registration';
      case _AuthFlow.none:
        return 'ADR Coaching Mobile';
    }
  }

  String get _primaryButtonLabel {
    switch (_activeFlow) {
      case _AuthFlow.studentLogin:
        return 'Student Login';
      case _AuthFlow.teacherLogin:
        return 'Teacher Login';
      case _AuthFlow.studentRegister:
        return 'Register Student';
      case _AuthFlow.teacherRegister:
        return 'Register Teacher';
      case _AuthFlow.none:
        return 'Continue';
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = ref.watch(authControllerProvider);

    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              Color(0xFFF4EEFF),
              Color(0xFFE9FDF3),
              Color(0xFFEAF7FF),
            ],
          ),
        ),
        child: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(20),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 760),
                child: Card(
                  elevation: 10,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(24),
                  ),
                  child: Padding(
                    padding: const EdgeInsets.all(20),
                    child: _activeFlow == _AuthFlow.none
                        ? _buildActionMenu()
                        : _buildFlowForm(auth),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildActionMenu() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          'ADR Coaching Mobile',
          style: Theme.of(context).textTheme.headlineSmall,
        ),
        const SizedBox(height: 8),
        const Text(
          'Choose one option to continue.',
        ),
        const SizedBox(height: 4),
        const Text(
          'Build: tapfix-2026-04-08',
          style: TextStyle(fontSize: 12, color: Color(0xFF64748B)),
        ),
        const SizedBox(height: 20),
        _actionButton(
          label: 'Student Login',
          icon: Icons.school_rounded,
          onTap: () => _goTo('/login/student', _AuthFlow.studentLogin),
        ),
        const SizedBox(height: 10),
        _actionButton(
          label: 'Teacher Login',
          icon: Icons.menu_book_rounded,
          onTap: () => _goTo('/login/teacher', _AuthFlow.teacherLogin),
        ),
        const SizedBox(height: 18),
        _actionButton(
          label: 'Student Registration',
          icon: Icons.how_to_reg_rounded,
          onTap: () => _goTo('/register/student', _AuthFlow.studentRegister),
          outlined: true,
        ),
        const SizedBox(height: 10),
        _actionButton(
          label: 'Teacher Registration',
          icon: Icons.person_add_alt_1_rounded,
          onTap: () => _goTo('/register/teacher', _AuthFlow.teacherRegister),
          outlined: true,
        ),
      ],
    );
  }

  Widget _buildFlowForm(AuthState auth) {
    return Form(
      key: _formKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              IconButton(
                onPressed: _backToMenu,
                icon: const Icon(Icons.arrow_back_rounded),
              ),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  _screenTitle,
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          _buildPhoneField(),
          const SizedBox(height: 12),
          _buildPasswordField(),
          if (!_isLoginFlow) ...[
            const SizedBox(height: 12),
            _buildConfirmPasswordField(),
            const SizedBox(height: 12),
            if (_isStudentFlow) _buildStudentRegistrationFields(),
            if (!_isStudentFlow) _buildTeacherRegistrationFields(),
          ],
          const SizedBox(height: 16),
          FilledButton(
            onPressed: auth.isLoading ? null : _submit,
            child: auth.isLoading
                ? const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : Text(_primaryButtonLabel),
          ),
          if (auth.errorMessage != null) ...[
            const SizedBox(height: 10),
            Text(
              auth.errorMessage!,
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
          ],
        ],
      ),
    );
  }

  Widget _actionButton({
    required String label,
    required IconData icon,
    required VoidCallback onTap,
    bool outlined = false,
  }) {
    if (outlined) {
      return SizedBox(
        width: double.infinity,
        child: OutlinedButton.icon(
          onPressed: onTap,
          icon: Icon(icon),
          label: Row(
            children: [
              Expanded(child: Text(label)),
              const Icon(Icons.arrow_forward_rounded, size: 18),
            ],
          ),
        ),
      );
    }

    return SizedBox(
      width: double.infinity,
      child: FilledButton.icon(
        onPressed: onTap,
        icon: Icon(icon),
        label: Row(
          children: [
            Expanded(child: Text(label)),
            const Icon(Icons.arrow_forward_rounded, size: 18),
          ],
        ),
      ),
    );
  }

  Widget _buildPhoneField() {
    return TextFormField(
      controller: _phoneController,
      keyboardType: TextInputType.phone,
      decoration: const InputDecoration(
        labelText: 'Contact Number',
        prefixIcon: Icon(Icons.phone_android_rounded),
      ),
      validator: (value) {
        final text = (value ?? '').trim();
        if (text.isEmpty) {
          return 'Contact number is required';
        }
        if (text.length < 10) {
          return 'Enter a valid contact number';
        }
        return null;
      },
    );
  }

  Widget _buildPasswordField() {
    return TextFormField(
      controller: _passwordController,
      obscureText: _obscurePassword,
      decoration: InputDecoration(
        labelText: 'Password',
        prefixIcon: const Icon(Icons.lock_rounded),
        suffixIcon: IconButton(
          onPressed: () {
            setState(() {
              _obscurePassword = !_obscurePassword;
            });
          },
          icon: Icon(
            _obscurePassword
                ? Icons.visibility_off_rounded
                : Icons.visibility_rounded,
          ),
        ),
      ),
      validator: (value) {
        if ((value ?? '').length < 8) {
          return 'Password must be at least 8 characters';
        }
        return null;
      },
    );
  }

  Widget _buildConfirmPasswordField() {
    return TextFormField(
      controller: _confirmPasswordController,
      obscureText: _obscureConfirm,
      decoration: InputDecoration(
        labelText: 'Confirm Password',
        prefixIcon: const Icon(Icons.verified_user_rounded),
        suffixIcon: IconButton(
          onPressed: () {
            setState(() {
              _obscureConfirm = !_obscureConfirm;
            });
          },
          icon: Icon(
            _obscureConfirm
                ? Icons.visibility_off_rounded
                : Icons.visibility_rounded,
          ),
        ),
      ),
      validator: (value) {
        if (!_isLoginFlow && (value ?? '').isEmpty) {
          return 'Confirm password is required';
        }
        return null;
      },
    );
  }

  Widget _buildStudentRegistrationFields() {
    return Column(
      children: [
        TextFormField(
          controller: _studentNameController,
          decoration: const InputDecoration(labelText: 'Student Name'),
          validator: _requiredValidator,
        ),
        const SizedBox(height: 12),
        TextFormField(
          controller: _studentClassController,
          decoration: const InputDecoration(labelText: 'Class'),
          validator: _requiredValidator,
        ),
        const SizedBox(height: 12),
        DropdownButtonFormField<String>(
          initialValue: _studentStream,
          decoration: const InputDecoration(labelText: 'Stream / Subject'),
          items: const [
            DropdownMenuItem(value: 'science', child: Text('Science')),
            DropdownMenuItem(value: 'commerce', child: Text('Commerce')),
            DropdownMenuItem(
              value: 'common',
              child: Text('Common (Class 10 and below)'),
            ),
          ],
          onChanged: (value) {
            if (value == null) {
              return;
            }
            setState(() {
              _studentStream = value;
            });
          },
        ),
        const SizedBox(height: 12),
        TextFormField(
          controller: _studentParentPhoneController,
          keyboardType: TextInputType.phone,
          decoration: const InputDecoration(labelText: 'Parent Contact Number'),
          validator: _requiredValidator,
        ),
        const SizedBox(height: 12),
        TextFormField(
          controller: _studentAddressController,
          decoration: const InputDecoration(labelText: 'Address'),
          validator: _requiredValidator,
        ),
        const SizedBox(height: 12),
        TextFormField(
          controller: _studentSchoolController,
          decoration: const InputDecoration(labelText: 'School Details'),
          validator: _requiredValidator,
        ),
        const SizedBox(height: 12),
        _PhotoPickerTile(
          title: 'Upload Photo',
          fileLabel: _studentPhoto == null
              ? 'No file selected'
              : _studentPhoto!.path.split('/').last,
          onPick: () => _pickPhoto(student: true),
        ),
      ],
    );
  }

  Widget _buildTeacherRegistrationFields() {
    return Column(
      children: [
        TextFormField(
          controller: _teacherNameController,
          decoration: const InputDecoration(labelText: 'Teacher Name'),
          validator: _requiredValidator,
        ),
        const SizedBox(height: 12),
        TextFormField(
          controller: _teacherAgeController,
          keyboardType: TextInputType.number,
          decoration: const InputDecoration(labelText: 'Age'),
          validator: _requiredValidator,
        ),
        const SizedBox(height: 12),
        DropdownButtonFormField<String>(
          initialValue: _teacherGender,
          decoration: const InputDecoration(labelText: 'Gender'),
          items: const [
            DropdownMenuItem(value: 'male', child: Text('Male')),
            DropdownMenuItem(value: 'female', child: Text('Female')),
            DropdownMenuItem(value: 'other', child: Text('Other')),
          ],
          onChanged: (value) {
            if (value == null) {
              return;
            }
            setState(() {
              _teacherGender = value;
            });
          },
        ),
        const SizedBox(height: 12),
        TextFormField(
          controller: _teacherQualificationController,
          decoration: const InputDecoration(labelText: 'Qualification'),
          validator: _requiredValidator,
        ),
        const SizedBox(height: 12),
        TextFormField(
          controller: _teacherSpecializationController,
          decoration: const InputDecoration(labelText: 'Specialization'),
          validator: _requiredValidator,
        ),
        const SizedBox(height: 12),
        TextFormField(
          controller: _teacherSchoolCollegeController,
          decoration: const InputDecoration(
            labelText: 'School / College (Optional)',
          ),
        ),
        const SizedBox(height: 12),
        TextFormField(
          controller: _teacherAddressController,
          decoration: const InputDecoration(labelText: 'Address'),
          validator: _requiredValidator,
        ),
        const SizedBox(height: 12),
        _PhotoPickerTile(
          title: 'Upload Photo',
          fileLabel: _teacherPhoto == null
              ? 'No file selected'
              : _teacherPhoto!.path.split('/').last,
          onPick: () => _pickPhoto(student: false),
        ),
      ],
    );
  }

  String? _requiredValidator(String? value) {
    if ((value ?? '').trim().isEmpty) {
      return 'This field is required';
    }
    return null;
  }
}

class _PhotoPickerTile extends StatelessWidget {
  const _PhotoPickerTile({
    required this.title,
    required this.fileLabel,
    required this.onPick,
  });

  final String title;
  final String fileLabel;
  final VoidCallback onPick;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: Theme.of(context).textTheme.titleSmall),
                const SizedBox(height: 4),
                Text(fileLabel, style: Theme.of(context).textTheme.bodySmall),
              ],
            ),
          ),
          OutlinedButton.icon(
            onPressed: onPick,
            icon: const Icon(Icons.upload_file_rounded),
            label: const Text('Select'),
          ),
        ],
      ),
    );
  }
}
