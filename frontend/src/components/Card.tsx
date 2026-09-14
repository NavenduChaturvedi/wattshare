export function Card({
  title,
  subtitle,
  icon,
  action,
  children,
}: {
  title: string;
  subtitle?: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section
      className="rounded-3xl p-5 shadow-[0_1px_2px_rgba(20,18,15,0.04),0_8px_24px_rgba(20,18,15,0.05)]"
      style={{ background: "var(--card-bg)" }}
    >
      <div className="mb-4 flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          {icon && (
            <span
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full"
              style={{ background: "var(--accent-soft)", color: "var(--accent)" }}
            >
              {icon}
            </span>
          )}
          <div>
            <h2 className="text-sm font-semibold" style={{ color: "var(--ink)" }}>
              {title}
            </h2>
            {subtitle && (
              <p className="text-xs" style={{ color: "var(--ink-muted)" }}>
                {subtitle}
              </p>
            )}
          </div>
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}
