import { useQuery } from '@tanstack/react-query';
import { listProducts } from '@/services/products';
import type { ProductFilters, SortState, PaginationState } from '@/types/filters';

export function useProducts(filters: ProductFilters, sort: SortState, pagination: PaginationState) {
  return useQuery({
    queryKey: ['products', filters, sort, pagination],
    queryFn: () => listProducts(filters, sort, pagination),
    placeholderData: (prev) => prev,
  });
}
