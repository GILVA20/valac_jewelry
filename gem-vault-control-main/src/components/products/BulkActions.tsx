import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Eye, EyeOff, Percent, Trash2 } from 'lucide-react';
import { ConfirmDialog } from '@/components/shared/ConfirmDialog';

interface Props {
  count: number;
  onActivate: () => void;
  onDeactivate: () => void;
  onDiscount: (pct: number) => void;
  onDelete: () => void;
  onClear: () => void;
}

export function BulkActions({ count, onActivate, onDeactivate, onDiscount, onDelete, onClear }: Props) {
  const [discountOpen, setDiscountOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [discountValue, setDiscountValue] = useState('');

  if (count === 0) return null;

  return (
    <>
      <div className="flex items-center gap-2 px-4 py-2 bg-accent rounded-lg animate-fade-in">
        <span className="text-sm font-medium text-accent-foreground">{count} seleccionados</span>
        <div className="flex gap-1 ml-2">
          <Button variant="outline" size="sm" className="h-7 text-xs" onClick={onActivate}>
            <Eye className="h-3 w-3 mr-1" /> Activar
          </Button>
          <Button variant="outline" size="sm" className="h-7 text-xs" onClick={onDeactivate}>
            <EyeOff className="h-3 w-3 mr-1" /> Desactivar
          </Button>
          <Button variant="outline" size="sm" className="h-7 text-xs" onClick={() => setDiscountOpen(true)}>
            <Percent className="h-3 w-3 mr-1" /> Descuento
          </Button>
          <Button variant="outline" size="sm" className="h-7 text-xs text-destructive" onClick={() => setDeleteOpen(true)}>
            <Trash2 className="h-3 w-3 mr-1" /> Eliminar
          </Button>
        </div>
        <Button variant="ghost" size="sm" className="h-7 text-xs ml-auto" onClick={onClear}>
          Deseleccionar
        </Button>
      </div>

      <Dialog open={discountOpen} onOpenChange={setDiscountOpen}>
        <DialogContent className="max-w-xs">
          <DialogHeader>
            <DialogTitle>Aplicar descuento</DialogTitle>
          </DialogHeader>
          <div className="flex items-center gap-2">
            <Input
              type="number"
              min={0}
              max={100}
              placeholder="0"
              value={discountValue}
              onChange={(e) => setDiscountValue(e.target.value)}
              className="text-center"
            />
            <span className="text-lg font-medium">%</span>
          </div>
          <DialogFooter>
            <Button
              onClick={() => {
                onDiscount(Number(discountValue));
                setDiscountOpen(false);
                setDiscountValue('');
              }}
              disabled={!discountValue || Number(discountValue) < 0 || Number(discountValue) > 100}
            >
              Aplicar a {count} productos
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Eliminar productos"
        description={`¿Eliminar ${count} productos? Esta acción no se puede deshacer.`}
        onConfirm={onDelete}
        destructive
      />
    </>
  );
}
