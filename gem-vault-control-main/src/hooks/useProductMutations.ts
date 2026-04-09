import { useMutation, useQueryClient } from '@tanstack/react-query';
import { createProduct, updateProduct, deleteProduct, deleteProducts, toggleActive, bulkToggleActive, bulkApplyDiscount, inlineUpdate } from '@/services/products';
import type { ProductInsert, ProductUpdate } from '@/types/product';
import { toast } from 'sonner';

export function useProductMutations() {
  const qc = useQueryClient();
  const invalidate = () => qc.invalidateQueries({ queryKey: ['products'] });

  const create = useMutation({
    mutationFn: (data: ProductInsert) => createProduct(data),
    onSuccess: () => { toast.success('Producto creado'); invalidate(); },
    onError: (e: Error) => toast.error(e.message),
  });

  const update = useMutation({
    mutationFn: ({ id, data }: { id: number; data: ProductUpdate }) => updateProduct(id, data),
    onSuccess: () => { toast.success('Producto actualizado'); invalidate(); qc.invalidateQueries({ queryKey: ['product'] }); },
    onError: (e: Error) => toast.error(e.message),
  });

  const remove = useMutation({
    mutationFn: (id: number) => deleteProduct(id),
    onSuccess: () => { toast.success('Producto eliminado'); invalidate(); },
    onError: (e: Error) => toast.error(e.message),
  });

  const removeBulk = useMutation({
    mutationFn: (ids: number[]) => deleteProducts(ids),
    onSuccess: () => { toast.success('Productos eliminados'); invalidate(); },
    onError: (e: Error) => toast.error(e.message),
  });

  const toggle = useMutation({
    mutationFn: ({ id, current }: { id: number; current: boolean }) => toggleActive(id, current),
    onSuccess: () => { toast.success('Estado actualizado'); invalidate(); },
    onError: (e: Error) => toast.error(e.message),
  });

  const bulkToggle = useMutation({
    mutationFn: ({ ids, activo }: { ids: number[]; activo: boolean }) => bulkToggleActive(ids, activo),
    onSuccess: () => { toast.success('Estado actualizado'); invalidate(); },
    onError: (e: Error) => toast.error(e.message),
  });

  const bulkDiscount = useMutation({
    mutationFn: ({ ids, pct }: { ids: number[]; pct: number }) => bulkApplyDiscount(ids, pct),
    onSuccess: () => { toast.success('Descuento aplicado'); invalidate(); },
    onError: (e: Error) => toast.error(e.message),
  });

  const inlineEdit = useMutation({
    mutationFn: ({ id, field, value }: { id: number; field: string; value: string | number }) => inlineUpdate(id, field, value),
    onSuccess: () => { toast.success('Actualizado'); invalidate(); },
    onError: (e: Error) => toast.error(e.message),
  });

  return { create, update, remove, removeBulk, toggle, bulkToggle, bulkDiscount, inlineEdit };
}
