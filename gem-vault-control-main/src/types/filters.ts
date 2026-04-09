export interface ProductFilters {
  search: string;
  estado: 'todos' | 'activos' | 'borradores';
  tipo_producto: string | null;
  tipo_oro: string | null;
  genero: string | null;
  stock: 'todos' | 'sin_stock' | 'stock_bajo' | 'con_stock';
  precio_min: number | null;
  precio_max: number | null;
}

export interface PaginationState {
  page: number;
  pageSize: number;
}

export interface SortState {
  column: string;
  ascending: boolean;
}

export const defaultFilters: ProductFilters = {
  search: '',
  estado: 'todos',
  tipo_producto: null,
  tipo_oro: null,
  genero: null,
  stock: 'todos',
  precio_min: null,
  precio_max: null,
};
