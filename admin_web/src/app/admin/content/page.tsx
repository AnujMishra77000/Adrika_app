'use client';

import { FormEvent, useEffect, useState } from 'react';

import { apiRequest } from '@/lib/api';

type Banner = {
  id: string;
  title: string;
  media_url: string;
  action_url: string | null;
  active_from: string;
  active_to: string;
  priority: number;
  is_popup: boolean;
};

type DailyThought = {
  id: string;
  thought_date: string;
  text: string;
  is_active: boolean;
};

export default function AdminContentPage() {
  const [banners, setBanners] = useState<Banner[]>([]);
  const [thoughts, setThoughts] = useState<DailyThought[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [bannerTitle, setBannerTitle] = useState('');
  const [bannerMediaUrl, setBannerMediaUrl] = useState('');
  const [bannerActionUrl, setBannerActionUrl] = useState('');
  const [bannerActiveFrom, setBannerActiveFrom] = useState('');
  const [bannerActiveTo, setBannerActiveTo] = useState('');
  const [bannerPriority, setBannerPriority] = useState('0');
  const [bannerPopup, setBannerPopup] = useState(false);

  const [thoughtDate, setThoughtDate] = useState('');
  const [thoughtText, setThoughtText] = useState('');
  const [thoughtActive, setThoughtActive] = useState(true);

  async function load() {
    try {
      const [bannerRes, thoughtRes] = await Promise.all([
        apiRequest<{ items: Banner[] }>('/api/v1/admin/banners?limit=100&offset=0'),
        apiRequest<{ items: DailyThought[] }>('/api/v1/admin/daily-thoughts?limit=100&offset=0'),
      ]);
      setBanners(bannerRes.items);
      setThoughts(thoughtRes.items);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load content');
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function createBanner(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    try {
      await apiRequest('/api/v1/admin/banners', {
        method: 'POST',
        body: JSON.stringify({
          title: bannerTitle,
          media_url: bannerMediaUrl,
          action_url: bannerActionUrl || null,
          active_from: new Date(bannerActiveFrom).toISOString(),
          active_to: new Date(bannerActiveTo).toISOString(),
          priority: Number(bannerPriority),
          is_popup: bannerPopup,
        }),
      });
      setBannerTitle('');
      setBannerMediaUrl('');
      setBannerActionUrl('');
      setBannerActiveFrom('');
      setBannerActiveTo('');
      setBannerPriority('0');
      setBannerPopup(false);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create banner');
    }
  }

  async function upsertDailyThought(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    try {
      await apiRequest('/api/v1/admin/daily-thoughts', {
        method: 'PUT',
        body: JSON.stringify({
          thought_date: thoughtDate,
          text: thoughtText,
          is_active: thoughtActive,
        }),
      });
      setThoughtDate('');
      setThoughtText('');
      setThoughtActive(true);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save daily thought');
    }
  }

  return (
    <section>
      <h1 style={{ marginTop: 0 }}>Content</h1>
      {error ? <p style={{ color: '#dc2626' }}>{error}</p> : null}

      <div className="grid">
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Create Banner</h3>
          <form onSubmit={createBanner}>
            <label className="field"><span>Title</span><input value={bannerTitle} onChange={(e) => setBannerTitle(e.target.value)} required /></label>
            <label className="field"><span>Media URL</span><input value={bannerMediaUrl} onChange={(e) => setBannerMediaUrl(e.target.value)} required /></label>
            <label className="field"><span>Action URL (optional)</span><input value={bannerActionUrl} onChange={(e) => setBannerActionUrl(e.target.value)} /></label>
            <div className="grid">
              <label className="field"><span>Active From</span><input type="datetime-local" value={bannerActiveFrom} onChange={(e) => setBannerActiveFrom(e.target.value)} required /></label>
              <label className="field"><span>Active To</span><input type="datetime-local" value={bannerActiveTo} onChange={(e) => setBannerActiveTo(e.target.value)} required /></label>
            </div>
            <label className="field"><span>Priority</span><input value={bannerPriority} onChange={(e) => setBannerPriority(e.target.value)} /></label>
            <label className="field" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <input type="checkbox" checked={bannerPopup} onChange={(e) => setBannerPopup(e.target.checked)} />
              <span>Show as popup</span>
            </label>
            <button className="btn" type="submit">Save Banner</button>
          </form>
        </div>

        <div className="card">
          <h3 style={{ marginTop: 0 }}>Upsert Daily Thought</h3>
          <form onSubmit={upsertDailyThought}>
            <label className="field"><span>Date</span><input type="date" value={thoughtDate} onChange={(e) => setThoughtDate(e.target.value)} required /></label>
            <label className="field"><span>Thought</span><textarea rows={4} value={thoughtText} onChange={(e) => setThoughtText(e.target.value)} required /></label>
            <label className="field" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <input type="checkbox" checked={thoughtActive} onChange={(e) => setThoughtActive(e.target.checked)} />
              <span>Active</span>
            </label>
            <button className="btn" type="submit">Save Daily Thought</button>
          </form>
        </div>
      </div>

      <div className="grid" style={{ marginTop: 16 }}>
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Banners</h3>
          <table className="table">
            <thead><tr><th>Title</th><th>Window</th><th>Priority</th><th>Popup</th></tr></thead>
            <tbody>
              {banners.map((banner) => (
                <tr key={banner.id}>
                  <td>{banner.title}</td>
                  <td>{new Date(banner.active_from).toLocaleString()} - {new Date(banner.active_to).toLocaleString()}</td>
                  <td>{banner.priority}</td>
                  <td>{banner.is_popup ? 'Yes' : 'No'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="card">
          <h3 style={{ marginTop: 0 }}>Daily Thoughts</h3>
          <table className="table">
            <thead><tr><th>Date</th><th>Thought</th><th>Status</th></tr></thead>
            <tbody>
              {thoughts.map((thought) => (
                <tr key={thought.id}>
                  <td>{thought.thought_date}</td>
                  <td>{thought.text}</td>
                  <td><span className="badge">{thought.is_active ? 'active' : 'inactive'}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
