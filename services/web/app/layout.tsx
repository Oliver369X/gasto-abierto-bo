import type { ReactNode } from "react";
import Link from "next/link";
import "./globals.css";

export const metadata = {
  title: "Gasto Abierto Bolivia",
  description: "Fiscalización ciudadana del gasto público con datos oficiales",
};

const NAV_MAIN = [
  { href: "/presupuesto", label: "Presupuesto" },
  { href: "/explorar", label: "Explorar" },
  { href: "/historico", label: "Histórico" },
  { href: "/alertas", label: "Alertas" },
];

const NAV_MORE = [
  { href: "/incendios", label: "Incendios" },
  { href: "/auditorias", label: "Auditorías" },
  { href: "/discrepancias", label: "Discrepancias" },
  { href: "/fuentes", label: "Fuentes" },
  { href: "/cobertura", label: "Cobertura" },
  { href: "/metodologia", label: "Metodología" },
];

const NAV_ALL = [...NAV_MAIN, ...NAV_MORE];

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="es">
      <body>
        <header className="site-header">
          <div className="wrap brand-row">
            <Link href="/" className="brand">
              <span className="brand-dot" aria-hidden="true" />
              Gasto Abierto <span>Bolivia</span>
            </Link>
            <nav className="nav-desktop" aria-label="Principal">
              {NAV_MAIN.map((n) => (
                <Link key={n.href} href={n.href}>
                  {n.label}
                </Link>
              ))}
              <details className="nav-mobile nav-more">
                <summary>Más</summary>
                <div className="nav-mobile-panel">
                  {NAV_MORE.map((n) => (
                    <Link key={n.href} href={n.href}>
                      {n.label}
                    </Link>
                  ))}
                </div>
              </details>
            </nav>
            <details className="nav-mobile nav-burger">
              <summary aria-label="Menú">Menú</summary>
              <div className="nav-mobile-panel">
                {NAV_ALL.map((n) => (
                  <Link key={n.href} href={n.href}>
                    {n.label}
                  </Link>
                ))}
              </div>
            </details>
          </div>
        </header>
        <main className="wrap">{children}</main>
        <footer className="site-footer wrap">
          <p>
            Datos de fuentes oficiales, siempre con enlace al origen. Código Apache-2.0 ·{" "}
            <Link href="/metodologia">Cómo trabajamos</Link>
          </p>
        </footer>
      </body>
    </html>
  );
}
