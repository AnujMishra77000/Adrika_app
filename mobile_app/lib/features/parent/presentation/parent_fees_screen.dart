import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/parent_models.dart';
import '../state/parent_providers.dart';

class ParentFeesScreen extends ConsumerWidget {
  const ParentFeesScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final students = ref.watch(linkedStudentsProvider);

    return students.when(
      data: (items) {
        if (items.isEmpty) {
          return const Center(child: Text('No linked students found.'));
        }

        final selected =
            ref.watch(selectedStudentIdProvider) ?? items.first.studentId;
        if (ref.watch(selectedStudentIdProvider) == null) {
          Future.microtask(() {
            ref.read(selectedStudentIdProvider.notifier).state =
                items.first.studentId;
          });
        }

        final invoices = ref.watch(feeInvoicesProvider);
        final payments = ref.watch(paymentsProvider);

        return ListView(
          padding: const EdgeInsets.all(16),
          children: [
            DropdownButtonFormField<String>(
              key: ValueKey(selected),
              initialValue: selected,
              decoration: const InputDecoration(
                labelText: 'Student',
                border: OutlineInputBorder(),
              ),
              items: items
                  .map(
                    (student) => DropdownMenuItem<String>(
                      value: student.studentId,
                      child: Text(student.fullName),
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
            _FeeSummaryCard(asyncInvoices: invoices),
            const SizedBox(height: 12),
            _InvoiceList(asyncInvoices: invoices),
            const SizedBox(height: 12),
            _PaymentList(asyncPayments: payments),
          ],
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
  const _FeeSummaryCard({required this.asyncInvoices});

  final AsyncValue<List<ParentFeeInvoice>> asyncInvoices;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: asyncInvoices.when(
          data: (items) {
            final pendingAmount = items
                .where((invoice) =>
                    invoice.status == 'pending' || invoice.status == 'overdue')
                .fold<double>(0, (sum, invoice) => sum + invoice.amount);

            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Fee Summary',
                    style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 8),
                Text('Total Invoices: ${items.length}'),
                Text('Pending Amount: ₹${pendingAmount.toStringAsFixed(2)}'),
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
                          title: Text(
                              '${invoice.invoiceNo} • ${invoice.periodLabel}'),
                          subtitle: Text(
                              'Due: ${invoice.dueDate} • Status: ${invoice.status}'),
                          trailing:
                              Text('₹${invoice.amount.toStringAsFixed(2)}'),
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
                          title:
                              Text('${payment.provider} • ${payment.status}'),
                          subtitle: Text('Ref: ${payment.externalRef ?? '-'}'),
                          trailing:
                              Text('₹${payment.amount.toStringAsFixed(2)}'),
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
