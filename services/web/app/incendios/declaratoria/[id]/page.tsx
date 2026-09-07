import Link from "next/link";
import { apiGet, formatDate, formatMoney } from "@/lib/api";
import { attributionLabel, cycleLabel, eventTypeLabel } from "@/lib/labels";

type DeclarationDetail = {
  id: number;
  title: string;
  decree_number?: string;
  event_type: string;
  promulgated_at?: string;
  summary?: string;
  url?: string;
  related_count: number;
  related_expenditures: {
    id: number;
    code: string;
    title: string;
    attribution: string;
    cycle: string;
    amount_attributed?: string;
    window: string;
    note: string;
  }[];
};

export default async function DeclaratoriaPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  let d: DeclarationDetail | null = null;
  try {
    d = await apiGet<DeclarationDetail>(`/v1/fire/declarations/${id}`);
  } catch {
    d = null;
  }

  if (!d) {
    return (
      <section className="section">
        <p className="lead">
          <Link href="/incendios">← Incendios</Link>
        </p>
        <h2>Declaratoria no encontrada</h2>
        <p className="empty">La declaratoria #{id} no existe o la API no está disponible.</p>
      </section>
    );
  }

  const year = d.promulgated_at ? new Date(d.promulgated_at).getFullYear() : null;

  return (
    <section className="section">
      <p className="lead">
        <Link href={year ? `/incendios?year=${year}` : "/incendios"}>
          Incendios{year ? ` ${year}` : ""}
        </Link>
        {" / "}
        Declaratoria #{d.id}
      </p>
      <h2>{d.title}</h2>
      <p className="lead">
        {eventTypeLabel(d.event_type)}
        {d.decree_number ? ` · Decreto ${d.decree_number}` : ""}
        {d.promulgated_at ? ` · ${formatDate(d.promulgated_at)}` : ""}
      </p>
      {d.summary && <p>{d.summary}</p>}
      {d.url && (
        <p>
          <a className="btn btn-ghost" href={d.url} target="_blank" rel="noreferrer">
            Documento oficial ↗
          </a>
        </p>
      )}

      <h3>Gasto relacionado ({d.related_count})</h3>
      <p className="lead">
        Expedientes del mismo territorio y año de la declaratoria. La relación es por
        territorio + ventana temporal — no prueba causalidad.
      </p>
      {d.related_expenditures.length === 0 ? (
        <p className="empty">Sin expedientes relacionados en la ventana.</p>
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
              {d.related_expenditures.map((e) => (
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
