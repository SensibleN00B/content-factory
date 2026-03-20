import type { ReactNode } from "react";

type SectionCardProps = {
  title: string;
  subtitle?: string;
  children: ReactNode;
  className?: string;
};

export function SectionCard({ title, subtitle, children, className }: SectionCardProps) {
  const classes = className ? `section-card ${className}` : "section-card";

  return (
    <section className={classes}>
      <header className="section-card-head">
        <h3>{title}</h3>
        {subtitle ? <p>{subtitle}</p> : null}
      </header>
      {children}
    </section>
  );
}
