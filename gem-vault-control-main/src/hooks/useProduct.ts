import { useQuery } from '@tanstack/react-query';
import { getProduct } from '@/services/products';

export function useProduct(id: number | undefined) {
  return useQuery({
    queryKey: ['product', id],
    queryFn: () => getProduct(id!),
    enabled: !!id,
  });
}
