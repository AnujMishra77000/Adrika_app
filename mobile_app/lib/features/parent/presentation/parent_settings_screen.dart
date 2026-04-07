import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/network/app_exception.dart';
import '../../auth/state/auth_controller.dart';
import '../data/parent_api.dart';
import '../models/parent_models.dart';
import '../state/parent_providers.dart';

class ParentSettingsScreen extends ConsumerStatefulWidget {
  const ParentSettingsScreen({super.key});

  @override
  ConsumerState<ParentSettingsScreen> createState() =>
      _ParentSettingsScreenState();
}

class _ParentSettingsScreenState extends ConsumerState<ParentSettingsScreen> {
  bool _initialized = false;
  bool _saving = false;

  bool _inAppEnabled = true;
  bool _pushEnabled = true;
  bool _whatsappEnabled = false;
  bool _feeRemindersEnabled = true;
  String _preferredLanguage = 'en';

  Future<void> _savePreferences() async {
    final token = ref.read(authControllerProvider).accessToken;
    if (token == null || token.isEmpty) {
      return;
    }

    setState(() {
      _saving = true;
    });

    try {
      await ref.read(parentApiProvider).updatePreferences(
            accessToken: token,
            preference: ParentPreference(
              inAppEnabled: _inAppEnabled,
              pushEnabled: _pushEnabled,
              whatsappEnabled: _whatsappEnabled,
              feeRemindersEnabled: _feeRemindersEnabled,
              preferredLanguage: _preferredLanguage,
            ),
          );
      ref.invalidate(parentPreferencesProvider);
      ref.invalidate(parentProfileProvider);

      if (!mounted) {
        return;
      }

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Preferences updated successfully.')),
      );
    } on AppException catch (error) {
      if (!mounted) {
        return;
      }

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(error.message)),
      );
    } finally {
      if (mounted) {
        setState(() {
          _saving = false;
        });
      }
    }
  }

  Future<void> _logout() async {
    await ref.read(authControllerProvider.notifier).logout();
    if (mounted) {
      context.go('/login');
    }
  }

  @override
  Widget build(BuildContext context) {
    final profile = ref.watch(parentProfileProvider);
    final preferences = ref.watch(parentPreferencesProvider);

    preferences.whenData((pref) {
      if (_initialized) {
        return;
      }

      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted) {
          return;
        }

        setState(() {
          _inAppEnabled = pref.inAppEnabled;
          _pushEnabled = pref.pushEnabled;
          _whatsappEnabled = pref.whatsappEnabled;
          _feeRemindersEnabled = pref.feeRemindersEnabled;
          _preferredLanguage = pref.preferredLanguage;
          _initialized = true;
        });
      });
    });

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        profile.when(
          data: (data) => Card(
            child: ListTile(
              title: Text(data.fullName),
              subtitle: Text('${data.email ?? '-'} | ${data.phone ?? '-'}'),
              trailing: Text('Students: ${data.linkedStudentsCount}'),
            ),
          ),
          loading: () => const Card(
            child: Padding(
              padding: EdgeInsets.all(16),
              child: CircularProgressIndicator(),
            ),
          ),
          error: (error, _) => Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Text(
                error.toString(),
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ),
          ),
        ),
        const SizedBox(height: 12),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Communication Preferences',
                    style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 8),
                SwitchListTile(
                  value: _inAppEnabled,
                  onChanged: (value) => setState(() => _inAppEnabled = value),
                  contentPadding: EdgeInsets.zero,
                  title: const Text('In-app Notifications'),
                ),
                SwitchListTile(
                  value: _pushEnabled,
                  onChanged: (value) => setState(() => _pushEnabled = value),
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Push Notifications'),
                ),
                SwitchListTile(
                  value: _whatsappEnabled,
                  onChanged: (value) =>
                      setState(() => _whatsappEnabled = value),
                  contentPadding: EdgeInsets.zero,
                  title: const Text('WhatsApp Notifications'),
                ),
                SwitchListTile(
                  value: _feeRemindersEnabled,
                  onChanged: (value) =>
                      setState(() => _feeRemindersEnabled = value),
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Fee Reminders'),
                ),
                const SizedBox(height: 8),
                DropdownButtonFormField<String>(
                  key: ValueKey(_preferredLanguage),
                  initialValue: _preferredLanguage,
                  decoration: const InputDecoration(
                    labelText: 'Preferred Language',
                    border: OutlineInputBorder(),
                  ),
                  items: const [
                    DropdownMenuItem(value: 'en', child: Text('English')),
                    DropdownMenuItem(value: 'hi', child: Text('Hindi')),
                  ],
                  onChanged: (value) {
                    if (value != null) {
                      setState(() => _preferredLanguage = value);
                    }
                  },
                ),
                const SizedBox(height: 12),
                FilledButton(
                  onPressed: _saving ? null : _savePreferences,
                  child: _saving
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Text('Save Preferences'),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),
        OutlinedButton.icon(
          onPressed: _logout,
          icon: const Icon(Icons.logout),
          label: const Text('Logout'),
        ),
      ],
    );
  }
}
