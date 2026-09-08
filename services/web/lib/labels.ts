const RULE: Record<string, string> = {
  supplier_concentration: "Concentración de proveedor",
  recurrent_direct_award: "Adjudicación directa recurrente",
  zero_execution_late: "Cero ejecución tardía",
  source_discrepancy: "Discrepancia entre fuentes",
  possible_split_awards: "Posible fraccionamiento",
  low_execution_ratio: "Baja ejecución presupuestaria",
  missing_nit_high_amount: "Proveedor sin NIT (monto alto)",
  amount_claim_conflict: "Conflicto de montos en reclamaciones",
  fire_supplier_concentration: "Incendios: concentración de proveedor",
  fire_low_prevention_share: "Incendios: baja inversión en prevención",
  fire_low_data_quality: "Incendios: baja calidad de datos",
  fire_aircraft_without_ops: "Incendios: aeronave sin operación trazable",
  fire_spend_without_territory: "Incendios: gasto sin territorio",
  fire_announcement_without_cuce: "Incendios: anuncio sin CUCE",
  fire_post_emergency_spend: "Incendios: gasto post-emergencia",
  fire_fragmentation: "Incendios: posible fraccionamiento",
  fire_atypical_price: "Incendios: precio atípico",
  fire_direct_without_evidence: "Incendios: directa sin evidencia",
  fire_large_pool_excluded: "Incendios: fondo grande excluido",
};

const SEVERITY: Record<string, string> = {
  high: "Alta",
  medium: "Media",
  low: "Baja",
};

const ATTRIBUTION: Record<string, string> = {
  directo: "Directo",
  probable: "Probable",
  parcial: "Parcial",
  indirecto: "Indirecto",
  no_relacionado: "No relacionado",
};

const CYCLE: Record<string, string> = {
  prevencion: "Prevención",
  preparacion: "Preparación",
  respuesta: "Respuesta",
  recuperacion: "Recuperación",
};

const RUN_STATUS: Record<string, string> = {
  ok: "Correcta",
  partial: "Parcial",
  error: "Con errores",
  running: "En curso",
};

const ACTIVITY_KIND: Record<string, string> = {
  contract: "Contrato",
  budget: "Presupuesto",
  alert: "Alerta",
  discrepancy: "Discrepancia",
  audit: "Auditoría",
};

const SEARCH_TYPE: Record<string, string> = {
  entity: "Entidad",
  contract: "Contrato",
  supplier: "Proveedor",
  alert: "Alerta",
};

const EVENT_TYPE: Record<string, string> = {
  incendio: "Incendio",
  desastre: "Desastre",
  emergencia: "Emergencia",
  sequia: "Sequía",
};

const RECOVERY_STATUS: Record<string, string> = {
  not_published: "No publicado",
  not_publicly_recoverable: "No recuperable públicamente",
  published: "Publicado",
  partial: "Parcial",
};

const LINK_STRENGTH: Record<string, string> = {
  strong: "Fuerte",
  medium: "Media",
  weak: "Débil",
};

const COVERAGE_FLAG: Record<string, string> = {
  has_award: "Con adjudicación",
  has_awarded_amount: "Con monto adjudicado",
  has_supplier: "Con proveedor",
  has_reference_price: "Con precio referencial",
};

const ASSET_TYPE: Record<string, string> = {
  helicopter: "Helicóptero",
  aircraft: "Aeronave",
  vehicle: "Vehículo",
  equipment: "Equipo",
  brigade: "Brigada",
};

const OWNERSHIP: Record<string, string> = {
  own: "Propio",
  rental: "Alquiler",
  donated: "Donado",
  mixed: "Mixto",
};

function humanize(raw: string): string {
  const s = raw.replace(/[_-]+/g, " ").trim();
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function from(table: Record<string, string>, v?: string | null): string {
  if (!v) return "—";
  return table[v] ?? table[v.toLowerCase()] ?? humanize(v);
}

export const severityLabel = (v?: string | null) => from(SEVERITY, v);
export const alertRuleLabel = (v?: string | null) => from(RULE, v);
export const attributionLabel = (v?: string | null) => from(ATTRIBUTION, v);
export const cycleLabel = (v?: string | null) => from(CYCLE, v);
export const runStatusLabel = (v?: string | null) => from(RUN_STATUS, v);
export const activityKindLabel = (v?: string | null) => from(ACTIVITY_KIND, v);
export const searchTypeLabel = (v?: string | null) => from(SEARCH_TYPE, v);
export const eventTypeLabel = (v?: string | null) => from(EVENT_TYPE, v);
export const recoveryStatusLabel = (v?: string | null) => from(RECOVERY_STATUS, v);
export const linkStrengthLabel = (v?: string | null) => from(LINK_STRENGTH, v);
export const coverageFlagLabel = (v?: string | null) => from(COVERAGE_FLAG, v);
export const assetTypeLabel = (v?: string | null) => from(ASSET_TYPE, v);
export const ownershipLabel = (v?: string | null) => from(OWNERSHIP, v);
