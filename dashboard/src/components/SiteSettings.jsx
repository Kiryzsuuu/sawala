import { useRef, useState } from "react";
import { X, Globe, Plus, Trash2, Upload } from "lucide-react";
import {
  SITE_DEFAULT_CONFIG,
  loadSiteConfig,
  saveSiteConfig,
  resetSiteConfig,
} from "../siteConfig";

function getAt(obj, path) {
  return path.reduce((node, key) => (node == null ? node : node[key]), obj);
}

function setAt(obj, path, value) {
  if (path.length === 0) return value;
  const [key, ...rest] = path;
  const clone = Array.isArray(obj) ? [...obj] : { ...obj };
  clone[key] = setAt(obj ? obj[key] : undefined, rest, value);
  return clone;
}

function Field({ label, hint, children }) {
  return (
    <div>
      <label className="mb-1.5 block text-xs font-medium text-ink-soft">{label}</label>
      {children}
      {hint && <p className="mb-3 mt-1 text-xs text-muted">{hint}</p>}
    </div>
  );
}

const inputClass =
  "w-full rounded-lg border border-line bg-paper px-3 py-2 text-sm text-ink-soft outline-none transition focus:border-ink-soft";

function Section({ title, hint, children }) {
  return (
    <div className="rounded-2xl border border-line bg-card p-5">
      <h3 className="text-sm font-semibold text-ink-soft">{title}</h3>
      {hint && <p className="mb-4 mt-1 text-xs text-muted">{hint}</p>}
      <div className="space-y-4">{children}</div>
    </div>
  );
}

function ImageField({ label, hint, value, onChange }) {
  const fileRef = useRef(null);

  function handleFile(e) {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => onChange(reader.result);
    reader.readAsDataURL(file);
    e.target.value = "";
  }

  return (
    <Field label={label} hint={hint}>
      <div className="flex items-center gap-3">
        {value ? (
          <img src={value} alt="" className="h-14 w-14 rounded-lg border border-line object-cover" />
        ) : (
          <div className="flex h-14 w-14 items-center justify-center rounded-lg border border-dashed border-line text-[10px] text-muted">
            No image
          </div>
        )}
        <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={handleFile} />
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          className="inline-flex items-center gap-1.5 rounded-lg bg-paper-alt px-3 py-2 text-xs text-ink-soft transition hover:bg-line"
        >
          <Upload size={13} /> Unggah
        </button>
        {value && (
          <button
            type="button"
            onClick={() => onChange("")}
            className="rounded-lg bg-paper-alt px-3 py-2 text-xs text-ink-soft transition hover:bg-line"
          >
            Hapus
          </button>
        )}
      </div>
    </Field>
  );
}

function ListEditor({ items, itemLabel, onChange, renderItem, makeEmpty }) {
  return (
    <div className="space-y-3">
      {items.map((item, i) => (
        <div key={i} className="relative rounded-xl border border-dashed border-line bg-paper p-3">
          <button
            type="button"
            onClick={() => onChange(items.filter((_, idx) => idx !== i))}
            className="absolute right-2 top-2 rounded-md bg-card px-1.5 py-0.5 text-[10px] font-medium text-ink-soft hover:text-ink"
          >
            <Trash2 size={12} />
          </button>
          <div className="space-y-2 pr-6">{renderItem(item, i, (next) => onChange(items.map((it, idx) => (idx === i ? next : it))))}</div>
        </div>
      ))}
      <button
        type="button"
        onClick={() => onChange([...items, makeEmpty()])}
        className="inline-flex items-center gap-1 text-xs font-medium text-ink-soft underline hover:text-ink"
      >
        <Plus size={12} /> Tambah {itemLabel}
      </button>
    </div>
  );
}

