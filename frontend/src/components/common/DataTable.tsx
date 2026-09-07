import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
  type SortingState,
  type RowSelectionState,
} from '@tanstack/react-table';
import { useRef } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { ChevronUp, ChevronDown, ChevronsUpDown } from 'lucide-react';
import { LoadingSkeleton } from './LoadingSkeleton';
import { EmptyState } from './EmptyState';
import { Pagination } from './Pagination';
import { cn } from '../../lib/utils';

interface DataTableProps<TData> {
  data: TData[];
  columns: ColumnDef<TData, any>[];
  isLoading?: boolean;
  page?: number;
  pageCount?: number;
  total?: number;
  perPage?: number;
  onPageChange?: (page: number) => void;
  onPerPageChange?: (perPage: number) => void;
  sorting?: SortingState;
  onSortingChange?: (sorting: SortingState) => void;
  rowSelection?: RowSelectionState;
  onRowSelectionChange?: (selection: RowSelectionState) => void;
  onRowClick?: (row: TData) => void;
  emptyState?: React.ReactNode;
  showCheckboxes?: boolean;
  toolbar?: React.ReactNode;
  enableVirtualization?: boolean;
  tableHeight?: number;
  className?: string;
}

export function DataTable<TData>({
  data,
  columns,
  isLoading = false,
  page = 1,
  pageCount = 1,
  total,
  perPage = 20,
  onPageChange,
  onPerPageChange,
  sorting = [],
  onSortingChange,
  rowSelection = {},
  onRowSelectionChange,
  onRowClick,
  emptyState,
  showCheckboxes = false,
  toolbar,
  enableVirtualization = false,
  tableHeight = 600,
  className,
}: DataTableProps<TData>) {
  const table = useReactTable({
    data,
    columns,
    state: {
      sorting,
      rowSelection,
    },
    onSortingChange,
    onRowSelectionChange,
    getCoreRowModel: getCoreRowModel(),
    manualSorting: true,
    manualPagination: true,
    enableRowSelection: showCheckboxes,
  });

  const rows = table.getRowModel().rows;
  const parentRef = useRef<HTMLDivElement>(null);
  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 44,
    overscan: 10,
  });

  if (isLoading) {
    return <LoadingSkeleton rows={5} cols={columns.length} type="table" />;
  }

  if (data.length === 0) {
    return (
      emptyState || <EmptyState title="Нет данных" description="Измените параметры фильтрации или создайте новый элемент" />
    );
  }

  const renderThead = (sticky: boolean) => (
    <thead className={cn(sticky && 'sticky top-0 z-10')} >
      {table.getHeaderGroups().map((headerGroup) => (
        <tr key={headerGroup.id} className="bg-slate-50 border-b border-slate-200">
          {headerGroup.headers.map((header) => (
            <th
              key={header.id}
              className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider select-none"
              style={{ width: header.column.getSize() }}
              onClick={header.column.getCanSort() ? header.column.getToggleSortingHandler() : undefined}
            >
              <div className="flex items-center gap-1">
                {flexRender(header.column.columnDef.header, header.getContext())}
                {header.column.getCanSort() && (
                  <span className="text-slate-400">
                    {header.column.getIsSorted() === 'asc' ? <ChevronUp className="h-3.5 w-3.5" /> : header.column.getIsSorted() === 'desc' ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronsUpDown className="h-3.5 w-3.5 opacity-50" />}
                  </span>
                )}
              </div>
            </th>
          ))}
        </tr>
      ))}
    </thead>
  );

  if (enableVirtualization) {
    return (
      <div className={cn('rounded-lg border border-slate-200 overflow-hidden bg-white', className)}>
        {toolbar && <div className="border-b border-slate-200 bg-slate-50 p-3">{toolbar}</div>}
        <div ref={parentRef} className="overflow-auto" style={{ height: `${tableHeight}px` }}>
          <table className="w-full text-sm" style={{ tableLayout: 'fixed', minWidth: `${table.getAllColumns().reduce((sum, c) => sum + c.getSize(), 0)}px` }}>
            <colgroup>
              {table.getAllColumns().map((col) => (
                <col key={col.id} style={{ width: col.getSize(), minWidth: col.getSize() }} />
              ))}
            </colgroup>
            {renderThead(true)}
            <tbody style={{ height: `${virtualizer.getTotalSize()}px`, position: 'relative' }}>
              {virtualizer.getVirtualItems().map((virtualRow) => {
                const row = rows[virtualRow.index];
                return (
                  <tr
                    key={row.id}
                    className={cn('absolute left-0 w-full border-b border-slate-100 transition-colors', onRowClick && 'cursor-pointer hover:bg-slate-50', row.getIsSelected() && 'bg-blue-50/50')}
                    style={{ height: `${virtualRow.size}px`, transform: `translateY(${virtualRow.start}px)` }}
                    onClick={() => onRowClick?.(row.original)}
                  >
                    {row.getVisibleCells().map((cell) => (
                      <td key={cell.id} className="px-4 py-3" style={{ width: cell.column.getSize() }}>
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    ))}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {total !== undefined && onPageChange && (
          <Pagination page={page} pageCount={pageCount} total={total} perPage={perPage} onPageChange={onPageChange} onPerPageChange={onPerPageChange || (() => {})} />
        )}
      </div>
    );
  }

  return (
    <div className={cn('rounded-lg border border-slate-200 overflow-hidden bg-white', className)}>
      {toolbar && <div className="border-b border-slate-200 bg-slate-50 p-3">{toolbar}</div>}
      <div className="overflow-x-auto">
        <table className="w-full text-sm" style={{ tableLayout: 'fixed', minWidth: `${table.getAllColumns().reduce((sum, c) => sum + c.getSize(), 0)}px` }}>
          <colgroup>
            {table.getAllColumns().map((col) => (
              <col key={col.id} style={{ width: col.getSize(), minWidth: col.getSize() }} />
            ))}
          </colgroup>
          {renderThead(false)}
          <tbody>
            {rows.map((row) => (
              <tr
                key={row.id}
                className={cn('border-b border-slate-100 transition-colors', onRowClick && 'cursor-pointer hover:bg-slate-50', row.getIsSelected() && 'bg-blue-50/50')}
                onClick={() => onRowClick?.(row.original)}
              >
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} className="px-4 py-3" style={{ width: cell.column.getSize() }}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {total !== undefined && onPageChange && (
        <Pagination page={page} pageCount={pageCount} total={total} perPage={perPage} onPageChange={onPageChange} onPerPageChange={onPerPageChange || (() => {})} />
      )}
    </div>
  );
}