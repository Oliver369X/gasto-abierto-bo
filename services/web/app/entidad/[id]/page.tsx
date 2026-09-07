import Link from "next/link";
import { apiGet, formatDate, formatMoney, qualityBadgeLabel } from "@/lib/api";
import { activityKindLabel, severityLabel } from "@/lib/labels";

type Budget = {
  id: number;
  year: number;
  current_amount?: string;
  executed_amount?: string;
  initial_amount?: string;
  budget_initial?: string;
  budget_current?: string;
  commitment?: string;
  payment?: string;
  budget_phase?: string;
  category?: string;
  source_id: string;
};
type Entity = {
  id: number;
  name: string;
  level: string;
  source_id: string;
  entity_master_id?: number;
  source_quality?: string;
};
type Contract = {
  id: number;
  cuce?: string;
  object_description?: string;
  amount?: string;
  category?: string;
};
type Activity = {
  kind: string;
  title: string;
  at?: string;
  href?: string;
  meta?: Record<string, string | null>;
};
type YearRow = {
  year: number;
  contracts: number;
  contract_amount: string;
  budget_lines: number;
  budget_current_total: string;
  budget_executed_total: string;
};
type Alert = { id: number; title: string; severity: string };
type Master = { id: number; canonical_name: string; level?: string; department?: string };

function executionRatio(current: string, executed: string) {
  const cur = Number(current);
  const exe = Number(executed);
  if (!cur || cur <= 0) return "—";
  return `${((exe / cur) * 100).toFixed(1)}%`;
}

