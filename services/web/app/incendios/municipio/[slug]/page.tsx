import Link from "next/link";
import { apiGet, formatMoney } from "@/lib/api";
import { attributionLabel, cycleLabel } from "@/lib/labels";

type Territory = {
  id: number;
  name: string;
  slug: string;
  parent_slug?: string | null;
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
  paying_entity_name?: string;
};

export default async function MunicipioIncendiosPage({
  params,
  searchParams,
}: {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ year?: string }>;
}) {
  const { slug } = await params;
  const sp = await searchParams;
  const year = Number(sp.year || "2024") || 2024;

  const [territoriesR, expendituresR, deptsR] = await Promise.allSettled([
    apiGet<Territory[]>(`/v1/fire/territories?level=municipio&year=${year}`),
    apiGet<Expenditure[]>(
      `/v1/fire/expenditures?year=${year}&territory=${encodeURIComponent(slug)}&limit=50`
    ),
    apiGet<Territory[]>(`/v1/fire/territories?level=departamento`),
  ]);
  const all = territoriesR.status === "fulfilled" ? territoriesR.value : [];
  const expenditures = expendituresR.status === "fulfilled" ? expendituresR.value : [];
  const depts = deptsR.status === "fulfilled" ? deptsR.value : [];

  const terr = all.find((t) => t.slug === slug) || null;
  const parentSlug = terr?.parent_slug || null;
  const parentName = parentSlug ? depts.find((d) => d.slug === parentSlug)?.name : null;

  const title =
    terr?.name ||
    slug
      .split("-")
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(" ");

  return (
    <section className="section">
      <p className="lead">
        <Link href={`/incendios?year=${year}`}>Incendios</Link>
        {parentSlug && (
          <>
            {" · "}
            <Link href={`/incendios/departamento/${parentSlug}?year=${year}`}>
              {parentName || parentSlug}
            </Link>
          </>
        )}
        {" / "}
        {title}
      </p>
      <h2>
        {title} — {year}
      </h2>
      <p className="lead">
        Gasto cuyo territorio beneficiado es este municipio. Quien paga puede ser el
        gobierno nacional, el departamento o el propio municipio.
      </p>

      <div className="grid-2" style={{ marginBottom: "1.5rem" }}>
        <article className="panel">
          <h3>Directo verificable</h3>
          <p className="stat">{formatMoney(terr?.amount_direct)}</p>
        </article>
        <article className="panel">
          <h3>Probable</h3>
          <p className="stat">{formatMoney(terr?.amount_probable)}</p>
        </article>
        <article className="panel">
          <h3>Expedientes</h3>
          <p className="stat">{terr?.expenditures ?? expenditures.length}</p>
        </article>
      </div>

      {expenditures.length === 0 ? (
        <p className="empty">Sin expedientes municipales en {year}.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Código</th>
                <th>Título</th>
                <th>Quién paga</th>
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
                  <td>{e.paying_entity_name || "—"}</td>
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
