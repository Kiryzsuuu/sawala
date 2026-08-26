/* SAWALA landing page - shared config store.
   Content is edited via admin.html and persisted in localStorage,
   so index.html always renders the latest saved version. */

const SAWALA_STORAGE_KEY = "sawala_site_config_v1";

const SAWALA_DEFAULT_CONFIG = {
  brand: {
    name: "sawala",
    logoImage: "", // base64 data URI, optional (overrides text logo when set)
  },
  nav: {
    links: [
      { label: "Fitur", href: "#fitur" },
      { label: "Cara Kerja", href: "#cara-kerja" },
      { label: "Deteksi", href: "#deteksi" },
      { label: "Harga", href: "#harga" },
    ],
    loginLabel: "Masuk",
    loginHref: "/app",
    ctaLabel: "Coba Gratis",
    ctaHref: "/app",
  },
  hero: {
    badge: "Live sekarang di dashboard kamu",
    titleBefore: "Pantau meeting Zoom & Meet, ",
    titleHighlight: "secara real-time.",
    lead: "SAWALA menganalisis setiap tile peserta secara otomatis, OnCam/OffCam, penggunaan HP, tanda fatigue, sampai ekspresi, lalu menampilkannya langsung di dashboard live. Tanpa plugin, tanpa ribet.",
    primaryCtaLabel: "Mulai Sesi Gratis",
    primaryCtaHref: "/app",
    secondaryCtaLabel: "Lihat Cara Kerja",
    secondaryCtaHref: "#cara-kerja",
    trustLine: "Berjalan lokal di laptop host - Tidak perlu install di sisi peserta",
    image: "", // optional base64 image to replace the illustrated tile grid
  },
  logos: {
    label: "Kompatibel dengan platform meeting favoritmu",
    items: ["Zoom", "Google Meet", "Microsoft Teams", "Webex"],
  },
  features: {
    kicker: "Fitur Utama",
    title: "Semua yang kamu butuhkan untuk memantau engagement peserta",
    subtitle: "Satu dashboard, empat lapis deteksi otomatis berbasis computer vision.",
    items: [
      { title: "Deteksi OnCam / OffCam", desc: "Ketahui siapa yang benar-benar menyalakan kamera dan siapa yang memakai avatar/foto statis, secara real-time per tile." },
      { title: "Deteksi Penggunaan HP", desc: "Sistem menandai peserta yang terlihat memegang atau melihat ponsel selama sesi berlangsung." },
      { title: "Indikator Fatigue", desc: "Analisis kelopak mata dan pola gerak untuk memberi sinyal dini kelelahan peserta di meeting panjang." },
      { title: "Ekspresi & Senyum", desc: "Rekap ekspresi peserta sepanjang sesi untuk membaca engagement tanpa perlu menonton ulang rekaman." },
      { title: "Screen Capture Lokal", desc: "Berjalan langsung dari layar host (mss) atau via browser (getDisplayMedia) tanpa install apa pun di sisi peserta." },
      { title: "Dashboard Live", desc: "Semua metrik tersaji real-time di web dashboard, siap dipantau dari perangkat lain di jaringan yang sama." },
    ],
  },
  steps: {
    kicker: "Cara Kerja",
    title: "Aktif dalam empat langkah sederhana",
    items: [
      { title: "Buka Gallery View", desc: "Susun peserta dalam mode gallery di Zoom atau Meet seperti biasa." },
      { title: "Klik Mulai Sesi", desc: "SAWALA mengambil screen capture layar host secara lokal, aman dan cepat." },
      { title: "Analisis Otomatis", desc: "Tiap tile peserta dipotong dan dianalisis model deteksi secara real-time." },
      { title: "Pantau di Dashboard", desc: "Lihat status tiap peserta langsung dari dashboard web yang live-update." },
    ],
  },
  insight: {
    kicker: "Insight Real-Time",
    title: "Data engagement, bukan sekadar daftar hadir",
    desc: "Alih-alih hanya mencatat kehadiran, SAWALA memberi gambaran nyata seberapa aktif peserta terlibat sepanjang meeting berlangsung.",
    checklist: [
      "Rekap OnCam rate per peserta dan per sesi",
      "Notifikasi saat penggunaan HP terdeteksi berulang",
      "Fallback heuristik otomatis jika model berat tidak terpasang",
      "Bisa jalan penuh offline di laptop host",
    ],
    ctaLabel: "Coba Sekarang",
    ctaHref: "/app",
    image: "", // optional base64 image to replace the stat mockup
  },
  pricing: {
    kicker: "Harga",
    title: "Gratis untuk mulai, siap dipakai kapan saja",
    subtitle: "SAWALA open-source dan bisa dijalankan sendiri (self-hosted), tanpa biaya lisensi.",
    plans: [
      { name: "Self-Hosted", desc: "Install via start.bat atau installer Windows. Jalan lokal, data tidak keluar dari perangkatmu.", price: "Gratis", ctaLabel: "Download", ctaHref: "/app", dark: false },
      { name: "Cloud (PM2 + Nginx)", desc: "Deploy di server sendiri untuk dipantau tim dari mana saja via browser.", price: "Hubungi Kami", ctaLabel: "Jadwalkan Demo", ctaHref: "/app", dark: true },
    ],
  },
  ctaBanner: {
    title: "Siap memantau meeting kamu?",
    subtitle: "Unduh SAWALA dan aktifkan sesi pertamamu dalam hitungan menit.",
    primaryLabel: "Masuk ke Dashboard",
    primaryHref: "/app",
    secondaryLabel: "Baca Dokumentasi",
    secondaryHref: "#",
  },
  footer: {
    description: "Sistem monitoring meeting real-time: OnCam/OffCam, deteksi HP, fatigue, dan ekspresi peserta, langsung di dashboard live.",
    columns: [
      { title: "Produk", links: [
        { label: "Fitur", href: "#fitur" },
        { label: "Cara Kerja", href: "#cara-kerja" },
        { label: "Insight", href: "#deteksi" },
        { label: "Harga", href: "#harga" },
      ]},
      { title: "Sumber Daya", links: [
        { label: "Dokumentasi", href: "#" },
        { label: "Panduan Penggunaan", href: "#" },
        { label: "Build Installer", href: "#" },
        { label: "Deploy Cloud", href: "#" },
      ]},
      { title: "Platform", links: [
        { label: "Zoom", href: "#" },
        { label: "Google Meet", href: "#" },
        { label: "Microsoft Teams", href: "#" },
        { label: "Webex", href: "#" },
      ]},
      { title: "Perusahaan", links: [
        { label: "Tentang", href: "#" },
        { label: "Kontak", href: "#" },
        { label: "Kebijakan Privasi", href: "#" },
      ]},
    ],
    copyright: "© 2026 SAWALA. Dibuat untuk monitoring meeting yang lebih baik.",
    tagline: "Skenario B - Host Monitoring",
  },
};

