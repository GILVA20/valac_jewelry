import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { PRODUCT_TYPES, GENDERS, MATERIALS } from '@/lib/constants';
import type { ProductFilters as FilterType } from '@/types/filters';
import { cn } from '@/lib/utils';
import { X } from 'lucide-react';

interface Props {
  filters: FilterType;
  onChange: (f: FilterType) => void;
}

export function ProductFilters({ filters, onChange }: Props) {
  const set = (partial: Partial<FilterType>) => onChange({ ...filters, ...partial });
  const hasFilters = filters.estado !== 'todos' || filters.tipo_producto || filters.tipo_oro || filters.genero || filters.stock !== 'todos';

  return (
    <div className="flex flex-wrap items-center gap-2">
      {/* Estado pills */}
      <div className="flex rounded-md border border-border overflow-hidden">
        {(['todos', 'activos', 'borradores'] as const).map((e) => (
          <button
            key={e}
            onClick={() => set({ estado: e })}
            className={cn(
              'px-3 py-1.5 text-xs font-medium transition-colors capitalize',
              filters.estado === e ? 'bg-primary text-primary-foreground' : 'bg-card text-muted-foreground hover:bg-muted'
            )}
          >
            {e}
          </button>
        ))}
      </div>

      <Select value={filters.tipo_producto || 'all'} onValueChange={(v) => set({ tipo_producto: v === 'all' ? null : v })}>
        <SelectTrigger className="w-[130px] h-8 text-xs">
          <SelectValue placeholder="Tipo" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">Todos los tipos</SelectItem>
          {PRODUCT_TYPES.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}
        </SelectContent>
      </Select>

      <Select value={filters.tipo_oro || 'all'} onValueChange={(v) => set({ tipo_oro: v === 'all' ? null : v })}>
        <SelectTrigger className="w-[130px] h-8 text-xs">
          <SelectValue placeholder="Material" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">Todos</SelectItem>
          {MATERIALS.map((m) => <SelectItem key={m} value={m}>{m}</SelectItem>)}
        </SelectContent>
      </Select>

      {/* Gender pills */}
      <div className="flex gap-1">
        {GENDERS.map((g) => (
          <button
            key={g}
            onClick={() => set({ genero: filters.genero === g ? null : g })}
            className={cn(
              'px-2.5 py-1 text-xs rounded-full border transition-colors',
              filters.genero === g
                ? 'border-primary bg-primary text-primary-foreground'
                : 'border-border text-muted-foreground hover:bg-muted'
            )}
          >
            {g}
          </button>
        ))}
      </div>

      <Select value={filters.stock} onValueChange={(v) => set({ stock: v as FilterType['stock'] })}>
        <SelectTrigger className="w-[120px] h-8 text-xs">
          <SelectValue placeholder="Stock" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="todos">Todo stock</SelectItem>
          <SelectItem value="sin_stock">Sin stock</SelectItem>
          <SelectItem value="stock_bajo">Stock bajo</SelectItem>
          <SelectItem value="con_stock">Con stock</SelectItem>
        </SelectContent>
      </Select>

      {hasFilters && (
        <Button
          variant="ghost"
          size="sm"
          className="h-8 text-xs text-muted-foreground"
          onClick={() => onChange({
            search: filters.search,
            estado: 'todos',
            tipo_producto: null,
            tipo_oro: null,
            genero: null,
            stock: 'todos',
            precio_min: null,
            precio_max: null,
          })}
        >
          <X className="h-3 w-3 mr-1" /> Limpiar
        </Button>
      )}
    </div>
  );
}
