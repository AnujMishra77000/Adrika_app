'use client';

import Link from 'next/link';
import { FormEvent, useEffect, useMemo, useState } from 'react';

import { apiRequest } from '@/lib/api';

import styles from './page.module.css';

type Student = {
  student_id: string;
  user_id: string;
  full_name: string;
  email: string | null;
  phone: string | null;
  status: 'active' | 'inactive' | 'suspended' | string;
  admission_no: string;
  roll_no: string;
  class_name: string | null;
  stream: string | null;
  parent_contact_number: string | null;
  admission_date: string | null;
  batch: { id: string; name: string; academic_year: number; standard_name: string | null } | null;
};

type Batch = {
  id: string;
  name: string;
  academic_year: number;
  standard_name?: string | null;
  standard?: { id: string; name: string } | null;
};

type FeeStructureOption = {
  id: string;
  name: string;
  class_level: number;
  stream: 'science' | 'commerce' | null;
  total_amount: number;
  installment_count: number;
  description?: string | null;
  is_active: boolean;
};

type EnquiryItem = {
  request_id: string;
  submitted_at: string | null;
  full_name: string;
  phone: string | null;
  email: string | null;
  class_name: string | null;
  stream: string | null;
  parent_contact_number: string | null;
  school_details: string | null;
  status: string;
};

type StudentSummary = {
  total_students: number;
  active_students: number;
  inactive_students: number;
  suspended_students: number;
  grade_counts: Record<
    string,
    {
      total: number;
      common: number;
      science: number;
      commerce: number;
    }
  >;
};

const emptySummary: StudentSummary = {
  total_students: 0,
  active_students: 0,
  inactive_students: 0,
  suspended_students: 0,
  grade_counts: {
    '10': { total: 0, common: 0, science: 0, commerce: 0 },
    '11': { total: 0, common: 0, science: 0, commerce: 0 },
    '12': { total: 0, common: 0, science: 0, commerce: 0 },
  },
};

type SeniorFilter = 'all' | '10' | '11_science' | '11_commerce' | '12_science' | '12_commerce';

type DirectorySegment = 'all' | 'junior' | 'middle' | 'senior';

type MiddleClassFilter = 'all' | '6' | '7' | '8' | '9';

type MiddleBoardFilter = 'all' | 'cbse_icse' | 'state';

type ClassLevelValue = '6' | '7' | '8' | '9' | '10' | '11' | '12';

type FeeScopeOption = {
  value: string;
  label: string;
  classLevel: number;
  stream: 'science' | 'commerce' | null;
};

const FEE_SCOPE_OPTIONS: FeeScopeOption[] = [
  { value: '6', label: '6th', classLevel: 6, stream: null },
  { value: '7', label: '7th', classLevel: 7, stream: null },
  { value: '8', label: '8th', classLevel: 8, stream: null },
  { value: '9', label: '9th', classLevel: 9, stream: null },
  { value: '10', label: '10th', classLevel: 10, stream: null },
  { value: '11_science', label: '11th Science', classLevel: 11, stream: 'science' },
  { value: '11_commerce', label: '11th Commerce', classLevel: 11, stream: 'commerce' },
  { value: '12_science', label: '12th Science', classLevel: 12, stream: 'science' },
  { value: '12_commerce', label: '12th Commerce', classLevel: 12, stream: 'commerce' },
];
function classNameFromScope(scope: FeeScopeOption): string {
  return `${scope.classLevel}th`;
}

function classLevelFromText(value: string | null | undefined): number | null {
  const source = (value ?? '').toLowerCase();
  if (!source) return null;

  if (source.includes('jrkg') || source.includes('jr kg') || source.includes('ukg') || source.includes('lkg')) {
    return 0;
  }

  for (let level = 12; level >= 1; level -= 1) {
    const pattern = new RegExp(`\\b${level}(st|nd|rd|th)?\\b`);
    if (pattern.test(source) || source.includes(`${level}th`)) {
      return level;
    }
  }

  return null;
}

function normalizeStream(value: string | null | undefined): 'science' | 'commerce' | null {
  const source = (value ?? '').trim().toLowerCase();
  if (!source) return null;
  if (source.includes('science') || source === 'sci') return 'science';
  if (source.includes('commerce') || source === 'comm') return 'commerce';
  return null;
}

function studentClassLevel(student: Student): number | null {
  return classLevelFromText(student.class_name) ?? classLevelFromText(student.batch?.standard_name);
}

function studentStream(student: Student): 'science' | 'commerce' | null {
  return normalizeStream(student.stream) ?? normalizeStream(student.batch?.standard_name);
}

function normalizeBoard(value: string | null | undefined): 'cbse_icse' | 'state' | null {
  const source = (value ?? '').trim().toLowerCase();
  if (!source) return null;
  if (source.includes('cbse') || source.includes('icse') || source.includes('cbsc') || source.includes('icsc')) {
    return 'cbse_icse';
  }
  if (source.includes('state board') || source.includes('state')) {
    return 'state';
  }
  return null;
}

