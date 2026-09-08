import Link from "next/link";
import { apiGet, apiPublicUrl, formatDate, formatMoney } from "@/lib/api";
import { attributionLabel, cycleLabel, eventTypeLabel } from "@/lib/labels";
import { rejectedSections } from "@/lib/settled";

type Ledger = {
  year: number;
  quality_grade?: string;
  disclaimer: string;
  expenditures_count: number;
  amount_direct_verifiable: string;
  amount_probable: string;
  amount_parcial: string;
  amount_contracted: string;
  amount_synthetic_excluded?: string;
  amount_pools_no_relacionado?: string;
  donations_amount: string;
  donations_in_kind: number;
  by_attribution: { attribution: string; label: string; count: number; amount: string }[];
  by_cycle: { cycle: string; label: string; count: number; amount: string }[];
  by_ledger_bucket?: { attribution: string; label: string; count: number; amount: string }[];
  by_department: {
    slug: string;
    name: string;
    count: number;
    amount_direct: string;
    amount_probable: string;
  }[];
};

type Coverage = {
  disclaimer: string;
  by_year: {
    year: number;
    expenditures: number;
    synthetic: number;
    amount_direct_verifiable: string;
    hectares_dgf_simb?: number;
    quality_grade: string;
  }[];
  expenditures_by_source: Record<string, number>;
  territorial_coverage_ola1?: {
    slug: string;
    name: string;
    level: string;
    expenditures?: number;
  }[];
  fire_events: number;
  fire_clusters: number;
  capability_assets: number;
  fire_links: number;
};

type CycleRollup = {
  disclaimer: string;
  years: {
    year: number;
    directo_verificable: number;
    probable: number;
    preventive_share?: number | null;
    reactive_share?: number | null;
    unique_processes: number;
    cycles: Record<string, { budgeted: number; contracted: number }>;
  }[];
};

type Payer = {
  entity_id: number;
  name: string;
  count: number;
  amount_probable: string;
  amount_verifiable: string;
};

type Expenditure = {
  id: number;
  code: string;
  title: string;
  attribution: string;
  cycle: string;
  amount_attributed?: string;
  quality_grade: string;
  beneficiary_territory_name?: string;
  year: number;
  is_synthetic?: boolean;
  ledger_bucket?: string;
  recovery_status?: string;
};

type Operation = {
  id: number;
  metric_key: string;
  metric_label: string;
  value_numeric?: string;
  unit?: string;
  evidence_quote?: string;
};

type Metrics = {
  preventive_ratio?: string;
  reactive_ratio?: string;
  top5_supplier_share?: string;
  cost_per_operation?: string;
  cost_per_fire_attended?: string;
  notes: string[];
};

type HistoryRow = {
  year: number;
  quality_grade: string;
  expenditures: number;
  amount_direct: string;
  amount_probable: string;
  firms_detections: number;
  notes?: string;
};

type Declaration = {
  id: number;
  title: string;
  decree_number?: string;
  event_type: string;
  promulgated_at?: string;
  summary?: string;
};

type Satellite = {
  year: number;
  total_detections: number;
  disclaimer: string;
  by_department: { department: string; count: number }[];
};

type Compare = {
  year: number;
  emergency_disaster_pool_executed?: string;
  fire_direct_verifiable: string;
  fire_probable: string;
  gap_pool_minus_direct?: string;
  disclaimer: string;
};

type Donation = {
  id: number;
  donor_name: string;
  description?: string;
  in_kind: boolean;
  amount?: string;
};

type CapabilitySummary = {
  year: number;
  preventive_assets: number;
  reactive_rentals: number;
  by_type: Record<string, number>;
  items: { id: number; asset_type: string; name: string; ownership: string }[];
};

function pct(v?: string | null): string {
  if (v == null || v === "") return "—";
  const n = Number(v);
  if (Number.isNaN(n)) return String(v);
  return `${(n * 100).toFixed(1)}%`;
}

