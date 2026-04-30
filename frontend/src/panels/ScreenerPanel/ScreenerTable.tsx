import * as React from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";
import { MetricCell } from "@/components/MetricCell";
import { ScoreBadge } from "@/components/ScoreBadge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { CompanyRow } from "@/hooks";
import { cn } from "@/lib/utils";

type SortDirection = "asc" | "desc";
type SortableColumnKey =
  | "ticker"
  | "name"
  | "total_score"
  | "sector"
  | "market_cap"
  | "pe_ratio"
  | "ev_ebitda"
  | "roe"
  | "revenue_growth"
  | "net_debt_to_ebitda";

interface SortState {
  key: SortableColumnKey;
  direction: SortDirection;
}

interface ScreenerTableProps {
  rows: CompanyRow[];
  activeTicker: string | null;
  panelFocused: boolean;
  onSelectTicker: (ticker: string | null) => void;
}

const DEFAULT_SORT: SortState = {
  key: "total_score",
  direction: "desc",
};

const VIRTUALIZATION_THRESHOLD = 200;

const COLUMN_LABELS: Record<SortableColumnKey, string> = {
  ticker: "Ticker",
  name: "Name",
  total_score: "Score",
  sector: "Sector",
  market_cap: "Market Cap",
  pe_ratio: "P/E",
  ev_ebitda: "EV/EBITDA",
  roe: "ROE",
  revenue_growth: "Rev Growth",
  net_debt_to_ebitda: "Net Debt/EBITDA",
};

function sortRows(rows: CompanyRow[], sort: SortState): CompanyRow[] {
  const sorted = [...rows];
  sorted.sort((left, right) => {
    const leftValue = left[sort.key];
    const rightValue = right[sort.key];

    if (leftValue === null && rightValue === null) {
      return 0;
    }
    if (leftValue === null) {
      return 1;
    }
    if (rightValue === null) {
      return -1;
    }

    if (typeof leftValue === "number" && typeof rightValue === "number") {
      return sort.direction === "asc" ? leftValue - rightValue : rightValue - leftValue;
    }

    const leftText = String(leftValue).toLowerCase();
    const rightText = String(rightValue).toLowerCase();
    if (leftText < rightText) {
      return sort.direction === "asc" ? -1 : 1;
    }
    if (leftText > rightText) {
      return sort.direction === "asc" ? 1 : -1;
    }
    return 0;
  });
  return sorted;
}

function SortIcon({ state, column }: { state: SortState; column: SortableColumnKey }) {
  if (state.key !== column) {
    return <ArrowUpDown className="h-3 w-3" />;
  }
  return state.direction === "asc" ? (
    <ArrowUp className="h-3 w-3" />
  ) : (
    <ArrowDown className="h-3 w-3" />
  );
}

function findNextTicker(
  rows: CompanyRow[],
  activeTicker: string | null,
  direction: 1 | -1,
): string | null {
  if (rows.length === 0) {
    return null;
  }

  const currentIndex = rows.findIndex((row) => row.ticker !== null && row.ticker === activeTicker);
  const fallbackIndex = direction === 1 ? 0 : rows.length - 1;
  const targetIndex = currentIndex < 0 ? fallbackIndex : Math.max(0, Math.min(rows.length - 1, currentIndex + direction));
  const row = rows[targetIndex];
  return row?.ticker ?? null;
}

function renderDataRow(
  row: CompanyRow,
  activeTicker: string | null,
  onSelectTicker: (ticker: string | null) => void,
  style?: React.CSSProperties,
) {
  const ticker = row.ticker;
  const isActive = ticker !== null && ticker === activeTicker;

  return (
    <TableRow
      key={row.company_id}
      style={style}
      className={cn(
        "cursor-pointer hover:bg-[var(--color-bg-elevated)]",
        isActive && "bg-[var(--color-accent)]/15",
      )}
      onClick={() => onSelectTicker(ticker)}
    >
      <TableCell className="font-mono text-xs text-[var(--color-text-primary)]">{ticker ?? "—"}</TableCell>
      <TableCell className="truncate text-xs text-[var(--color-text-primary)]">{row.name}</TableCell>
      <TableCell>
        <ScoreBadge score={row.total_score} />
      </TableCell>
      <TableCell className="text-xs text-[var(--color-text-muted)]">{row.sector ?? "—"}</TableCell>
      <TableCell>
        <MetricCell value={row.market_cap} type="market_cap" format="currency" />
      </TableCell>
      <TableCell>
        <MetricCell value={row.pe_ratio} type="pe_ratio" format="ratio" />
      </TableCell>
      <TableCell>
        <MetricCell value={row.ev_ebitda} type="ev_ebitda" format="ratio" />
      </TableCell>
      <TableCell>
        <MetricCell value={row.roe} type="roe" format="percent" />
      </TableCell>
      <TableCell>
        <MetricCell value={row.revenue_growth} type="revenue_growth" format="percent" />
      </TableCell>
      <TableCell>
        <MetricCell value={row.net_debt_to_ebitda} type="net_debt_to_ebitda" format="ratio" />
      </TableCell>
    </TableRow>
  );
}

