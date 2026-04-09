import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import type { Product } from '@/types/product';
import type { SortState } from '@/types/filters';
import { StatusBadge } from './StatusBadge';
import { StockBadge } from './StockBadge';
import { PricingDisplay } from './PricingDisplay';
import { Checkbox } from '@/components/ui/checkbox';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Pencil, Copy, Trash2, ArrowUpDown, ArrowUp, ArrowDown, ImageIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

interface Props {
  products: Product[];
  loading: boolean;
  sort: SortState;
  onSortChange: (s: SortState) => void;
  selectedIds: number[];
  onSelectionChange: (ids: number[]) => void;
  onToggleActive: (id: number, current: boolean) => void;
  onDelete: (id: number) => void;
  onDuplicate: (product: Product) => void;
  onInlineEdit: (id: number, field: string, value: string | number) => void;
}

function SortHeader({ label, column, sort, onSort }: { label: string; column: string; sort: SortState; onSort: (s: SortState) => void }) {
  const active = sort.column === column;
  return (
    <button
      className="flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
      onClick={() => onSort({ column, ascending: active ? !sort.ascending : true })}
    >
      {label}
      {active ? (sort.ascending ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />) : <ArrowUpDown className="h-3 w-3 opacity-40" />}
    </button>
  );
}

