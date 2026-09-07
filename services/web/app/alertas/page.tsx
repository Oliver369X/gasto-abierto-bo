import Link from "next/link";
import { apiGet } from "@/lib/api";
import { severityLabel } from "@/lib/labels";
import { Pager } from "@/app/components/Pager";

type Alert = {
  id: number;
  rule_id: string;
  severity: string;
  title: string;
  explanation: string;
  entity_id?: number;
  supplier_id?: number;
  contract_id?: number;
  evidence: Record<string, unknown>;
};

const FILTERS = [
  { value: "", label: "Todas" },
  { value: "high", label: "Alta" },
  { value: "medium", label: "Media" },
  { value: "low", label: "Baja" },
];

export default async function AlertasPage({
  searchParams,
}: {
  searchParams: Promise<{ severity?: string; page?: string }>;
}) {
  const sp = await searchParams;
  const current = sp.severity || "";
  const page = Math.max(1, Number(sp.page) || 1);
  const pageSize = 24;
  let alerts: Alert[] = [];
  let apiDown = false;
  try {
    const params = new URLSearchParams({
      limit: String(pageSize),
      offset: String((page - 1) * pageSize),
    });
    if (current) params.set("severity", current);
    alerts = await apiGet<Alert[]>(`/v1/alerts?${params}`);
  } catch {
    apiDown = true;
  }

  return (
    <section className="section">
      <h2>Alertas</h2>
      <p className="lead">
        Reglas transparentes — cada alerta incluye umbral, evidencia y explicación.
      </p>

      <div className="chips">
        {FILTERS.map((f) => (
          <Link
            key={f.value}
            href={f.value ? `/alertas?severity=${f.value}` : "/alertas"}
            className={`chip ${current === f.value ? "active" : ""}`}
          >
            {f.label}
          </Link>
        ))}
      </div>

      {apiDown ? (
        <p className="error-box">No pudimos cargar las alertas. Verificá que la API esté arriba.</p>
      ) : alerts.length === 0 ? (
        <p className="empty">No hay alertas con este filtro.</p>
      ) : (
        <div className="grid-2">
          {alerts.map((a) => (
            <article key={a.id} className="panel">
              <span className={`badge badge-${a.severity}`}>{severityLabel(a.severity)}</span>
              <h3 style={{ marginTop: "0.5rem", textTransform: "none", letterSpacing: 0, fontSize: "1rem", color: "var(--ink)" }}>
                <Link href={`/alertas/${a.id}`} style={{ color: "inherit" }}>
                  {a.title}
                </Link>
              </h3>
              <p className="hint">{a.explanation}</p>
              <p className="hint" style={{ marginTop: "0.6rem" }}>
                {a.entity_id ? <Link href={`/entidad/${a.entity_id}`}>Entidad</Link> : null}
                {a.supplier_id ? (
                  <>
                    {a.entity_id ? " · " : ""}
                    <Link href={`/proveedor/${a.supplier_id}`}>Proveedor</Link>
                  </>
                ) : null}
                {a.contract_id ? (
                  <>
                    {a.entity_id || a.supplier_id ? " · " : ""}
                    <Link href={`/contrato/${a.contract_id}`}>Contrato</Link>
                  </>
                ) : null}
              </p>
            </article>
          ))}
        </div>
      )}
      {!apiDown && (
        <Pager
          pathname="/alertas"
          params={current ? { severity: current } : {}}
          page={page}
          pageSize={pageSize}
          count={alerts.length}
        />
      )}
    </section>
  );
}
