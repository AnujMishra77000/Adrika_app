"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import { apiRequest } from "@/lib/api";

type ParentItem = {
  parent_id: string;
  user_id: string;
  full_name: string;
  email: string | null;
  phone: string | null;
  linked_students_count: number;
  created_at: string;
};

type StudentItem = {
  student_id: string;
  full_name: string;
  admission_no: string;
  roll_no: string;
};

type ParentLink = {
  link_id: string;
  student_id: string;
  student_name: string;
  admission_no: string;
  roll_no: string;
  relation_type: string;
  is_primary: boolean;
  is_active: boolean;
  created_at: string;
};

export default function AdminParentsPage() {
  const [parents, setParents] = useState<ParentItem[]>([]);
  const [students, setStudents] = useState<StudentItem[]>([]);
  const [links, setLinks] = useState<ParentLink[]>([]);

  const [loading, setLoading] = useState(true);
  const [loadingLinks, setLoadingLinks] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [search, setSearch] = useState("");
  const [selectedParentId, setSelectedParentId] = useState("");

  const [parentUserId, setParentUserId] = useState("");
  const [studentId, setStudentId] = useState("");
  const [relationType, setRelationType] = useState("guardian");
  const [isPrimary, setIsPrimary] = useState(false);

  const selectedParent = useMemo(
    () => parents.find((item) => item.parent_id === selectedParentId) ?? null,
    [parents, selectedParentId],
  );

  async function loadParents(query?: string) {
    const params = new URLSearchParams({ limit: "100", offset: "0" });
    const trimmed = (query ?? search).trim();
    if (trimmed) {
      params.set("search", trimmed);
    }

    const response = await apiRequest<{ items: ParentItem[] }>(
      `/api/v1/admin/parents?${params.toString()}`,
    );
    setParents(response.items);

    if (response.items.length === 0) {
      setSelectedParentId("");
      setLinks([]);
      return response.items;
    }

    const stillExists = response.items.some((item) => item.parent_id === selectedParentId);
    const parentIdToUse = stillExists ? selectedParentId : response.items[0].parent_id;
    const userIdToUse =
      response.items.find((item) => item.parent_id === parentIdToUse)?.user_id ?? response.items[0].user_id;

    setSelectedParentId(parentIdToUse);
    setParentUserId(userIdToUse);

    return response.items;
  }

  async function loadStudents() {
    const response = await apiRequest<{ items: StudentItem[] }>(
      "/api/v1/admin/students?limit=100&offset=0",
    );
    setStudents(response.items);
    if (!studentId && response.items.length > 0) {
      setStudentId(response.items[0].student_id);
    }
  }

  async function loadLinks(parentId: string) {
    if (!parentId) {
      setLinks([]);
      return;
    }

    setLoadingLinks(true);
    try {
      const response = await apiRequest<{ items: ParentLink[] }>(
        `/api/v1/admin/parents/${parentId}/links?limit=100&offset=0`,
      );
      setLinks(response.items);
    } finally {
      setLoadingLinks(false);
    }
  }

  async function loadAll() {
    setLoading(true);
    setError(null);
    try {
      await Promise.all([loadParents(), loadStudents()]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load parent data");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (selectedParentId) {
      void loadLinks(selectedParentId);
    }
  }, [selectedParentId]);

  async function onSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      await loadParents(search);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to search parents");
    }
  }

  async function onCreateLink(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await apiRequest("/api/v1/admin/parents/links", {
        method: "POST",
        body: JSON.stringify({
          parent_user_id: parentUserId,
          student_id: studentId,
          relation_type: relationType,
          is_primary: isPrimary,
        }),
      });

      const refreshedParents = await loadParents(search);
      const parentForUser = refreshedParents.find((item) => item.user_id === parentUserId);
      if (parentForUser) {
        setSelectedParentId(parentForUser.parent_id);
        await loadLinks(parentForUser.parent_id);
      }
      setIsPrimary(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create parent link");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section>
      <h1 style={{ marginTop: 0 }}>Parents</h1>
      <p className="muted">Manage parent accounts and link parents to students.</p>
      {error ? <p style={{ color: "#dc2626" }}>{error}</p> : null}

      <div className="grid" style={{ marginBottom: 16 }}>
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Parent Directory</h3>
          <form onSubmit={onSearch} style={{ marginBottom: 12, display: "flex", gap: 8 }}>
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search name, email, or phone"
              style={{ flex: 1, border: "1px solid var(--line)", borderRadius: 8, padding: "8px 10px" }}
            />
            <button className="btn" type="submit">
              Search
            </button>
          </form>

          {loading ? (
            <p>Loading parents...</p>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Parent</th>
                  <th>Contact</th>
                  <th>Links</th>
                </tr>
              </thead>
              <tbody>
                {parents.map((parent) => (
                  <tr
                    key={parent.parent_id}
                    onClick={() => {
                      setSelectedParentId(parent.parent_id);
                      setParentUserId(parent.user_id);
                    }}
                    style={{
                      cursor: "pointer",
                      background: parent.parent_id === selectedParentId ? "#eef4ff" : "transparent",
                    }}
                  >
                    <td>{parent.full_name}</td>
                    <td>{parent.email ?? parent.phone ?? "-"}</td>
                    <td>{parent.linked_students_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="card">
          <h3 style={{ marginTop: 0 }}>Create Parent Link</h3>
          <form onSubmit={onCreateLink}>
            <label className="field">
              <span>Parent User</span>
              <select value={parentUserId} onChange={(event) => setParentUserId(event.target.value)} required>
                <option value="">Select parent</option>
                {parents.map((parent) => (
                  <option key={parent.user_id} value={parent.user_id}>
                    {parent.full_name} ({parent.email ?? parent.phone ?? "no-contact"})
                  </option>
                ))}
              </select>
            </label>

            <label className="field">
              <span>Student</span>
              <select value={studentId} onChange={(event) => setStudentId(event.target.value)} required>
                <option value="">Select student</option>
                {students.map((student) => (
                  <option key={student.student_id} value={student.student_id}>
                    {student.full_name} ({student.admission_no})
                  </option>
                ))}
              </select>
            </label>

            <label className="field">
              <span>Relation</span>
              <select value={relationType} onChange={(event) => setRelationType(event.target.value)}>
                <option value="father">Father</option>
                <option value="mother">Mother</option>
                <option value="guardian">Guardian</option>
                <option value="other">Other</option>
              </select>
            </label>

            <label className="field" style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <input
                type="checkbox"
                checked={isPrimary}
                onChange={(event) => setIsPrimary(event.target.checked)}
              />
              <span>Set as primary link</span>
            </label>

            <button className="btn" type="submit" disabled={submitting}>
              {submitting ? "Linking..." : "Create Link"}
            </button>
          </form>
        </div>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Selected Parent Links</h3>
        {selectedParent ? (
          <p className="muted" style={{ marginTop: 0 }}>
            {selectedParent.full_name} ({selectedParent.email ?? selectedParent.phone ?? "-"})
          </p>
        ) : null}
        {loadingLinks ? (
          <p>Loading links...</p>
        ) : links.length === 0 ? (
          <p className="muted">No linked students found for selected parent.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Student</th>
                <th>Admission</th>
                <th>Roll No</th>
                <th>Relation</th>
                <th>Primary</th>
                <th>Active</th>
              </tr>
            </thead>
            <tbody>
              {links.map((link) => (
                <tr key={link.link_id}>
                  <td>{link.student_name}</td>
                  <td>{link.admission_no}</td>
                  <td>{link.roll_no}</td>
                  <td>{link.relation_type}</td>
                  <td>{link.is_primary ? "Yes" : "No"}</td>
                  <td>{link.is_active ? "Yes" : "No"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}