function sawalaDeepMerge(base, override) {
  if (Array.isArray(base)) {
    return Array.isArray(override) ? override : base;
  }
  if (typeof base === "object" && base !== null) {
    const result = { ...base };
    if (typeof override === "object" && override !== null) {
      for (const key of Object.keys(override)) {
        result[key] = key in base ? sawalaDeepMerge(base[key], override[key]) : override[key];
      }
    }
    return result;
  }
  return override !== undefined ? override : base;
}

function sawalaLoadConfig() {
  try {
    const raw = localStorage.getItem(SAWALA_STORAGE_KEY);
    if (!raw) return JSON.parse(JSON.stringify(SAWALA_DEFAULT_CONFIG));
    const saved = JSON.parse(raw);
    return sawalaDeepMerge(SAWALA_DEFAULT_CONFIG, saved);
  } catch (e) {
    console.warn("Gagal memuat konfigurasi tersimpan, memakai default.", e);
    return JSON.parse(JSON.stringify(SAWALA_DEFAULT_CONFIG));
  }
}

function sawalaSaveConfig(config) {
  localStorage.setItem(SAWALA_STORAGE_KEY, JSON.stringify(config));
}

function sawalaResetConfig() {
  localStorage.removeItem(SAWALA_STORAGE_KEY);
}
