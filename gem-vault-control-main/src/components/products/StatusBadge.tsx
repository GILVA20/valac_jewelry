import { cn } from '@/lib/utils';

interface StatusBadgeProps {
  activo: boolean;
  onClick?: () => void;
}

export function StatusBadge({ activo, onClick }: StatusBadgeProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium transition-colors cursor-pointer',
        activo
          ? 'bg-success/15 text-success hover:bg-success/25'
          : 'bg-warning/15 text-warning hover:bg-warning/25'
      )}
    >
      <span className={cn('w-1.5 h-1.5 rounded-full mr-1.5', activo ? 'bg-success' : 'bg-warning')} />
      {activo ? 'Activo' : 'Borrador'}
    </button>
  );
}
