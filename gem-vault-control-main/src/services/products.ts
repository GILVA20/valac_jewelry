import { supabase } from './supabase';
import type { Product, ProductInsert, ProductUpdate } from '@/types/product';
import type { ProductFilters, SortState, PaginationState } from '@/types/filters';

interface ListResult {
  data: Product[];
  count: number;
}

export async function listProducts(
  filters: ProductFilters,
  sort: SortState,
  pagination: PaginationState
): Promise<ListResult> {
  let query = supabase
    .from('products')
    .select('*, product_images(id, imagen, orden)', { count: 'exact' });

  if (filters.search) {
    query = query.ilike('nombre', `%${filters.search}%`);
  }
  if (filters.estado === 'activos') query = query.eq('activo', true);
  if (filters.estado === 'borradores') query = query.eq('activo', false);
  if (filters.tipo_producto) query = query.eq('tipo_producto', filters.tipo_producto);
  if (filters.tipo_oro) query = query.eq('tipo_oro', filters.tipo_oro);
  if (filters.genero) query = query.eq('genero', filters.genero);
  if (filters.precio_min != null) query = query.gte('precio', filters.precio_min);
  if (filters.precio_max != null) query = query.lte('precio', filters.precio_max);
  if (filters.stock === 'sin_stock') query = query.eq('stock_total', 0);
  if (filters.stock === 'stock_bajo') query = query.gt('stock_total', 0).lt('stock_total', 5);
  if (filters.stock === 'con_stock') query = query.gte('stock_total', 5);

  const offset = (pagination.page - 1) * pagination.pageSize;
  query = query
    .order(sort.column, { ascending: sort.ascending })
    .range(offset, offset + pagination.pageSize - 1);

  const { data, count, error } = await query;
  if (error) throw error;

  return {
    data: (data as Product[]) || [],
    count: count || 0,
  };
}

export async function getProduct(id: number): Promise<Product> {
  const { data, error } = await supabase
    .from('products')
    .select('*, product_images(id, imagen, orden)')
    .eq('id', id)
    .single();
  if (error) throw error;
  return data as Product;
}

export async function createProduct(product: ProductInsert): Promise<Product> {
  const precio_descuento = product.precio * (1 - (product.descuento_pct || 0) / 100);
  const { data, error } = await supabase
    .from('products')
    .insert({ ...product, precio_descuento })
    .select()
    .single();
  if (error) throw error;
  return data as Product;
}

export async function updateProduct(id: number, updates: ProductUpdate): Promise<Product> {
  const payload: Record<string, unknown> = { ...updates, updated_at: new Date().toISOString() };
  if (updates.precio != null || updates.descuento_pct != null) {
    const precio = updates.precio ?? 0;
    const descuento = updates.descuento_pct ?? 0;
    payload.precio_descuento = precio * (1 - descuento / 100);
  }
  const { data, error } = await supabase
    .from('products')
    .update(payload)
    .eq('id', id)
    .select()
    .single();
  if (error) throw error;
  return data as Product;
}

export async function deleteProduct(id: number): Promise<void> {
  const { error } = await supabase.from('products').delete().eq('id', id);
  if (error) throw error;
}

export async function deleteProducts(ids: number[]): Promise<void> {
  const { error } = await supabase.from('products').delete().in('id', ids);
  if (error) throw error;
}

export async function toggleActive(id: number, current: boolean): Promise<void> {
  const { error } = await supabase.from('products').update({ activo: !current }).eq('id', id);
  if (error) throw error;
}

export async function bulkToggleActive(ids: number[], activo: boolean): Promise<void> {
  const { error } = await supabase.from('products').update({ activo }).in('id', ids);
  if (error) throw error;
}

export async function bulkApplyDiscount(ids: number[], descuento_pct: number): Promise<void> {
  // Need to fetch prices first to calc precio_descuento
  const { data: products, error: fetchError } = await supabase
    .from('products')
    .select('id, precio')
    .in('id', ids);
  if (fetchError) throw fetchError;

  for (const p of products || []) {
    const precio_descuento = p.precio * (1 - descuento_pct / 100);
    await supabase.from('products').update({ descuento_pct, precio_descuento }).eq('id', p.id);
  }
}

export async function inlineUpdate(id: number, field: string, value: string | number): Promise<void> {
  const updates: Record<string, unknown> = { [field]: value, updated_at: new Date().toISOString() };
  if (field === 'precio') {
    // Re-fetch descuento to recalc
    const { data } = await supabase.from('products').select('descuento_pct').eq('id', id).single();
    const pct = data?.descuento_pct || 0;
    updates.precio_descuento = (value as number) * (1 - pct / 100);
  }
  const { error } = await supabase.from('products').update(updates).eq('id', id);
  if (error) throw error;
}
