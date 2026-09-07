import Link from "next/link";
import { apiGet, formatMoney } from "@/lib/api";

type BudgetTotals = {
  lines: number;
  current_total: string;
  executed_total: string;
  payment_total: string;
  execution_ratio_pct?: number;
  years: number[];
  source_id: string;
};

type Aggregate = {
  key: string;
  label: string;
  lines: number;
  current_total: string;
  executed_total: string;
  entity_count: number;
  execution_ratio_pct?: number;
  href?: string;
};

type CrossSource = {
  discrepancies_budget_vs_contracts: number;
  cuces_multi_source: number;
};

function pct(v?: number) {
  if (v === undefined || v === null) return "—";
  return `${v.toFixed(1)}%`;
}

export default async function PresupuestoPage({
  searchParams,
}: {
  searchParams: Promise<{ year?: string; group?: string }>;
}) {
  const sp = await searchParams;
  const year = sp.year ? Number(sp.year) : undefined;
  const group = sp.group || "department";
  const yearQ = year ? `&year=${year}` : "";

  let totals: BudgetTotals | null = null;
  let byDept: Aggregate[] = [];
  let byEntity: Aggregate[] = [];
  let byYear: Aggregate[] = [];
  let cross: CrossSource | null = null;
  let apiDown = false;

  try {
    [totals, byDept, byEntity, byYear, cross] = await Promise.all([
      apiGet<BudgetTotals>(`/v1/budgets/totals${year ? `?year=${year}` : ""}`),
      apiGet<Aggregate[]>(`/v1/budgets/aggregate?group_by=department${yearQ}&limit=12`),
      apiGet<Aggregate[]>(`/v1/budgets/aggregate?group_by=entity${yearQ}&limit=10`),
      apiGet<Aggregate[]>(`/v1/budgets/aggregate?group_by=year&limit=10`),
      apiGet<CrossSource>("/v1/cross-source/summary"),
    ]);
  } catch {
    apiDown = true;
  }

  const activeGroup =
    group === "entity" ? byEntity : group === "year" ? byYear : byDept;
  const years = totals?.years?.length ? totals.years : byYear.map((y) => Number(y.key));

  return (
    <section className="section">
      <h2>Presupuesto público</h2>
      <p className="lead">
        Datos del{" "}
        <a href="https://abierto.economiayfinanzas.gob.bo/" rel="noreferrer" target="_blank">
          Presupuesto Abierto
        </a>{" "}
        (MEFP): institución, objeto, gestión y geografía. Correlacionamos con contratos y
        discrepancias entre fuentes.
      </p>

      {apiDown && (
        <p className="error-box">
          No pudimos cargar datos presupuestarios. Levantá el stack con{" "}
          <code>docker compose up -d</code> y ejecutá{" "}
          <code>python -m scripts.cli gasto seed --profile history</code>.
        </p>
      )}

      {totals && (
        <div className="grid-2" style={{ marginBottom: "1.5rem" }}>
          <article className="panel">
            <h3>Líneas presupuestarias</h3>
            <p className="stat">{totals.lines.toLocaleString("es-BO")}</p>
            <p className="hint">Fuente: {totals.source_id}</p>
          </article>
          <article className="panel">
            <h3>Presupuesto vigente</h3>
            <p className="stat-sm">{formatMoney(totals.current_total)}</p>
            {year ? <p className="hint">Gestión {year}</p> : null}
          </article>
          <article className="panel">
            <h3>Ejecutado / pagado</h3>
            <p className="stat-sm">{formatMoney(totals.payment_total || totals.executed_total)}</p>
            <p className="hint">Ratio ejecución: {pct(totals.execution_ratio_pct)}</p>
          </article>
          {cross && (
            <article className="panel">
              <h3>Cruce con contratos</h3>
              <p className="stat">{cross.discrepancies_budget_vs_contracts}</p>
              <p className="hint">
                discrepancias presupuesto vs contratos ·{" "}
                <Link href="/discrepancias">Ver detalle</Link>
              </p>
            </article>
          )}
        </div>
      )}

      <form className="search-bar" action="/presupuesto" method="get">
        <label>
          Gestión{" "}
          <select name="year" defaultValue={year || ""}>
            <option value="">Todas</option>
            {years.map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
        </label>
        <label>
          Agrupar por{" "}
          <select name="group" defaultValue={group}>
            <option value="department">Departamento</option>
            <option value="entity">Institución</option>
            <option value="year">Año</option>
          </select>
        </label>
        <button type="submit" className="btn btn-primary">
          Filtrar
        </button>
      </form>

      <div className="table-wrap" style={{ marginTop: "1.25rem" }}>
        <table>
          <thead>
            <tr>
              <th>
                {group === "entity"
                  ? "Institución"
                  : group === "year"
                    ? "Gestión"
                    : "Departamento"}
              </th>
              <th>Líneas</th>
              <th>Vigente</th>
              <th>Ejecutado</th>
              <th>Entidades</th>
              <th>Ejecución</th>
            </tr>
          </thead>
          <tbody>
            {activeGroup.map((row) => (
              <tr key={row.key}>
                <td>
                  {row.href ? (
                    <Link href={row.href}>{row.label}</Link>
                  ) : (
                    row.label
                  )}
                </td>
                <td>{row.lines.toLocaleString("es-BO")}</td>
                <td>{formatMoney(row.current_total)}</td>
                <td>{formatMoney(row.executed_total)}</td>
                <td>{row.entity_count || "—"}</td>
                <td>{pct(row.execution_ratio_pct)}</td>
              </tr>
            ))}
            {activeGroup.length === 0 && (
              <tr>
                <td colSpan={6}>Sin datos para este filtro.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <p style={{ marginTop: "1.5rem", color: "var(--muted)" }}>
        Actualizar datos oficiales:{" "}
        <code>python -m scripts.cli gasto fetch-presupuesto</code> (URLs en{" "}
        <code>PRESUPUESTO_ABIERTO_DOWNLOAD_URLS</code>) ·{" "}
        <Link href="/historico">Serie histórica</Link> ·{" "}
        <Link href="/metodologia">Metodología</Link>
      </p>
    </section>
  );
}