function studentBoard(student: Student): 'cbse_icse' | 'state' | null {
  return normalizeBoard(student.class_name) ?? normalizeBoard(student.batch?.standard_name);
}

function boardLabel(board: 'cbse_icse' | 'state' | null): string {
  if (board === 'cbse_icse') return 'CBSE/ICSE';
  if (board === 'state') return 'State Board';
  return '-';
}

function batchStandardName(batch: Batch | null | undefined): string | null {
  if (!batch) return null;
  return batch.standard_name ?? batch.standard?.name ?? null;
}

function batchClassLevel(batch: Batch | null | undefined): number | null {
  return classLevelFromText(batchStandardName(batch));
}

function batchStream(batch: Batch | null | undefined): 'science' | 'commerce' | null {
  return normalizeStream(batchStandardName(batch));
}

function batchBoard(batch: Batch | null | undefined): 'cbse_icse' | 'state' | null {
  return normalizeBoard(batchStandardName(batch));
}

function feeStructureLabel(item: FeeStructureOption): string {
  const stream = item.stream ? ` - ${item.stream}` : '';
  return `${item.name} (${item.class_level}${stream}) - INR ${Math.round(item.total_amount)}`;
}



function isAdminCreatedFeeStructure(item: FeeStructureOption): boolean {
  const name = (item.name ?? '').trim();
  const description = (item.description ?? '').toLowerCase();
  const isManualByName = /^manual-\d+-.+/.test(name.toLowerCase());
  const isManualByDescription = description.includes('auto-generated manual fee structure for student onboarding');
  return !(isManualByName || isManualByDescription);
}

function buildInstallmentPreview(totalFee: number, paidAmount: number, installmentCount: number) {
  const total = Math.max(0, totalFee);
  const first = Math.min(Math.max(0, paidAmount), total);
  const remaining = Math.max(total - first, 0);
  const safeInstallmentCount = Math.max(1, Math.floor(installmentCount || 1));
  const tailCount = Math.max(safeInstallmentCount - 1, 0);
  const parts: number[] = [];

  if (tailCount > 0) {
    const base = Number((remaining / tailCount).toFixed(2));
    for (let index = 0; index < tailCount; index += 1) {
      if (index === tailCount - 1) {
        const consumed = parts.reduce((sum, value) => sum + value, 0);
        parts.push(Number((remaining - consumed).toFixed(2)));
      } else {
        parts.push(base);
      }
    }
  }

  return {
    total,
    first: Number(first.toFixed(2)),
    parts,
    installment_count: safeInstallmentCount,
    remaining: Number(remaining.toFixed(2)),
  };
}

function matchesDirectoryFilter(
  student: Student,
  {
    segment,
    seniorFilter,
    middleClassFilter,
    middleBoardFilter,
  }: {
    segment: DirectorySegment;
    seniorFilter: SeniorFilter;
    middleClassFilter: MiddleClassFilter;
    middleBoardFilter: MiddleBoardFilter;
  },
): boolean {
  const classLevel = studentClassLevel(student);
  const stream = studentStream(student);
  const board = studentBoard(student);

  if (segment === 'junior') {
    return classLevel !== null && classLevel >= 0 && classLevel <= 5;
  }

  if (segment === 'middle') {
    if (classLevel === null || classLevel < 6 || classLevel > 9) {
      return false;
    }

    if (middleClassFilter !== 'all' && classLevel !== Number(middleClassFilter)) {
      return false;
    }

    if (middleBoardFilter === 'cbse_icse') {
      return board === 'cbse_icse';
    }

    if (middleBoardFilter === 'state') {
      return board === 'state';
    }

    return true;
  }

  if (segment === 'senior') {
    switch (seniorFilter) {
      case '10':
        return classLevel === 10;
      case '11_science':
        return classLevel === 11 && stream === 'science';
      case '11_commerce':
        return classLevel === 11 && stream === 'commerce';
      case '12_science':
        return classLevel === 12 && stream === 'science';
      case '12_commerce':
        return classLevel === 12 && stream === 'commerce';
      default:
        return classLevel !== null && classLevel >= 10;
    }
  }

  return true;
}

