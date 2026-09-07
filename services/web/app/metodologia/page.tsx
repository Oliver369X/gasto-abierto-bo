export default function MetodologiaPage() {
  return (
    <section className="section">
      <h2>Metodología</h2>
      <p className="lead">Cómo se construyen los datos y las alertas. Sin cajas negras.</p>
      <div className="grid-2">
        <article className="panel">
          <h3>
            <code>supplier_concentration</code>
          </h3>
          <p>Proveedor ≥35% del monto contractual de una entidad.</p>
        </article>
        <article className="panel">
          <h3>
            <code>recurrent_direct_award</code>
          </h3>
          <p>≥2 contratos directa/excepción/emergencia al mismo proveedor.</p>
        </article>
        <article className="panel">
          <h3>
            <code>zero_execution_late</code>
          </h3>
          <p>Vigente ≥1M BOB y ejecución 0 post-Q3.</p>
        </article>
        <article className="panel">
          <h3>
            <code>source_discrepancy</code>
          </h3>
          <p>Montos distintos entre fuentes para el mismo concepto/CUCE.</p>
        </article>
        <article className="panel">
          <h3>
            <code>possible_split_awards</code>
          </h3>
          <p>≥3 contratos chicos misma pareja entidad-proveedor en ≤45 días.</p>
        </article>
        <article className="panel">
          <h3>
            <code>low_execution_ratio</code>
          </h3>
          <p>Ejecución &lt;15% con vigente ≥5M BOB (desde junio).</p>
        </article>
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
      </div>

      <p style={{ marginTop: "1.5rem", color: "var(--muted)" }}>
        Raw en MinIO, SCD2 en presupuestos, fichas en <code>docs/sources/</code>, política en{" "}
        <code>docs/legal/data-policy.md</code>.
      </p>
    </section>
  );
}
