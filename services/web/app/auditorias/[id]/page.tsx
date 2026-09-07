import Link from "next/link";
import { apiGet, formatMoney } from "@/lib/api";
import { severityLabel } from "@/lib/labels";

type Finding = {
  id: number;
  title: string;
  description?: string;
  severity?: string;
  entity_id?: number;
  contract_id?: number;
  amount?: string;
};

type Audit = {
  id: number;
  entity_id?: number;
  title: string;
  year?: number;
  url: string;
  findings_summary?: string;
  source_id: string;
};

export default async function AuditoriaDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  let audit: Audit | null = null;
  let findings: Finding[] = [];
  try {
    audit = await apiGet<Audit>(`/v1/audits/${id}`);
  } catch {
    audit = null;
  }
  if (audit) {
    try {
      findings = await apiGet<Finding[]>(`/v1/audits/${id}/findings`);
    } catch {
      findings = [];
    }
  }

  if (!audit) {
    return (
      <section className="section">
        <h2>Auditoría no encontrada</h2>
        <p className="empty">La auditoría #{id} no existe o la API no está disponible.</p>
        <p>
          <Link href="/auditorias">← Volver a auditorías</Link>
        </p>
      </section>
    );
  }

  return (
    <section className="section">
      <p className="lead">
        <Link href="/auditorias">Auditorías</Link> / #{audit.id}
      </p>
      <h2>{audit.title}</h2>
      <p className="lead">
        Año {audit.year ?? "—"} · Fuente {audit.source_id}
        {audit.entity_id ? (
          <>
            {" · "}
            <Link href={`/entidad/${audit.entity_id}`}>Ver entidad</Link>
          </>
        ) : null}
      </p>
      <p>
        <a className="btn btn-ghost" href={audit.url} target="_blank" rel="noreferrer">
          Documento origen ↗
        </a>
      </p>

      <h3>Hallazgos</h3>
      {findings.length === 0 ? (
        <p className="empty">Sin hallazgos estructurados vinculados todavía.</p>
      ) : (
        <ul className="provenance-list">
          {findings.map((f) => (
            <li key={f.id}>
              <span>
                {f.severity ? (
                  <span className={`badge badge-${f.severity}`}>{severityLabel(f.severity)}</span>
                ) : null}{" "}
                {f.title}
                {f.amount ? ` · ${formatMoney(f.amount)}` : ""}
                {f.description ? (
                  <p style={{ color: "var(--muted)", margin: "0.25rem 0 0" }}>{f.description}</p>
                ) : null}
              </span>
              {f.contract_id ? <Link href={`/contrato/${f.contract_id}`}>Contrato</Link> : <span />}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
