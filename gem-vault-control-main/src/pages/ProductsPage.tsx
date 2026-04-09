import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useProducts } from '@/hooks/useProducts';
import { useProductMutations } from '@/hooks/useProductMutations';
import { AppLayout } from '@/components/layout/AppLayout';
import { ProductsTable } from '@/components/products/ProductsTable';
import { ProductFilters } from '@/components/products/ProductFilters';
import { BulkActions } from '@/components/products/BulkActions';
import { Pagination } from '@/components/products/Pagination';
import { SearchInput } from '@/components/shared/SearchInput';
import { EmptyState } from '@/components/shared/EmptyState';
import { CsvImportDialog } from '@/components/csv-import/CsvImportDialog';
import { Button } from '@/components/ui/button';
import { Plus, FileUp } from 'lucide-react';
import { defaultFilters, type ProductFilters as FilterType, type SortState, type PaginationState } from '@/types/filters';
import { PAGE_SIZE } from '@/lib/constants';
import type { Product } from '@/types/product';

export default function ProductsPage() {
  const navigate = useNavigate();
  const [filters, setFilters] = useState<FilterType>(defaultFilters);
  const [sort, setSort] = useState<SortState>({ column: 'created_at', ascending: false });
  const [pagination, setPagination] = useState<PaginationState>({ page: 1, pageSize: PAGE_SIZE });
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [csvOpen, setCsvOpen] = useState(false);

  const { data, isLoading } = useProducts(filters, sort, pagination);
  const products = data?.data || [];
  const totalCount = data?.count || 0;
  const totalPages = Math.ceil(totalCount / PAGE_SIZE);

  const { toggle, remove, create, removeBulk, bulkToggle, bulkDiscount, inlineEdit } = useProductMutations();

  const handleFilterChange = useCallback((f: FilterType) => {
    setFilters(f);
    setPagination(p => ({ ...p, page: 1 }));
  }, []);

  const handleSearch = useCallback((search: string) => {
    setFilters(f => ({ ...f, search }));
    setPagination(p => ({ ...p, page: 1 }));
  }, []);

  const handleDuplicate = useCallback((p: Product) => {
    create.mutate({
      nombre: `${p.nombre} (copia)`,
      descripcion: p.descripcion,
      precio: p.precio,
      descuento_pct: p.descuento_pct,
      precio_descuento: p.precio_descuento,
      tipo_producto: p.tipo_producto,
      genero: p.genero,
      tipo_oro: p.tipo_oro,
      imagen: p.imagen,
      stock_total: 0,
      activo: false,
      destacado: false,
      external_id: null,
      created_by: null,
      updated_by: null,
    });
  }, [create]);

  return (
    <AppLayout>
      <div className="p-6 space-y-4 max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold">Productos</h1>
            <p className="text-sm text-muted-foreground">
              {totalCount} producto{totalCount !== 1 ? 's' : ''}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => setCsvOpen(true)}>
              <FileUp className="h-4 w-4 mr-1.5" /> Importar CSV
            </Button>
            <Button size="sm" onClick={() => navigate('/products/new')}>
              <Plus className="h-4 w-4 mr-1.5" /> Agregar producto
            </Button>
          </div>
        </div>

        {/* Search + Filters */}
        <div className="space-y-3">
          <div className="max-w-sm">
            <SearchInput value={filters.search} onChange={handleSearch} placeholder="Buscar productos..." />
          </div>
          <ProductFilters filters={filters} onChange={handleFilterChange} />
        </div>

        {/* Bulk actions */}
        <BulkActions
          count={selectedIds.length}
          onActivate={() => { bulkToggle.mutate({ ids: selectedIds, activo: true }); setSelectedIds([]); }}
          onDeactivate={() => { bulkToggle.mutate({ ids: selectedIds, activo: false }); setSelectedIds([]); }}
          onDiscount={(pct) => { bulkDiscount.mutate({ ids: selectedIds, pct }); setSelectedIds([]); }}
          onDelete={() => { removeBulk.mutate(selectedIds); setSelectedIds([]); }}
          onClear={() => setSelectedIds([])}
        />

        {/* Table or empty */}
        {!isLoading && products.length === 0 ? (
          filters.search || filters.estado !== 'todos' || filters.tipo_producto || filters.genero || filters.tipo_oro || filters.stock !== 'todos' ? (
            <EmptyState
              title="No se encontraron productos"
              description="No hay productos con estos filtros."
              actionLabel="Limpiar filtros"
              onAction={() => handleFilterChange(defaultFilters)}
            />
          ) : (
            <EmptyState
              title="No hay productos todavía"
              description="Agrega tu primer producto para empezar."
              actionLabel="Agregar producto"
              onAction={() => navigate('/products/new')}
            />
          )
        ) : (
          <ProductsTable
            products={products}
            loading={isLoading}
            sort={sort}
            onSortChange={setSort}
            selectedIds={selectedIds}
            onSelectionChange={setSelectedIds}
            onToggleActive={(id, current) => toggle.mutate({ id, current })}
            onDelete={(id) => remove.mutate(id)}
            onDuplicate={handleDuplicate}
            onInlineEdit={(id, field, value) => inlineEdit.mutate({ id, field, value })}
          />
        )}

        {/* Pagination */}
        <Pagination page={pagination.page} totalPages={totalPages} onPageChange={(p) => setPagination(prev => ({ ...prev, page: p }))} />
      </div>

      <CsvImportDialog open={csvOpen} onOpenChange={setCsvOpen} />
    </AppLayout>
  );
}
