import Link from "next/link";
import { apiGet, formatMoney, qualityBadgeLabel } from "@/lib/api";

type Supplier = {
  id: number;
  name: string;
  nit?: string;
  source_id: string;
  supplier_master_id?: number;
  source_quality?: string;
  is_synthetic?: boolean;
  canonical_name?: string;
};
type Contract = {
  id: number;
  cuce?: string;
  entity_id: number;
  object_description?: string;
  amount?: string;
  modality?: string;
  contract_date?: string;
};
type Entity = { id: number; name: string };
type Master = {
  id: number;
  canonical_name: string;
  nit?: string;
  department?: string;
};

export default async function ProveedorPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  let supplier: Supplier | null = null;
  try {
    supplier = await apiGet<Supplier>(`/v1/suppliers/${id}`);
  } catch {
    supplier = null;
  }

  if (!supplier) {
    return (
      <section className="section">
        <h2>Proveedor no encontrado</h2>
        <p className="empty">El proveedor #{id} no existe o la API no está disponible.</p>
        <p>
          <Link href="/explorar">← Volver a explorar</Link>
        </p>
      </section>
    );
  }

  const [contractsR, entitiesR] = await Promise.allSettled([
    apiGet<Contract[]>(`/v1/contracts?supplier=${id}&limit=50`),
    apiGet<Entity[]>("/v1/entities?limit=200"),
  ]);
  const contracts = contractsR.status === "fulfilled" ? contractsR.value : [];
  const entities = entitiesR.status === "fulfilled" ? entitiesR.value : [];
  const entityMap = Object.fromEntries(entities.map((e) => [e.id, e.name]));

  let master: Master | null = null;
  let aliases: string[] = [];
  if (supplier.supplier_master_id) {
    const [masterR, aliasesR] = await Promise.allSettled([
      apiGet<Master>(`/v1/supplier-masters/${supplier.supplier_master_id}`),
      apiGet<string[]>(`/v1/supplier-masters/${supplier.supplier_master_id}/aliases`),
    ]);
    master = masterR.status === "fulfilled" ? masterR.value : null;
    aliases = aliasesR.status === "fulfilled" ? aliasesR.value : [];
  }

  const years = [
    ...new Set(
      contracts
        .map((c) => (c.contract_date ? Number(String(c.contract_date).slice(0, 4)) : null))
        .filter((y): y is number => !!y)
    ),
  ].sort();

  return (
    <section className="section">
      <h2>{master?.canonical_name || supplier.name}</h2>
      <p className="lead">
        NIT: {master?.nit || supplier.nit || "—"} · Fuente: {supplier.source_id} ·{" "}
        {qualityBadgeLabel(supplier.source_quality, supplier.is_synthetic)}
      </p>
      {aliases.length > 0 ? (
        <p className="lead">
          También aparece como: {Array.from(new Set(aliases)).slice(0, 8).join(" · ")}
        </p>
      ) : null}
      {years.length > 0 ? <p className="lead">Años con contratos: {years.join(", ")}</p> : null}

      <h3>Contratos</h3>
      {contracts.length === 0 ? (
        <p className="empty">Sin contratos registrados para este proveedor.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>CUCE</th>
                <th>Entidad</th>
                <th>Objeto</th>
                <th>Modalidad</th>
                <th>Monto</th>
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
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
