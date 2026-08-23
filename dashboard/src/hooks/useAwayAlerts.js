import { useEffect, useRef, useState } from "react";

const FLAG_LABELS = {
  AVATAR: "kemungkinan pakai avatar/foto",
  HOLDING_PHONE: "terlihat memegang HP",
  FATIGUE: "menunjukkan tanda kelelahan",
  OFFCAM: "kamera mati",
};

function supportsNotifications() {
  return typeof window !== "undefined" && "Notification" in window;
}

export function useAwayAlerts(participants) {
  const [permission, setPermission] = useState(supportsNotifications() ? Notification.permission : "unsupported");
  const previousFlagsRef = useRef({});

  useEffect(() => {
    if (!supportsNotifications() || permission !== "granted") {
      // Masih catat state flag saat ini supaya begitu izin diberikan nanti,
      // notifikasi tidak langsung membanjir untuk flag yang sudah lama ada.
      const snapshot = {};
      for (const p of participants) snapshot[p.id] = new Set(p.flags || []);
      previousFlagsRef.current = snapshot;
      return;
    }

    const tabIsHidden = document.hidden;

    for (const p of participants) {
      const prevFlags = previousFlagsRef.current[p.id] || new Set();
      const currentFlags = new Set(p.flags || []);

      for (const flag of currentFlags) {
        const isNew = !prevFlags.has(flag);
        const label = FLAG_LABELS[flag];
        if (isNew && label && tabIsHidden) {
          const notif = new Notification("SAWALA", {
            body: `${p.name}: ${label}`,
            tag: `${p.id}-${flag}`,
          });
          notif.onclick = () => {
            window.focus();
            notif.close();
          };
        }
      }

      previousFlagsRef.current[p.id] = currentFlags;
    }
  }, [participants, permission]);

  async function requestPermission() {
    if (!supportsNotifications()) return;
    const result = await Notification.requestPermission();
    setPermission(result);
  }

  return { permission, requestPermission };
}
