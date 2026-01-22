// ========================================
// INLINE EDIT SCRIPT - External File
// ========================================

console.log('[INLINE-EDIT] ✅ Script externo CARGADO');

(function() {
  'use strict';
  
  function init() {
    console.log('[INLINE-EDIT] Función init() ejecutada');
    
    // ========================================
    // AGREGAR DINÁMICAMENTE atributos a celdas de NOMBRE
    // ========================================
    // Esto evita problemas de caché de Flask
    // La columna de nombre es la 3ª (<td>) en cada fila
    const rows = document.querySelectorAll('tbody tr');
    console.log('[INLINE-EDIT] Filas encontradas:', rows.length);
    
    rows.forEach((row, rowIdx) => {
      const cells = row.querySelectorAll('td');
      // Estructura: [checkbox, ID, Nombre, Stock, Precio, ...]
      if (cells.length >= 3) {
        const nombreCell = cells[2];
        const idCell = cells[1];
        const productId = idCell.textContent.trim();
        
        // Si la celda de nombre NO tiene data-editable, agregárselo
        if (!nombreCell.hasAttribute('data-editable')) {
          nombreCell.setAttribute('data-editable', 'true');
          nombreCell.setAttribute('data-field', 'nombre');
          nombreCell.setAttribute('data-id', productId);
          if (rowIdx < 3) {
            console.log('[INLINE-EDIT] Agregado data-editable a nombre fila', rowIdx, 'ID:', productId);
          }
        }
      }
    });
    
    // ========================================
    // BUSCAR CELDAS EDITABLES
    // ========================================
    const cells = document.querySelectorAll('[data-editable="true"]');
    console.log('[INLINE-EDIT] Celdas encontradas:', cells.length);
    
    if (cells.length === 0) {
      console.warn('[INLINE-EDIT] ❌ No hay celdas con data-editable="true"');
      return;
    }
    
    // Contar por tipo
    const byType = {};
    cells.forEach((cell) => {
      const field = cell.dataset.field;
      byType[field] = (byType[field] || 0) + 1;
    });
    console.log('[INLINE-EDIT] Por tipo:', byType);
    
    cells.forEach((cell, idx) => {
      console.log(`[INLINE-EDIT] Celda ${idx}:`, cell.dataset.field, cell.dataset.id);
      
      cell.style.cursor = 'pointer';
      cell.addEventListener('click', function(e) {
        console.log('[INLINE-EDIT] CLICK en:', this.dataset.field);
        handleCellClick.call(this, e);
      });
    });
  }
  
  function handleCellClick(e) {
    console.log('[INLINE-EDIT] Click detectado, target:', e.target.tagName, e.target.className);
    
    // Ignorar SOLO si hace clic en botones o inputs directos
    if (e.target.tagName === 'BUTTON' || e.target.tagName === 'INPUT') {
      console.log('[INLINE-EDIT] Clic en botón/input directo, ignorando');
      return;
    }
    
    // Ignorar si ya hay un input de edición abierto (sin atributo 'name')
    // Los inputs del formulario oculto tienen name="stock_total", etc.
    // Los inputs que creamos NO tienen atributo name
    if (this.querySelector('input:not([name])')) {
      console.log('[INLINE-EDIT] Ya en edición, ignorando');
      return;
    }
    
    // Proceder a editar (aunque haya un formulario oculto dentro)
    const field = this.dataset.field;
    const id = this.dataset.id;
    const span = this.querySelector('.current-value');
    const oldVal = span ? span.textContent.replace(/[$,%]/g, '').trim() : '';
    
    console.log('[INLINE-EDIT] Editando:', field, 'Valor:', oldVal);
    
    const input = document.createElement('input');
    input.type = field === 'nombre' ? 'text' : 'number';
    input.value = oldVal;
    if (field !== 'nombre') {
      input.min = '0';
      if (field === 'precio') input.step = '0.01';
      input.className = 'w-full bg-blue-50 border-b-2 border-blue-500 px-1 py-1 text-right rounded-sm font-semibold';
    } else {
      input.className = 'w-full bg-blue-50 border-b-2 border-blue-500 px-1 py-1 rounded-sm font-semibold';
    }
    
    // Ocultar span y form, mostrar input
    if (span) span.style.display = 'none';
    const form = this.querySelector('form');
    if (form) form.style.display = 'none';
    
    this.appendChild(input);
    input.focus();
    input.select();
    
    const cellRef = this; // Guardar referencia a la celda
    
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        console.log('[INLINE-EDIT] Enter presionado, guardando...');
        saveChange(cellRef, field, id, input.value, oldVal);
      } else if (e.key === 'Escape') {
        e.preventDefault();
        console.log('[INLINE-EDIT] Escape presionado, cancelando...');
        restoreCell(cellRef, field, oldVal);
      }
    });
    
    input.addEventListener('blur', () => {
      console.log('[INLINE-EDIT] Blur en input, guardando en 100ms...');
      setTimeout(() => saveChange(cellRef, field, id, input.value, oldVal), 100);
    });
  }
  
  function saveChange(cell, field, id, newVal, oldVal) {
    if (newVal.trim() === oldVal.trim()) {
      console.log('[INLINE-EDIT] Sin cambios');
      restoreCell(cell, field, oldVal);
      return;
    }
    
    let validated = newVal;
    
    // Validar según el tipo de campo
    if (field !== 'nombre') {
      const num = field === 'precio' ? parseFloat(newVal) : parseInt(newVal, 10);
      if (isNaN(num) || num < 0) {
        console.error('[INLINE-EDIT] Valor inválido:', newVal);
        alert('❌ Valor inválido');
        restoreCell(cell, field, oldVal);
        return;
      }
      validated = num;
    } else {
      // Para nombre, validar que no esté vacío
      if (!newVal.trim()) {
        console.error('[INLINE-EDIT] Nombre vacío');
        alert('❌ El nombre no puede estar vacío');
        restoreCell(cell, field, oldVal);
        return;
      }
      validated = newVal.trim();
    }
    
    cell.classList.add('opacity-60', 'pointer-events-none');
    
    const url = `/admin/supabase_products/api/quick-update/${id}`;
    console.log('[INLINE-EDIT] POST:', url, 'Value:', validated);
    
    fetch(url, {
      method: 'PATCH',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({field, value: validated})
    })
    .then(r => r.json())
    .then(data => {
      console.log('[INLINE-EDIT] Respuesta:', data);
      
      if (data.status === 'success') {
        // Guardar referencias al span y form ANTES de limpiar
        const span = cell.querySelector('.current-value');
        const form = cell.querySelector('form');
        const oldSpanContent = span ? span.textContent : '';
        
        // Limpiar COMPLETAMENTE el contenido de la celda
        cell.innerHTML = '';
        
        // Reconstruir con nuevo valor
        const display = field === 'precio' ? `$${data.new_value}` : data.new_value;
        const newSpan = document.createElement('span');
        newSpan.className = 'current-value';
        newSpan.textContent = display;
        cell.appendChild(newSpan);
        
        // Si había un formulario, restaurarlo
        if (form) {
          // Actualizar el valor del input del formulario también
          const formInput = form.querySelector('input[name]');
          if (formInput) {
            formInput.value = data.new_value;
          }
          form.style.display = 'none';
          cell.appendChild(form);
        }
        
        cell.classList.remove('opacity-60', 'pointer-events-none');
        cell.classList.add('bg-green-100');
        setTimeout(() => cell.classList.remove('bg-green-100'), 1500);
        console.log('[INLINE-EDIT] ✓ Guardado OK');
      } else {
        throw new Error(data.message || 'Error');
      }
    })
    .catch(err => {
      console.error('[INLINE-EDIT] Error:', err.message);
      cell.classList.remove('opacity-60', 'pointer-events-none');
      alert('❌ ' + err.message);
      restoreCell(cell, field, oldVal);
    });
  }
  
  function restoreCell(cell, field, oldVal) {
    const display = field === 'precio' ? `$${parseFloat(oldVal).toFixed(2)}` : oldVal;
    
    // Guardar referencias
    const form = cell.querySelector('form');
    
    // Limpiar COMPLETAMENTE
    cell.innerHTML = '';
    
    // Reconstruir span
    const span = document.createElement('span');
    span.className = 'current-value';
    span.textContent = display;
    cell.appendChild(span);
    
    // Restaurar form (si existe)
    if (form) {
      form.style.display = 'none';
      cell.appendChild(form);
    }
    
    cell.classList.remove('opacity-60', 'pointer-events-none');
  }
  
  // Esperar a que DOM esté listo
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
  
})();

console.log('[INLINE-EDIT] ✅ Script external listo');
