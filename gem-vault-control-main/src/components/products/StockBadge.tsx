import { cn } from '@/lib/utils';

export function StockBadge({ stock }: { stock: number }) {
  return (
    <span
      className={cn(
        'tabular-nums text-sm font-medium',
        stock === 0 && 'text-destructive',
        stock > 0 && stock < 5 && 'text-warning',
        stock >= 5 && 'text-success'
      )}
    >
      {stock}
    </span>
  );
}
