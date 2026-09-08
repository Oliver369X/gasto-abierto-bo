import Link from "next/link";
import { apiGet, formatMoney } from "@/lib/api";

type YearAgg = {
  year: number;
  contracts: number;
  contract_amount: string;
  budget_lines: number;
  budget_current_total: string;
  budget_executed_total: string;
};

function executionRatio(current: string, executed: string) {
  const cur = Number(current);
  const exe = Number(executed);
  if (!cur || cur <= 0) return "—";
  return `${((exe / cur) * 100).toFixed(1)}%`;
}

type Compare = {
  year_a: number;
  year_b: number;
  contracts_a: number;
  contracts_b: number;
  contracts_delta_pct?: number;
  amount_a: string;
  amount_b: string;
  amount_delta_pct?: number;
  budget_current_a: string;
  budget_current_b: string;
  budget_delta_pct?: number;
};

function pct(v?: number) {
  if (v === undefined || v === null) return "—";
  return `${v.toFixed(1)}%`;
}

function compareDeltaLabel(v?: number) {
  if (v === undefined || v === null) return "—";
  return pct(v);
}

export default async function HistoricoPage({
  searchParams,
}: {
  searchParams: Promise<{ a?: string; b?: string }>;
}) {
  const sp = await searchParams;
  let years: YearAgg[] = [];
  let apiDown = false;
  try {
    years = await apiGet<YearAgg[]>("/v1/history/years");
  } catch {
    apiDown = true;
  }

  const sorted = [...years].map((y) => y.year).sort((x, y) => y - x);
  const withData = years.filter((y) => y.contracts > 0 || y.budget_lines > 0);
  const dataYears = withData.map((y) => y.year).sort((a, b) => b - a);
  const yearB = Number(sp.b) || dataYears[0] || sorted[0] || 2025;
  const yearA = Number(sp.a) || dataYears[1] || dataYears[0] || yearB - 1;

  let compare: Compare | null = null;
  let compareError = false;
  try {
    compare = await apiGet<Compare>(`/v1/history/compare?year_a=${yearA}&year_b=${yearB}`);
  } catch {
    compare = null;
    compareError = !apiDown;
  }

  return (
    <section className="section">
      <h2>Histórico</h2>
      <p className="lead">
        Serie consolidada por gestión desde Presupuesto Abierto y contratos SICOES/OCP.
        Compará dos años lado a lado. Solo se suman montos efectivamente reportados — la
        ausencia de dato nunca cuenta como Bs 0.
      </p>

      {apiDown && <p className="error-box">No pudimos cargar la serie histórica.</p>}

      {!apiDown && compareError && (
        <p className="error-box">
          No pudimos cargar la comparación {yearA} vs {yearB}. Revisá que existan datos para
          ambas gestiones.
        </p>
      )}

      <form className="search-bar" action="/historico" method="get">
        <label>
          Año A{" "}
          <input type="number" name="a" defaultValue={yearA} min={2016} max={2030} />
        </label>
        <label>
          Año B{" "}
          <input type="number" name="b" defaultValue={yearB} min={2016} max={2030} />
        </label>
        <button type="submit" className="btn btn-primary">
          Comparar
        </button>
      </form>

      {compare && (
        <div className="grid-2" style={{ marginBottom: "1.75rem" }}>
          <article className="panel">
            <h3>Contratos {compare.year_a} vs {compare.year_b}</h3>
            <p>
              {compare.contracts_a} → {compare.contracts_b} · Δ {compareDeltaLabel(compare.contracts_delta_pct)}
            </p>
          </article>
          <article className="panel">
            <h3>Monto contratos</h3>
            <p>
              {formatMoney(compare.amount_a)} → {formatMoney(compare.amount_b)} · Δ{" "}
              {compareDeltaLabel(compare.amount_delta_pct)}
            </p>
          </article>
          <article className="panel">
            <h3>Presupuesto vigente</h3>
            <p>
              {formatMoney(compare.budget_current_a)} → {formatMoney(compare.budget_current_b)} · Δ{" "}
              {compareDeltaLabel(compare.budget_delta_pct)}
            </p>
          </article>
        </div>
      )}

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Año</th>
              <th>Contratos</th>
              <th>Monto contratos</th>
              <th>Líneas presupuesto</th>
              <th>Vigente</th>
              <th>Ejecutado</th>
              <th>Ejecución</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {years.map((y) => (
              <tr key={y.year}>
                <td>{y.year}</td>
                <td>{y.contracts}</td>
                <td>{formatMoney(y.contract_amount)}</td>
                <td>{y.budget_lines}</td>
                <td>{formatMoney(y.budget_current_total)}</td>
                <td>{formatMoney(y.budget_executed_total)}</td>
                <td>{executionRatio(y.budget_current_total, y.budget_executed_total)}</td>
                <td>
                  <Link href={`/presupuesto?year=${y.year}`}>Presupuesto</Link>
                  {" · "}
                  <Link href={`/explorar?year=${y.year}`}>Contratos</Link>
                  {" · "}
                  <Link href={`/historico?a=${y.year - 1}&b=${y.year}`}>YoY</Link>
                </td>
              </tr>
            ))}
            {years.length === 0 && (
              <tr>
                <td colSpan={8}>Sin serie histórica.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