export default function SiteSettings({ onClose }) {
  const [config, setConfig] = useState(loadSiteConfig);
  const [savedMsg, setSavedMsg] = useState("");
  const importRef = useRef(null);

  function set(path, value) {
    setConfig((prev) => setAt(prev, path, value));
  }

  function get(path) {
    return getAt(config, path);
  }

  function handleSave() {
    saveSiteConfig(config);
    setSavedMsg("Tersimpan! Refresh landing page untuk melihat hasilnya.");
    setTimeout(() => setSavedMsg(""), 3000);
  }

  function handleReset() {
    if (!confirm("Kembalikan semua pengaturan landing page ke default?")) return;
    resetSiteConfig();
    setConfig(structuredClone(SITE_DEFAULT_CONFIG));
  }

  function handleExport() {
    const blob = new Blob([JSON.stringify(config, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "sawala-site-config.json";
    a.click();
    URL.revokeObjectURL(url);
  }

  function handleImport(e) {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        setConfig(JSON.parse(reader.result));
      } catch {
        alert("File JSON tidak valid.");
      }
    };
    reader.readAsText(file);
    e.target.value = "";
  }

  return (
    <div className="fixed inset-0 z-40 flex items-start justify-center overflow-y-auto bg-ink/40 p-3 sm:p-6">
      <div className="w-full max-w-3xl rounded-2xl border border-line bg-paper p-5 shadow-sm sm:p-6">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-sm font-semibold text-ink-soft">
            <Globe size={16} />
            Site Settings - Landing Page
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={handleExport}
              className="rounded-lg bg-paper-alt px-3 py-2 text-xs text-ink-soft transition hover:bg-line"
            >
              Export JSON
            </button>
            <button
              onClick={() => importRef.current?.click()}
              className="rounded-lg bg-paper-alt px-3 py-2 text-xs text-ink-soft transition hover:bg-line"
            >
              Import JSON
            </button>
            <input ref={importRef} type="file" accept="application/json" className="hidden" onChange={handleImport} />
            <button
              onClick={handleReset}
              className="rounded-lg bg-paper-alt px-3 py-2 text-xs text-ink-soft transition hover:bg-line"
            >
              Reset Default
            </button>
            <button
              onClick={handleSave}
              className="rounded-lg bg-ink-soft px-3 py-2 text-xs font-medium text-paper transition hover:bg-ink"
            >
              Simpan
            </button>
            <button onClick={onClose} className="text-muted hover:text-ink">
              <X size={18} />
            </button>
          </div>
        </div>

        {savedMsg && <p className="mb-4 text-xs text-ink-soft">{savedMsg}</p>}

        <div className="max-h-[70vh] space-y-4 overflow-y-auto pr-1">
          <Section title="Brand">
            <Field label="Nama Brand">
              <input className={inputClass} value={get(["brand", "name"])} onChange={(e) => set(["brand", "name"], e.target.value)} />
            </Field>
            <ImageField
              label="Logo (opsional)"
              hint="Menggantikan teks nama brand kalau diisi."
              value={get(["brand", "logoImage"])}
              onChange={(v) => set(["brand", "logoImage"], v)}
            />
          </Section>

          <Section title="Navigasi">
            <ListEditor
              items={get(["nav", "links"])}
              itemLabel="Menu"
              onChange={(v) => set(["nav", "links"], v)}
              makeEmpty={() => ({ label: "Menu Baru", href: "#" })}
              renderItem={(item, _i, update) => (
                <>
                  <input className={inputClass} placeholder="Label" value={item.label} onChange={(e) => update({ ...item, label: e.target.value })} />
                  <input className={inputClass} placeholder="Href" value={item.href} onChange={(e) => update({ ...item, href: e.target.value })} />
                </>
              )}
            />
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <Field label="Label Login">
                <input className={inputClass} value={get(["nav", "loginLabel"])} onChange={(e) => set(["nav", "loginLabel"], e.target.value)} />
              </Field>
              <Field label="Label Tombol CTA">
                <input className={inputClass} value={get(["nav", "ctaLabel"])} onChange={(e) => set(["nav", "ctaLabel"], e.target.value)} />
              </Field>
            </div>
          </Section>

          <Section title="Hero">
            <Field label="Badge Kecil">
              <input className={inputClass} value={get(["hero", "badge"])} onChange={(e) => set(["hero", "badge"], e.target.value)} />
            </Field>
            <Field label="Judul (bagian normal)">
              <input className={inputClass} value={get(["hero", "titleBefore"])} onChange={(e) => set(["hero", "titleBefore"], e.target.value)} />
            </Field>
            <Field label="Judul (bagian penekanan)">
              <input className={inputClass} value={get(["hero", "titleHighlight"])} onChange={(e) => set(["hero", "titleHighlight"], e.target.value)} />
            </Field>
            <Field label="Deskripsi">
              <textarea className={`${inputClass} min-h-[70px]`} value={get(["hero", "lead"])} onChange={(e) => set(["hero", "lead"], e.target.value)} />
            </Field>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <Field label="Tombol Utama - Label">
                <input className={inputClass} value={get(["hero", "primaryCtaLabel"])} onChange={(e) => set(["hero", "primaryCtaLabel"], e.target.value)} />
              </Field>
              <Field label="Tombol Utama - Link">
                <input className={inputClass} value={get(["hero", "primaryCtaHref"])} onChange={(e) => set(["hero", "primaryCtaHref"], e.target.value)} />
              </Field>
            </div>
            <Field label="Trust Line">
              <input className={inputClass} value={get(["hero", "trustLine"])} onChange={(e) => set(["hero", "trustLine"], e.target.value)} />
            </Field>
            <ImageField
              label="Gambar Hero (opsional)"
              hint="Menggantikan ilustrasi grid tile bawaan kalau diisi."
              value={get(["hero", "image"])}
              onChange={(v) => set(["hero", "image"], v)}
            />
          </Section>

          <Section title="Fitur Utama">
            <Field label="Kicker">
              <input className={inputClass} value={get(["features", "kicker"])} onChange={(e) => set(["features", "kicker"], e.target.value)} />
            </Field>
            <Field label="Judul">
              <input className={inputClass} value={get(["features", "title"])} onChange={(e) => set(["features", "title"], e.target.value)} />
            </Field>
            <ListEditor
              items={get(["features", "items"])}
              itemLabel="Fitur"
              onChange={(v) => set(["features", "items"], v)}
              makeEmpty={() => ({ title: "Fitur Baru", desc: "Deskripsi fitur." })}
              renderItem={(item, _i, update) => (
                <>
                  <input className={inputClass} placeholder="Judul" value={item.title} onChange={(e) => update({ ...item, title: e.target.value })} />
                  <textarea className={`${inputClass} min-h-[56px]`} placeholder="Deskripsi" value={item.desc} onChange={(e) => update({ ...item, desc: e.target.value })} />
                </>
              )}
            />
          </Section>

          <Section title="Cara Kerja (Steps)">
            <Field label="Judul">
              <input className={inputClass} value={get(["steps", "title"])} onChange={(e) => set(["steps", "title"], e.target.value)} />
            </Field>
            <ListEditor
              items={get(["steps", "items"])}
              itemLabel="Langkah"
              onChange={(v) => set(["steps", "items"], v)}
              makeEmpty={() => ({ title: "Langkah Baru", desc: "Deskripsi langkah." })}
              renderItem={(item, _i, update) => (
                <>
                  <input className={inputClass} placeholder="Judul Langkah" value={item.title} onChange={(e) => update({ ...item, title: e.target.value })} />
                  <textarea className={`${inputClass} min-h-[56px]`} placeholder="Deskripsi" value={item.desc} onChange={(e) => update({ ...item, desc: e.target.value })} />
                </>
              )}
            />
          </Section>

          <Section title="Insight Real-Time">
            <Field label="Judul">
              <input className={inputClass} value={get(["insight", "title"])} onChange={(e) => set(["insight", "title"], e.target.value)} />
            </Field>
            <Field label="Deskripsi">
              <textarea className={`${inputClass} min-h-[56px]`} value={get(["insight", "desc"])} onChange={(e) => set(["insight", "desc"], e.target.value)} />
            </Field>
            <ListEditor
              items={get(["insight", "checklist"])}
              itemLabel="Poin"
              onChange={(v) => set(["insight", "checklist"], v)}
              makeEmpty={() => "Poin baru"}
              renderItem={(item, _i, update) => (
                <input className={inputClass} value={item} onChange={(e) => update(e.target.value)} />
              )}
            />
            <ImageField
              label="Gambar Insight (opsional)"
              hint="Menggantikan mockup statistik bawaan kalau diisi."
              value={get(["insight", "image"])}
              onChange={(v) => set(["insight", "image"], v)}
            />
          </Section>

          <Section title="Harga">
            <Field label="Judul">
              <input className={inputClass} value={get(["pricing", "title"])} onChange={(e) => set(["pricing", "title"], e.target.value)} />
            </Field>
            <ListEditor
              items={get(["pricing", "plans"])}
              itemLabel="Paket"
              onChange={(v) => set(["pricing", "plans"], v)}
              makeEmpty={() => ({ name: "Paket Baru", desc: "Deskripsi.", price: "Rp0", ctaLabel: "Pilih", ctaHref: "/app/", dark: false })}
              renderItem={(item, _i, update) => (
                <>
                  <input className={inputClass} placeholder="Nama Paket" value={item.name} onChange={(e) => update({ ...item, name: e.target.value })} />
                  <textarea className={`${inputClass} min-h-[56px]`} placeholder="Deskripsi" value={item.desc} onChange={(e) => update({ ...item, desc: e.target.value })} />
                  <input className={inputClass} placeholder="Harga" value={item.price} onChange={(e) => update({ ...item, price: e.target.value })} />
                  <label className="flex items-center gap-2 text-xs font-medium text-ink-soft">
                    <input type="checkbox" checked={!!item.dark} onChange={(e) => update({ ...item, dark: e.target.checked })} />
                    Tampilkan gelap (highlight)
                  </label>
                </>
              )}
            />
          </Section>

          <Section title="CTA Banner">
            <Field label="Judul">
              <input className={inputClass} value={get(["ctaBanner", "title"])} onChange={(e) => set(["ctaBanner", "title"], e.target.value)} />
            </Field>
            <Field label="Subjudul">
              <input className={inputClass} value={get(["ctaBanner", "subtitle"])} onChange={(e) => set(["ctaBanner", "subtitle"], e.target.value)} />
            </Field>
          </Section>

          <Section title="Footer">
            <Field label="Deskripsi Singkat">
              <textarea className={`${inputClass} min-h-[56px]`} value={get(["footer", "description"])} onChange={(e) => set(["footer", "description"], e.target.value)} />
            </Field>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <Field label="Copyright">
                <input className={inputClass} value={get(["footer", "copyright"])} onChange={(e) => set(["footer", "copyright"], e.target.value)} />
              </Field>
              <Field label="Tagline">
                <input className={inputClass} value={get(["footer", "tagline"])} onChange={(e) => set(["footer", "tagline"], e.target.value)} />
              </Field>
            </div>
          </Section>
        </div>
      </div>
    </div>
  );
}
