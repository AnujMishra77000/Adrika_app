"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import { apiRequest } from "@/lib/api";

import styles from "./enquiries.module.css";

type Batch = {
  id: string;
  name: string;
  academic_year: number;
  standard_name?: string | null;
  standard?: { id: string; name: string } | null;
};

type FeeStructure = {
  id: string;
  name: string;
  class_level: number;
  stream: "science" | "commerce" | null;
  total_amount: number;
  installment_count: number;
  is_active: boolean;
};

type EnquiryItem = {
  enquiry_id: string;
  student_name: string;
  class_level: number;
  previous_class: string | null;
  previous_percentage: number | null;
  school_name: string | null;
  language: string;
  contact_number: string;
  parent_contact_number: string;
  batch_id: string | null;
  follow_up_at: string | null;
  fee_class_level: number;
  fee_stream: string | null;
  fee_structure_id: string | null;
  fee_structure_name: string | null;
  manual_fee_amount: number | null;
  manual_fee_installment_count: number | null;
  fee_amount: number | null;
  negotiable_amount: number | null;
  installment_count: number | null;
  initial_fee_paid_amount: number | null;
  initial_fee_paid_on: string | null;
  initial_fee_payment_mode: string | null;
  initial_fee_reference_no: string | null;
  initial_fee_note: string | null;
  converted_student_id: string | null;
  status: "interested" | "follow_up" | "confirmed" | "not_interested";
  notes: string | null;
  created_at: string;
};

type EnquiryTimelineItem = {
  timeline_id: string;
  enquiry_id: string;
  from_status: string | null;
  to_status: string;
  note: string | null;
  changed_at: string;
  changed_by_user_id: string | null;
  changed_by_name: string | null;
};

type FeeScopeOption = {
  value: string;
  label: string;
  classLevel: number;
  stream: "science" | "commerce" | null;
};

const FEE_SCOPE_OPTIONS: FeeScopeOption[] = [
  { value: "6", label: "6th", classLevel: 6, stream: null },
  { value: "7", label: "7th", classLevel: 7, stream: null },
  { value: "8", label: "8th", classLevel: 8, stream: null },
  { value: "9", label: "9th", classLevel: 9, stream: null },
  { value: "10", label: "10th", classLevel: 10, stream: null },
  { value: "11_science", label: "11th Science", classLevel: 11, stream: "science" },
  { value: "11_commerce", label: "11th Commerce", classLevel: 11, stream: "commerce" },
  { value: "12_science", label: "12th Science", classLevel: 12, stream: "science" },
  { value: "12_commerce", label: "12th Commerce", classLevel: 12, stream: "commerce" },
];

function currency(value: number | null | undefined): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(value ?? 0);
}

function formatDateTime(value: string | null): string {
  if (!value) return "-";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "-";
  return parsed.toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });
}

function toInputDateTime(value: string | null): string {
  if (!value) {
    return "";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "";
  }
  const year = parsed.getFullYear();
  const month = String(parsed.getMonth() + 1).padStart(2, "0");
  const day = String(parsed.getDate()).padStart(2, "0");
  const hour = String(parsed.getHours()).padStart(2, "0");
  const minute = String(parsed.getMinutes()).padStart(2, "0");
  return `${year}-${month}-${day}T${hour}:${minute}`;
}

function feeStreamLabel(stream: string | null | undefined): string {
  if (!stream) return "-";
  return stream === "science" ? "Science" : stream === "commerce" ? "Commerce" : stream;
}

function classLevelFromText(value: string | null | undefined): number | null {
  const source = (value ?? "").toLowerCase();
  if (!source) return null;
  for (let level = 12; level >= 1; level -= 1) {
    if (source.includes(`${level}th`) || new RegExp(`\\b${level}(st|nd|rd|th)?\\b`).test(source)) {
      return level;
    }
  }
  return null;
}

function normalizeStream(value: string | null | undefined): "science" | "commerce" | null {
  const source = (value ?? "").trim().toLowerCase();
  if (!source) return null;
  if (source.includes("science") || source === "sci") return "science";
  if (source.includes("commerce") || source === "comm") return "commerce";
  return null;
}

function normalizeBoard(value: string | null | undefined): "cbse_icse" | "state" | null {
  const source = (value ?? "").trim().toLowerCase();
  if (!source) return null;
  if (source.includes("cbse") || source.includes("icse") || source.includes("cbsc") || source.includes("icsc")) return "cbse_icse";
  if (source.includes("state")) return "state";
  return null;
}

function batchStandardName(batch: Batch | null | undefined): string | null {
  if (!batch) return null;
  return batch.standard_name ?? batch.standard?.name ?? null;
}

function batchClassLevel(batch: Batch | null | undefined): number | null {
  return classLevelFromText(batchStandardName(batch));
}

function batchStream(batch: Batch | null | undefined): "science" | "commerce" | null {
  return normalizeStream(batchStandardName(batch));
}

function batchBoard(batch: Batch | null | undefined): "cbse_icse" | "state" | null {
  return normalizeBoard(batchStandardName(batch));
}

function scopeValueFrom(classLevel: number, stream: string | null): string {
  if (classLevel <= 10) {
    return String(classLevel);
  }
  const normalized = stream?.toLowerCase() === "commerce" ? "commerce" : "science";
  return `${classLevel}_${normalized}`;
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
    first: Number(first.toFixed(2)),
    parts,
  };
}

