import Link from "next/link";
import { apiGet, formatMoney } from "@/lib/api";
import { Pager } from "@/app/components/Pager";

type Disc = {
  id: number;
  concept: string;
  entity_id?: number;
  amount_a?: string;
  amount_b?: string;
  source_a: string;
  source_b: string;
  ref_a?: string;
  ref_b?: string;
  delta_pct?: number;
};

type CrossSource = {
  contracts_with_cuce: number;
  cuces_multi_source: number;
  discrepancies_total: number;
  discrepancies_cuce: number;
  discrepancies_budget_vs_contracts: number;
  sources_in_contracts: string[];
};

function contractHref(ref?: string) {
  if (!ref) return null;
  if (/^\d+$/.test(ref)) return `/contrato/${ref}`;
  return `/explorar?q=${encodeURIComponent(ref)}`;
}

export default async function DiscrepanciasPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string }>;
}) {
  const sp = await searchParams;
  const page = Math.max(1, Number(sp.page) || 1);
  const pageSize = 50;

  const [rowsR, summaryR] = await Promise.allSettled([
    apiGet<Disc[]>(`/v1/discrepancies?limit=${pageSize}&offset=${(page - 1) * pageSize}`),
    apiGet<CrossSource>("/v1/cross-source/summary"),
  ]);
  const rows = rowsR.status === "fulfilled" ? rowsR.value : null;
  const summary = summaryR.status === "fulfilled" ? summaryR.value : null;

  return (
    <section className="section">
      <h2>Discrepancias</h2>
      <p className="lead">
        Cuando dos fuentes reportan montos distintos para el mismo concepto, conservamos
        ambas cifras y mostramos la diferencia.
      </p>

      {summary && (
        <div className="grid-2" style={{ marginBottom: "1.5rem" }}>
          <article className="panel">
            <h3>Contratos con CUCE</h3>
            <p className="stat">{summary.contracts_with_cuce.toLocaleString("es-BO")}</p>
            <p className="hint">
              {summary.cuces_multi_source.toLocaleString("es-BO")} reportados por más de una fuente
            </p>
          </article>
          <article className="panel">
            <h3>Discrepancias totales</h3>
            <p className="stat">{summary.discrepancies_total.toLocaleString("es-BO")}</p>
            <p className="hint">
              {summary.discrepancies_cuce} por contrato ·{" "}
              {summary.discrepancies_budget_vs_contracts} presupuesto vs contratos
            </p>
          </article>
          <article className="panel">
            <h3>Fuentes contrastadas</h3>
            <p className="stat-sm">{summary.sources_in_contracts.length}</p>
            <p className="hint">{summary.sources_in_contracts.join(" · ")}</p>
          </article>
        </div>
      )}

      {rows === null ? (
        <p className="error-box">No pudimos cargar las discrepancias.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Concepto</th>
                <th>Fuente A</th>
                <th>Monto A</th>
                <th>Fuente B</th>
                <th>Monto B</th>
                <th>Δ%</th>
                <th>Refs</th>
                <th>Entidad</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((d) => {
                const ha = contractHref(d.ref_a);
                const hb = contractHref(d.ref_b);
                return (
                  <tr key={d.id} id={`disc-${d.id}`}>
                    <td>{d.concept}</td>
                    <td>{d.source_a}</td>
                    <td>{formatMoney(d.amount_a)}</td>
                    <td>{d.source_b}</td>
                    <td>{formatMoney(d.amount_b)}</td>
                    <td>{d.delta_pct != null ? `${d.delta_pct.toFixed(1)}%` : "—"}</td>
                    <td>
                      {ha ? <Link href={ha}>{d.ref_a}</Link> : d.ref_a || "—"}
                      {" / "}
                      {hb ? <Link href={hb}>{d.ref_b}</Link> : d.ref_b || "—"}
                    </td>
                    <td>
                      {d.entity_id ? (
                        <Link href={`/entidad/${d.entity_id}`}>#{d.entity_id}</Link>
                      ) : (
                        "—"
                      )}
                    </td>
                  </tr>
                );
              })}
              {rows.length === 0 && (
                <tr>
                  <td colSpan={8}>Sin discrepancias registradas entre fuentes.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
      {rows !== null && (
        <Pager
          pathname="/discrepancias"
          params={{}}
          page={page}
          pageSize={pageSize}
          count={rows.length}
        />
      )}
    </section>
  );
}
