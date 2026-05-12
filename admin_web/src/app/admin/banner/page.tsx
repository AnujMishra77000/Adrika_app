"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

import { apiRequest } from "@/lib/api";

import styles from "./banner.module.css";

type BannerItem = {
  id: string;
  title: string;
  media_url: string;
  action_url: string | null;
  active_from: string;
  active_to: string;
  priority: number;
  is_popup: boolean;
  is_active: boolean;
  is_live: boolean;
};

type UploadResponse = {
  file_url: string;
  width: number;
  height: number;
};

function toLocalDateTimeInputValue(value: Date): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  const hours = String(value.getHours()).padStart(2, "0");
  const minutes = String(value.getMinutes()).padStart(2, "0");
  return `${year}-${month}-${day}T${hours}:${minutes}`;
}

export default function AdminBannerPage() {
  const [items, setItems] = useState<BannerItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [toggleBusyId, setToggleBusyId] = useState<string | null>(null);

  const [title, setTitle] = useState("");
  const [actionUrl, setActionUrl] = useState("");
  const [priority, setPriority] = useState("0");
  const [isPopup, setIsPopup] = useState(false);
  const [isActive, setIsActive] = useState(true);
  const [file, setFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const now = useMemo(() => new Date(), []);
  const defaultFrom = useMemo(() => toLocalDateTimeInputValue(now), [now]);
  const defaultTo = useMemo(() => {
    const next = new Date(now.getTime());
    next.setDate(next.getDate() + 30);
    return toLocalDateTimeInputValue(next);
  }, [now]);
  const [activeFrom, setActiveFrom] = useState(defaultFrom);
  const [activeTo, setActiveTo] = useState(defaultTo);

  async function loadBanners() {
    try {
      const response = await apiRequest<{ items: BannerItem[] }>("/api/v1/admin/banners?limit=200&offset=0");
      setItems(response.items ?? []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load banners");
    }
  }

  useEffect(() => {
    void loadBanners();
  }, []);

  const activeItems = useMemo(
    () => items.filter((item) => item.is_active),
    [items],
  );
  const inactiveItems = useMemo(
    () => items.filter((item) => !item.is_active),
    [items],
  );

  async function createBanner(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const fromForm = formData.get("banner_file");
    const selectedFile = fromForm instanceof File && fromForm.size > 0 ? fromForm : file;

    if (!selectedFile) {
      setError("Please select a banner image");
      return;
    }

    try {
      setBusy(true);
      setError(null);

      const uploadBody = new FormData();
      uploadBody.append("file", selectedFile);
      const uploaded = await apiRequest<UploadResponse>("/api/v1/admin/banners/upload", {
        method: "POST",
        body: uploadBody,
      });

      await apiRequest("/api/v1/admin/banners", {
        method: "POST",
        body: JSON.stringify({
          title,
          media_url: uploaded.file_url,
          action_url: actionUrl || null,
          active_from: new Date(activeFrom).toISOString(),
          active_to: new Date(activeTo).toISOString(),
          priority: Number(priority),
          is_popup: isPopup,
          is_active: isActive,
        }),
      });

      setTitle("");
      setActionUrl("");
      setPriority("0");
      setIsPopup(false);
      setIsActive(true);
      setFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      setActiveFrom(defaultFrom);
      setActiveTo(defaultTo);
      await loadBanners();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create banner");
    } finally {
      setBusy(false);
    }
  }

  async function toggleBannerStatus(item: BannerItem, nextState: boolean) {
    try {
      setToggleBusyId(item.id);
      setError(null);
      await apiRequest(`/api/v1/admin/banners/${item.id}`, {
        method: "PATCH",
        body: JSON.stringify({ is_active: nextState }),
      });
      await loadBanners();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update banner status");
    } finally {
      setToggleBusyId(null);
    }
  }

  return (
    <section className={styles.root}>
      <header className={styles.hero}>
        <h1 className={styles.title}>Banner Management</h1>
        <p className={styles.subtitle}>
          Upload 16:9 student app banners, keep them Active/Inactive, and publish live instantly.
          Non-16:9 uploads are auto center-cropped to 16:9.
        </p>
      </header>

      {error ? <p className={styles.error}>{error}</p> : null}

      <div className={styles.grid}>
        <article className={styles.card}>
          <h2 className={styles.cardTitle}>Create Banner</h2>
          <p className={styles.hint}>
            Supported: JPG/PNG/WEBP. Backend normalizes to 16:9 and optimizes output.
          </p>

          <form onSubmit={createBanner}>
            <label className={styles.field}>
              <span className={styles.fieldLabel}>Title</span>
              <input
                className={styles.input}
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                required
              />
            </label>

            <label className={styles.field}>
              <span className={styles.fieldLabel}>Banner Image</span>
              <input
                ref={fileInputRef}
                className={styles.input}
                type="file"
                name="banner_file"
                accept="image/jpeg,image/jpg,image/png,image/webp"
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                required
              />
            </label>
            {file ? (
              <p className={styles.hint} style={{ marginTop: -2 }}>
                Selected: {file.name}
              </p>
            ) : null}

            <label className={styles.field}>
              <span className={styles.fieldLabel}>Action URL (optional)</span>
              <input
                className={styles.input}
                placeholder="/student/notices"
                value={actionUrl}
                onChange={(event) => setActionUrl(event.target.value)}
              />
            </label>

            <div className={styles.row}>
              <label className={styles.field}>
                <span className={styles.fieldLabel}>Active From</span>
                <input
                  className={styles.input}
                  type="datetime-local"
                  value={activeFrom}
                  onChange={(event) => setActiveFrom(event.target.value)}
                  required
                />
              </label>
              <label className={styles.field}>
                <span className={styles.fieldLabel}>Active To</span>
                <input
                  className={styles.input}
                  type="datetime-local"
                  value={activeTo}
                  onChange={(event) => setActiveTo(event.target.value)}
                  required
                />
              </label>
            </div>

            <div className={styles.row}>
              <label className={styles.field}>
                <span className={styles.fieldLabel}>Priority (0-100)</span>
                <input
                  className={styles.input}
                  type="number"
                  min={0}
                  max={100}
                  value={priority}
                  onChange={(event) => setPriority(event.target.value)}
                />
              </label>
              <label className={styles.field}>
                <span className={styles.fieldLabel}>Popup</span>
                <select
                  className={styles.select}
                  value={isPopup ? "yes" : "no"}
                  onChange={(event) => setIsPopup(event.target.value === "yes")}
                >
                  <option value="no">No</option>
                  <option value="yes">Yes</option>
                </select>
              </label>
            </div>

            <label className={styles.toggleRow}>
              <input
                type="checkbox"
                checked={isActive}
                onChange={(event) => setIsActive(event.target.checked)}
              />
              Active immediately
            </label>

            <div className={styles.buttonRow}>
              <button className={styles.btnPrimary} type="submit" disabled={busy}>
                {busy ? "Saving..." : "Upload & Create Banner"}
              </button>
            </div>
          </form>
        </article>

        <section className={styles.bannerLists}>
          <article className={styles.listBlock}>
            <div className={styles.listHeader}>
              <h3 className={styles.listTitle}>Active Banners</h3>
              <span className={styles.countPill}>{activeItems.length}</span>
            </div>
            {activeItems.length === 0 ? (
              <div className={styles.empty}>No active banners</div>
            ) : (
              <div className={styles.tableWrap}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th>Preview</th>
                      <th>Title</th>
                      <th>Window</th>
                      <th>Priority</th>
                      <th>Status</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {activeItems.map((item) => (
                      <tr key={item.id}>
                        <td><img src={item.media_url} alt={item.title} className={styles.thumb} /></td>
                        <td>{item.title}</td>
                        <td>
                          {new Date(item.active_from).toLocaleString()} - {new Date(item.active_to).toLocaleString()}
                        </td>
                        <td>{item.priority}</td>
                        <td>
                          <span className={item.is_live ? styles.badgeLive : styles.badgeWindow}>
                            {item.is_live ? "Live" : "Window Pending"}
                          </span>
                        </td>
                        <td>
                          <button
                            className={styles.btnSecondary}
                            type="button"
                            disabled={toggleBusyId === item.id}
                            onClick={() => void toggleBannerStatus(item, false)}
                          >
                            {toggleBusyId === item.id ? "Updating..." : "Make Inactive"}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </article>

          <article className={styles.listBlock}>
            <div className={styles.listHeader}>
              <h3 className={styles.listTitle}>Inactive Banners</h3>
              <span className={styles.countPill}>{inactiveItems.length}</span>
            </div>
            {inactiveItems.length === 0 ? (
              <div className={styles.empty}>No inactive banners</div>
            ) : (
              <div className={styles.tableWrap}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th>Preview</th>
                      <th>Title</th>
                      <th>Window</th>
                      <th>Priority</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {inactiveItems.map((item) => (
                      <tr key={item.id}>
                        <td><img src={item.media_url} alt={item.title} className={styles.thumb} /></td>
                        <td>{item.title}</td>
                        <td>
                          {new Date(item.active_from).toLocaleString()} - {new Date(item.active_to).toLocaleString()}
                        </td>
                        <td>{item.priority}</td>
                        <td>
                          <button
                            className={styles.btnPrimary}
                            type="button"
                            disabled={toggleBusyId === item.id}
                            onClick={() => void toggleBannerStatus(item, true)}
                          >
                            {toggleBusyId === item.id ? "Updating..." : "Make Active"}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </article>
        </section>
      </div>
    </section>
  );
}