function share(v?: number | null): string {
  return v == null ? "—" : `${(v * 100).toFixed(1)}%`;
}

export default async function IncendiosPage({
  searchParams,
}: {
  searchParams: Promise<{
    year?: string;
    attribution?: string;
    cycle?: string;
    ilustrativos?: string;
  }>;
}) {
  const sp = await searchParams;
  const year = Number(sp.year || "2024") || 2024;
  const attribution = sp.attribution || "";
  const cycle = sp.cycle || "";
  // Modo honesto por defecto: ocultar filas sintéticas / ilustrativas
  const showIllustrative = sp.ilustrativos === "1";

  const q = new URLSearchParams({ year: String(year), limit: "40" });
  if (attribution) q.set("attribution", attribution);
  if (cycle) q.set("cycle", cycle);

  const [
    ledgerR,
    expendituresR,
    operationsR,
    metricsR,
    historyR,
    declarationsR,
    satelliteR,
    compareR,
    donationsR,
    coverageR,
    cyclesR,
    payersR,
    capabilitiesR,
  ] = await Promise.allSettled([
    apiGet<Ledger>(`/v1/fire/ledger?year=${year}`),
    apiGet<Expenditure[]>(`/v1/fire/expenditures?${q}`),
    apiGet<Operation[]>(`/v1/fire/operations?year=${year}`),
    apiGet<Metrics>(`/v1/fire/metrics?year=${year}`),
    apiGet<HistoryRow[]>("/v1/fire/history"),
    apiGet<Declaration[]>(`/v1/fire/declarations?year=${year}&limit=20`),
    apiGet<Satellite>(`/v1/fire/satellite?year=${year}`),
    apiGet<Compare>(`/v1/fire/compare?year=${year}`),
    apiGet<Donation[]>(`/v1/fire/donations?year=${year}`),
    apiGet<Coverage>("/v1/fire/coverage"),
    apiGet<CycleRollup>(`/v1/fire/cycles?year=${year}`),
    apiGet<Payer[]>(`/v1/fire/payers?year=${year}&limit=10`),
    apiGet<CapabilitySummary>(`/v1/fire/capabilities/summary?year=${year}`),
  ]);

  const ledger = ledgerR.status === "fulfilled" ? ledgerR.value : null;
  const expenditures = expendituresR.status === "fulfilled" ? expendituresR.value : [];
  const operations = operationsR.status === "fulfilled" ? operationsR.value : [];
  const metrics = metricsR.status === "fulfilled" ? metricsR.value : null;
  const history = historyR.status === "fulfilled" ? historyR.value : [];
  const declarations = declarationsR.status === "fulfilled" ? declarationsR.value : [];
  const satellite = satelliteR.status === "fulfilled" ? satelliteR.value : null;
  const compare = compareR.status === "fulfilled" ? compareR.value : null;
  const donations = donationsR.status === "fulfilled" ? donationsR.value : [];
  const coverage = coverageR.status === "fulfilled" ? coverageR.value : null;
  const cycles = cyclesR.status === "fulfilled" ? cyclesR.value : null;
  const payers = payersR.status === "fulfilled" ? payersR.value : [];
  const capabilities = capabilitiesR.status === "fulfilled" ? capabilitiesR.value : null;

  const partialFailures = rejectedSections(
    [
      ledgerR,
      expendituresR,
      operationsR,
      metricsR,
      historyR,
      declarationsR,
      satelliteR,
      compareR,
      donationsR,
      coverageR,
      cyclesR,
      payersR,
      capabilitiesR,
    ],
    [
      "resumen del ledger",
      "gastos",
      "operaciones",
      "métricas",
      "historia",
      "declaraciones",
      "satélite",
      "comparación",
      "donaciones",
      "cobertura",
      "ciclos presupuestarios",
      "pagadores",
      "capacidades",
    ],
  );

  const visibleExpenditures = showIllustrative
    ? expenditures
    : expenditures.filter((e) => !e.is_synthetic && e.ledger_bucket !== "sintetico");

  const years = history.length ? history.map((h) => h.year) : [2022, 2023, 2024, 2025];

  return (
    <>
      <section className="hero">
        <h1>¿Cuánto se gastó en incendios forestales?</h1>
        <p>
          Un libro mayor público: cada boliviano trazado hasta su fuente oficial.
          No es una cifra oficial única — es lo verificable, separado de lo probable.
        </p>
        <div className="cta-row">
          <Link className="btn btn-ghost" href="/incendios/mapa">
            Mapa territorial
          </Link>
          <Link className="btn btn-ghost" href="/metodologia#incendios">
            Cómo lo calculamos
          </Link>
          <a
            className="btn btn-ghost"
            href={apiPublicUrl(`/v1/fire/export.csv?year=${year}`)}
          >
            Descargar CSV
          </a>
        </div>
      </section>

      <section className="section" style={{ paddingTop: "0.5rem" }}>
        <div className="chips">
          {years.map((y) => (
            <Link
              key={y}
              className={`chip ${y === year ? "active" : ""}`}
              href={`/incendios?year=${y}`}
            >
              {y}
            </Link>
          ))}
        </div>
      </section>

      {partialFailures.length > 0 && (
        <section className="section" style={{ paddingTop: 0 }}>
          <p className="notice">
            Algunas secciones no cargaron ({partialFailures.join(", ")}). El resto de la página
            sigue disponible.
          </p>
        </section>
      )}

      {!ledger && (
        <section className="section" style={{ paddingTop: 0 }}>
          <p className="error-box">
            Aún no hay datos del ledger de incendios para {year}. Si administrás este
            despliegue, cargá el corpus de demostración documentado en{" "}
            <Link href="/metodologia#incendios">metodología · incendios</Link> y{" "}
            <Link href="/fuentes">fuentes</Link>.
          </p>
        </section>
      )}

      {ledger && (
        <>
          <section className="section" style={{ paddingTop: 0 }}>
            <h2>Lo verificable en {year}</h2>
            <p className="lead">{ledger.disclaimer}</p>
            <div className="grid-2">
              <article className="panel">
                <h3>Directo verificable</h3>
                <p className="stat">{formatMoney(ledger.amount_direct_verifiable)}</p>
                <p className="hint">Con evidencia documental (calidad A)</p>
              </article>
              <article className="panel">
                <h3>Probable</h3>
                <p className="stat">{formatMoney(ledger.amount_probable)}</p>
                <p className="hint">Relacionado, sin evidencia completa — no se suma al total</p>
              </article>
              <article className="panel">
                <h3>Parcial / pools</h3>
                <p className="stat">{formatMoney(ledger.amount_parcial)}</p>
                {ledger.amount_pools_no_relacionado && (
                  <p className="hint">
                    Pools excluidos: {formatMoney(ledger.amount_pools_no_relacionado)}
                  </p>
                )}
              </article>
              <article className="panel">
                <h3>Expedientes</h3>
                <p className="stat">{ledger.expenditures_count}</p>
                {ledger.quality_grade && (
                  <p className="hint">Calidad de la gestión: grado {ledger.quality_grade}</p>
                )}
              </article>
            </div>
            <p className="notice" style={{ marginTop: "1rem" }}>
              Esto <strong>no es el gasto total nacional</strong> en incendios — solo lo
              trazable con evidencia pública.
            </p>

            {(ledger.by_attribution.length > 0 || ledger.by_cycle.length > 0) && (
              <div className="chips" style={{ marginTop: "1.25rem" }}>
                {ledger.by_attribution.map((a) => (
                  <Link
                    key={a.attribution}
                    className={`chip ${attribution === a.attribution ? "active" : ""}`}
                    href={`/incendios?year=${year}&attribution=${a.attribution}`}
                  >
                    {a.label} ({a.count})
                  </Link>
                ))}
                {ledger.by_cycle.map((c) => (
                  <Link
                    key={c.cycle}
                    className={`chip ${cycle === c.cycle ? "active" : ""}`}
                    href={`/incendios?year=${year}&cycle=${c.cycle}`}
                  >
                    {c.label} ({c.count})
                  </Link>
                ))}
                {(attribution || cycle) && (
                  <Link className="chip" href={`/incendios?year=${year}`}>
                    Quitar filtros
                  </Link>
                )}
              </div>
            )}
          </section>

          <section className="section">
            <h2>Por departamento</h2>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Departamento</th>
                    <th>Expedientes</th>
                    <th>Directo</th>
                    <th>Probable</th>
                  </tr>
                </thead>
                <tbody>
                  {ledger.by_department.map((d) => (
                    <tr key={d.slug}>
                      <td>
                        <Link href={`/incendios/departamento/${d.slug}?year=${year}`}>
                          {d.name}
                        </Link>
                      </td>
                      <td>{d.count}</td>
                      <td>{formatMoney(d.amount_direct)}</td>
                      <td>{formatMoney(d.amount_probable)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="section">
            <h2>Expedientes</h2>
            <p className="lead">
              Cada expediente muestra quién paga, dónde se usa el dinero y su evidencia.
            </p>
            {visibleExpenditures.length === 0 ? (
              <p className="empty">Sin expedientes para estos filtros.</p>
            ) : (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Código</th>
                      <th>Título</th>
                      <th>Atribución</th>
                      <th>Ciclo</th>
                      <th>Territorio</th>
                      <th>Monto</th>
                    </tr>
                  </thead>
                  <tbody>
                    {visibleExpenditures.map((e) => (
                      <tr key={e.id}>
                        <td>
                          <Link href={`/incendios/expediente/${e.id}`}>{e.code}</Link>
                        </td>
                        <td>{e.title}</td>
                        <td>{attributionLabel(e.attribution)}</td>
                        <td>{cycleLabel(e.cycle)}</td>
                        <td>{e.beneficiary_territory_name || "—"}</td>
                        <td>{formatMoney(e.amount_attributed)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <p style={{ marginTop: "0.85rem" }}>
              {showIllustrative ? (
                <Link href={`/incendios?year=${year}`}>Ocultar filas ilustrativas</Link>
              ) : (
                <Link href={`/incendios?year=${year}&ilustrativos=1`}>
                  Mostrar también filas ilustrativas / sintéticas
                </Link>
              )}
            </p>
          </section>

          <section className="section">
            <h2>Profundizar</h2>
            <p className="lead">Análisis secundarios, desplegá el que te interese.</p>

            {payers.length > 0 && (
              <details className="more">
                <summary>Quién gastó ({year})</summary>
                <div className="more-body">
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Entidad</th>
                          <th>Expedientes</th>
                          <th>Verificable</th>
                          <th>Probable</th>
                        </tr>
                      </thead>
                      <tbody>
                        {payers.map((p) => (
                          <tr key={p.entity_id}>
                            <td>
                              <Link href={`/entidad/${p.entity_id}`}>{p.name}</Link>
                            </td>
                            <td>{p.count}</td>
                            <td>{formatMoney(p.amount_verifiable)}</td>
                            <td>{formatMoney(p.amount_probable)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </details>
            )}

            {cycles && cycles.years[0] && (
              <details className="more">
                <summary>Prevención vs respuesta ({year})</summary>
                <div className="more-body">
                  <p className="lead">{cycles.disclaimer}</p>
                  <div className="grid-2" style={{ marginBottom: "1rem" }}>
                    <article className="panel">
                      <h3>Preventivo (prevención + preparación)</h3>
                      <p className="stat-sm">{share(cycles.years[0].preventive_share)}</p>
                    </article>
                    <article className="panel">
                      <h3>Reactivo (respuesta + recuperación)</h3>
                      <p className="stat-sm">{share(cycles.years[0].reactive_share)}</p>
                    </article>
                  </div>
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Ciclo</th>
                          <th>Contratado</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(cycles.years[0].cycles).map(([c, v]) => (
                          <tr key={c}>
                            <td>{cycleLabel(c)}</td>
                            <td>{formatMoney(String(v.contracted))}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </details>
            )}

            {compare && (
              <details className="more">
                <summary>Anunciado vs verificable</summary>
                <div className="more-body">
                  <p className="lead">{compare.disclaimer}</p>
                  <div className="grid-2">
                    <article className="panel">
                      <h3>Pool emergencia/desastre</h3>
                      <p className="stat-sm">
                        {formatMoney(compare.emergency_disaster_pool_executed)}
                      </p>
                      <p className="hint">Multi-evento — no es solo incendios</p>
                    </article>
                    <article className="panel">
                      <h3>Directo incendios (ledger)</h3>
                      <p className="stat-sm">{formatMoney(compare.fire_direct_verifiable)}</p>
                    </article>
                    <article className="panel">
                      <h3>Brecha (pool − directo)</h3>
                      <p className="stat-sm">{formatMoney(compare.gap_pool_minus_direct)}</p>
                    </article>
                    <article className="panel">
                      <h3>Probable adicional</h3>
                      <p className="stat-sm">{formatMoney(compare.fire_probable)}</p>
                    </article>
                  </div>
                </div>
              </details>
            )}

            {capabilities && (
              <details className="more">
                <summary>Capacidad propia vs alquileres ({year})</summary>
                <div className="more-body">
                  <div className="grid-2" style={{ marginBottom: "1rem" }}>
                    <article className="panel">
                      <h3>Activos preventivos</h3>
                      <p className="stat-sm">{capabilities.preventive_assets}</p>
                    </article>
                    <article className="panel">
                      <h3>Alquileres reactivos</h3>
                      <p className="stat-sm">{capabilities.reactive_rentals}</p>
                    </article>
                  </div>
                  {Object.keys(capabilities.by_type).length > 0 && (
                    <p className="lead">
                      Por tipo:{" "}
                      {Object.entries(capabilities.by_type)
                        .map(([type, count]) => `${type}: ${count}`)
                        .join(" · ")}
                    </p>
                  )}
                </div>
              </details>
            )}

            {metrics && (
              <details className="more">
                <summary>Métricas ({year})</summary>
                <div className="more-body">
                  <div className="grid-2">
                    <article className="panel">
                      <h3>Preventivo / total</h3>
                      <p className="stat-sm">{pct(metrics.preventive_ratio)}</p>
                    </article>
                    <article className="panel">
                      <h3>Respuesta / total</h3>
                      <p className="stat-sm">{pct(metrics.reactive_ratio)}</p>
                    </article>
                    <article className="panel">
                      <h3>Top 5 proveedores</h3>
                      <p className="stat-sm">{pct(metrics.top5_supplier_share)}</p>
                    </article>
                    <article className="panel">
                      <h3>Costo por operación</h3>
                      <p className="stat-sm">{formatMoney(metrics.cost_per_operation)}</p>
                    </article>
                  </div>
                </div>
              </details>
            )}

            {history.length > 0 && (
              <details className="more">
                <summary>Serie histórica</summary>
                <div className="more-body">
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Año</th>
                          <th>Calidad</th>
                          <th>Expedientes</th>
                          <th>Directo</th>
                          <th>Probable</th>
                          <th>Focos FIRMS</th>
                        </tr>
                      </thead>
                      <tbody>
                        {history.map((h) => (
                          <tr key={h.year}>
                            <td>
                              <Link href={`/incendios?year=${h.year}`}>{h.year}</Link>
                            </td>
                            <td>{h.quality_grade}</td>
                            <td>{h.expenditures}</td>
                            <td>{formatMoney(h.amount_direct)}</td>
                            <td>{formatMoney(h.amount_probable)}</td>
                            <td>{h.firms_detections}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </details>
            )}

            {satellite && (
              <details className="more">
                <summary>Focos satelitales FIRMS ({year})</summary>
                <div className="more-body">
                  <p className="lead">{satellite.disclaimer}</p>
                  <p>
                    Detecciones en muestra: <strong>{satellite.total_detections}</strong>
                  </p>
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Departamento</th>
                          <th>Focos (muestra)</th>
                        </tr>
                      </thead>
                      <tbody>
                        {satellite.by_department.map((d) => (
                          <tr key={d.department}>
                            <td>{d.department}</td>
                            <td>{d.count}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </details>
            )}

            {declarations.length > 0 && (
              <details className="more">
                <summary>Declaratorias de emergencia ({year})</summary>
                <div className="more-body">
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Decreto</th>
                          <th>Tipo</th>
                          <th>Fecha</th>
                          <th>Título</th>
                        </tr>
                      </thead>
                      <tbody>
                        {declarations.map((d) => (
                          <tr key={d.id}>
                            <td>{d.decree_number || "—"}</td>
                            <td>{eventTypeLabel(d.event_type)}</td>
                            <td>{formatDate(d.promulgated_at)}</td>
                            <td>
                              <Link href={`/incendios/declaratoria/${d.id}`}>{d.title}</Link>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </details>
            )}

            {donations.length > 0 && (
              <details className="more">
                <summary>Donaciones y ayuda ({year})</summary>
                <div className="more-body">
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Donante</th>
                          <th>Descripción</th>
                          <th>En especie</th>
                          <th>Monto</th>
                        </tr>
                      </thead>
                      <tbody>
                        {donations.map((d) => (
                          <tr key={d.id}>
                            <td>{d.donor_name}</td>
                            <td>{d.description || "—"}</td>
                            <td>{d.in_kind ? "Sí" : "No"}</td>
                            <td>{formatMoney(d.amount)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </details>
            )}

            {operations.length > 0 && (
              <details className="more">
                <summary>Resultados operativos</summary>
                <div className="more-body">
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Métrica</th>
                          <th>Valor</th>
                          <th>Evidencia</th>
                        </tr>
                      </thead>
                      <tbody>
                        {operations.map((o) => (
                          <tr key={o.id}>
                            <td>{o.metric_label}</td>
                            <td>
                              {o.value_numeric != null
                                ? Number(o.value_numeric).toLocaleString("es-BO")
                                : "—"}{" "}
                              {o.unit || ""}
                            </td>
                            <td style={{ maxWidth: "28rem" }}>{o.evidence_quote || "—"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </details>
            )}

            {coverage && (
              <details className="more">
                <summary>Cobertura del ledger</summary>
                <div className="more-body">
                  <p className="lead">{coverage.disclaimer}</p>
                  <div className="grid-2" style={{ marginBottom: "1rem" }}>
                    <article className="panel">
                      <h3>Eventos canónicos</h3>
                      <p className="stat-sm">{coverage.fire_events}</p>
                    </article>
                    <article className="panel">
                      <h3>Clusters satélite</h3>
                      <p className="stat-sm">{coverage.fire_clusters}</p>
                    </article>
                    <article className="panel">
                      <h3>Activos de capacidad</h3>
                      <p className="stat-sm">{coverage.capability_assets}</p>
                    </article>
                    <article className="panel">
                      <h3>Vínculos con evidencia</h3>
                      <p className="stat-sm">{coverage.fire_links}</p>
                    </article>
                  </div>
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Fuente</th>
                          <th>Expedientes</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(coverage.expenditures_by_source).map(([src, n]) => (
                          <tr key={src}>
                            <td>{src}</td>
                            <td>{n}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </details>
            )}
          </section>
        </>
      )}
    </>
  );
}
