import { useState, useCallback } from 'react';
import { parseCsvFile, importCsvRows, type CsvParseResult, type CsvRow } from '@/services/csv-import';
import { useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

type Step = 'upload' | 'preview' | 'importing' | 'done';

export function useCsvImport() {
  const qc = useQueryClient();
  const [step, setStep] = useState<Step>('upload');
  const [result, setResult] = useState<CsvParseResult | null>(null);
  const [progress, setProgress] = useState({ current: 0, total: 0 });
  const [importedIds, setImportedIds] = useState<number[]>([]);

  const parseFile = useCallback(async (file: File) => {
    try {
      const parsed = await parseCsvFile(file);
      setResult(parsed);
      setStep('preview');
    } catch {
      toast.error('Error al parsear CSV');
    }
  }, []);

  const startImport = useCallback(async () => {
    if (!result) return;
    setStep('importing');
    try {
      const ids = await importCsvRows(result.rows, (current, total) => {
        setProgress({ current, total });
      });
      setImportedIds(ids);
      setStep('done');
      qc.invalidateQueries({ queryKey: ['products'] });
      toast.success(`${ids.length} productos importados como borradores`);
    } catch {
      toast.error('Error durante la importación');
      setStep('preview');
    }
  }, [result, qc]);

  const reset = useCallback(() => {
    setStep('upload');
    setResult(null);
    setProgress({ current: 0, total: 0 });
    setImportedIds([]);
  }, []);

  return { step, result, progress, importedIds, parseFile, startImport, reset };
}