export function ScreenerTable({ rows, activeTicker, panelFocused, onSelectTicker }: ScreenerTableProps) {
  const [sortState, setSortState] = React.useState<SortState>(DEFAULT_SORT);
  const sortedRows = React.useMemo(() => sortRows(rows, sortState), [rows, sortState]);
  const virtualized = sortedRows.length > VIRTUALIZATION_THRESHOLD;
  const scrollRef = React.useRef<HTMLDivElement | null>(null);

  const rowVirtualizer = useVirtualizer({
    count: virtualized ? sortedRows.length : 0,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => 38,
    overscan: 8,
  });

  React.useEffect(() => {
    const onNavigateRows = (event: Event) => {
      if (!panelFocused) {
        return;
      }
      const detail = (event as CustomEvent<{ panel: string | null; direction: 1 | -1 }>).detail;
      if (detail.panel !== "screener") {
        return;
      }
      const ticker = findNextTicker(sortedRows, activeTicker, detail.direction);
      if (ticker) {
        onSelectTicker(ticker);
      }
    };

    const onOpenSelected = (event: Event) => {
      if (!panelFocused) {
        return;
      }
      const detail = (event as CustomEvent<{ panel: string | null }>).detail;
      if (detail.panel !== "screener") {
        return;
      }
      if (activeTicker) {
        onSelectTicker(activeTicker);
      }
    };

    window.addEventListener("workspace:navigate-rows", onNavigateRows);
    window.addEventListener("workspace:open-selected", onOpenSelected);
    return () => {
      window.removeEventListener("workspace:navigate-rows", onNavigateRows);
      window.removeEventListener("workspace:open-selected", onOpenSelected);
    };
  }, [activeTicker, onSelectTicker, panelFocused, sortedRows]);

  const handleSort = (column: SortableColumnKey) => {
    setSortState((current) => {
      if (current.key === column) {
        return {
          key: column,
          direction: current.direction === "asc" ? "desc" : "asc",
        };
      }
      return {
        key: column,
        direction: column === "name" || column === "ticker" || column === "sector" ? "asc" : "desc",
      };
    });
  };

  return (
    <div ref={scrollRef} className="h-full overflow-auto">
      <Table className="table-fixed">
        <TableHeader>
          <TableRow>
            {(Object.keys(COLUMN_LABELS) as SortableColumnKey[]).map((column) => (
              <TableHead key={column}>
                <button
                  type="button"
                  className="inline-flex items-center gap-1 font-mono text-[11px] uppercase"
                  onClick={() => handleSort(column)}
                >
                  {COLUMN_LABELS[column]}
                  <SortIcon state={sortState} column={column} />
                </button>
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody
          style={
            virtualized
              ? {
                  display: "grid",
                  height: `${rowVirtualizer.getTotalSize()}px`,
                  position: "relative",
                }
              : undefined
          }
        >
          {sortedRows.length === 0 ? (
            <TableRow>
              <TableCell colSpan={10} className="py-6 text-center font-mono text-sm text-[var(--color-text-muted)]">
                No companies match current filters.
              </TableCell>
            </TableRow>
          ) : virtualized ? (
            rowVirtualizer.getVirtualItems().map((virtualItem) => {
              const row = sortedRows[virtualItem.index];
              if (!row) {
                return null;
              }
              return renderDataRow(row, activeTicker, onSelectTicker, {
                position: "absolute",
                top: 0,
                left: 0,
                width: "100%",
                transform: `translateY(${virtualItem.start}px)`,
              });
            })
          ) : (
            sortedRows.map((row) => renderDataRow(row, activeTicker, onSelectTicker))
          )}
        </TableBody>
      </Table>
    </div>
  );
}