export default function AdminStudentsPage() {
  const [students, setStudents] = useState<Student[]>([]);
  const [batches, setBatches] = useState<Batch[]>([]);
  const [summary, setSummary] = useState<StudentSummary>(emptySummary);
  const [feeStructures, setFeeStructures] = useState<FeeStructureOption[]>([]);
  const [enquiryCount, setEnquiryCount] = useState(0);

  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [batchUpdatingUserId, setBatchUpdatingUserId] = useState<string | null>(null);

  const [fullName, setFullName] = useState('');
  const [classLevel, setClassLevel] = useState<ClassLevelValue>('10');
  const [previousClass, setPreviousClass] = useState('');
  const [previousPercentage, setPreviousPercentage] = useState('');
  const [schoolName, setSchoolName] = useState('');
  const [language, setLanguage] = useState<'english' | 'hindi'>('english');
  const [phone, setPhone] = useState('');
  const [parentContactNumber, setParentContactNumber] = useState('');

  const [feeMode, setFeeMode] = useState<'structure' | 'manual'>('structure');
  const [feeStructureId, setFeeStructureId] = useState('');
  const [manualFeeAmount, setManualFeeAmount] = useState('');
  const [installments, setInstallments] = useState('3');
  const [feeScope, setFeeScope] = useState('10');
  const [negotiableAmount, setNegotiableAmount] = useState('');
  const [initialFeePaidAmount, setInitialFeePaidAmount] = useState('');
  const [initialFeePaidOn, setInitialFeePaidOn] = useState('');
  const [initialFeePaymentMode, setInitialFeePaymentMode] = useState<'cash' | 'upi' | 'bank_transfer' | 'card' | 'cheque' | 'other'>('cash');
  const [initialFeeReferenceNo, setInitialFeeReferenceNo] = useState('');
  const [initialFeeNote, setInitialFeeNote] = useState('');

  const [searchText, setSearchText] = useState('');
  const [directorySegment, setDirectorySegment] = useState<DirectorySegment>('all');
  const [seniorFilter, setSeniorFilter] = useState<SeniorFilter>('all');
  const [middleClassFilter, setMiddleClassFilter] = useState<MiddleClassFilter>('all');
  const [middleBoardFilter, setMiddleBoardFilter] = useState<MiddleBoardFilter>('all');
  const [onboardingBoard, setOnboardingBoard] = useState<'cbse_icse' | 'state' | ''>('');
  const [selectedOnboardingBatchId, setSelectedOnboardingBatchId] = useState('');
  const [batchSelectionByStudent, setBatchSelectionByStudent] = useState<Record<string, string>>({});
  const [showCreateStudentForm, setShowCreateStudentForm] = useState(false);


  const selectedScope = useMemo(
    () => FEE_SCOPE_OPTIONS.find((item) => item.value === feeScope) ?? FEE_SCOPE_OPTIONS[0],
    [feeScope],
  );

  useEffect(() => {
    if (classLevel === '6' || classLevel === '7' || classLevel === '8' || classLevel === '9' || classLevel === '10') {
      setFeeScope(classLevel);
      return;
    }
    if (classLevel === '11' && !feeScope.startsWith('11_')) {
      setFeeScope('11_science');
      return;
    }
    if (classLevel === '12' && !feeScope.startsWith('12_')) {
      setFeeScope('12_science');
    }
  }, [classLevel, feeScope]);

  useEffect(() => {
    if (classLevel !== '6' && classLevel !== '7' && classLevel !== '8' && classLevel !== '9') {
      setOnboardingBoard('');
    }
  }, [classLevel]);

  useEffect(() => {
    if (directorySegment !== 'middle') {
      setMiddleClassFilter('all');
      setMiddleBoardFilter('all');
    }
    if (directorySegment !== 'senior') {
      setSeniorFilter('all');
    }
  }, [directorySegment]);

  const eligibleOnboardingBatches = useMemo(() => {
    const selectedLevel = Number(classLevel);
    const selectedStream = selectedScope.stream;
    const requiresBoard = selectedLevel >= 6 && selectedLevel <= 9;

    return batches.filter((batch) => {
      const batchLevel = batchClassLevel(batch);
      if (batchLevel !== selectedLevel) {
        return false;
      }
      if (selectedLevel >= 11 && selectedLevel <= 12) {
        return batchStream(batch) === selectedStream;
      }
      if (requiresBoard) {
        if (!onboardingBoard) return true;
        const detectedBoard = batchBoard(batch);
        // Keep legacy/unlabeled middle-school batches visible.
        if (!detectedBoard) return true;
        return detectedBoard === onboardingBoard;
      }
      return true;
    });
  }, [batches, classLevel, onboardingBoard, selectedScope.stream]);

  useEffect(() => {
    if (!eligibleOnboardingBatches.some((item) => item.id === selectedOnboardingBatchId)) {
      setSelectedOnboardingBatchId(eligibleOnboardingBatches[0]?.id ?? '');
    }
  }, [eligibleOnboardingBatches, selectedOnboardingBatchId]);

  const selectedOnboardingBatch = useMemo(() => {
    return eligibleOnboardingBatches.find((item) => item.id === selectedOnboardingBatchId) ?? null;
  }, [eligibleOnboardingBatches, selectedOnboardingBatchId]);

  const eligibleFeeStructures = useMemo(() => {
    return feeStructures
      .filter((item) => isAdminCreatedFeeStructure(item))
      .filter((item) => {
        if (!item.is_active) return false;
        if (item.class_level !== selectedScope.classLevel) return false;
        if (selectedScope.classLevel <= 10) return item.stream === null;
        return item.stream === selectedScope.stream;
      })
      .sort((a, b) => a.total_amount - b.total_amount);
  }, [feeStructures, selectedScope]);

  const selectedStructure = useMemo(
    () => eligibleFeeStructures.find((item) => item.id === feeStructureId) ?? null,
    [eligibleFeeStructures, feeStructureId],
  );

  const selectedFeeBaseTotal = useMemo(() => {
    if (feeMode === 'manual') {
      const manual = Number(manualFeeAmount || 0);
      return manual > 0 ? manual : 0;
    }
    return selectedStructure?.total_amount ?? 0;
  }, [feeMode, manualFeeAmount, selectedStructure]);

  const selectedNegotiableAmount = useMemo(() => {
    const value = Number(negotiableAmount || 0);
    return value > 0 ? value : 0;
  }, [negotiableAmount]);

  const selectedFeeTotal = useMemo(() => {
    if (selectedNegotiableAmount > 0) {
      return selectedNegotiableAmount;
    }
    return selectedFeeBaseTotal;
  }, [selectedFeeBaseTotal, selectedNegotiableAmount]);

  const selectedInstallmentCount = useMemo(() => {
    return Math.max(1, Number(installments || 1));
  }, [installments]);

  const installmentPreview = useMemo(() => {
    const total = Number(selectedFeeTotal || 0);
    if (total <= 0) return null;
    const paid = Number(initialFeePaidAmount || 0);
    return buildInstallmentPreview(total, paid, selectedInstallmentCount);
  }, [selectedFeeTotal, initialFeePaidAmount, selectedInstallmentCount]);

  const visibleStudents = useMemo(() => {
    const query = searchText.trim().toLowerCase();
    return students.filter((student) => {
      if (
        !matchesDirectoryFilter(student, {
          segment: directorySegment,
          seniorFilter,
          middleClassFilter,
          middleBoardFilter,
        })
      ) {
        return false;
      }
      if (!query) {
        return true;
      }
      return (
        (student.full_name ?? '').toLowerCase().includes(query) ||
        (student.phone ?? '').toLowerCase().includes(query) ||
        (student.parent_contact_number ?? '').toLowerCase().includes(query) ||
        (student.admission_no ?? '').toLowerCase().includes(query)
      );
    });
  }, [students, searchText, directorySegment, seniorFilter, middleClassFilter, middleBoardFilter]);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [studentRes, batchRes, summaryRes, feeRes, enquiryRes] = await Promise.all([
        apiRequest<{ items: Student[] }>('/api/v1/admin/students?limit=100&offset=0'),
        apiRequest<{ items: Batch[] }>('/api/v1/admin/batches?limit=200&offset=0'),
        apiRequest<StudentSummary>('/api/v1/admin/students/summary'),
        apiRequest<{ items: FeeStructureOption[] }>('/api/v1/admin/fees/structures?is_active=true&limit=100&offset=0'),
        apiRequest<{ items: EnquiryItem[]; meta: { total: number } }>('/api/v1/admin/enquiries?limit=20&offset=0'),
      ]);

      setStudents(studentRes.items);
      setBatches(batchRes.items);
      setSummary(summaryRes);
      setFeeStructures(feeRes.items);
      setEnquiryCount(enquiryRes.meta.total);
      setBatchSelectionByStudent(
        Object.fromEntries(studentRes.items.map((item) => [item.student_id, item.batch?.id ?? ''])),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load student operations');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function createStudent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSuccess(null);

    const initialAmount = Number(initialFeePaidAmount || 0);
    const manualAmount = Number(manualFeeAmount || 0);
    const negotiable = Number(negotiableAmount || 0);

    if (feeMode === 'structure' && !feeStructureId) {
      setError('Please select fee structure.');
      return;
    }
    if (feeMode === 'manual' && manualAmount <= 0) {
      setError('Please enter manual total fee.');
      return;
    }
    if (Number(installments || 0) < 1) {
      setError('EMI count should be at least 1.');
      return;
    }
    if (negotiable > 0 && selectedFeeBaseTotal > 0 && negotiable > selectedFeeBaseTotal) {
      setError('Negotiable amount cannot exceed selected fee amount.');
      return;
    }

    const normalizedNote = [
      initialFeeNote.trim() || null,
      negotiableAmount.trim() ? `Negotiable Amount: ${negotiableAmount.trim()}` : null,
    ]
      .filter(Boolean)
      .join(' | ') || null;

    const isMiddleClass = classLevel === '6' || classLevel === '7' || classLevel === '8' || classLevel === '9';
    if (isMiddleClass && !onboardingBoard) {
      setError('Please select board (CBSE/ICSE or State Board) before assigning batch.');
      return;
    }
    if (!selectedOnboardingBatchId) {
      setError('Please assign a batch before creating student.');
      return;
    }

    const generatedSuffix = String(Date.now()).slice(-6);
    const autoAdmissionNo = `ADM-${classLevel}-${generatedSuffix}`;
    const autoRollNo = `R-${generatedSuffix}`;
    const normalizedSchoolDetails = [
      schoolName.trim() || null,
      previousClass.trim() ? `Previous Class: ${previousClass.trim()}` : null,
      previousPercentage.trim() ? `Previous Percentage: ${previousPercentage.trim()}` : null,
      `Language: ${language}`,
    ]
      .filter(Boolean)
      .join(' | ');

    const payload = {
      full_name: fullName.trim(),
      email: null,
      phone: phone.trim() || null,
      admission_no: autoAdmissionNo,
      roll_no: autoRollNo,
      batch_id: selectedOnboardingBatchId,
      class_name: classNameFromScope(selectedScope),
      stream: selectedScope.classLevel <= 10 ? null : selectedScope.stream,
      parent_contact_number: parentContactNumber.trim() || null,
      address: null,
      school_details: normalizedSchoolDetails || null,
      fee_structure_id: feeMode === 'structure' ? (feeStructureId || null) : null,
      manual_fee_amount: feeMode === 'manual' && manualAmount > 0 ? manualAmount : null,
      manual_fee_installment_count:
        feeMode === 'manual' && manualAmount > 0 ? Number(installments || 3) : null,
      negotiable_amount: negotiable > 0 ? negotiable : null,
      installment_count: Number(installments || 1),
      initial_fee_paid_amount: initialAmount > 0 ? initialAmount : null,
      initial_fee_paid_on: initialAmount > 0 && initialFeePaidOn ? initialFeePaidOn : null,
      initial_fee_payment_mode: initialFeePaymentMode,
      initial_fee_reference_no: initialFeeReferenceNo.trim() || null,
      initial_fee_note: normalizedNote,
    };

    try {
      const created = await apiRequest<any>('/api/v1/admin/students', {
        method: 'POST',
        body: JSON.stringify(payload),
      });

      setFullName('');
      setPhone('');
      setClassLevel('10');
      setPreviousClass('');
      setPreviousPercentage('');
      setSchoolName('');
      setLanguage('english');
      setParentContactNumber('');
      setFeeMode('structure');
      setFeeStructureId('');
      setManualFeeAmount('');
      setInstallments('3');
      setFeeScope('10');
      setOnboardingBoard('');
      setSelectedOnboardingBatchId('');
      setNegotiableAmount('');
      setInitialFeePaidAmount('');
      setInitialFeePaidOn('');
      setInitialFeePaymentMode('cash');
      setInitialFeeReferenceNo('');
      setInitialFeeNote('');
      const issuedPassword = created?.issued_password ? String(created.issued_password) : null;
      const loginId = created?.login_id ? String(created.login_id) : phone.trim();
      setSuccess(
        issuedPassword
          ? `Student created successfully. Login ID: ${loginId}, Password: ${issuedPassword}`
          : 'Student created successfully and added into class-wise records.',
      );
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create student');
    }
  }


  async function assignBatch(student: Student) {
    const selectedBatchId = batchSelectionByStudent[student.student_id];
    if (!selectedBatchId) {
      setError('Select a batch before assigning.');
      return;
    }

    setBatchUpdatingUserId(student.user_id);
    setError(null);
    setSuccess(null);
    try {
      await apiRequest(`/api/v1/admin/students/${student.user_id}`, {
        method: 'PATCH',
        body: JSON.stringify({ batch_id: selectedBatchId }),
      });
      setSuccess(`Batch allocation updated for ${student.full_name}.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to assign batch');
    } finally {
      setBatchUpdatingUserId(null);
    }
  }


  return (
    <section className={`student-admin-theme ${styles.operationsRoot}`}>
      <h1 className={styles.pageTitle}>Student Operations</h1>
      <p className={`muted ${styles.pageSubtitle}`}>
        Manage student lifecycle with class/stream controls, enquiries, batch allocation and fee onboarding.
      </p>

      {error ? <p style={{ color: '#dc2626' }}>{error}</p> : null}
      {success ? <p style={{ color: '#166534' }}>{success}</p> : null}

      <div className={styles.navGrid}>
        <Link
          className={styles.navCard}
          href="/admin/students/count"
          aria-label={`Student Count total ${summary.total_students}`}
        >
          <h3 className={styles.navTitle}>Student Count</h3>
        </Link>

        <Link className={styles.navCard} href="/admin/students/details">
          <h3 className={styles.navTitle}>Student Details</h3>
        </Link>

        <Link
          className={styles.navCard}
          href="/admin/enquiries"
          aria-label={`Enquiry pending ${enquiryCount}`}
        >
          <h3 className={styles.navTitle}>Enquiry</h3>
        </Link>

        <Link className={styles.navCard} href="/admin/students/create-batch">
          <h3 className={styles.navTitle}>Batch Creation</h3>
        </Link>

        <Link className={styles.navCard} href="/admin/fees?section=students">
          <h3 className={styles.navTitle}>Fee Collection</h3>
        </Link>

        <Link className={styles.navCard} href="/admin/fees?section=structure">
          <h3 className={styles.navTitle}>Fee Structure</h3>
        </Link>

        <Link className={styles.navCard} href="/admin/students/credentials">
          <h3 className={styles.navTitle}>Student Credentials</h3>
        </Link>
      </div>

      <div className={styles.sectionStack}>
      <div className={`card ${styles.directoryCard}`} id="student-directory">
        <h3 className={styles.sectionHeading}>Student Directory</h3>
        <div className={styles.directoryToolbar}>
          <div className={styles.filterRow}>
            <button
              className={`${styles.actionButton} ${styles.purpleButton} ${directorySegment === 'all' ? styles.filterActive : ''}`}
              type="button"
              onClick={() => setDirectorySegment('all')}
            >
              All Students
            </button>
            <button
              className={`${styles.actionButton} ${styles.purpleButton} ${directorySegment === 'junior' ? styles.filterActive : ''}`}
              type="button"
              onClick={() => setDirectorySegment('junior')}
            >
              Jr.KG to 5th
            </button>
            <button
              className={`${styles.actionButton} ${styles.purpleButton} ${directorySegment === 'middle' ? styles.filterActive : ''}`}
              type="button"
              onClick={() => setDirectorySegment('middle')}
            >
              6th to 9th
            </button>
            <button
              className={`${styles.actionButton} ${styles.purpleButton} ${directorySegment === 'senior' ? styles.filterActive : ''}`}
              type="button"
              onClick={() => setDirectorySegment('senior')}
            >
              10th to 12th
            </button>
            <button
              className={`${styles.actionButton} ${styles.purpleButton} ${showCreateStudentForm ? styles.filterActive : ''}`}
              type="button"
              onClick={() => setShowCreateStudentForm((current) => !current)}
              aria-expanded={showCreateStudentForm}
              aria-controls="create-student"
            >
              {showCreateStudentForm ? 'Hide Create Student' : 'Create Student'}
            </button>
          </div>

          {directorySegment === 'middle' ? (
            <>
              <div className={styles.filterRow}>
                <button
                  className={`${styles.actionButton} ${styles.purpleButton} ${middleClassFilter === 'all' ? styles.filterActive : ''}`}
                  type="button"
                  onClick={() => setMiddleClassFilter('all')}
                >
                  All Classes
                </button>
                {(['6', '7', '8', '9'] as const).map((level) => (
                  <button
                    key={level}
                    className={`${styles.actionButton} ${styles.purpleButton} ${middleClassFilter === level ? styles.filterActive : ''}`}
                    type="button"
                    onClick={() => setMiddleClassFilter(level)}
                  >
                    Class {level}
                  </button>
                ))}
              </div>
              <div className={styles.filterRow}>
                <button
                  className={`${styles.actionButton} ${styles.purpleButton} ${middleBoardFilter === 'all' ? styles.filterActive : ''}`}
                  type="button"
                  onClick={() => setMiddleBoardFilter('all')}
                >
                  All Boards
                </button>
                <button
                  className={`${styles.actionButton} ${styles.purpleButton} ${middleBoardFilter === 'cbse_icse' ? styles.filterActive : ''}`}
                  type="button"
                  onClick={() => setMiddleBoardFilter('cbse_icse')}
                >
                  CBSE/ICSE
                </button>
                <button
                  className={`${styles.actionButton} ${styles.purpleButton} ${middleBoardFilter === 'state' ? styles.filterActive : ''}`}
                  type="button"
                  onClick={() => setMiddleBoardFilter('state')}
                >
                  State Board
                </button>
              </div>
            </>
          ) : null}

          {directorySegment === 'senior' ? (
            <div className={styles.filterRow}>
              <button
                className={`${styles.actionButton} ${styles.purpleButton} ${seniorFilter === 'all' ? styles.filterActive : ''}`}
                type="button"
                onClick={() => setSeniorFilter('all')}
              >
                All Senior
              </button>
              <button
                className={`${styles.actionButton} ${styles.purpleButton} ${seniorFilter === '10' ? styles.filterActive : ''}`}
                type="button"
                onClick={() => setSeniorFilter('10')}
              >
                10th
              </button>
              <button
                className={`${styles.actionButton} ${styles.purpleButton} ${seniorFilter === '11_science' ? styles.filterActive : ''}`}
                type="button"
                onClick={() => setSeniorFilter('11_science')}
              >
                11th Science
              </button>
              <button
                className={`${styles.actionButton} ${styles.purpleButton} ${seniorFilter === '11_commerce' ? styles.filterActive : ''}`}
                type="button"
                onClick={() => setSeniorFilter('11_commerce')}
              >
                11th Commerce
              </button>
              <button
                className={`${styles.actionButton} ${styles.purpleButton} ${seniorFilter === '12_science' ? styles.filterActive : ''}`}
                type="button"
                onClick={() => setSeniorFilter('12_science')}
              >
                12th Science
              </button>
              <button
                className={`${styles.actionButton} ${styles.purpleButton} ${seniorFilter === '12_commerce' ? styles.filterActive : ''}`}
                type="button"
                onClick={() => setSeniorFilter('12_commerce')}
              >
                12th Commerce
              </button>
            </div>
          ) : null}

          <label className={`field ${styles.searchField}`}>
            <span>Search Student (name / mobile / parent mobile / admission no)</span>
            <input value={searchText} onChange={(e) => setSearchText(e.target.value)} />
          </label>
        </div>

        {showCreateStudentForm ? (
        <div className={`card ${styles.createStudentCard}`} id="create-student">
          <h3 className={styles.sectionHeading}>Create Student</h3>
          <form onSubmit={createStudent} className={styles.createStudentForm}>
            <div className={styles.formGrid}>
              <label className="field">
                <span>Student Name</span>
                <input value={fullName} onChange={(e) => setFullName(e.target.value)} required />
              </label>
              <label className="field">
                <span>Class</span>
                <select value={classLevel} onChange={(e) => setClassLevel(e.target.value as ClassLevelValue)}>
                  <option value="6">6th</option>
                  <option value="7">7th</option>
                  <option value="8">8th</option>
                  <option value="9">9th</option>
                  <option value="10">10th</option>
                  <option value="11">11th</option>
                  <option value="12">12th</option>
                </select>
              </label>
              <label className="field">
                <span>Previous Class</span>
                <input value={previousClass} onChange={(e) => setPreviousClass(e.target.value)} />
              </label>
              <label className="field">
                <span>Previous Percentage</span>
                <input type="number" step="0.01" min={0} max={100} value={previousPercentage} onChange={(e) => setPreviousPercentage(e.target.value)} />
              </label>
              <label className="field">
                <span>School Name</span>
                <input value={schoolName} onChange={(e) => setSchoolName(e.target.value)} />
              </label>
              <label className="field">
                <span>Language</span>
                <select value={language} onChange={(e) => setLanguage(e.target.value as 'english' | 'hindi')}>
                  <option value="english">English</option>
                  <option value="hindi">Hindi</option>
                </select>
              </label>
              <label className="field">
                <span>Contact Number</span>
                <input value={phone} onChange={(e) => setPhone(e.target.value)} required />
              </label>
              <label className="field">
                <span>Parent Contact</span>
                <input value={parentContactNumber} onChange={(e) => setParentContactNumber(e.target.value)} required />
              </label>

              {(classLevel === '6' || classLevel === '7' || classLevel === '8' || classLevel === '9') ? (
                <label className="field">
                  <span>Board</span>
                  <select value={onboardingBoard} onChange={(e) => setOnboardingBoard(e.target.value as 'cbse_icse' | 'state' | '')}>
                    <option value="">Select Board</option>
                    <option value="cbse_icse">CBSE/ICSE</option>
                    <option value="state">State Board</option>
                  </select>
                </label>
              ) : null}
              <label className="field">
                <span>Batch Allocation</span>
                <select
                  value={selectedOnboardingBatchId}
                  onChange={(e) => setSelectedOnboardingBatchId(e.target.value)}
                  required
                >
                  <option value="">Select Batch</option>
                  {eligibleOnboardingBatches.map((batch) => (
                    <option key={batch.id} value={batch.id}>
                      {batch.name} ({batch.academic_year}) {batchStandardName(batch) ? `- ${batchStandardName(batch)}` : ''}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <div className={styles.feeSetupBox}>
              <h2 className={styles.cardTitle}>Section 2: Fee Details</h2>
              <div className={styles.feeFormGrid}>
                <label className={styles.feeField}>
                  <span>Fee Details</span>
                  <select
                    value={feeScope}
                    onChange={(e) => {
                      const value = e.target.value;
                      setFeeScope(value);
                      const scope = FEE_SCOPE_OPTIONS.find((item) => item.value === value) ?? FEE_SCOPE_OPTIONS[0];
                      setClassLevel(String(scope.classLevel) as ClassLevelValue);
                    }}
                  >
                    {FEE_SCOPE_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className={styles.feeField}>
                  <span>Mode</span>
                  <select value={feeMode} onChange={(e) => setFeeMode(e.target.value as 'structure' | 'manual')}>
                    <option value="structure">Fee Structure</option>
                    <option value="manual">Manual</option>
                  </select>
                </label>
                {feeMode === 'structure' ? (
                  <label className={styles.feeField}>
                    <span>Fee Structure</span>
                    <select value={feeStructureId} onChange={(e) => setFeeStructureId(e.target.value)}>
                      <option value="">Select admin fee structure</option>
                      {eligibleFeeStructures.map((item) => (
                        <option key={item.id} value={item.id}>
                          {feeStructureLabel(item)}
                        </option>
                      ))}
                    </select>
                  </label>
                ) : (
                  <label className={styles.feeField}>
                    <span>Manual Total Fee</span>
                    <input
                      type="number"
                      min="0"
                      step="1"
                      value={manualFeeAmount}
                      onChange={(e) => setManualFeeAmount(e.target.value)}
                    />
                  </label>
                )}
                <label className={styles.feeField}>
                  <span>Negotiable Amount</span>
                  <input
                    type="number"
                    min="0"
                    step="1"
                    value={negotiableAmount}
                    onChange={(e) => setNegotiableAmount(e.target.value)}
                  />
                </label>
                <label className={styles.feeField}>
                  <span>EMI Count</span>
                  <input
                    type="number"
                    min="1"
                    max="24"
                    value={installments}
                    onChange={(e) => setInstallments(e.target.value)}
                  />
                </label>
                <label className={styles.feeField}>
                  <span>Paid Amount (First Installment)</span>
                  <input
                    type="number"
                    min="0"
                    step="1"
                    value={initialFeePaidAmount}
                    onChange={(e) => setInitialFeePaidAmount(e.target.value)}
                  />
                </label>
                <label className={styles.feeField}>
                  <span>Paid On</span>
                  <input type="date" value={initialFeePaidOn} onChange={(e) => setInitialFeePaidOn(e.target.value)} />
                </label>
                <label className={styles.feeField}>
                  <span>Payment Mode</span>
                  <select
                    value={initialFeePaymentMode}
                    onChange={(e) =>
                      setInitialFeePaymentMode(
                        e.target.value as 'cash' | 'upi' | 'bank_transfer' | 'card' | 'cheque' | 'other',
                      )
                    }
                  >
                    <option value="cash">Cash</option>
                    <option value="upi">UPI</option>
                    <option value="bank_transfer">Bank Transfer</option>
                    <option value="card">Card</option>
                    <option value="cheque">Cheque</option>
                    <option value="other">Other</option>
                  </select>
                </label>
                <label className={styles.feeField}>
                  <span>Payment Ref</span>
                  <input value={initialFeeReferenceNo} onChange={(e) => setInitialFeeReferenceNo(e.target.value)} />
                </label>
                <label className={`${styles.feeField} ${styles.fieldWide}`}>
                  <span>Notes (optional)</span>
                  <input value={initialFeeNote} onChange={(e) => setInitialFeeNote(e.target.value)} />
                </label>
              </div>
              <div className={styles.infoStrip}>
                <span>Assigned Batch: {selectedOnboardingBatch ? `${selectedOnboardingBatch.name} (${selectedOnboardingBatch.academic_year})` : 'No batch selected'}</span>
              </div>
            </div>

            {installmentPreview ? (
              <div className={styles.infoStrip}>
                <span>Selected Fee Scope: {selectedScope.label}</span>
                <span>First EMI: {Math.round(installmentPreview.first)}</span>
                {installmentPreview.parts.map((value, index) => (
                  <span key={`emi-preview-${index}`}>EMI {index + 2}: {Math.round(value)}</span>
                ))}
              </div>
            ) : null}

            <div className={styles.actions}>
              <button className={`${styles.actionButton} ${styles.purpleButton}`} type="submit">
                Create Student
              </button>
            </div>
          </form>
        </div>
        ) : null}

        {loading ? (
          <p>Loading...</p>
        ) : (
          <div className={styles.directoryTableWrap}>
            <table className={`table ${styles.directoryTable}`}>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Class</th>
                  <th>Stream</th>
                  <th>Board</th>
                  <th>Student Contact</th>
                  <th>Parent Contact</th>
                  <th>Admission Date</th>
                  <th>Status</th>
                  <th>Batch Allocation</th>
                </tr>
              </thead>
              <tbody>
                {visibleStudents.map((student) => {
                  const statusTone =
                    student.status === 'active'
                      ? styles.statusActive
                      : student.status === 'inactive'
                        ? styles.statusInactive
                        : styles.statusNeutral;


                  const statusLabel =
                    student.status === 'active'
                      ? 'Active'
                      : student.status === 'inactive'
                        ? 'Inactive'
                        : student.status;

                  return (
                    <tr key={student.student_id}>
                      <td>
                        <div className={styles.nameCell}>{student.full_name}</div>
                        <div className={`muted ${styles.subText}`}>
                          {student.admission_no} • {student.roll_no}
                        </div>
                      </td>
                      <td>{student.class_name ?? student.batch?.standard_name ?? '-'}</td>
                      <td>{student.stream ?? '-'}</td>
                      <td>{boardLabel(studentBoard(student))}</td>
                      <td>{student.phone ?? '-'}</td>
                      <td>{student.parent_contact_number ?? '-'}</td>
                      <td>{student.admission_date ?? '-'}</td>
                      <td>
                        <span className={`${styles.statusBadge} ${statusTone}`}>{statusLabel}</span>
                      </td>
                      <td className={styles.batchCell}>
                        <div className={styles.batchControls}>
                          <select
                            className={styles.batchSelect}
                            value={batchSelectionByStudent[student.student_id] ?? ''}
                            onChange={(e) =>
                              setBatchSelectionByStudent((current) => ({
                                ...current,
                                [student.student_id]: e.target.value,
                              }))
                            }
                          >
                            <option value="">Select Batch</option>
                            {batches.map((item) => (
                              <option key={item.id} value={item.id}>
                                {item.name} ({item.academic_year}) {batchStandardName(item) ? `- ${batchStandardName(item)}` : ''}
                              </option>
                            ))}
                          </select>
                          <button
                            className={`${styles.actionButton} ${styles.purpleButton}`}
                            type="button"
                            onClick={() => assignBatch(student)}
                            disabled={batchUpdatingUserId === student.user_id}
                          >
                            {batchUpdatingUserId === student.user_id ? 'Assigning...' : 'Assign Batch'}
                          </button>
                        </div>
                      </td>                    </tr>
                  );
                })}
                {visibleStudents.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="muted">
                      No students found for selected filters.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        )}
      </div>


      </div>
    </section>
  );
}
