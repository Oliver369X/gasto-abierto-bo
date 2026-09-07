import Link from "next/link";
import { apiGet } from "@/lib/api";
import { severityLabel } from "@/lib/labels";

type Alert = {
  id: number;
  rule_id: string;
  severity: string;
  title: string;
  explanation: string;
  entity_id?: number;
  supplier_id?: number;
  contract_id?: number;
  evidence: Record<string, unknown>;
  source_id: string;
};

export default async function AlertaDetallePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  let a: Alert | null = null;
  try {
    a = await apiGet<Alert>(`/v1/alerts/${id}`);
  } catch {
    a = null;
  }
  if (!a) {
    return (
      <section className="section">
        <h2>Alerta no encontrada</h2>
        <p className="empty">La alerta #{id} no existe o la API no está disponible.</p>
        <p>
          <Link href="/alertas">← Volver a alertas</Link>
        </p>
      </section>
    );
  }

  return (
    <section className="section">
      <p className="lead">
        <Link href="/alertas">Alertas</Link> / #{a.id}
      </p>
      <span className={`badge badge-${a.severity}`}>{severityLabel(a.severity)}</span>
      <h2 style={{ marginTop: "0.75rem" }}>{a.title}</h2>
      <p className="lead">{a.explanation}</p>

      <div className="grid-2">
        <article className="panel">
          <h3>Regla</h3>
          <p>
            <code>{a.rule_id}</code>
          </p>
          <p className="hint">Fuente: {a.source_id}</p>
        </article>
        <article className="panel">
          <h3>Relacionado</h3>
          <p>
            {a.entity_id ? <Link href={`/entidad/${a.entity_id}`}>Entidad</Link> : null}
            {a.supplier_id ? (
              <>
                {a.entity_id ? " · " : ""}
                <Link href={`/proveedor/${a.supplier_id}`}>Proveedor</Link>
              </>
            ) : null}
            {a.contract_id ? (
              <>
                {a.entity_id || a.supplier_id ? " · " : ""}
                <Link href={`/contrato/${a.contract_id}`}>Contrato</Link>
              </>
            ) : null}
            {!a.entity_id && !a.supplier_id && !a.contract_id ? "—" : null}
          </p>
        </article>
      </div>

      <h3>Evidencia</h3>
      <pre className="evidence">{JSON.stringify(a.evidence || {}, null, 2)}</pre>
    </section>
  );
}
