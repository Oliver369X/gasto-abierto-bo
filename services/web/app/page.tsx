import Link from "next/link";
import { apiGet, formatMoney } from "@/lib/api";
import { severityLabel } from "@/lib/labels";

type Stats = {
  entities: number;
  contracts: number;
  alerts: number;
  audits: number;
  total_contract_amount: string;
  alerts_by_severity: Record<string, number>;
};

type Alert = { id: number; title: string; severity: string; explanation: string };

export default async function HomePage() {
  let stats: Stats | null = null;
  let alerts: Alert[] = [];
  let apiDown = false;
  try {
    stats = await apiGet<Stats>("/v1/stats");
    alerts = await apiGet<Alert[]>("/v1/alerts?limit=3");
  } catch {
    apiDown = true;
  }

  return (
    <>
      <section className="hero">
        <h1>El gasto público de Bolivia, explicado y verificable</h1>
        <p>
          Consolidamos presupuestos, contrataciones y auditorías de fuentes
          oficiales — cada cifra enlaza a su documento de origen.
        </p>
        <div className="cta-row">
          <Link className="btn btn-primary" href="/incendios">
            Gasto en incendios 2024
          </Link>
          <Link className="btn btn-ghost" href="/explorar">
            Explorar contratos
          </Link>
        </div>
      </section>

      {apiDown && (
        <section className="section">
          <p className="error-box">
            No pudimos conectar con la API. Si estás en local, levantá el stack con{" "}
            <code>docker compose up -d</code> y recargá la página.
          </p>
        </section>
      )}

      {stats && (
        <section className="section">
          <h2>Qué hay dentro</h2>
          <p className="lead">Cobertura actual de la plataforma.</p>
          <div className="grid-2">
            <article className="panel">
              <h3>Contratos</h3>
              <p className="stat">{stats.contracts.toLocaleString("es-BO")}</p>
              <p className="hint">{formatMoney(stats.total_contract_amount)} adjudicados</p>
            </article>
            <article className="panel">
              <h3>Entidades públicas</h3>
              <p className="stat">{stats.entities.toLocaleString("es-BO")}</p>
            </article>
            <article className="panel">
              <h3>Alertas activas</h3>
              <p className="stat">{stats.alerts.toLocaleString("es-BO")}</p>
              <p className="hint">
                {(stats.alerts_by_severity.high || 0) > 0
                  ? `${stats.alerts_by_severity.high} de severidad alta`
                  : "Reglas transparentes con evidencia"}
              </p>
            </article>
            <article className="panel">
              <h3>Auditorías</h3>
              <p className="stat">{stats.audits.toLocaleString("es-BO")}</p>
            </article>
          </div>
        </section>
      )}

      {alerts.length > 0 && (
        <section className="section">
          <h2>Alertas recientes</h2>
          <p className="lead">
            Cada alerta explica la regla que la disparó y muestra su evidencia.
          </p>
          <div className="grid-2">
            {alerts.map((a) => (
              <article key={a.id} className="panel">
                <span className={`badge badge-${a.severity}`}>
                  {severityLabel(a.severity)}
                </span>
                <h3 style={{ marginTop: "0.5rem", textTransform: "none", letterSpacing: 0, fontSize: "1rem", color: "var(--ink)" }}>
                  <Link href={`/alertas/${a.id}`} style={{ color: "inherit" }}>
                    {a.title}
                  </Link>
                </h3>
                <p className="hint">{a.explanation}</p>
              </article>
            ))}
          </div>
          <p style={{ marginTop: "1rem" }}>
            <Link href="/alertas">Ver todas las alertas →</Link>
          </p>
        </section>
      )}
    </>
  );
}
