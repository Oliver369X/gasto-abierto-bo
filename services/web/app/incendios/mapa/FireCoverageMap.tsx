"use client";

import { useEffect, useMemo, useState } from "react";

type Feature = {
  properties: {
    slug: string;
    name: string;
    level?: string;
    coverage_level?: string;
    expenditures: number;
    amount_direct_verifiable?: number;
  };
  geometry: { type: "Polygon"; coordinates: number[][][] };
};

type FeatureCollection = { type: "FeatureCollection"; features: Feature[] };

const COLORS: Record<string, string> = {
  Alta: "#f87171",
  Media: "#fdba74",
  Baja: "#fde047",
  "Sin datos": "#e7e5e0",
};

export default function FireCoverageMap({ year }: { year: number }) {
  const [data, setData] = useState<FeatureCollection | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    setData(null);
    setError(false);
    const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8010";
    fetch(`${base}/v1/fire/coverage.geojson?year=${year}`)
      .then((response) => {
        if (!response.ok) throw new Error(`GeoJSON ${response.status}`);
        return response.json();
      })
      .then(setData)
      .catch(() => setError(true));
  }, [year]);

  const polygons = useMemo(() => {
    if (!data) return [];
    const points = data.features.flatMap((feature) => feature.geometry.coordinates[0]);
    const lons = points.map(([lon]) => lon);
    const lats = points.map(([, lat]) => lat);
    const minLon = Math.min(...lons);
    const maxLon = Math.max(...lons);
    const minLat = Math.min(...lats);
    const maxLat = Math.max(...lats);
    const project = ([lon, lat]: number[]) => [
      20 + ((lon - minLon) / (maxLon - minLon)) * 560,
      20 + ((maxLat - lat) / (maxLat - minLat)) * 360,
    ];
    return data.features.map((feature) => ({
      ...feature,
      points: feature.geometry.coordinates[0]
        .map(project)
        .map(([x, y]) => `${x},${y}`)
        .join(" "),
    }));
  }, [data]);

  if (error) {
    return (
      <p className="empty">
        No pudimos cargar la cobertura territorial. La tabla de abajo sigue disponible.
      </p>
    );
  }
  if (!data) return <p className="empty">Cargando mapa…</p>;

  return (
    <div>
      <svg
        viewBox="0 0 600 400"
        role="img"
        aria-label={`Cobertura de incendios ${year} para Santa Cruz, Beni y Pando`}
        style={{ width: "100%", maxWidth: "720px", background: "#f8fafc", borderRadius: "12px" }}
      >
        {polygons.map((feature) => (
          <g key={feature.properties.slug}>
            <polygon
              points={feature.points}
              fill={
                COLORS[feature.properties.level || feature.properties.coverage_level || ""] ||
                COLORS["Sin datos"]
              }
              stroke="#ffffff"
              strokeWidth="2"
            >
              <title>
                {feature.properties.name}:{" "}
                {feature.properties.level || feature.properties.coverage_level},{" "}
                {feature.properties.expenditures} expedientes
              </title>
            </polygon>
          </g>
        ))}
      </svg>
      <p>
        {polygons
          .map(
            (feature) =>
              `${feature.properties.name}: ${feature.properties.coverage_level} (${feature.properties.expenditures})`
          )
          .join(" · ")}
      </p>
    </div>
  );
}
