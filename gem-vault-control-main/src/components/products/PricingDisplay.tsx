export function PricingDisplay({ precio, descuento_pct, precio_descuento }: {
  precio: number;
  descuento_pct: number;
  precio_descuento: number;
}) {
  const fmt = (n: number) => new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' }).format(n);

  if (!descuento_pct) {
    return <span className="tabular-nums text-sm font-medium">{fmt(precio)}</span>;
  }

  return (
    <div className="flex flex-col">
      <span className="tabular-nums text-sm font-medium">{fmt(precio_descuento)}</span>
      <div className="flex items-center gap-1">
        <span className="tabular-nums text-xs text-muted-foreground line-through">{fmt(precio)}</span>
        <span className="text-xs text-destructive font-medium">-{descuento_pct}%</span>
      </div>
    </div>
  );
}
