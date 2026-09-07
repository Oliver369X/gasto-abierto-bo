import Link from "next/link";
import { apiGet } from "@/lib/api";
import { Pager } from "@/app/components/Pager";

type Audit = {
  id: number;
  entity_id?: number;
  title: string;
  year?: number;
  url: string;
  findings_summary?: string;
  source_id: string;
};

export default async function AuditoriasPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string }>;
}) {
  const sp = await searchParams;
  const page = Math.max(1, Number(sp.page) || 1);
  const pageSize = 50;
  let audits: Audit[] = [];
  let apiDown = false;
  try {
    audits = await apiGet<Audit[]>(
      `/v1/audits?limit=${pageSize}&offset=${(page - 1) * pageSize}`
    );
  } catch {
    apiDown = true;
  }

  return (
    <section className="section">
      <h2>Auditorías</h2>
      <p className="lead">
        Metadatos públicos de informes de la Contraloría y otras fuentes. Sin datos
        reservados.
      </p>
      {apiDown ? (
        <p className="error-box">No pudimos cargar las auditorías.</p>
      ) : audits.length === 0 ? (
        <p className="empty">Todavía no hay auditorías cargadas.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Título</th>
                <th>Año</th>
                <th>Fuente</th>
              </tr>
            </thead>
            <tbody>
              {audits.map((a) => (
                <tr key={a.id}>
                  <td>
                    <Link href={`/auditorias/${a.id}`}>{a.title}</Link>
                    {a.findings_summary ? (
                      <p style={{ color: "var(--muted)", margin: "0.25rem 0 0" }}>
                        {a.findings_summary.slice(0, 160)}
                      </p>
                    ) : null}
                  </td>
                  <td>{a.year ?? "—"}</td>
                  <td>{a.source_id}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {!apiDown && (
        <Pager pathname="/auditorias" params={{}} page={page} pageSize={pageSize} count={audits.length} />
      )}
    </section>
  );
}