export default async function EntidadPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  let entity: Entity | null = null;
  try {
    entity = await apiGet<Entity>(`/v1/entities/${id}`);
  } catch {
    entity = null;
  }

  if (!entity) {
    return (
      <section className="section">
        <h2>Entidad no encontrada</h2>
        <p className="empty">La entidad #{id} no existe o la API no está disponible.</p>
        <p>
          <Link href="/explorar">← Volver a explorar</Link>
        </p>
      </section>
    );
  }

  const [contractsR, budgetsR, activityR, alertsR, historyR] = await Promise.allSettled([
    apiGet<Contract[]>(`/v1/contracts?entity=${id}&limit=50`),
    apiGet<Budget[]>(`/v1/budgets?entity_id=${id}`),
    apiGet<Activity[]>(`/v1/entities/${id}/activity?limit=30`),
    apiGet<Alert[]>(`/v1/alerts?entity_id=${id}&limit=10`),
    apiGet<YearRow[]>(`/v1/history/years?entity_id=${id}`),
  ]);
  const contracts = contractsR.status === "fulfilled" ? contractsR.value : [];
  const budgets = budgetsR.status === "fulfilled" ? budgetsR.value : [];
  const activity = activityR.status === "fulfilled" ? activityR.value : [];
  const alerts = alertsR.status === "fulfilled" ? alertsR.value : [];
  const history = historyR.status === "fulfilled" ? historyR.value : [];

  let master: Master | null = null;
  let aliases: string[] = [];
  if (entity.entity_master_id) {
    const [masterR, aliasesR] = await Promise.allSettled([
      apiGet<Master>(`/v1/entity-masters/${entity.entity_master_id}`),
      apiGet<string[]>(`/v1/entity-masters/${entity.entity_master_id}/aliases`),
    ]);
    master = masterR.status === "fulfilled" ? masterR.value : null;
    aliases = aliasesR.status === "fulfilled" ? aliasesR.value : [];
  }

  return (
    <section className="section">
      <h2>{master?.canonical_name || entity.name}</h2>
      <p className="lead">
        {master?.level || entity.level}
        {master?.department ? ` · ${master.department}` : ""} · Fuente: {entity.source_id} ·{" "}
        {qualityBadgeLabel(entity.source_quality)}
      </p>
      {aliases.length > 0 ? (
        <p className="lead">
          También aparece como: {Array.from(new Set(aliases)).slice(0, 6).join(" · ")}
        </p>
      ) : null}

      {alerts.length > 0 && (
        <>
          <h3>Alertas</h3>
          <ul className="provenance-list" style={{ marginBottom: "1.5rem" }}>
            {alerts.map((a) => (
              <li key={a.id}>
                <span>
                  <span className={`badge badge-${a.severity}`}>{severityLabel(a.severity)}</span>{" "}
                  {a.title}
                </span>
                <Link href={`/alertas/${a.id}`}>Ver</Link>
              </li>
            ))}
          </ul>
        </>
      )}

      <h3>Actividad reciente</h3>
      {activity.length === 0 ? (
        <p className="empty">Sin actividad registrada.</p>
      ) : (
        <ul className="provenance-list" style={{ marginBottom: "1.5rem" }}>
          {activity.map((ev, i) => (
            <li key={`${ev.kind}-${i}`}>
              <span>
                <span className="badge badge-cat">{activityKindLabel(ev.kind)}</span> {ev.title}
                {ev.at ? <span style={{ color: "var(--muted)" }}> · {formatDate(ev.at)}</span> : null}
              </span>
              {ev.href ? (
                ev.href.startsWith("http") ? (
                  <a href={ev.href} rel="noreferrer" target="_blank">
                    Abrir
                  </a>
                ) : (
                  <Link href={ev.href}>Abrir</Link>
                )
              ) : (
                <span />
              )}
            </li>
          ))}
        </ul>
      )}

      <h3>Presupuesto</h3>
      <p className="lead">
        Inicial, vigente y ejecutado son fases del mismo presupuesto — no se suman entre sí.
      </p>

      {history.length > 0 && (
        <>
          <h4>Correlación por gestión</h4>
          <p className="lead" style={{ marginBottom: "0.75rem" }}>
            Presupuesto vigente vs. contratos adjudicados por año (fuente Presupuesto Abierto + SICOES/OCP).
          </p>
          <div className="table-wrap" style={{ marginBottom: "1.5rem" }}>
            <table>
              <thead>
                <tr>
                  <th>Gestión</th>
                  <th>Líneas PPTO</th>
                  <th>Vigente</th>
                  <th>Ejecutado</th>
                  <th>Contratos</th>
                  <th>Monto contratos</th>
                  <th>Ejecución PPTO</th>
                </tr>
              </thead>
              <tbody>
                {history.map((y) => (
                  <tr key={y.year}>
                    <td>
                      <Link href={`/presupuesto?year=${y.year}`}>{y.year}</Link>
                    </td>
                    <td>{y.budget_lines}</td>
                    <td>{formatMoney(y.budget_current_total)}</td>
                    <td>{formatMoney(y.budget_executed_total)}</td>
                    <td>{y.contracts}</td>
                    <td>{formatMoney(y.contract_amount)}</td>
                    <td>
                      {executionRatio(y.budget_current_total, y.budget_executed_total)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {budgets.length === 0 ? (
        <p className="empty">Sin líneas presupuestarias para esta entidad.</p>
      ) : (
        <div className="table-wrap" style={{ marginBottom: "1.5rem" }}>
          <table>
            <thead>
              <tr>
                <th>Gestión</th>
                <th>Inicial</th>
                <th>Vigente</th>
                <th>Compromiso</th>
                <th>Ejecutado</th>
                <th>Fuente</th>
              </tr>
            </thead>
            <tbody>
              {budgets.map((b) => (
                <tr key={b.id}>
                  <td>{b.year}</td>
                  <td>{formatMoney(b.budget_initial || b.initial_amount)}</td>
                  <td>{formatMoney(b.budget_current || b.current_amount)}</td>
                  <td>{formatMoney(b.commitment)}</td>
                  <td>{formatMoney(b.payment || b.executed_amount)}</td>
                  <td>{b.source_id}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <h3>Contratos</h3>
      {contracts.length === 0 ? (
        <p className="empty">Sin contratos registrados para esta entidad.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>CUCE</th>
                <th>Objeto</th>
                <th>Categoría</th>
                <th>Monto</th>
              </tr>
            </thead>
            <tbody>
              {contracts.map((c) => (
                <tr key={c.id}>
                  <td>
                    <Link href={`/contrato/${c.id}`}>{c.cuce || `#${c.id}`}</Link>
                  </td>
                  <td>{c.object_description || "—"}</td>
                  <td>{c.category || "—"}</td>
                  <td>{formatMoney(c.amount)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
