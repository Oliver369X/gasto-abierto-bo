import Link from "next/link";
import { apiGet } from "@/lib/api";
import { coverageFlagLabel } from "@/lib/labels";

type Flag = { flag: string; count: number; pct: number };
type Coverage = {
  sample_size: number;
  flags: Flag[];
  gate_pass: boolean;
  thresholds: Record<string, number>;
  known_amount_universe?: number;
  known_amount_flags?: Flag[];
  catalog_note?: string;
};

type Gate = {
  version: string;
  checks: Record<string, boolean>;
  notes: string[];
  pass: boolean;
};

type Conflict = {
  id: number;
  entity_type: string;
  entity_id: number;
  field: string;
  status: string;
  claim_ids: number[];
};

const CHECK_LABELS: Record<string, string> = {
  contracts_min: "Mínimo de contratos",
  entities_min: "Mínimo de entidades",
  alerts_present: "Alertas generadas",
  provenance_complete: "Trazabilidad completa",
  history_years: "Serie histórica multi-año",
};

function checkLabel(k: string): string {
  return CHECK_LABELS[k] ?? k.replace(/[_-]+/g, " ");
}

export default async function CoberturaPage() {
  const [coverageR, gateR, conflictsR] = await Promise.allSettled([
    apiGet<Coverage>("/v1/coverage/sicoes"),
    apiGet<Gate>("/v1/product-gate"),
    apiGet<Conflict[]>("/v1/conflicts?limit=20"),
  ]);
  const coverage = coverageR.status === "fulfilled" ? coverageR.value : null;
  const gate = gateR.status === "fulfilled" ? gateR.value : null;
  const conflicts = conflictsR.status === "fulfilled" ? conflictsR.value : [];

  return (
    <section className="section">
      <h2>Cobertura y calidad de datos</h2>
      <p className="lead">
        {coverage?.catalog_note ||
          "Qué tan completa es la información que publicamos y qué chequeos automáticos pasan."}
      </p>

      {!coverage ? (
        <p className="error-box">No pudimos cargar la cobertura.</p>
      ) : (
        <>
          <h3>Muestra SICOES reciente</h3>
          <p className="lead">
            {coverage.sample_size.toLocaleString("es-BO")} contratos en muestra ·{" "}
            {coverage.gate_pass
              ? "umbral de enriquecimiento cumplido"
              : "umbral de enriquecimiento no cumplido"}
          </p>
          <div className="table-wrap" style={{ marginBottom: "1.5rem" }}>
            <table>
              <thead>
                <tr>
                  <th>Dato</th>
                  <th>Contratos</th>
                  <th>%</th>
                  <th>Umbral</th>
                </tr>
              </thead>
              <tbody>
                {coverage.flags.map((f) => (
                  <tr key={f.flag}>
                    <td>{coverageFlagLabel(f.flag)}</td>
                    <td>{f.count.toLocaleString("es-BO")}</td>
                    <td>{f.pct}%</td>
                    <td>
                      {coverage.thresholds[f.flag] != null
                        ? `${Math.round(coverage.thresholds[f.flag] * 100)}%`
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {(coverage.known_amount_flags || []).length > 0 && (
            <>
              <h3>
                Contratos con monto conocido (
                {(coverage.known_amount_universe ?? 0).toLocaleString("es-BO")})
              </h3>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Dato</th>
                      <th>Contratos</th>
                      <th>%</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(coverage.known_amount_flags || []).map((f) => (
                      <tr key={`k-${f.flag}`}>
                        <td>{coverageFlagLabel(f.flag)}</td>
                        <td>{f.count.toLocaleString("es-BO")}</td>
                        <td>{f.pct}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </>
      )}

      <h3>Conflictos abiertos entre fuentes</h3>
      {conflicts.length === 0 ? (
        <p className="empty">Sin conflictos abiertos.</p>
      ) : (
        <ul className="provenance-list">
          {conflicts.map((c) => (
            <li key={c.id}>
              <span>
                {c.entity_type === "contract" ? "Contrato" : c.entity_type} #{c.entity_id} · campo{" "}
                <code>{c.field}</code>
              </span>
              <Link href={c.entity_type === "contract" ? `/contrato/${c.entity_id}` : "/explorar"}>
                Ver
              </Link>
            </li>
          ))}
        </ul>
      )}

      <h3>Chequeos de producto</h3>
      {!gate ? (
        <p className="error-box">No disponible.</p>
      ) : (
        <>
          <p className={gate.pass ? "notice" : "error-box"}>
            {gate.pass
              ? "Todos los chequeos automáticos pasan."
              : "Hay chequeos que no pasan — estamos trabajando en ellos."}
          </p>
          <ul className="provenance-list">
            {Object.entries(gate.checks).map(([k, v]) => (
              <li key={k}>
                <span>{checkLabel(k)}</span>
                <span className={v ? "status-ok" : "status-error"}>{v ? "Pasa" : "No pasa"}</span>
              </li>
            ))}
          </ul>
          {(gate.notes || []).length > 0 && (
            <ul>
              {gate.notes.map((n) => (
                <li key={n} style={{ color: "var(--muted)" }}>
                  {n}
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </section>
  );
}
