import Link from "next/link";
import { apiGet, formatDate, formatMoney } from "@/lib/api";
import FireCoverageMap from "./FireCoverageMap";

type Territory = {
  id: number;
  name: string;
  slug: string;
  level: string;
  expenditures?: number;
  amount_direct?: string;
  amount_probable?: string;
  firms_detections?: number;
};

type Satellite = {
  year: number;
  total_detections: number;
  disclaimer: string;
  by_department: { department: string; count: number }[];
  sample: {
    id: number;
    acq_date?: string;
    latitude?: string;
    longitude?: string;
    department?: string;
    municipality?: string;
    confidence?: string;
  }[];
};

export default async function MapaIncendiosPage({
  searchParams,
}: {
  searchParams: Promise<{ year?: string }>;
}) {
  const sp = await searchParams;
  const year = Number(sp.year || "2024") || 2024;

  const [deptsR, satelliteR] = await Promise.allSettled([
    apiGet<Territory[]>(`/v1/fire/territories?level=departamento&year=${year}`),
    apiGet<Satellite>(`/v1/fire/satellite?year=${year}`),
  ]);
  const depts = deptsR.status === "fulfilled" ? deptsR.value : [];
  const satellite = satelliteR.status === "fulfilled" ? satelliteR.value : null;

  return (
    <section className="section">
      <p className="lead">
        <Link href={`/incendios?year=${year}`}>Incendios</Link> / Mapa
      </p>
      <h2>Mapa territorial — {year}</h2>
      <p className="lead">
        Cobertura del ledger por departamento: dónde hay gasto verificable y dónde
        todavía no hay datos públicos suficientes.
      </p>

      <div className="chips">
        {[2022, 2023, 2024, 2025].map((y) => (
          <Link
            key={y}
            className={`chip ${y === year ? "active" : ""}`}
            href={`/incendios/mapa?year=${y}`}
          >
            {y}
          </Link>
        ))}
      </div>

      <FireCoverageMap year={year} />

      <h3>Por departamento</h3>
      {depts.length === 0 ? (
        <p className="empty">Sin datos territoriales para {year}.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Departamento</th>
                <th>Expedientes</th>
                <th>Directo</th>
                <th>Probable</th>
                <th>Focos FIRMS</th>
              </tr>
            </thead>
            <tbody>
              {depts
                .slice()
                .sort((a, b) => Number(b.amount_direct || 0) - Number(a.amount_direct || 0))
                .map((d) => (
                  <tr key={d.slug}>
                    <td>
                      <Link href={`/incendios/departamento/${d.slug}?year=${year}`}>{d.name}</Link>
                    </td>
                    <td>{d.expenditures ?? 0}</td>
                    <td>{formatMoney(d.amount_direct)}</td>
                    <td>{formatMoney(d.amount_probable)}</td>
                    <td>{d.firms_detections ?? 0}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      )}

      {satellite && satellite.sample.length > 0 && (
        <details className="more" style={{ marginTop: "1.5rem" }}>
          <summary>Focos satelitales FIRMS — muestra ({satellite.total_detections})</summary>
          <div className="more-body">
            <p className="lead">{satellite.disclaimer}</p>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Fecha</th>
                    <th>Departamento</th>
                    <th>Municipio</th>
                    <th>Lat</th>
                    <th>Lon</th>
                    <th>Confianza</th>
                  </tr>
                </thead>
                <tbody>
                  {satellite.sample.map((s) => (
                    <tr key={s.id}>
                      <td>{formatDate(s.acq_date)}</td>
                      <td>{s.department || "—"}</td>
                      <td>{s.municipality || "—"}</td>
                      <td>{s.latitude ?? "—"}</td>
                      <td>{s.longitude ?? "—"}</td>
                      <td>{s.confidence || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </details>
      )}
    </section>
  );
}