export function ProductsTable({ products, loading, sort, onSortChange, selectedIds, onSelectionChange, onToggleActive, onDelete, onDuplicate, onInlineEdit }: Props) {
  const navigate = useNavigate();
  const [editingCell, setEditingCell] = useState<{ id: number; field: string } | null>(null);
  const [editValue, setEditValue] = useState('');
  const [deleteId, setDeleteId] = useState<number | null>(null);

  const allSelected = products.length > 0 && selectedIds.length === products.length;
  const toggleAll = () => onSelectionChange(allSelected ? [] : products.map(p => p.id));
  const toggleOne = (id: number) => onSelectionChange(
    selectedIds.includes(id) ? selectedIds.filter(i => i !== id) : [...selectedIds, id]
  );

  const startEdit = useCallback((id: number, field: string, currentValue: string | number) => {
    setEditingCell({ id, field });
    setEditValue(String(currentValue));
  }, []);

  const commitEdit = useCallback(() => {
    if (editingCell) {
      const value = editingCell.field === 'nombre' ? editValue : Number(editValue);
      onInlineEdit(editingCell.id, editingCell.field, value);
      setEditingCell(null);
    }
  }, [editingCell, editValue, onInlineEdit]);

  if (loading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-14 w-full rounded-md" />
        ))}
      </div>
    );
  }

  return (
    <>
      <div className="border border-border rounded-lg overflow-hidden bg-card">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/50">
                <th className="w-10 p-3">
                  <Checkbox checked={allSelected} onCheckedChange={toggleAll} />
                </th>
                <th className="w-12 p-3" />
                <th className="p-3 text-left"><SortHeader label="Nombre" column="nombre" sort={sort} onSort={onSortChange} /></th>
                <th className="p-3 text-left">Estado</th>
                <th className="p-3 text-right"><SortHeader label="Precio" column="precio" sort={sort} onSort={onSortChange} /></th>
                <th className="p-3 text-center"><SortHeader label="Stock" column="stock_total" sort={sort} onSort={onSortChange} /></th>
                <th className="p-3 text-left">Tipo</th>
                <th className="p-3 text-left">Material</th>
                <th className="p-3 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {products.map((p) => (
                <tr key={p.id} className={cn('border-b border-border last:border-0 hover:bg-muted/30 transition-colors', selectedIds.includes(p.id) && 'bg-accent/50')}>
                  <td className="p-3">
                    <Checkbox checked={selectedIds.includes(p.id)} onCheckedChange={() => toggleOne(p.id)} />
                  </td>
                  <td className="p-3">
                    {p.imagen ? (
                      <img src={p.imagen} alt={p.nombre} className="w-10 h-10 rounded-md object-cover" />
                    ) : (
                      <div className="w-10 h-10 rounded-md bg-muted flex items-center justify-center">
                        <ImageIcon className="h-4 w-4 text-muted-foreground" />
                      </div>
                    )}
                  </td>
                  <td className="p-3">
                    {editingCell?.id === p.id && editingCell.field === 'nombre' ? (
                      <input
                        autoFocus
                        className="w-full bg-transparent border-b border-primary outline-none text-sm font-medium"
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        onBlur={commitEdit}
                        onKeyDown={(e) => { if (e.key === 'Enter') commitEdit(); if (e.key === 'Escape') setEditingCell(null); }}
                      />
                    ) : (
                      <div onDoubleClick={() => startEdit(p.id, 'nombre', p.nombre)} className="cursor-text">
                        <div className="font-medium truncate max-w-[200px]">{p.nombre}</div>
                        <div className="text-xs text-muted-foreground truncate max-w-[200px]">{p.descripcion}</div>
                      </div>
                    )}
                  </td>
                  <td className="p-3">
                    <StatusBadge activo={p.activo} onClick={() => onToggleActive(p.id, p.activo)} />
                  </td>
                  <td className="p-3 text-right">
                    {editingCell?.id === p.id && editingCell.field === 'precio' ? (
                      <input
                        autoFocus
                        type="number"
                        className="w-24 bg-transparent border-b border-primary outline-none text-sm text-right tabular-nums"
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        onBlur={commitEdit}
                        onKeyDown={(e) => { if (e.key === 'Enter') commitEdit(); if (e.key === 'Escape') setEditingCell(null); }}
                      />
                    ) : (
                      <div onDoubleClick={() => startEdit(p.id, 'precio', p.precio)} className="cursor-text">
                        <PricingDisplay precio={p.precio} descuento_pct={p.descuento_pct} precio_descuento={p.precio_descuento} />
                      </div>
                    )}
                  </td>
                  <td className="p-3 text-center">
                    {editingCell?.id === p.id && editingCell.field === 'stock_total' ? (
                      <input
                        autoFocus
                        type="number"
                        className="w-16 bg-transparent border-b border-primary outline-none text-sm text-center tabular-nums"
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        onBlur={commitEdit}
                        onKeyDown={(e) => { if (e.key === 'Enter') commitEdit(); if (e.key === 'Escape') setEditingCell(null); }}
                      />
                    ) : (
                      <div onDoubleClick={() => startEdit(p.id, 'stock_total', p.stock_total)} className="cursor-text">
                        <StockBadge stock={p.stock_total} />
                      </div>
                    )}
                  </td>
                  <td className="p-3 text-xs text-muted-foreground">{p.tipo_producto}</td>
                  <td className="p-3 text-xs text-muted-foreground">{p.tipo_oro}</td>
                  <td className="p-3">
                    <div className="flex items-center justify-end gap-1">
                      <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => navigate(`/products/${p.id}`)}>
                        <Pencil className="h-3.5 w-3.5" />
                      </Button>
                      <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => onDuplicate(p)}>
                        <Copy className="h-3.5 w-3.5" />
                      </Button>
                      <Button variant="ghost" size="icon" className="h-7 w-7 text-destructive" onClick={() => setDeleteId(p.id)}>
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {deleteId !== null && (
        <div className="fixed inset-0 bg-foreground/20 backdrop-blur-sm flex items-center justify-center z-50" onClick={() => setDeleteId(null)}>
          <div className="bg-card p-6 rounded-lg shadow-lg max-w-sm" onClick={(e) => e.stopPropagation()}>
            <h3 className="font-semibold mb-2">¿Eliminar producto?</h3>
            <p className="text-sm text-muted-foreground mb-4">Esta acción no se puede deshacer.</p>
            <div className="flex gap-2 justify-end">
              <Button variant="outline" size="sm" onClick={() => setDeleteId(null)}>Cancelar</Button>
              <Button variant="destructive" size="sm" onClick={() => { onDelete(deleteId); setDeleteId(null); }}>Eliminar</Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
