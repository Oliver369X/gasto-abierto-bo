import Link from "next/link";

type PagerProps = {
  pathname: string;
  params: Record<string, string>;
  page: number;
  pageSize: number;
  count: number;
};

export function Pager({ pathname, params, page, pageSize, count }: PagerProps) {
  const href = (p: number) => {
    const q = new URLSearchParams({ ...params, page: String(p) });
    return `${pathname}?${q.toString()}`;
  };
  if (page <= 1 && count < pageSize) return null;
  return (
    <div
      className="cta-row"
      style={{ marginTop: "1rem", justifyContent: "flex-end", alignItems: "center" }}
    >
      {page > 1 ? (
        <Link className="btn btn-ghost" href={href(page - 1)}>
          ← Anterior
        </Link>
      ) : null}
      <span style={{ color: "var(--muted)", fontSize: "0.9rem" }}>Página {page}</span>
      {count >= pageSize ? (
        <Link className="btn btn-ghost" href={href(page + 1)}>
          Siguiente →
        </Link>
      ) : null}
    </div>
  );
}
