export function apiBase(): string {
  // Server-side (Docker): talk to api service; browser: host-mapped port
  if (typeof window === "undefined") {
    return (
      process.env.API_INTERNAL_URL ||
      process.env.NEXT_PUBLIC_API_URL ||
      "http://api:8000"
    );
  }
  return process.env.NEXT_PUBLIC_API_URL || "";
}

/** Browser-facing API URL (downloads, external links). Uses /api proxy when env unset. */
export function apiPublicUrl(path: string): string {
  const p = path.startsWith("/") ? path : `/${path}`;
  const publicBase = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");
  if (publicBase) {
    return `${publicBase}${p}`;
  }
  return `/api${p}`;
}

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${apiBase()}${path}`, { next: { revalidate: 15 } });
  if (!res.ok) throw new Error(`API ${res.status} ${path}`);
  return res.json() as Promise<T>;
}

export function formatDate(v?: string | null): string {
  if (!v) return "—";
  const d = new Date(v);
  if (Number.isNaN(d.getTime())) return v;
  return d.toLocaleDateString("es-BO", { year: "numeric", month: "short", day: "numeric" });
}

export function formatDateTime(v?: string | null): string {
  if (!v) return "—";
  const d = new Date(v);
  if (Number.isNaN(d.getTime())) return v;
  return d.toLocaleString("es-BO", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatMoney(v?: string | number | null): string {
  if (v === null || v === undefined || v === "") return "Sin monto reportado";
  const n = typeof v === "number" ? v : Number(v);
  if (Number.isNaN(n)) return String(v);
  return n.toLocaleString("es-BO", { style: "currency", currency: "BOB", maximumFractionDigits: 0 });
}

export function qualityBadgeLabel(q?: string | null, isSynthetic?: boolean): string {
  if (isSynthetic || q === "SYNTHETIC" || q === "PLACEHOLDER") return "Sintético";
  if (q === "OFFICIAL_VERIFIED") return "Oficial verificado";
  if (q === "OFFICIAL_UNVERIFIED") return "Fuente oficial";
  if (q === "PARTIAL") return "Parcial";
  if (q === "CONFLICTED") return "En conflicto";
  if (q === "INFERRED") return "Inferido";
  if (!q) return "Pendiente";
  return q;
}
