import Link from "next/link";
import { apiGet, formatDate, formatMoney } from "@/lib/api";
import { attributionLabel, cycleLabel } from "@/lib/labels";

type Territory = {
  id: number;
  name: string;
  slug: string;
  expenditures?: number;
  amount_direct?: string;
  amount_probable?: string;
};

type Expenditure = {
  id: number;
  code: string;
  title: string;
  attribution: string;
  cycle: string;
  amount_attributed?: string;
  quality_grade: string;
};

type Satellite = {
  sample: {
    id: number;
    acq_date?: string;
    municipality?: string;
    latitude?: string;
    longitude?: string;
    confidence?: string;
  }[];
};

type DeptLedger = {
  disclaimer: string;
  expenditures_count: number;
  amount_direct_verifiable: string;
  amount_probable: string;
};

export default async function DepartamentoIncendiosPage({
  params,
  searchParams,
}: {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ year?: string }>;
}) {
  const { slug } = await params;
  const sp = await searchParams;
  const year = Number(sp.year || "2024") || 2024;

  const [ledgerR, expendituresR, munisR, satelliteR, deptsR] = await Promise.allSettled([
    apiGet<DeptLedger>(`/v1/fire/ledger?year=${year}&department=${encodeURIComponent(slug)}`),
    apiGet<Expenditure[]>(
      `/v1/fire/expenditures?year=${year}&territory=${encodeURIComponent(slug)}&limit=80`
    ),
    apiGet<Territory[]>(
      `/v1/fire/territories?level=municipio&parent_slug=${encodeURIComponent(slug)}&year=${year}`
    ),
    apiGet<Satellite>(`/v1/fire/satellite?year=${year}`),
    apiGet<Territory[]>(`/v1/fire/territories?level=departamento`),
  ]);
  const ledger = ledgerR.status === "fulfilled" ? ledgerR.value : null;
  const expenditures = expendituresR.status === "fulfilled" ? expendituresR.value : [];
  const munis = munisR.status === "fulfilled" ? munisR.value : [];
  const satellite = satelliteR.status === "fulfilled" ? satelliteR.value : null;
  const depts = deptsR.status === "fulfilled" ? deptsR.value : [];

  const apiName = depts.find((d) => d.slug === slug)?.name;
  const title =
    apiName ||
    slug
      .split("-")
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(" ");

  const muniHotspots =
    satellite?.sample.filter(
      (s) =>
        s.municipality &&
        munis.some((m) => m.name.toLowerCase() === s.municipality!.toLowerCase())
    ) || [];

  return (
    <section className="section">
      <p className="lead">
        <Link href={`/incendios?year=${year}`}>Incendios</Link>
        {" · "}
        <Link href={`/incendios/mapa?year=${year}`}>Mapa</Link>
        {" / "}
        {title}
      </p>
      <h2>
        {title} — {year}
      </h2>
      <p className="lead">
        Gasto cuyo territorio beneficiado es este departamento (incluye sus municipios).
        La entidad que paga puede ser nacional o departamental. {ledger?.disclaimer}
      </p>

      {ledger && (
        <div className="grid-2" style={{ marginBottom: "1.5rem" }}>
          <article className="panel">
            <h3>Directo verificable</h3>
            <p className="stat">{formatMoney(ledger.amount_direct_verifiable)}</p>
          </article>
          <article className="panel">
            <h3>Probable</h3>
            <p className="stat">{formatMoney(ledger.amount_probable)}</p>
          </article>
          <article className="panel">
            <h3>Expedientes</h3>
            <p className="stat">{ledger.expenditures_count}</p>
          </article>
          <article className="panel">
            <h3>Datos</h3>
            <p>
              <a
                href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010"}/v1/fire/export.csv?year=${year}&territory=${encodeURIComponent(slug)}`}
              >
                Descargar CSV del departamento
              </a>
            </p>
          </article>
        </div>
      )}

      {munis.length > 0 && (
        <>
          <h3>Municipios</h3>
          <div className="table-wrap" style={{ marginBottom: "1.5rem" }}>
            <table>
              <thead>
                <tr>
                  <th>Municipio</th>
                  <th>Expedientes</th>
                  <th>Directo</th>
                  <th>Probable</th>
                </tr>
              </thead>
              <tbody>
                {munis.map((m) => (
                  <tr key={m.slug}>
                    <td>
                      <Link href={`/incendios/municipio/${m.slug}?year=${year}`}>{m.name}</Link>
                    </td>
                    <td>{m.expenditures ?? 0}</td>
                    <td>{formatMoney(m.amount_direct)}</td>
                    <td>{formatMoney(m.amount_probable)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {muniHotspots.length > 0 && (
        <details className="more">
          <summary>Focos satelitales FIRMS en el departamento</summary>
          <div className="more-body">
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Fecha</th>
                    <th>Municipio</th>
                    <th>Lat/Lon</th>
                    <th>Confianza</th>
                  </tr>
                </thead>
                <tbody>
                  {muniHotspots.map((s) => (
                    <tr key={s.id}>
                      <td>{formatDate(s.acq_date)}</td>
                      <td>{s.municipality}</td>
                      <td>
                        {s.latitude}, {s.longitude}
                      </td>
                      <td>{s.confidence || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </details>
      )}

      <h3>Expedientes</h3>
      {expenditures.length === 0 ? (
        <p className="empty">Sin expedientes para este departamento en {year}.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Código</th>
                <th>Título</th>
                <th>Atribución</th>
                <th>Ciclo</th>
                <th>Monto</th>
              </tr>
            </thead>
            <tbody>
              {expenditures.map((e) => (
                <tr key={e.id}>
                  <td>
                    <Link href={`/incendios/expediente/${e.id}`}>{e.code}</Link>
                  </td>
                  <td>{e.title}</td>
                  <td>{attributionLabel(e.attribution)}</td>
                  <td>{cycleLabel(e.cycle)}</td>
                  <td>{formatMoney(e.amount_attributed)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
