import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Package, ShoppingCart, Tag, BarChart3, FolderOpen, Camera, ChevronLeft, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';

const navItems = [
  { icon: Package, label: 'Productos', href: '/', active: true },
  { icon: ShoppingCart, label: 'Pedidos', href: '#', soon: true },
  { icon: Tag, label: 'Cupones', href: '#', soon: true },
  { icon: BarChart3, label: 'Analytics', href: '#', soon: true },
  { icon: FolderOpen, label: 'Colecciones', href: '#', soon: true },
  { icon: Camera, label: 'Studio', href: '#', soon: true },
];

export function AppSidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();

  return (
    <aside
      className={cn(
        'flex flex-col border-r border-border bg-card transition-all duration-200 shrink-0',
        collapsed ? 'w-16' : 'w-60'
      )}
    >
      {/* Logo */}
      <div className="flex items-center gap-2 px-4 h-14 border-b border-border">
        <div className="w-8 h-8 rounded-md bg-primary flex items-center justify-center">
          <span className="text-primary-foreground font-bold text-sm">V</span>
        </div>
        {!collapsed && <span className="font-semibold text-sm tracking-tight">VALAC Joyas</span>}
      </div>

      {/* Nav */}
      <nav className="flex-1 py-3 px-2 space-y-1">
        {navItems.map((item) => {
          const isActive = item.href === '/' ? location.pathname === '/' : location.pathname.startsWith(item.href);
          const content = (
            <Link
              key={item.label}
              to={item.soon ? '#' : item.href}
              className={cn(
                'flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors',
                isActive
                  ? 'bg-accent text-accent-foreground font-medium'
                  : 'text-muted-foreground hover:bg-muted hover:text-foreground',
                item.soon && 'opacity-50 cursor-not-allowed'
              )}
              onClick={item.soon ? (e) => e.preventDefault() : undefined}
            >
              <item.icon className="h-4 w-4 shrink-0" />
              {!collapsed && <span>{item.label}</span>}
              {!collapsed && item.soon && (
                <span className="ml-auto text-[10px] bg-muted text-muted-foreground px-1.5 py-0.5 rounded">Pronto</span>
              )}
            </Link>
          );

          if (collapsed && item.soon) {
            return (
              <Tooltip key={item.label}>
                <TooltipTrigger asChild>{content}</TooltipTrigger>
                <TooltipContent side="right">Próximamente</TooltipContent>
              </Tooltip>
            );
          }
          if (collapsed) {
            return (
              <Tooltip key={item.label}>
                <TooltipTrigger asChild>{content}</TooltipTrigger>
                <TooltipContent side="right">{item.label}</TooltipContent>
              </Tooltip>
            );
          }
          return content;
        })}
      </nav>

      {/* Footer */}
      <div className="border-t border-border px-2 py-2 flex items-center justify-between">
        {!collapsed && <span className="text-[10px] text-muted-foreground px-2">v1.0 · VALAC Inventory</span>}
        <Button variant="ghost" size="icon" className="h-7 w-7 shrink-0" onClick={() => setCollapsed(!collapsed)}>
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </Button>
      </div>
    </aside>
  );
}
