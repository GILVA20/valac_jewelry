import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { useCsvImport } from '@/hooks/useCsvImport';
import { Upload, FileText, CheckCircle, AlertCircle } from 'lucide-react';
import { useCallback } from 'react';
import { cn } from '@/lib/utils';

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CsvImportDialog({ open, onOpenChange }: Props) {
  const { step, result, progress, importedIds, parseFile, startImport, reset } = useCsvImport();

  const handleClose = () => {
    onOpenChange(false);
    setTimeout(reset, 300);
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file?.name.endsWith('.csv')) parseFile(file);
  }, [parseFile]);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) parseFile(file);
  }, [parseFile]);

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Importar CSV</DialogTitle>
        </DialogHeader>

        {step === 'upload' && (
          <div
            onDrop={handleDrop}
            onDragOver={(e) => e.preventDefault()}
            className="border-2 border-dashed border-border rounded-lg p-12 text-center hover:border-primary/50 transition-colors"
          >
            <Upload className="h-10 w-10 text-muted-foreground mx-auto mb-3" />
            <p className="text-sm font-medium mb-1">Arrastra tu archivo CSV aquí</p>
            <p className="text-xs text-muted-foreground mb-4">o haz clic para seleccionar</p>
            <label>
              <input type="file" accept=".csv" className="hidden" onChange={handleFileSelect} />
              <Button variant="outline" size="sm" asChild>
                <span>Seleccionar archivo</span>
              </Button>
            </label>
            <p className="text-[10px] text-muted-foreground mt-4">
              Columnas esperadas: nombre, descripcion, precio, tipo_producto, genero, tipo_oro, imagen, stock_total
            </p>
          </div>
        )}

        {step === 'preview' && result && (
          <div className="space-y-4">
            <div className="flex gap-3">
              <div className="flex items-center gap-1.5 text-sm">
                <CheckCircle className="h-4 w-4 text-success" />
                <span>{result.validCount} válidos</span>
              </div>
              <div className="flex items-center gap-1.5 text-sm">
                <AlertCircle className="h-4 w-4 text-destructive" />
                <span>{result.errorCount} errores</span>
              </div>
            </div>

            <div className="border border-border rounded-md overflow-x-auto max-h-[300px] overflow-y-auto">
              <table className="w-full text-xs">
                <thead className="bg-muted/50 sticky top-0">
                  <tr>
                    <th className="p-2 text-left w-8">#</th>
                    {result.columns.slice(0, 6).map((c) => (
                      <th key={c} className="p-2 text-left">{c}</th>
                    ))}
                    <th className="p-2 text-left">Estado</th>
                  </tr>
                </thead>
                <tbody>
                  {result.rows.slice(0, 20).map((row) => (
                    <tr key={row.rowIndex} className={cn('border-t border-border', !row.valid && 'bg-destructive/5')}>
                      <td className="p-2 text-muted-foreground">{row.rowIndex + 1}</td>
                      {result.columns.slice(0, 6).map((c) => (
                        <td key={c} className="p-2 truncate max-w-[120px]">{row.raw[c]}</td>
                      ))}
                      <td className="p-2">
                        {row.valid ? (
                          <CheckCircle className="h-3.5 w-3.5 text-success" />
                        ) : (
                          <span className="text-destructive text-[10px]">{row.errors[0]}</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="flex gap-2 justify-end">
              <Button variant="outline" onClick={handleClose}>Cancelar</Button>
              <Button onClick={startImport} disabled={result.validCount === 0}>
                <FileText className="h-4 w-4 mr-2" />
                Importar {result.validCount} como borradores
              </Button>
            </div>
          </div>
        )}

        {step === 'importing' && (
          <div className="py-8 space-y-4 text-center">
            <p className="text-sm font-medium">Importando productos...</p>
            <Progress value={(progress.current / progress.total) * 100} className="h-2" />
            <p className="text-xs text-muted-foreground">{progress.current} de {progress.total}</p>
          </div>
        )}

        {step === 'done' && (
          <div className="py-8 text-center space-y-4">
            <CheckCircle className="h-12 w-12 text-success mx-auto" />
            <p className="text-sm font-medium">{importedIds.length} productos importados como borradores</p>
            <Button onClick={handleClose}>Cerrar</Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