export default function AdminEnquiriesPage() {
  const [items, setItems] = useState<EnquiryItem[]>([]);
  const [batches, setBatches] = useState<Batch[]>([]);
  const [structures, setStructures] = useState<FeeStructure[]>([]);
  const [editStructures, setEditStructures] = useState<FeeStructure[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [updating, setUpdating] = useState(false);
  const [timelineLoading, setTimelineLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [studentName, setStudentName] = useState("");
  const [classLevel, setClassLevel] = useState("10");
  const [batchBoardFilter, setBatchBoardFilter] = useState<"cbse_icse" | "state" | "">("");
  const [batchId, setBatchId] = useState("");
  const [previousClass, setPreviousClass] = useState("");
  const [previousPercentage, setPreviousPercentage] = useState("");
  const [schoolName, setSchoolName] = useState("");
  const [language, setLanguage] = useState<"hindi" | "english">("english");
  const [contactNumber, setContactNumber] = useState("");
  const [parentContactNumber, setParentContactNumber] = useState("");
  const [followUpAt, setFollowUpAt] = useState("");
  const [feeScope, setFeeScope] = useState("10");
  const [feeStructureId, setFeeStructureId] = useState("");
  const [feeMode, setFeeMode] = useState<"structure" | "manual">("structure");
  const [manualFeeAmount, setManualFeeAmount] = useState("");
  const [manualFeeInstallmentCount, setManualFeeInstallmentCount] = useState("3");
  const [negotiableAmount, setNegotiableAmount] = useState("");
  const [installments, setInstallments] = useState("3");
  const [initialFeePaidAmount, setInitialFeePaidAmount] = useState("");
  const [initialFeePaidOn, setInitialFeePaidOn] = useState("");
  const [initialFeePaymentMode, setInitialFeePaymentMode] = useState<"cash" | "upi" | "bank_transfer" | "card" | "cheque" | "other">("cash");
  const [initialFeeReferenceNo, setInitialFeeReferenceNo] = useState("");
  const [initialFeeNote, setInitialFeeNote] = useState("");
  const [statusValue, setStatusValue] = useState<"interested" | "follow_up" | "confirmed" | "not_interested">(
    "follow_up",
  );
  const [notes, setNotes] = useState("");

  const [selectedEnquiryId, setSelectedEnquiryId] = useState<string | null>(null);
  const [timelineItems, setTimelineItems] = useState<EnquiryTimelineItem[]>([]);
  const [editStudentName, setEditStudentName] = useState("");
  const [editClassLevel, setEditClassLevel] = useState("10");
  const [editBatchBoardFilter, setEditBatchBoardFilter] = useState<"cbse_icse" | "state" | "">("");
  const [editBatchId, setEditBatchId] = useState("");
  const [editPreviousClass, setEditPreviousClass] = useState("");
  const [editPreviousPercentage, setEditPreviousPercentage] = useState("");
  const [editSchoolName, setEditSchoolName] = useState("");
  const [editLanguage, setEditLanguage] = useState<"hindi" | "english">("english");
  const [editContactNumber, setEditContactNumber] = useState("");
  const [editParentContactNumber, setEditParentContactNumber] = useState("");
  const [editFollowUpAt, setEditFollowUpAt] = useState("");
  const [editFeeScope, setEditFeeScope] = useState("10");
  const [editFeeStructureId, setEditFeeStructureId] = useState("");
  const [editFeeMode, setEditFeeMode] = useState<"structure" | "manual">("structure");
  const [editManualFeeAmount, setEditManualFeeAmount] = useState("");
  const [editManualFeeInstallmentCount, setEditManualFeeInstallmentCount] = useState("3");
  const [editNegotiableAmount, setEditNegotiableAmount] = useState("");
  const [editInstallments, setEditInstallments] = useState("3");
  const [editInitialFeePaidAmount, setEditInitialFeePaidAmount] = useState("");
  const [editInitialFeePaidOn, setEditInitialFeePaidOn] = useState("");
  const [editInitialFeePaymentMode, setEditInitialFeePaymentMode] = useState<"cash" | "upi" | "bank_transfer" | "card" | "cheque" | "other">("cash");
  const [editInitialFeeReferenceNo, setEditInitialFeeReferenceNo] = useState("");
  const [editInitialFeeNote, setEditInitialFeeNote] = useState("");
  const [editStatusValue, setEditStatusValue] = useState<"interested" | "follow_up" | "confirmed" | "not_interested">(
    "follow_up",
  );
  const [editNotes, setEditNotes] = useState("");
  const [statusNote, setStatusNote] = useState("");

  const selectedScope = useMemo(
    () => FEE_SCOPE_OPTIONS.find((item) => item.value === feeScope) ?? FEE_SCOPE_OPTIONS[0],
    [feeScope],
  );
  const selectedStructure = useMemo(
    () => structures.find((item) => item.id === feeStructureId) ?? null,
    [structures, feeStructureId],
  );
  const selectedEditScope = useMemo(
    () => FEE_SCOPE_OPTIONS.find((item) => item.value === editFeeScope) ?? FEE_SCOPE_OPTIONS[0],
    [editFeeScope],
  );
  const selectedEditStructure = useMemo(
    () => editStructures.find((item) => item.id === editFeeStructureId) ?? null,
    [editStructures, editFeeStructureId],
  );
  const selectedEnquiry = useMemo(
    () => items.find((item) => item.enquiry_id === selectedEnquiryId) ?? null,
    [items, selectedEnquiryId],
  );

  const createBatchOptions = useMemo(() => {
    const level = Number(classLevel);
    const isMiddle = level >= 6 && level <= 9;
    return batches.filter((batch) => {
      if (batchClassLevel(batch) !== level) return false;
      if (level >= 11 && level <= 12) {
        return batchStream(batch) === selectedScope.stream;
      }
      if (isMiddle) {
        if (!batchBoardFilter) return false;
        return batchBoard(batch) === batchBoardFilter;
      }
      return true;
    });
  }, [batches, classLevel, batchBoardFilter, selectedScope.stream]);

  const editBatchOptions = useMemo(() => {
    const level = Number(editClassLevel);
    const isMiddle = level >= 6 && level <= 9;
    return batches.filter((batch) => {
      if (batchClassLevel(batch) !== level) return false;
      if (level >= 11 && level <= 12) {
        return batchStream(batch) === selectedEditScope.stream;
      }
      if (isMiddle) {
        if (!editBatchBoardFilter) return false;
        return batchBoard(batch) === editBatchBoardFilter;
      }
      return true;
    });
  }, [batches, editClassLevel, editBatchBoardFilter, selectedEditScope.stream]);

  const createFeeTotal = useMemo(() => {
    if (feeMode === "manual") {
      const manual = Number(manualFeeAmount || 0);
      return manual > 0 ? manual : 0;
    }
    return selectedStructure?.total_amount ?? 0;
  }, [feeMode, manualFeeAmount, selectedStructure]);

  const editFeeTotal = useMemo(() => {
    if (editFeeMode === "manual") {
      const manual = Number(editManualFeeAmount || 0);
      return manual > 0 ? manual : 0;
    }
    return selectedEditStructure?.total_amount ?? 0;
  }, [editFeeMode, editManualFeeAmount, selectedEditStructure]);

  const filteredItems = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return items;
    return items.filter((item) => {
      return (
        item.student_name.toLowerCase().includes(q) ||
        item.contact_number.toLowerCase().includes(q) ||
        item.parent_contact_number.toLowerCase().includes(q) ||
        String(item.class_level).includes(q)
      );
    });
  }, [items, search]);

  async function loadEnquiries() {
    const response = await apiRequest<{ items: EnquiryItem[] }>("/api/v1/admin/enquiries?limit=100&offset=0");
    setItems(response.items ?? []);
  }

  async function loadFeeStructures(scope: FeeScopeOption, mode: "create" | "edit") {
    const params = new URLSearchParams({
      class_level: String(scope.classLevel),
      is_active: "true",
      limit: "100",
      offset: "0",
    });
    if (scope.stream) {
      params.set("stream", scope.stream);
    }
    const response = await apiRequest<{ items: FeeStructure[] }>(`/api/v1/admin/fees/structures?${params.toString()}`);
    const list = response.items ?? [];

    if (mode === "create") {
      setStructures(list);
      setFeeStructureId((prev) => (list.some((item) => item.id === prev) ? prev : list[0]?.id ?? ""));
      if (!installments && list[0]?.installment_count) {
        setInstallments(String(list[0].installment_count));
      }
      return;
    }

    setEditStructures(list);
    setEditFeeStructureId((prev) => (list.some((item) => item.id === prev) ? prev : list[0]?.id ?? ""));
    if (!editInstallments && list[0]?.installment_count) {
      setEditInstallments(String(list[0].installment_count));
    }
  }

  async function loadTimeline(enquiryId: string) {
    setTimelineLoading(true);
    try {
      const response = await apiRequest<{ items: EnquiryTimelineItem[] }>(
        `/api/v1/admin/enquiries/${enquiryId}/timeline?limit=100&offset=0`,
      );
      setTimelineItems(response.items ?? []);
    } finally {
      setTimelineLoading(false);
    }
  }

  async function bootstrap() {
    setLoading(true);
    setError(null);
    try {
      await Promise.all([
        loadEnquiries(),
        loadFeeStructures(selectedScope, "create"),
        apiRequest<{ items: Batch[] }>("/api/v1/admin/batches?limit=200&offset=0").then((res) => setBatches(res.items ?? [])),
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load enquiry module");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void bootstrap();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    void loadFeeStructures(selectedScope, "create").catch((err) => {
      setError(err instanceof Error ? err.message : "Failed to load fee structures");
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [feeScope]);

  useEffect(() => {
    if (!selectedEnquiryId) {
      return;
    }
    void loadFeeStructures(selectedEditScope, "edit").catch((err) => {
      setError(err instanceof Error ? err.message : "Failed to load edit fee structures");
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editFeeScope, selectedEnquiryId]);

  useEffect(() => {
    if (classLevel === "6" || classLevel === "7" || classLevel === "8" || classLevel === "9" || classLevel === "10") {
      setFeeScope(classLevel);
    } else if (classLevel === "11" && !feeScope.startsWith("11_")) {
      setFeeScope("11_science");
    } else if (classLevel === "12" && !feeScope.startsWith("12_")) {
      setFeeScope("12_science");
    }
  }, [classLevel, feeScope]);

  useEffect(() => {
    if (editClassLevel === "6" || editClassLevel === "7" || editClassLevel === "8" || editClassLevel === "9" || editClassLevel === "10") {
      setEditFeeScope(editClassLevel);
    } else if (editClassLevel === "11" && !editFeeScope.startsWith("11_")) {
      setEditFeeScope("11_science");
    } else if (editClassLevel === "12" && !editFeeScope.startsWith("12_")) {
      setEditFeeScope("12_science");
    }
  }, [editClassLevel, editFeeScope]);

  useEffect(() => {
    if (classLevel !== "6" && classLevel !== "7" && classLevel !== "8" && classLevel !== "9") {
      setBatchBoardFilter("");
    }
    if (!createBatchOptions.some((batch) => batch.id === batchId)) {
      setBatchId(createBatchOptions[0]?.id ?? "");
    }
  }, [classLevel, createBatchOptions, batchId]);

  useEffect(() => {
    if (editClassLevel !== "6" && editClassLevel !== "7" && editClassLevel !== "8" && editClassLevel !== "9") {
      setEditBatchBoardFilter("");
    }
    if (!editBatchOptions.some((batch) => batch.id === editBatchId)) {
      setEditBatchId(editBatchOptions[0]?.id ?? "");
    }
  }, [editClassLevel, editBatchOptions, editBatchId]);

  async function onCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      if (feeMode === "structure" && !feeStructureId) {
        setError("Please select fee structure.");
        return;
      }
      if (feeMode === "manual" && Number(manualFeeAmount || 0) <= 0) {
        setError("Please enter manual total fee.");
        return;
      }
      if (Number(installments || 0) < 1) {
        setError("EMI count should be at least 1.");
        return;
      }
      if (statusValue === "confirmed" && !batchId) {
        setError("Batch allocation is required when status is Confirmed.");
        return;
      }

      const response = await apiRequest<any>("/api/v1/admin/enquiries", {
        method: "POST",
        body: JSON.stringify({
          student_name: studentName.trim(),
          class_level: Number(classLevel),
          previous_class: previousClass.trim() || null,
          previous_percentage: previousPercentage.trim() ? Number(previousPercentage) : null,
          school_name: schoolName.trim() || null,
          language,
          contact_number: contactNumber.trim(),
          parent_contact_number: parentContactNumber.trim(),
          follow_up_at: followUpAt ? new Date(followUpAt).toISOString() : null,
          batch_id: batchId || null,
          fee_class_level: selectedScope.classLevel,
          fee_stream: selectedScope.stream,
          fee_structure_id: feeMode === "structure" ? (feeStructureId || null) : null,
          manual_fee_amount: feeMode === "manual" && Number(manualFeeAmount || 0) > 0 ? Number(manualFeeAmount) : null,
          manual_fee_installment_count:
            feeMode === "manual" ? Number(installments || manualFeeInstallmentCount || 3) : null,
          negotiable_amount: negotiableAmount.trim() ? Number(negotiableAmount) : null,
          installment_count: installments.trim() ? Number(installments) : null,
          initial_fee_paid_amount: initialFeePaidAmount.trim() ? Number(initialFeePaidAmount) : null,
          initial_fee_paid_on: initialFeePaidOn ? initialFeePaidOn : null,
          initial_fee_payment_mode: initialFeePaymentMode,
          initial_fee_reference_no: initialFeeReferenceNo.trim() || null,
          initial_fee_note: initialFeeNote.trim() || null,
          status: statusValue,
          notes: notes.trim() || null,
        }),
      });

      if (response?.conversion?.student_id) {
        const loginId = response?.conversion?.login_id ?? response?.contact_number ?? contactNumber.trim();
        const generatedPassword = response?.conversion?.generated_password ?? response?.generated_password ?? null;
        setSuccess(
          generatedPassword
            ? `Enquiry converted to student (${response.conversion.student_id}). Login ID: ${loginId}, Temporary Password: ${generatedPassword}`
            : `Enquiry converted to student (${response.conversion.student_id}).`,
        );
      } else {
        setSuccess("Enquiry saved successfully.");
      }
      setStudentName("");
      setPreviousClass("");
      setPreviousPercentage("");
      setSchoolName("");
      setContactNumber("");
      setParentContactNumber("");
      setFollowUpAt("");
      setBatchBoardFilter("");
      setBatchId("");
      setFeeMode("structure");
      setManualFeeAmount("");
      setManualFeeInstallmentCount("3");
      setNegotiableAmount("");
      setInitialFeePaidAmount("");
      setInitialFeePaidOn("");
      setInitialFeePaymentMode("cash");
      setInitialFeeReferenceNo("");
      setInitialFeeNote("");
      setNotes("");
      await loadEnquiries();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save enquiry");
    } finally {
      setSaving(false);
    }
  }

  async function onEditSelect(item: EnquiryItem) {
    setSelectedEnquiryId(item.enquiry_id);
    setEditStudentName(item.student_name);
    setEditClassLevel(String(item.class_level));
    setEditPreviousClass(item.previous_class ?? "");
    setEditPreviousPercentage(item.previous_percentage != null ? String(item.previous_percentage) : "");
    setEditSchoolName(item.school_name ?? "");
    setEditLanguage(item.language === "hindi" ? "hindi" : "english");
    setEditContactNumber(item.contact_number);
    setEditParentContactNumber(item.parent_contact_number);
    setEditFollowUpAt(toInputDateTime(item.follow_up_at));
    setEditBatchId(item.batch_id ?? "");
    if (item.batch_id) {
      const linkedBatch = batches.find((batch) => batch.id === item.batch_id);
      setEditBatchBoardFilter(batchBoard(linkedBatch) ?? "");
    } else {
      setEditBatchBoardFilter("");
    }
    setEditFeeScope(scopeValueFrom(item.fee_class_level, item.fee_stream));
    setEditFeeStructureId(item.fee_structure_id ?? "");
    setEditFeeMode(item.manual_fee_amount != null && item.manual_fee_amount > 0 ? "manual" : "structure");
    setEditManualFeeAmount(item.manual_fee_amount != null ? String(item.manual_fee_amount) : "");
    setEditManualFeeInstallmentCount(
      item.manual_fee_installment_count != null ? String(item.manual_fee_installment_count) : "3",
    );
    setEditNegotiableAmount(item.negotiable_amount != null ? String(item.negotiable_amount) : "");
    setEditInstallments(item.installment_count != null ? String(item.installment_count) : "");
    setEditInitialFeePaidAmount(item.initial_fee_paid_amount != null ? String(item.initial_fee_paid_amount) : "");
    setEditInitialFeePaidOn(item.initial_fee_paid_on ? toInputDateTime(item.initial_fee_paid_on) : "");
    setEditInitialFeePaymentMode((item.initial_fee_payment_mode as any) || "cash");
    setEditInitialFeeReferenceNo(item.initial_fee_reference_no ?? "");
    setEditInitialFeeNote(item.initial_fee_note ?? "");
    setEditStatusValue(item.status);
    setEditNotes(item.notes ?? "");
    setStatusNote("");

    await Promise.all([
      loadTimeline(item.enquiry_id),
      loadFeeStructures(
        FEE_SCOPE_OPTIONS.find((entry) => entry.value === scopeValueFrom(item.fee_class_level, item.fee_stream)) ??
          FEE_SCOPE_OPTIONS[0],
        "edit",
      ),
    ]);
  }

  async function onUpdate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedEnquiryId) return;

    setUpdating(true);
    setError(null);
    setSuccess(null);
    try {
      if (editFeeMode === "structure" && !editFeeStructureId) {
        setError("Please select fee structure.");
        return;
      }
      if (editFeeMode === "manual" && Number(editManualFeeAmount || 0) <= 0) {
        setError("Please enter manual total fee.");
        return;
      }
      if (Number(editInstallments || 0) < 1) {
        setError("EMI count should be at least 1.");
        return;
      }
      if (editStatusValue === "confirmed" && !editBatchId) {
        setError("Batch allocation is required when status is Confirmed.");
        return;
      }

      const payload: Record<string, unknown> = {
        student_name: editStudentName.trim(),
        class_level: Number(editClassLevel),
        previous_class: editPreviousClass.trim() || null,
        previous_percentage: editPreviousPercentage.trim() ? Number(editPreviousPercentage) : null,
        school_name: editSchoolName.trim() || null,
        language: editLanguage,
        contact_number: editContactNumber.trim(),
        parent_contact_number: editParentContactNumber.trim(),
        batch_id: editBatchId || null,
        fee_class_level: selectedEditScope.classLevel,
        fee_stream: selectedEditScope.stream,
        fee_structure_id: editFeeMode === "structure" ? (editFeeStructureId || null) : null,
        manual_fee_amount: editFeeMode === "manual" && Number(editManualFeeAmount || 0) > 0 ? Number(editManualFeeAmount) : null,
        manual_fee_installment_count:
          editFeeMode === "manual" ? Number(editInstallments || editManualFeeInstallmentCount || 3) : null,
        negotiable_amount: editNegotiableAmount.trim() ? Number(editNegotiableAmount) : null,
        installment_count: editInstallments.trim() ? Number(editInstallments) : null,
        initial_fee_paid_amount: editInitialFeePaidAmount.trim() ? Number(editInitialFeePaidAmount) : null,
        initial_fee_paid_on: editInitialFeePaidOn ? editInitialFeePaidOn : null,
        initial_fee_payment_mode: editInitialFeePaymentMode,
        initial_fee_reference_no: editInitialFeeReferenceNo.trim() || null,
        initial_fee_note: editInitialFeeNote.trim() || null,
        status: editStatusValue,
        notes: editNotes.trim() || null,
        status_note: statusNote.trim() || null,
      };
      if (editFollowUpAt) {
        payload.follow_up_at = new Date(editFollowUpAt).toISOString();
      }

      const response = await apiRequest<any>(`/api/v1/admin/enquiries/${selectedEnquiryId}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });

      if (response?.conversion?.student_id) {
        const loginId = response?.conversion?.login_id ?? response?.contact_number ?? editContactNumber.trim();
        const generatedPassword = response?.conversion?.generated_password ?? response?.generated_password ?? null;
        setSuccess(
          generatedPassword
            ? `Enquiry updated and converted (${response.conversion.student_id}). Login ID: ${loginId}, Temporary Password: ${generatedPassword}`
            : `Enquiry updated and converted to student (${response.conversion.student_id}).`,
        );
      } else {
        setSuccess("Enquiry updated successfully.");
      }
      await Promise.all([loadEnquiries(), loadTimeline(selectedEnquiryId)]);
      setStatusNote("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update enquiry");
    } finally {
      setUpdating(false);
    }
  }

  return (
    <section className={styles.root}>
      <div className={styles.header}>
        <h1 className={styles.title}>Enquiry</h1>
        <p className={styles.subtitle}>Capture, edit and track enquiry follow-up progression with full status timeline.</p>
      </div>

      {error ? <p className={styles.error}>{error}</p> : null}
      {success ? <p className={styles.success}>{success}</p> : null}

      <form className={styles.card} onSubmit={onCreate}>
        <h2 className={styles.cardTitle}>Section 1: Student Details</h2>
        <div className={styles.formGrid}>
          <label className={styles.field}>
            <span>Student Name</span>
            <input value={studentName} onChange={(e) => setStudentName(e.target.value)} required />
          </label>
          <label className={styles.field}>
            <span>Class</span>
            <select value={classLevel} onChange={(e) => setClassLevel(e.target.value)} required>
              <option value="6">6th</option>
              <option value="7">7th</option>
              <option value="8">8th</option>
              <option value="9">9th</option>
              <option value="10">10th</option>
              <option value="11">11th</option>
              <option value="12">12th</option>
            </select>
          </label>
          <label className={styles.field}>
            <span>Previous Class</span>
            <input value={previousClass} onChange={(e) => setPreviousClass(e.target.value)} />
          </label>
          <label className={styles.field}>
            <span>Previous Percentage</span>
            <input type="number" step="0.01" min={0} max={100} value={previousPercentage} onChange={(e) => setPreviousPercentage(e.target.value)} />
          </label>
          <label className={styles.field}>
            <span>School Name</span>
            <input value={schoolName} onChange={(e) => setSchoolName(e.target.value)} />
          </label>
          <label className={styles.field}>
            <span>Language</span>
            <select value={language} onChange={(e) => setLanguage(e.target.value as "hindi" | "english")}>
              <option value="english">English</option>
              <option value="hindi">Hindi</option>
            </select>
          </label>
          <label className={styles.field}>
            <span>Contact Number</span>
            <input value={contactNumber} onChange={(e) => setContactNumber(e.target.value)} required />
          </label>
          <label className={styles.field}>
            <span>Parent Contact</span>
            <input value={parentContactNumber} onChange={(e) => setParentContactNumber(e.target.value)} required />
          </label>
          <label className={styles.field}>
            <span>Follow-up Date/Time</span>
            <input type="datetime-local" value={followUpAt} onChange={(e) => setFollowUpAt(e.target.value)} />
          </label>

          {(classLevel === "6" || classLevel === "7" || classLevel === "8" || classLevel === "9") ? (
            <label className={styles.field}>
              <span>Board</span>
              <select value={batchBoardFilter} onChange={(e) => setBatchBoardFilter(e.target.value as "cbse_icse" | "state" | "")}> 
                <option value="">Select Board</option>
                <option value="cbse_icse">CBSE/ICSE</option>
                <option value="state">State Board</option>
              </select>
            </label>
          ) : null}
          <label className={styles.field}>
            <span>Batch Allocation {statusValue === "confirmed" ? "(Required)" : "(Optional)"}</span>
            <select value={batchId} onChange={(e) => setBatchId(e.target.value)}>
              <option value="">Select Batch</option>
              {createBatchOptions.map((batch) => (
                <option key={batch.id} value={batch.id}>
                  {batch.name} ({batch.academic_year}) {batchStandardName(batch) ? `- ${batchStandardName(batch)}` : ""}
                </option>
              ))}
            </select>
          </label>
        </div>

        <h2 className={styles.cardTitle}>Section 2: Fee Details</h2>
        <div className={styles.formGrid}>
          <label className={styles.field}>
            <span>Fee Details</span>
            <select value={feeScope} onChange={(e) => setFeeScope(e.target.value)}>
              {FEE_SCOPE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label className={styles.field}>
            <span>Mode</span>
            <select value={feeMode} onChange={(e) => setFeeMode(e.target.value as "structure" | "manual")}>
              <option value="structure">Fee Structure</option>
              <option value="manual">Manual</option>
            </select>
          </label>
          {feeMode === "structure" ? (
            <label className={styles.field}>
              <span>Fee Structure</span>
              <select value={feeStructureId} onChange={(e) => setFeeStructureId(e.target.value)}>
                {structures.length === 0 ? <option value="">No active fee structure</option> : null}
                {structures.map((structure) => (
                  <option key={structure.id} value={structure.id}>
                    {structure.name} - {currency(structure.total_amount)}
                  </option>
                ))}
              </select>
            </label>
          ) : (
            <label className={styles.field}>
              <span>Manual Total Fee</span>
              <input type="number" min={0} step="0.01" value={manualFeeAmount} onChange={(e) => setManualFeeAmount(e.target.value)} />
            </label>
          )}
          <label className={styles.field}>
            <span>Negotiable Amount</span>
            <input type="number" min={0} step="0.01" value={negotiableAmount} onChange={(e) => setNegotiableAmount(e.target.value)} />
          </label>
          <label className={styles.field}>
            <span>EMI Count</span>
            <input type="number" min={1} max={24} value={installments} onChange={(e) => setInstallments(e.target.value)} />
          </label>
          <label className={styles.field}>
            <span>Paid Amount (First Installment)</span>
            <input type="number" min={0} step="0.01" value={initialFeePaidAmount} onChange={(e) => setInitialFeePaidAmount(e.target.value)} />
          </label>
          <label className={styles.field}>
            <span>Paid On</span>
            <input type="date" value={initialFeePaidOn} onChange={(e) => setInitialFeePaidOn(e.target.value)} />
          </label>
          <label className={styles.field}>
            <span>Payment Mode</span>
            <select value={initialFeePaymentMode} onChange={(e) => setInitialFeePaymentMode(e.target.value as any)}>
              <option value="cash">Cash</option>
              <option value="upi">UPI</option>
              <option value="bank_transfer">Bank Transfer</option>
              <option value="card">Card</option>
              <option value="cheque">Cheque</option>
              <option value="other">Other</option>
            </select>
          </label>
          <label className={styles.field}>
            <span>Payment Ref</span>
            <input value={initialFeeReferenceNo} onChange={(e) => setInitialFeeReferenceNo(e.target.value)} />
          </label>
          <label className={styles.field}>
            <span>Status</span>
            <select value={statusValue} onChange={(e) => setStatusValue(e.target.value as typeof statusValue)}>
              <option value="interested">Intrested</option>
              <option value="follow_up">Follow-up</option>
              <option value="confirmed">Confirmed</option>
              <option value="not_interested">Not-Intrested</option>
            </select>
          </label>
          <label className={`${styles.field} ${styles.fieldWide}`}>
            <span>Notes (optional)</span>
            <textarea rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
          </label>
        </div>

        <div className={styles.infoStrip}>
          <span>Selected Fee Scope: {selectedScope.label}</span>
          <span>Auto Fee: {createFeeTotal > 0 ? currency(createFeeTotal) : "-"}</span>
          {createFeeTotal > 0 ? (
            <span>
              {(() => {
                const preview = buildInstallmentPreview(
                  createFeeTotal,
                  Number(initialFeePaidAmount || 0),
                  Number(installments || 1),
                );
                return `First EMI ${currency(preview.first)}${preview.parts.map((part, index) => ` | EMI ${index + 2} ${currency(part)}`).join("")}`;
              })()}
            </span>
          ) : null}
        </div>

        <div className={styles.actions}>
          <button className="btn" type="submit" disabled={saving}>
            {saving ? "Saving..." : "Save Enquiry"}
          </button>
        </div>
      </form>

      <div className={styles.card}>
        <div className={styles.listHeader}>
          <h2 className={styles.cardTitle}>Enquiry List</h2>
          <label className={styles.searchField}>
            <span>Search</span>
            <input placeholder="Name / contact / class" value={search} onChange={(e) => setSearch(e.target.value)} />
          </label>
        </div>

        {loading ? (
          <p>Loading enquiries...</p>
        ) : (
          <div className={styles.tableWrap}>
            <table className="table">
              <thead>
                <tr>
                  <th>Student</th>
                  <th>Class</th>
                  <th>Contacts</th>
                  <th>Fee Scope</th>
                  <th>Fee</th>
                  <th>Status</th>
                  <th>Follow-up</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredItems.map((item) => (
                  <tr key={item.enquiry_id}>
                    <td>
                      <div className={styles.mainCell}>{item.student_name}</div>
                      <div className={styles.subCell}>{item.school_name ?? "-"}</div>
                    </td>
                    <td>
                      {item.class_level}th
                      {item.previous_class ? <div className={styles.subCell}>Prev: {item.previous_class}</div> : null}
                    </td>
                    <td>
                      <div>{item.contact_number}</div>
                      <div className={styles.subCell}>Parent: {item.parent_contact_number}</div>
                    </td>
                    <td>
                      <div>{item.fee_class_level}th</div>
                      <div className={styles.subCell}>{feeStreamLabel(item.fee_stream)}</div>
                    </td>
                    <td>
                      <div>{currency(item.fee_amount)}</div>
                      <div className={styles.subCell}>Negotiable: {currency(item.negotiable_amount)}</div>
                    </td>
                    <td>{item.status}</td>
                    <td>{formatDateTime(item.follow_up_at)}</td>
                    <td>
                      <button className="btn" type="button" onClick={() => void onEditSelect(item)}>
                        Edit
                      </button>
                    </td>
                  </tr>
                ))}
                {filteredItems.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="muted">
                      No enquiries found.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {selectedEnquiry ? (
        <div className={styles.editLayout}>
          <form className={styles.card} onSubmit={onUpdate}>
            <h2 className={styles.cardTitle}>Edit Enquiry</h2>
            <div className={styles.formGrid}>
              <label className={styles.field}>
                <span>Student Name</span>
                <input value={editStudentName} onChange={(e) => setEditStudentName(e.target.value)} required />
              </label>
              <label className={styles.field}>
                <span>Class</span>
                <select value={editClassLevel} onChange={(e) => setEditClassLevel(e.target.value)}>
                  <option value="6">6th</option>
                  <option value="7">7th</option>
                  <option value="8">8th</option>
                  <option value="9">9th</option>
                  <option value="10">10th</option>
                  <option value="11">11th</option>
                  <option value="12">12th</option>
                </select>
              </label>
              <label className={styles.field}>
                <span>Previous Class</span>
                <input value={editPreviousClass} onChange={(e) => setEditPreviousClass(e.target.value)} />
              </label>
              <label className={styles.field}>
                <span>Previous Percentage</span>
                <input type="number" step="0.01" min={0} max={100} value={editPreviousPercentage} onChange={(e) => setEditPreviousPercentage(e.target.value)} />
              </label>
              <label className={styles.field}>
                <span>School Name</span>
                <input value={editSchoolName} onChange={(e) => setEditSchoolName(e.target.value)} />
              </label>
              <label className={styles.field}>
                <span>Language</span>
                <select value={editLanguage} onChange={(e) => setEditLanguage(e.target.value as "hindi" | "english")}>
                  <option value="english">English</option>
                  <option value="hindi">Hindi</option>
                </select>
              </label>
              <label className={styles.field}>
                <span>Contact Number</span>
                <input value={editContactNumber} onChange={(e) => setEditContactNumber(e.target.value)} />
              </label>
              <label className={styles.field}>
                <span>Parent Contact</span>
                <input value={editParentContactNumber} onChange={(e) => setEditParentContactNumber(e.target.value)} />
              </label>
              <label className={styles.field}>
                <span>Follow-up Date/Time</span>
                <input type="datetime-local" value={editFollowUpAt} onChange={(e) => setEditFollowUpAt(e.target.value)} />
              </label>

              {(editClassLevel === "6" || editClassLevel === "7" || editClassLevel === "8" || editClassLevel === "9") ? (
                <label className={styles.field}>
                  <span>Board</span>
                  <select value={editBatchBoardFilter} onChange={(e) => setEditBatchBoardFilter(e.target.value as "cbse_icse" | "state" | "")}> 
                    <option value="">Select Board</option>
                    <option value="cbse_icse">CBSE/ICSE</option>
                    <option value="state">State Board</option>
                  </select>
                </label>
              ) : null}
              <label className={styles.field}>
                <span>Batch Allocation {editStatusValue === "confirmed" ? "(Required)" : "(Optional)"}</span>
                <select value={editBatchId} onChange={(e) => setEditBatchId(e.target.value)}>
                  <option value="">Select Batch</option>
                  {editBatchOptions.map((batch) => (
                    <option key={batch.id} value={batch.id}>
                      {batch.name} ({batch.academic_year}) {batchStandardName(batch) ? `- ${batchStandardName(batch)}` : ""}
                    </option>
                  ))}
                </select>
              </label>

              <label className={styles.field}>
                <span>Fee Details</span>
                <select value={editFeeScope} onChange={(e) => setEditFeeScope(e.target.value)}>
                  {FEE_SCOPE_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className={styles.field}>
                <span>Mode</span>
                <select value={editFeeMode} onChange={(e) => setEditFeeMode(e.target.value as "structure" | "manual")}>
                  <option value="structure">Fee Structure</option>
                  <option value="manual">Manual</option>
                </select>
              </label>
              {editFeeMode === "structure" ? (
                <label className={styles.field}>
                  <span>Fee Structure</span>
                  <select value={editFeeStructureId} onChange={(e) => setEditFeeStructureId(e.target.value)}>
                    {editStructures.length === 0 ? <option value="">No active fee structure</option> : null}
                    {editStructures.map((structure) => (
                      <option key={structure.id} value={structure.id}>
                        {structure.name} - {currency(structure.total_amount)}
                      </option>
                    ))}
                  </select>
                </label>
              ) : (
                <label className={styles.field}>
                  <span>Manual Total Fee</span>
                  <input type="number" min={0} step="0.01" value={editManualFeeAmount} onChange={(e) => setEditManualFeeAmount(e.target.value)} />
                </label>
              )}
              <label className={styles.field}>
                <span>Negotiable Amount</span>
                <input type="number" min={0} step="0.01" value={editNegotiableAmount} onChange={(e) => setEditNegotiableAmount(e.target.value)} />
              </label>
              <label className={styles.field}>
                <span>EMI Count</span>
                <input type="number" min={1} max={24} value={editInstallments} onChange={(e) => setEditInstallments(e.target.value)} />
              </label>
              <label className={styles.field}>
                <span>Paid Amount (First Installment)</span>
                <input type="number" min={0} step="0.01" value={editInitialFeePaidAmount} onChange={(e) => setEditInitialFeePaidAmount(e.target.value)} />
              </label>
              <label className={styles.field}>
                <span>Paid On</span>
                <input type="date" value={editInitialFeePaidOn.slice(0, 10)} onChange={(e) => setEditInitialFeePaidOn(e.target.value)} />
              </label>
              <label className={styles.field}>
                <span>Payment Mode</span>
                <select value={editInitialFeePaymentMode} onChange={(e) => setEditInitialFeePaymentMode(e.target.value as any)}>
                  <option value="cash">Cash</option>
                  <option value="upi">UPI</option>
                  <option value="bank_transfer">Bank Transfer</option>
                  <option value="card">Card</option>
                  <option value="cheque">Cheque</option>
                  <option value="other">Other</option>
                </select>
              </label>
              <label className={styles.field}>
                <span>Payment Ref</span>
                <input value={editInitialFeeReferenceNo} onChange={(e) => setEditInitialFeeReferenceNo(e.target.value)} />
              </label>
              <label className={styles.field}>
                <span>Status</span>
                <select value={editStatusValue} onChange={(e) => setEditStatusValue(e.target.value as typeof editStatusValue)}>
                  <option value="interested">Intrested</option>
                  <option value="follow_up">Follow-up</option>
                  <option value="confirmed">Confirmed</option>
                  <option value="not_interested">Not-Intrested</option>
                </select>
              </label>

              <label className={`${styles.field} ${styles.fieldWide}`}>
                <span>Status Update Note (timeline)</span>
                <input
                  placeholder="Add short note for this update"
                  value={statusNote}
                  onChange={(e) => setStatusNote(e.target.value)}
                />
              </label>
              <label className={`${styles.field} ${styles.fieldWide}`}>
                <span>Notes</span>
                <textarea rows={2} value={editNotes} onChange={(e) => setEditNotes(e.target.value)} />
              </label>
            </div>

            <div className={styles.infoStrip}>
              <span>Selected: {selectedEnquiry.student_name}</span>
              <span>Auto Fee: {editFeeTotal > 0 ? currency(editFeeTotal) : "-"}</span>
              {editFeeTotal > 0 ? (
                <span>
                  {(() => {
                    const preview = buildInstallmentPreview(
                      editFeeTotal,
                      Number(editInitialFeePaidAmount || 0),
                      Number(editInstallments || 1),
                    );
                    return `First EMI ${currency(preview.first)}${preview.parts.map((part, index) => ` | EMI ${index + 2} ${currency(part)}`).join("")}`;
                  })()}
                </span>
              ) : null}
            </div>

            <div className={styles.actions}>
              <button className="btn" type="submit" disabled={updating}>
                {updating ? "Updating..." : "Update Enquiry"}
              </button>
            </div>
          </form>

          <div className={styles.card}>
            <h2 className={styles.cardTitle}>Status Timeline</h2>
            {timelineLoading ? <p>Loading timeline...</p> : null}
            {!timelineLoading && timelineItems.length === 0 ? <p className="muted">No timeline entries yet.</p> : null}
            {!timelineLoading && timelineItems.length > 0 ? (
              <div className={styles.timeline}>
                {timelineItems.map((item) => (
                  <div className={styles.timelineRow} key={item.timeline_id}>
                    <div className={styles.timelineStatus}>
                      {item.from_status ? `${item.from_status} → ${item.to_status}` : item.to_status}
                    </div>
                    <div className={styles.timelineMeta}>
                      {formatDateTime(item.changed_at)} • {item.changed_by_name ?? "Admin"}
                    </div>
                    <div className={styles.timelineNote}>{item.note || "-"}</div>
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        </div>
      ) : null}
    </section>
  );
}
