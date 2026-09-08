import { apiGet, apiPublicUrl, formatDateTime } from "@/lib/api";
import { runStatusLabel } from "@/lib/labels";

type Source = {
  source_id: string;
  last_status?: string;
  last_finished_at?: string;
  records_out?: number;
  license_note: string;
};

type Run = {
  id: number;
  source_id: string;
  status: string;
  records_out: number;
  records_in?: number;
  started_at: string;
  finished_at?: string;
  error_message?: string;
  meta?: { item_errors?: { uri?: string; error?: string }[]; skipped_rows?: number };
};

type Doc = {
  id: number;
  url: string;
  source_id: string;
  minio_key?: string;
  sha256?: string;
  mime?: string;
};

function statusClass(s: string) {
  if (s === "ok") return "status-ok";
  if (s === "partial") return "status-partial";
  if (s === "error") return "status-error";
  return "";
}

export default async function FuentesPage() {
  const [sourcesR, runsR, docsR] = await Promise.allSettled([
    apiGet<Source[]>("/v1/sources"),
    apiGet<Run[]>("/v1/ingestion-runs?limit=20"),
    apiGet<Doc[]>("/v1/documents?limit=20"),
  ]);
  const sources = sourcesR.status === "fulfilled" ? sourcesR.value : null;
  const runs = runsR.status === "fulfilled" ? runsR.value : null;
  const docs = docsR.status === "fulfilled" ? docsR.value : null;

  return (
    <section className="section">
      <h2>Fuentes e ingesta</h2>
      <p className="lead">
        De dónde sale cada dato, cuándo se actualizó y acceso al documento original.
      </p>

      <h3>Catálogo de fuentes</h3>
      {!sources ? (
        <p className="error-box">No pudimos cargar el catálogo.</p>
      ) : (
        <div className="table-wrap" style={{ marginBottom: "1.5rem" }}>
          <table>
            <thead>
              <tr>
                <th>Fuente</th>
                <th>Última corrida</th>
                <th>Registros</th>
                <th>Fecha</th>
              </tr>
            </thead>
            <tbody>
              {sources.map((s) => (
                <tr key={s.source_id}>
                  <td>
                    <code>{s.source_id}</code>
                  </td>
                  <td className={statusClass(s.last_status || "")}>
                    {runStatusLabel(s.last_status)}
                  </td>
                  <td>{s.records_out ?? "—"}</td>
                  <td>{formatDateTime(s.last_finished_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <h3>Últimas corridas</h3>
      {!runs ? (
        <p className="error-box">No pudimos cargar las corridas.</p>
      ) : (
        <div className="table-wrap" style={{ marginBottom: "1.5rem" }}>
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Fuente</th>
                <th>Estado</th>
                <th>Leídos / cargados</th>
                <th>Errores</th>
                <th>Inicio</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((r) => {
                const errs = r.meta?.item_errors?.length || 0;
                return (
                  <tr key={r.id}>
                    <td>{r.id}</td>
                    <td>{r.source_id}</td>
                    <td className={statusClass(r.status)}>{runStatusLabel(r.status)}</td>
                    <td>
                      {r.records_in ?? "—"} / {r.records_out}
                    </td>
                    <td>{errs > 0 ? `${errs} ítem(s)` : r.error_message || "—"}</td>
                    <td>{formatDateTime(r.started_at)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <h3>Documentos originales</h3>
      {!docs ? (
        <p className="error-box">No pudimos cargar los documentos.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Fuente</th>
                <th>URL origen</th>
                <th>SHA256</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {docs.map((d) => (
                <tr key={d.id}>
                  <td>{d.id}</td>
                  <td>{d.source_id}</td>
                  <td style={{ maxWidth: 260, overflow: "hidden", textOverflow: "ellipsis" }}>
                    {d.url ? (
                      <a href={d.url} rel="noreferrer" target="_blank">
                        {d.url}
                      </a>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td>
                    <code>{d.sha256 ? d.sha256.slice(0, 12) : "—"}</code>
                  </td>
                  <td>
                    <a className="btn btn-ghost" href={apiPublicUrl(`/v1/documents/${d.id}/download`)}>
                      Descargar
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
