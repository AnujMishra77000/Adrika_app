import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/parent_models.dart';
import '../state/parent_providers.dart';

class ParentFeesScreen extends ConsumerWidget {
  const ParentFeesScreen({super.key});

  Future<void> _refresh(WidgetRef ref, String studentId) async {
    ref.invalidate(parentFeeInvoicesByStudentProvider(studentId));
    ref.invalidate(parentPaymentsByStudentProvider(studentId));
    ref.invalidate(parentDashboardProvider);

    await Future.wait([
      ref.read(parentFeeInvoicesByStudentProvider(studentId).future),
      ref.read(parentPaymentsByStudentProvider(studentId).future),
      ref.read(parentDashboardProvider.future),
    ]);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final students = ref.watch(linkedStudentsProvider);

    return students.when(
      data: (items) {
        if (items.isEmpty) {
          return const Center(child: Text('No linked students found.'));
        }

        final selectedStudentId =
            ref.watch(activeStudentIdProvider) ?? items.first.studentId;

        final invoices =
            ref.watch(parentFeeInvoicesByStudentProvider(selectedStudentId));
        final payments = ref.watch(parentPaymentsByStudentProvider(selectedStudentId));

        return RefreshIndicator(
          onRefresh: () => _refresh(ref, selectedStudentId),
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.all(16),
            children: [
              DropdownButtonFormField<String>(
                key: ValueKey(selectedStudentId),
                initialValue: selectedStudentId,
                decoration: const InputDecoration(
                  labelText: 'Student',
                  border: OutlineInputBorder(),
                ),
                items: items
                    .map(
                      (student) => DropdownMenuItem<String>(
                        value: student.studentId,
                        child: Text('${student.fullName} (${student.rollNo})'),
                      ),
                    )
                    .toList(growable: false),
                onChanged: (value) {
                  if (value != null) {
                    ref.read(selectedStudentIdProvider.notifier).state = value;
                  }
                },
              ),
              const SizedBox(height: 12),
              _FeeSummaryCard(asyncInvoices: invoices, asyncPayments: payments),
              const SizedBox(height: 12),
              _InvoiceList(asyncInvoices: invoices),
              const SizedBox(height: 12),
              _PaymentList(asyncPayments: payments),
            ],
          ),
        );
      },
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (error, _) => Center(
        child: Text(
          error.toString(),
          style: TextStyle(color: Theme.of(context).colorScheme.error),
        ),
      ),
    );
  }
}

class _FeeSummaryCard extends StatelessWidget {
  const _FeeSummaryCard({
    required this.asyncInvoices,
    required this.asyncPayments,
  });

  final AsyncValue<List<ParentFeeInvoice>> asyncInvoices;
  final AsyncValue<List<ParentPayment>> asyncPayments;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: asyncInvoices.when(
          data: (invoices) {
            final pendingAmount = invoices
                .where((invoice) =>
                    invoice.status == 'pending' || invoice.status == 'overdue')
                .fold<double>(0, (sum, invoice) => sum + invoice.amount);

            final paidAmount = invoices
                .where((invoice) => invoice.status == 'paid')
                .fold<double>(0, (sum, invoice) => sum + invoice.amount);

            final paymentsCount = asyncPayments.maybeWhen(
              data: (items) => items.length,
              orElse: () => 0,
            );

            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Fee Summary',
                    style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 8),
                Text('Total Invoices: ${invoices.length}'),
                Text('Paid Amount: ₹${paidAmount.toStringAsFixed(2)}'),
                Text('Pending Amount: ₹${pendingAmount.toStringAsFixed(2)}'),
                Text('Payments Recorded: $paymentsCount'),
              ],
            );
          },
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (error, _) => Text(
            error.toString(),
            style: TextStyle(color: Theme.of(context).colorScheme.error),
          ),
        ),
      ),
    );
  }
}

class _InvoiceList extends StatelessWidget {
  const _InvoiceList({required this.asyncInvoices});

  final AsyncValue<List<ParentFeeInvoice>> asyncInvoices;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Invoices', style: Theme.of(context).textTheme.titleMedium),
            const Divider(),
            asyncInvoices.when(
              data: (items) {
                if (items.isEmpty) {
                  return const Text('No invoices found.');
                }

                return Column(
                  children: items
                      .map(
                        (invoice) => ListTile(
                          contentPadding: EdgeInsets.zero,
                          title: Text('${invoice.invoiceNo} • ${invoice.periodLabel}'),
                          subtitle: Text(
                            'Due: ${invoice.dueDate} • Status: ${invoice.status}',
                          ),
                          trailing: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            crossAxisAlignment: CrossAxisAlignment.end,
                            children: [
                              Text('₹${invoice.amount.toStringAsFixed(2)}'),
                              Text(_formatDate(invoice.paidAt)),
                            ],
                          ),
                        ),
                      )
                      .toList(growable: false),
                );
              },
              loading: () => const CircularProgressIndicator(strokeWidth: 2),
              error: (error, _) => Text(
                error.toString(),
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _PaymentList extends StatelessWidget {
  const _PaymentList({required this.asyncPayments});

  final AsyncValue<List<ParentPayment>> asyncPayments;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Payments', style: Theme.of(context).textTheme.titleMedium),
            const Divider(),
            asyncPayments.when(
              data: (items) {
                if (items.isEmpty) {
                  return const Text('No payments found.');
                }

                return Column(
                  children: items
                      .map(
                        (payment) => ListTile(
                          contentPadding: EdgeInsets.zero,
                          title: Text('${payment.provider} • ${payment.status}'),
                          subtitle: Text(
                            'Ref: ${payment.externalRef ?? '-'} • ${_formatDate(payment.paidAt)}',
                          ),
                          trailing: Text('₹${payment.amount.toStringAsFixed(2)}'),
                        ),
                      )
                      .toList(growable: false),
                );
              },
              loading: () => const CircularProgressIndicator(strokeWidth: 2),
              error: (error, _) => Text(
                error.toString(),
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

String _formatDate(String? value) {
  if (value == null || value.isEmpty) {
    return '-';
  }
  return value.split('T').first;
}
