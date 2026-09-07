import Link from "next/link";
import { apiBase, apiGet, formatMoney } from "@/lib/api";
import {
  attributionLabel,
  cycleLabel,
  linkStrengthLabel,
  recoveryStatusLabel,
} from "@/lib/labels";

type Expenditure = {
  id: number;
  code: string;
  year: number;
  title: string;
  object_description?: string;
  attribution: string;
  confidence_score: string;
  classification_method: string;
  cycle: string;
  amount_contract?: string;
  amount_attributed?: string;
  quality_grade: string;
  cuce?: string;
  paying_entity_name?: string;
  supplier_name?: string;
  beneficiary_territory_name?: string;
  beneficiary_territory_slug?: string;
  beneficiary_territory_level?: string;
  contract_id?: number;
  document_id?: number;
  evidence: Record<string, unknown>;
  source_id: string;
  ledger_bucket?: string;
  is_synthetic?: boolean;
  recovery_status?: string;
  link_strength?: string;
};

type Chain = {
  code: string;
  link_strength?: string;
  disclaimer: string;
  chain: {
    strength: string;
    to_type: string;
    to_id: number;
    label?: string;
    code?: string;
    metric_key?: string;
    note?: string;
    evidence?: Record<string, unknown>;
  }[];
};

export default async function ExpedientePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  let exp: Expenditure | null = null;
  try {
    exp = await apiGet<Expenditure>(`/v1/fire/expenditures/${id}`);
  } catch {
    exp = null;
  }

  if (!exp) {
    return (
      <section className="section">
        <p className="lead">
          <Link href="/incendios">← Incendios</Link>
        </p>
        <h2>Expediente no encontrado</h2>
        <p className="empty">El expediente #{id} no existe o la API no está disponible.</p>
      </section>
    );
  }

  let chain: Chain | null = null;
  try {
    chain = await apiGet<Chain>(`/v1/fire/expenditures/${id}/chain`);
  } catch {
    chain = null;
  }

  const ev = exp.evidence || {};
  const api = apiBase();
  const territoryHref = exp.beneficiary_territory_slug
    ? exp.beneficiary_territory_level === "municipio"
      ? `/incendios/municipio/${exp.beneficiary_territory_slug}?year=${exp.year}`
      : `/incendios/departamento/${exp.beneficiary_territory_slug}?year=${exp.year}`
    : null;

  return (
    <section className="section">
      <p className="lead">
        <Link href={`/incendios?year=${exp.year}`}>Incendios {exp.year}</Link>
        {territoryHref && (
          <>
            {" · "}
            <Link href={territoryHref}>{exp.beneficiary_territory_name}</Link>
          </>
        )}
        {" / "}
        {exp.code}
      </p>
      <h2>{exp.code}</h2>
      <p className="lead">{exp.title}</p>
      {exp.is_synthetic && (
        <p className="notice">Fila ilustrativa / sintética — excluida de los totales públicos.</p>
      )}

      <div className="grid-2" style={{ marginTop: "1.25rem" }}>
        <article className="panel">
          <h3>Monto atribuido</h3>
          <p className="stat">{formatMoney(exp.amount_attributed)}</p>
          <p className="hint">Contrato: {formatMoney(exp.amount_contract)}</p>
        </article>
        <article className="panel">
          <h3>Clasificación</h3>
          <p>
            {attributionLabel(exp.attribution)} · {cycleLabel(exp.cycle)}
          </p>
          <p className="hint">
            Calidad grado {exp.quality_grade} · confianza {exp.confidence_score}
          </p>
          <p className="hint">Recuperación: {recoveryStatusLabel(exp.recovery_status)}</p>
        </article>
        <article className="panel">
          <h3>Quién paga ≠ dónde se usa</h3>
          <p>Paga: {exp.paying_entity_name || "—"}</p>
          <p>
            Territorio:{" "}
            {territoryHref ? (
              <Link href={territoryHref}>{exp.beneficiary_territory_name}</Link>
            ) : (
              exp.beneficiary_territory_name || "—"
            )}
          </p>
          <p className="hint">Proveedor: {exp.supplier_name || "No publicado"}</p>
        </article>
        <article className="panel">
          <h3>Identificadores</h3>
          <p>CUCE: {exp.cuce || "No recuperable públicamente"}</p>
          <p>
            Contrato:{" "}
            {exp.contract_id ? (
              <Link href={`/contrato/${exp.contract_id}`}>#{exp.contract_id}</Link>
            ) : (
              "No publicado"
            )}
          </p>
          <p className="hint">
            Fuente: {exp.source_id}
            {exp.document_id ? (
              <>
                {" · "}
                <a href={`${api}/v1/documents/${exp.document_id}/download`}>documento original</a>
              </>
            ) : null}
          </p>
        </article>
      </div>

      {exp.object_description && (
        <>
          <h3>Objeto</h3>
          <p>{exp.object_description}</p>
        </>
      )}

      {chain && (
        <>
          <h3>Cadena dinero ↔ operación ↔ evento</h3>
          <p className="lead">{chain.disclaimer}</p>
          <p>
            Fuerza del vínculo:{" "}
            <strong>{linkStrengthLabel(chain.link_strength || exp.link_strength)}</strong>
          </p>
          {chain.chain.length === 0 ? (
            <p className="empty">
              Sin vínculos con evidencia compartida — no inventamos enlaces por año.
            </p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Fuerza</th>
                    <th>Tipo</th>
                    <th>Destino</th>
                    <th>Base</th>
                  </tr>
                </thead>
                <tbody>
                  {chain.chain.map((c) => (
                    <tr key={`${c.to_type}-${c.to_id}`}>
                      <td>{linkStrengthLabel(c.strength)}</td>
                      <td>{c.to_type}</td>
                      <td>{c.label || c.code || `#${c.to_id}`}</td>
                      <td>{((c.evidence?.basis as string[]) || []).join(", ") || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      <h3>Evidencia</h3>
      <pre className="evidence">{JSON.stringify(ev, null, 2)}</pre>
    </section>
  );
}
