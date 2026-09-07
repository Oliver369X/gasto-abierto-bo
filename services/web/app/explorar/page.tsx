import Link from "next/link";
import { apiGet, formatMoney, qualityBadgeLabel } from "@/lib/api";
import { searchTypeLabel } from "@/lib/labels";
import { Pager } from "@/app/components/Pager";

type Contract = {
  id: number;
  cuce?: string;
  entity_id: number;
  supplier_id?: number;
  object_description?: string;
  amount?: string;
  modality?: string;
  category?: string;
  source_id: string;
  source_quality?: string;
  is_synthetic?: boolean;
};

type Entity = { id: number; name: string; level: string };
type Category = { id: string; label: string; contracts: number };
type SearchHit = { type: string; id: number; title: string; subtitle?: string; href: string };

export default async function ExplorarPage({
  searchParams,
}: {
  searchParams: Promise<{
    q?: string;
    year?: string;
    category?: string;
    modality?: string;
    page?: string;
  }>;
}) {
  const sp = await searchParams;
  const q = sp.q?.trim() || "";
  const year = sp.year?.trim() || "";
  const category = sp.category?.trim() || "";
  const modality = sp.modality?.trim() || "";
  const page = Math.max(1, Number(sp.page) || 1);
  const pageSize = 40;

  const params = new URLSearchParams({
    limit: String(pageSize),
    offset: String((page - 1) * pageSize),
  });
  if (q) params.set("q", q);
  if (year) params.set("year", year);
  if (category) params.set("category", category);
  if (modality) params.set("modality", modality);
  const eParams = new URLSearchParams({ limit: "40" });
  if (q) eParams.set("q", q);

  const jobs: Promise<unknown>[] = [
    apiGet<Contract[]>(`/v1/contracts?${params}`),
    apiGet<Entity[]>(`/v1/entities?${eParams}`),
    apiGet<Category[]>("/v1/categories"),
  ];
  if (q.length >= 2) {
    jobs.push(apiGet<{ hits: SearchHit[] }>(`/v1/search?q=${encodeURIComponent(q)}&limit=12`));
  }
  const [contractsR, entitiesR, categoriesR, searchR] = await Promise.allSettled(jobs);
  const contracts = contractsR.status === "fulfilled" ? (contractsR.value as Contract[]) : null;
  const entities = entitiesR.status === "fulfilled" ? (entitiesR.value as Entity[]) : [];
  const categories = categoriesR.status === "fulfilled" ? (categoriesR.value as Category[]) : [];
  const hits =
    searchR?.status === "fulfilled"
      ? (searchR.value as { hits: SearchHit[] }).hits || []
      : [];
  const apiDown = contracts === null;
  const entityMap = Object.fromEntries(entities.map((e) => [e.id, e.name]));

  return (
    <section className="section">
      <h2>Explorar</h2>
      <p className="lead">Buscá contratos, entidades y proveedores; filtrá por categoría y año.</p>

      <form className="search-bar" action="/explorar" method="get">
        <input
          type="search"
          name="q"
          defaultValue={q}
          placeholder="Entidad, CUCE, proveedor, alerta…"
          aria-label="Buscar"
        />
        <input
          type="number"
          name="year"
          defaultValue={year}
          placeholder="Año"
          min={2016}
          max={2030}
          style={{ maxWidth: 110 }}
          aria-label="Año"
        />
        <input
          type="text"
          name="modality"
          defaultValue={modality}
          placeholder="Modalidad"
          style={{ maxWidth: 160 }}
          aria-label="Modalidad"
        />
        {category ? <input type="hidden" name="category" value={category} /> : null}
        <button type="submit" className="btn btn-primary">
          Buscar
        </button>
      </form>

      {categories.length > 0 && (
        <div className="chips">
          <Link
            href={`/explorar${q ? `?q=${encodeURIComponent(q)}` : ""}`}
            className={`chip ${!category ? "active" : ""}`}
          >
            Todas
          </Link>
          {categories.map((c) => {
            const href = `/explorar?category=${c.id}${year ? `&year=${year}` : ""}${q ? `&q=${encodeURIComponent(q)}` : ""}`;
            return (
              <Link key={c.id} href={href} className={`chip ${category === c.id ? "active" : ""}`}>
                {c.label} ({c.contracts})
              </Link>
            );
          })}
        </div>
      )}

      {apiDown && (
        <p className="error-box">
          No pudimos conectar con la API. Levantá el stack con <code>docker compose up -d</code>.
        </p>
      )}

      {hits.length > 0 && (
        <>
          <h3>Resultados de búsqueda</h3>
          <ul className="provenance-list" style={{ marginBottom: "1.5rem" }}>
            {hits.map((h) => (
              <li key={`${h.type}-${h.id}`}>
                <span>
                  <span className="badge badge-cat">{searchTypeLabel(h.type)}</span> {h.title}
                  {h.subtitle ? ` — ${h.subtitle}` : ""}
                </span>
                <Link href={h.href}>Abrir</Link>
              </li>
            ))}
          </ul>
        </>
      )}

      {entities.length > 0 && (
        <>
          <h3>Entidades</h3>
          <div className="table-wrap" style={{ marginBottom: "1.5rem" }}>
            <table>
              <thead>
                <tr>
                  <th>Nombre</th>
                  <th>Nivel</th>
                </tr>
              </thead>
              <tbody>
                {entities.map((e) => (
                  <tr key={e.id}>
                    <td>
                      <Link href={`/entidad/${e.id}`}>{e.name}</Link>
                    </td>
                    <td>{e.level}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      <h3>Contratos</h3>
      {contracts !== null && contracts.length === 0 ? (
        <p className="empty">Sin contratos para estos filtros.</p>
      ) : contracts === null ? null : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>CUCE</th>
                <th>Entidad</th>
                <th>Objeto</th>
                <th>Modalidad</th>
                <th>Monto</th>
                <th>Calidad</th>
              </tr>
            </thead>
            <tbody>
              {contracts.map((c) => (
                <tr key={c.id}>
                  <td>
                    <Link href={`/contrato/${c.id}`}>{c.cuce || `#${c.id}`}</Link>
                  </td>
                  <td>
                    <Link href={`/entidad/${c.entity_id}`}>
                      {entityMap[c.entity_id] || `Entidad #${c.entity_id}`}
                    </Link>
                  </td>
                  <td>{c.object_description || "—"}</td>
                  <td>{c.modality || "—"}</td>
                  <td>{formatMoney(c.amount)}</td>
                  <td>{qualityBadgeLabel(c.source_quality, c.is_synthetic)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {contracts !== null && (
        <Pager
          pathname="/explorar"
          params={{
            ...(q ? { q } : {}),
            ...(year ? { year } : {}),
            ...(category ? { category } : {}),
            ...(modality ? { modality } : {}),
          }}
          page={page}
          pageSize={pageSize}
          count={contracts.length}
        />
      )}
    </section>
  );
}
