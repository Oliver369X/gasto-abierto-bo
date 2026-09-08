import { alertRuleLabel } from "@/lib/labels";

const RULES = [
  {
    id: "supplier_concentration",
    desc: "Proveedor ≥35% del monto contractual de una entidad.",
  },
  {
    id: "recurrent_direct_award",
    desc: "≥2 contratos directa/excepción/emergencia al mismo proveedor.",
  },
  {
    id: "zero_execution_late",
    desc: "Vigente ≥1M BOB y ejecución 0 post-Q3.",
  },
  {
    id: "source_discrepancy",
    desc: "Montos distintos entre fuentes para el mismo concepto/CUCE.",
  },
  {
    id: "possible_split_awards",
    desc: "≥3 contratos chicos misma pareja entidad-proveedor en ≤45 días.",
  },
  {
    id: "low_execution_ratio",
    desc: "Ejecución <15% con vigente ≥5M BOB (desde junio).",
  },
];

const FIRE_RULES = [
  {
    id: "fire_supplier_concentration",
    desc: "Un proveedor concentra ≥40% del gasto atribuido a incendios en una gestión.",
  },
  {
    id: "fire_low_prevention_share",
    desc: "Gasto en prevención bajo respecto al total atribuido (≥5M BOB).",
  },
  {
    id: "fire_low_data_quality",
    desc: "Muchos expedientes sin CUCE, territorio o evidencia trazable.",
  },
  {
    id: "fire_aircraft_without_ops",
    desc: "Pago o alquiler de aeronave sin salida operacional registrada.",
  },
  {
    id: "fire_fragmentation",
    desc: "Posible fraccionamiento de contratos de respuesta a incendios.",
  },
];

export default function MetodologiaPage() {
  return (
    <section className="section">
      <h2>Metodología</h2>
      <p className="lead">Cómo se construyen los datos y las alertas. Sin cajas negras.</p>
      <div className="grid-2">
        {RULES.map((r) => (
          <article key={r.id} className="panel">
            <h3>{alertRuleLabel(r.id)}</h3>
            <p>{r.desc}</p>
            <p className="hint">
              Identificador técnico: <code>{r.id}</code>
            </p>
          </article>
        ))}
      </div>

      <div id="presupuesto" style={{ marginTop: "2.5rem" }}>
        <h2>Presupuesto Abierto — integración</h2>
        <p className="lead">
          Preferimos descargas oficiales CSV/Parquet desde{" "}
          <a href="https://abierto.economiayfinanzas.gob.bo/descargas" rel="noreferrer" target="_blank">
            abierto.economiayfinanzas.gob.bo/descargas
          </a>{" "}
          sobre scraping del portal. Correlacionamos por institución, departamento, gestión y
          objeto de gasto; cruzamos con contratos SICOES/OCP y marcamos discrepancias.
        </p>
      </div>

      <div id="incendios" style={{ marginTop: "2.5rem" }}>
        <h2>AURA Incendios — atribución</h2>
        <p className="lead">
          No todo gasto de «emergencia o desastre» es incendio forestal. Cada expediente
          lleva atribución explícita.
        </p>
        <div className="grid-2">
          <article className="panel">
            <h3>DIRECTO</h3>
            <p>
              100 % explícito (p. ej. «alquiler de aeronave para lucha contra incendios
              forestales»). Entra al total verificable.
            </p>
          </article>
          <article className="panel">
            <h3>PROBABLE</h3>
            <p>Vocabulario fuerte (cisterna, EPP forestal) sin mención explícita de incendio.</p>
          </article>
          <article className="panel">
            <h3>PARCIAL</h3>
            <p>Solo una fracción del contrato/partida se atribuye al evento.</p>
          </article>
          <article className="panel">
            <h3>INDIRECTO / NO RELACIONADO</h3>
            <p>
              Capacidad general o emergencia genérica (inundación, sequía, ayuda humanitaria
              sin fuego). <strong>No</strong> se suma al gasto verificable de incendios.
            </p>
          </article>
        </div>
        <p style={{ marginTop: "1rem" }}>
          Ciclos: prevención → preparación → respuesta → recuperación. Separación: entidad
          que paga ≠ territorio beneficiado ≠ ubicación del proveedor. Inventario de fuentes:{" "}
          <code>docs/sources/fire-inventory.md</code>.
        </p>
        <h3 style={{ marginTop: "1.5rem" }}>Reglas de alerta (incendios)</h3>
        <div className="grid-2">
          {FIRE_RULES.map((r) => (
            <article key={r.id} className="panel">
              <h3>{alertRuleLabel(r.id)}</h3>
              <p>{r.desc}</p>
              <p className="hint">
                Identificador técnico: <code>{r.id}</code>
              </p>
            </article>
          ))}
        </div>
      </div>

      <p style={{ marginTop: "1.5rem", color: "var(--muted)" }}>
        Raw en MinIO, SCD2 en presupuestos, fichas en <code>docs/sources/</code>, política en{" "}
        <code>docs/legal/data-policy.md</code>.
      </p>
    </section>
  );
}
