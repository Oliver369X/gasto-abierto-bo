import Link from "next/link";
import { apiGet, apiPublicUrl, formatDate, formatMoney, qualityBadgeLabel } from "@/lib/api";

type DocRef = { minio_key?: string; sha256?: string; url?: string };

type Contract = {
  id: number;
  cuce?: string;
  entity_id: number;
  supplier_id?: number;
  object_description?: string;
  amount?: string;
  modality?: string;
  category?: string;
  status?: string;
  contract_date?: string;
  source_id: string;
  documents: DocRef[];
  ingestion_run_id?: number;
  source_quality?: string;
  is_synthetic?: boolean;
  data_origin?: string;
  source_note?: string;
  completeness_level?: number;
  evidence_status?: string;
  confidence_score?: string;
  reference_price?: string;
};

type DocumentRow = {
  id: number;
  url: string;
  sha256?: string;
  minio_key?: string;
  ingestion_run_id?: number;
};

type Claim = {
  id: number;
  field: string;
  value_text?: string;
  value_num?: string;
  confidence?: string;
  source_id: string;
};

type Evidence = {
  id: number;
  claim_id: number;
  quote?: string;
  page?: number;
  url?: string;
  sha256?: string;
};

export default async function ContratoPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  let c: Contract | null = null;
  try {
    c = await apiGet<Contract>(`/v1/contracts/${id}`);
  } catch {
    c = null;
  }
  if (!c) {
    return (
      <section className="section">
        <h2>Contrato no encontrado</h2>
        <p className="empty">El contrato #{id} no existe o la API no está disponible.</p>
        <p>
          <Link href="/explorar">← Volver a explorar</Link>
        </p>
      </section>
    );
  }

  const [docsR, claimsR, evidenceR] = await Promise.allSettled([
    c.ingestion_run_id
      ? apiGet<DocumentRow[]>(`/v1/documents?limit=50`)
      : Promise.resolve<DocumentRow[]>([]),
    apiGet<Claim[]>(`/v1/contracts/${id}/claims`),
    apiGet<Evidence[]>(`/v1/contracts/${id}/evidence`),
  ]);
  const allDocs = docsR.status === "fulfilled" ? docsR.value : [];
  const linkedDocs = allDocs.filter((d) => d.ingestion_run_id === c.ingestion_run_id);
  const claims = claimsR.status === "fulfilled" ? claimsR.value : [];
  const evidence = evidenceR.status === "fulfilled" ? evidenceR.value : [];

  return (
    <section className="section">
      <h2>{c.cuce || `Contrato #${c.id}`}</h2>
      <p className="lead">{c.object_description || "Sin objeto descripto"}</p>
      <p>
        {c.category ? <span className="badge badge-cat">{c.category}</span> : null}{" "}
        <span className="badge badge-cat">
          {qualityBadgeLabel(c.source_quality, c.is_synthetic)}
        </span>{" "}
        {c.completeness_level != null ? (
          <span className="badge badge-cat">Completitud {c.completeness_level}/5</span>
        ) : null}
      </p>

      <div className="grid-2" style={{ marginTop: "1.25rem" }}>
        <article className="panel">
          <h3>Monto adjudicado</h3>
          <p className="stat-sm">{formatMoney(c.amount)}</p>
          {c.reference_price ? (
            <p className="hint">Precio referencial: {formatMoney(c.reference_price)}</p>
          ) : null}
        </article>
        <article className="panel">
          <h3>Modalidad</h3>
          <p>{c.modality || "—"}</p>
        </article>
        <article className="panel">
          <h3>Estado y fecha</h3>
          <p>
            {c.status || "—"} · {formatDate(c.contract_date)}
          </p>
        </article>
        <article className="panel">
          <h3>Trazabilidad</h3>
          <p>
            Fuente <code>{c.source_id}</code>
            {c.data_origin ? <> · origen {c.data_origin}</> : null}
            {c.source_note ? <> · {c.source_note}</> : null}
            {c.ingestion_run_id ? (
              <>
                {" · "}
                <Link href="/fuentes">corrida #{c.ingestion_run_id}</Link>
              </>
            ) : null}
          </p>
        </article>
      </div>

      <h3>Evidencia</h3>
      {claims.length === 0 && evidence.length === 0 ? (
        <p className="empty">Sin evidencia vinculada todavía.</p>
      ) : (
        <ul className="provenance-list">
          {claims.map((cl) => {
            const ev = evidence.find((e) => e.claim_id === cl.id);
            return (
              <li key={cl.id}>
                <span>
                  <strong>{cl.field}</strong>: {cl.value_text || cl.value_num || "—"}
                  {cl.confidence ? ` · confianza ${cl.confidence}` : ""}
                  {ev?.quote ? ` · “${ev.quote}”` : ""}
                  {ev?.page != null ? ` · p.${ev.page}` : ""}
                  {ev?.url ? (
                    <>
                      {" · "}
                      <a href={ev.url} rel="noreferrer" target="_blank">
                        fuente
                      </a>
                    </>
                  ) : null}
                </span>
                <span style={{ color: "var(--muted)", fontSize: "0.85rem" }}>{cl.source_id}</span>
              </li>
            );
          })}
        </ul>
      )}

      <h3>Documentos originales</h3>
      {linkedDocs.length === 0 && (c.documents || []).length === 0 ? (
        <p className="empty">Sin documentos asociados a esta corrida de ingesta.</p>
      ) : (
        <ul className="provenance-list">
          {linkedDocs.map((d) => (
            <li key={d.id}>
              <span>
                <code>{d.sha256 ? d.sha256.slice(0, 16) : "sin sha"}</code>
                {d.url ? (
                  <>
                    {" · "}
                    <a href={d.url} rel="noreferrer" target="_blank">
                      origen
                    </a>
                  </>
                ) : null}
              </span>
              <a className="btn btn-ghost" href={apiPublicUrl(`/v1/documents/${d.id}/download`)}>
                Descargar
              </a>
            </li>
          ))}
          {linkedDocs.length === 0 &&
            (c.documents || []).map((d, i) => (
              <li key={i}>
                <span>
                  <code>{d.sha256 ? String(d.sha256).slice(0, 16) : d.minio_key || "doc"}</code>
                </span>
                <Link href="/fuentes">Ver en Fuentes</Link>
              </li>
            ))}
        </ul>
      )}

      <p style={{ marginTop: "1.5rem" }}>
        <Link href={`/entidad/${c.entity_id}`}>Ver entidad</Link>
        {c.supplier_id ? (
          <>
            {" · "}
            <Link href={`/proveedor/${c.supplier_id}`}>Ver proveedor</Link>
          </>
        ) : null}
      </p>
    </section>
  );
}
